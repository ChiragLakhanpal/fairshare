import http from "node:http";
import type { AddressInfo } from "node:net";
import { expect, test, type Page } from "@playwright/test";

const me = {
  email: "dana@example.com", user: "dana", inside_app: true, scopes: ["sql", "genie", "model-serving"], backend: "databricks", model: "databricks/x",
  genie: null, data_through: "2026-09", regions: ["All", "Central", "East", "West"], months: ["2026-09", "2026-08"], links: {},
};
const summary = {
  region: "All", month: "2026-09", prior_month: "2025-09", headline: "September closed ahead of pace and a little under fair share.",
  kpis: { aa_revenue: 4492373, aa_revenue_prior_year: 4456241, yoy_pct: 0.8, aa_share_pct: 37.8, fair_share_pct: 39.0, share_gap_pts: -1.2, share_gap_usd: -143384, pace_pct: 139.1 },
  movers: [{ agency_id: 5, agency: "Harbor Business Travel", region: "East", share_now_pct: 34.2, share_prior_pct: 44.3, share_chg_pts: -10.1, revenue_now: 330114, yoy_pct: -16.4 }],
  behind_pace: [{ agency_id: 5, agency: "Harbor Business Travel", pace_pct: 96.1, aa_revenue: 330114, yoy_pct: -16.4 }], calls: [], agency_count: 4,
};
// What the home page says is worth knowing: one line about an agency (its action opens Delegate) and one about the network (its action asks).
const signals = {
  region: "All", month: "2026-09",
  signals: [
    { kind: "clause", severity: "watch", agency: "Harbor Business Travel", chip: "What does Harbor Business Travel's agreement say about its revenue commitment?",
      sentence: { text: "Harbor Business Travel is at 96.1% of its revenue commitment, with $46K of advanced incentive at risk.", status: "verified",
        numbers: [{ raw: "96.1%", source: "signals#1", fact: "value_pct=96.1" }, { raw: "$46K", source: "signals#1", fact: "dollars=46357.0" }] },
      action: { kind: "delegate", agent: "watch", label: "Open Agreement watch" } },
    { kind: "capacity", severity: "watch", agency: null, chip: "How did AA's seats on ORD-SFO change against last year?",
      sentence: { text: "AA cut seats 4.4% on ORD-SFO against last September, and fair share there fell 1.3 points, the largest capacity move this month.", status: "verified",
        numbers: [{ raw: "4.4%", source: "signals#2", fact: "seats_yoy_pct=-4.4" }, { raw: "1.4 points", source: "signals#2", fact: "fair_chg_pts=-1.3" }] },
      action: { kind: "ask", question: "How did AA's seats on ORD-SFO change against last year?", label: "Ask about the market" } },
  ],
  calls: [
    { i: 1, tool: "signals", args: { block: "agreement checks", table: "ops.agreement_checks" }, sql: "SELECT 1", rows: 1, note: "", preview: [{ agency_name: "Harbor Business Travel", value_pct: 96.1, dollars: 46357 }], genie: null, ms: 0 },
    { i: 2, tool: "signals", args: { block: "capacity moves", table: "gold.fact_market_capacity" }, sql: "SELECT 2", rows: 1, note: "", preview: [{ market: "ORD-SFO", seats_yoy_pct: -4.4, fair_chg_pts: -1.3 }], genie: null, ms: 0 },
  ],
};
const catalog = {
  agents: [{ key: "watch", name: "Agreement watch", summary: "", one_liner: "", cadence: "", steps: [], reads: [], writes: [], approver: "", scope_kind: "region", last_run: null, waiting: 2, running: null, pages: [] }],
  managers: [], markets: [], crm_label: "the CRM stand-in",
};
const allRemoved = [
  'id: 1\nevent: status\ndata: {"type":"status","phase":"model","text":"I am reading your question and choosing the query.","t_ms":0}\n\n',
  'id: 2\nevent: answer\ndata: {"question":"q","text":"Harbor sold $999K. Source: ask_metrics.","model":"x","kind":"numbers","sentences":[{"text":"Harbor sold $999K.","status":"flagged","numbers":[{"raw":"$999K","source":null,"fact":null}]},{"text":"Source: ask_metrics.","status":"note","numbers":[]}],"removed":[{"sentence":"Harbor sold $999K.","reason":"no query supports $999K"}],"could_not_verify":[],"verified_text":"Source: ask_metrics.","calls":[],"sources":[],"follow_ups":[],"genie_conversation_id":null,"timing":{"total_ms":1,"tools_ms":0},"cached":null,"trace_url":null}\n\n',
  'id: 3\nevent: done\ndata: {"t_ms":2}\n\n',
].join("");
const startEvent = 'id: 1\nevent: status\ndata: {"type":"status","phase":"model","text":"I am reading your question and choosing the query.","t_ms":0}\n\n';
const sqlEvent = 'id: 2\nevent: status\ndata: {"type":"status","phase":"sql","tool":"run_sql","args":{"sql":"SELECT agency_name\\nFROM aa_demo.gold.sales_metrics"},"text":"I am running a query on your data.","t_ms":10}\n\n';
const answerEvent = 'id: 3\nevent: answer\ndata: {"question":"Why is Harbor down this month?","text":"Harbor sold $330K, down 16.4%.","model":"x","kind":"numbers","sentences":[{"text":"Harbor sold $330K, down 16.4%.","status":"verified","numbers":[{"raw":"$330K","source":"run_sql#1","fact":"330114"},{"raw":"16.4%","source":"run_sql#1","fact":"-16.4"}]}],"removed":[],"could_not_verify":[],"verified_text":"Harbor sold $330K, down 16.4%.","calls":[{"i":1,"tool":"run_sql","args":{},"sql":"SELECT 1","rows":1,"note":"","preview":[{"aa_revenue":330114}],"genie":null,"ms":12}],"sources":["SQL"],"follow_ups":["Why did this change?"],"genie_conversation_id":null,"timing":{"total_ms":40,"tools_ms":12},"cached":null,"trace_url":null}\n\n';
const doneEvent = 'id: 4\nevent: done\ndata: {"t_ms":41}\n\n';
const sse = startEvent + sqlEvent + answerEvent + doneEvent;

// A real stream for the in-flight tests: the status events first, the answer seconds later (route.fulfill sends everything at once).
let slow: http.Server;
let slowUrl = "";
test.beforeAll(async () => {
  slow = http.createServer((_req, res) => {
    res.writeHead(200, { "content-type": "text/event-stream", "cache-control": "no-store" });
    res.write(startEvent);
    setTimeout(() => res.write(sqlEvent), 500);
    setTimeout(() => res.end(answerEvent + doneEvent), 5000);
  });
  await new Promise<void>((r) => slow.listen(0, "127.0.0.1", r));
  slowUrl = `http://127.0.0.1:${(slow.address() as AddressInfo).port}/ask`;
});
test.afterAll(() => slow.close());

async function mock(page: Page) {
  await page.route("**/api/me", (r) => r.fulfill({ json: me }));
  await page.route("**/api/summary**", (r) => r.fulfill({ json: summary }));
  await page.route("**/api/signals**", (r) => r.fulfill({ json: signals }));
  await page.route("**/api/agents", (r) => r.fulfill({ json: catalog }));
  await page.route("**/api/definitions", (r) => r.fulfill({ json: { kpis: [{ kpi: "fair_share", display_name: "Fair share", definition_en: "The exact wording.", metric_view_expr: "SUM(x)", dax_twin: "", twin_sql: "" }], parity: { run_id: "a", run_at: "2026-10-12T07:49:32", kpis: 6, rows: 1500, drift: 0, grid: {}, by_kpi: { fair_share: { rows: 250, drift: 0 } }, drifting: [], source: "csv" }, runs: [] } }));
  await page.route("**/api/ask", (r) => r.fulfill({ status: 200, headers: { "content-type": "text/event-stream" }, body: sse }));
}

test("the summary is the first screen and folds into the strip on send", async ({ page }) => {
  await mock(page);
  await page.goto("/");
  await expect(page.getByRole("heading", { name: summary.headline })).toBeVisible();
  await expect(page.getByText("$4.49M")).toBeVisible();
  await expect(page.getByText("37.8%", { exact: true })).toBeVisible();
  await expect(page.getByText(/One agency is behind pace: Harbor Business Travel at 96.1%. The other 3 are ahead./)).toBeVisible();
  await expect(page.getByText("That is $143K below fair share.")).toBeVisible();
  await page.getByLabel("Ask a question").fill("Why is Harbor down this month?");
  await page.keyboard.press("Enter");
  const strip = page.getByRole("button", { name: /Show the summary/ });
  await expect(strip).toBeVisible();
  await expect(strip).toHaveAttribute("aria-expanded", "false");
  await expect(page.getByText("Harbor sold $330K, down 16.4%.")).toBeVisible();
  await expect(page.getByText("All 2 numbers in this answer came from the query results.")).toBeVisible();
  await page.getByRole("button", { name: "Show the query" }).click();
  await expect(page.locator("pre.sql")).toHaveText("SELECT 1");
  await strip.click();
  await expect(page.getByRole("button", { name: /Hide the summary/ })).toHaveAttribute("aria-expanded", "true");
  await expect(page.getByRole("heading", { name: summary.headline })).toBeVisible();
  await page.keyboard.press("Escape");
  await expect(page.getByRole("button", { name: /Show the summary/ })).toBeVisible();
});

test("the sidebar collapse is remembered and the definition window opens and closes", async ({ page }) => {
  await mock(page);
  await page.goto("/");
  await page.getByRole("button", { name: "Collapse the sidebar" }).click();
  await expect(page.getByRole("navigation", { name: "Sidebar, collapsed" })).toBeVisible();
  await page.reload();
  await expect(page.getByRole("navigation", { name: "Sidebar, collapsed" })).toBeVisible();
  await page.getByRole("button", { name: "Fair share", exact: true }).click();
  const dialog = page.getByRole("dialog", { name: "Fair share" });
  await expect(dialog).toContainText("Fair share is AA's share of the scheduled seats");
  await expect(dialog).toContainText("A SQL copy of the Power BI measure was checked against this definition on October 12, and all 250 values matched.");
  await page.keyboard.press("Escape");
  await expect(dialog).toBeHidden();
  // pace has no twin, so the mock has no entry for it: the definition shows and the check line does not
  await page.getByRole("button", { name: "Pace to goal", exact: true }).click();
  const pace = page.getByRole("dialog");
  await expect(pace).toContainText("Pace is year-to-date AA revenue");
  await expect(pace).not.toContainText("Power BI");
  await page.keyboard.press("Escape");
  await expect(pace).toBeHidden();
});

test("an answer whose every numeric sentence was removed says so", async ({ page }) => {
  await mock(page);
  await page.route("**/api/ask", (r) => r.fulfill({ status: 200, headers: { "content-type": "text/event-stream" }, body: allRemoved }));
  await page.goto("/");
  await page.getByLabel("Ask a question").fill("q");
  await page.keyboard.press("Enter");
  await expect(page.getByText(/I could not show this answer/)).toBeVisible();
  await expect(page.getByText("I removed one sentence before showing you this answer.")).toBeVisible();
  await expect(page.getByText("Source: ask_metrics.")).toBeHidden();
});

test("save as a PDF prints only the answer", async ({ page }) => {
  await mock(page);
  await page.goto("/");
  await page.evaluate(() => { (window as unknown as { print: () => void }).print = () => {}; });
  await page.getByLabel("Ask a question").fill("Why is Harbor down this month?");
  await page.keyboard.press("Enter");
  await expect(page.getByText("Harbor sold $330K, down 16.4%.")).toBeVisible();
  await page.getByRole("button", { name: "More actions for this answer" }).click();
  await page.getByRole("menuitem", { name: "Save as a PDF" }).click();
  await page.emulateMedia({ media: "print" });
  await expect(page.locator(".print-target")).toBeVisible();
  await expect(page.locator(".print-target").getByText("Harbor sold $330K, down 16.4%.")).toBeVisible();
  await expect(page.getByRole("navigation", { name: "Sidebar" })).toBeHidden();
});

test("the sidebar fills the window and carries the AA lockup and the product name", async ({ page }) => {
  await mock(page);
  await page.goto("/");
  await expect(page).toHaveTitle("Fairshare");
  const nav = page.getByRole("navigation", { name: "Sidebar" });
  expect((await nav.boundingBox())!.height).toBe(900);
  await expect(nav.getByRole("img", { name: "American Airlines" })).toBeVisible();
  await expect(nav.getByText("Fairshare", { exact: true })).toBeVisible();
  await expect(nav.getByText("fairshare, agency sales")).toHaveCount(0);
  await page.getByRole("button", { name: "Collapse the sidebar" }).click();
  await expect(page.getByRole("navigation", { name: "Sidebar, collapsed" }).getByRole("img", { name: "American Airlines" })).toBeVisible();
});

test("the first screen greets by the time of day", async ({ page }) => {
  await mock(page);
  await page.goto("/");
  await expect(page.getByText(/^Good (morning|afternoon|evening)\. /)).toBeVisible();
});

test("copying the summary confirms and writes structured text", async ({ page, context }) => {
  await context.grantPermissions(["clipboard-read", "clipboard-write"]);
  await mock(page);
  await page.goto("/");
  await page.getByRole("button", { name: "Share this summary" }).click();
  await page.getByRole("menuitem", { name: "Copy as text" }).click();
  await expect(page.getByRole("status")).toHaveText("Copied.");
  const text = await page.evaluate(() => navigator.clipboard.readText());
  expect(text.split("\n")).toContain("AA revenue: $4.49M, up 0.8% from September 2025.");
  expect(text).toContain("\n• Harbor Business Travel lost 10.1 points of share");
});

test("while an answer is in flight the steps show their workings and a running clock", async ({ page }) => {
  await mock(page);
  await page.route("**/api/ask", (r) => r.continue({ url: slowUrl }));
  await page.goto("/");
  await page.getByLabel("Ask a question").fill("Why is Harbor down this month?");
  await page.keyboard.press("Enter");
  await expect(page.getByText("I am reading your question and choosing the query.")).toBeVisible();
  // the question moves to the top of the view, under the strip, so the answer reads from its question down
  const bubble = page.locator("section").getByText("Why is Harbor down this month?", { exact: true });
  await expect(page.getByRole("button", { name: /Show the summary/ })).toBeVisible();
  await page.waitForTimeout(700); // the summary has finished folding, so the page is as short as it gets
  expect((await bubble.boundingBox())!.y).toBeLessThan(140);
  await expect(page.getByText("I am running a query on your data.")).toBeVisible();
  await expect(page.getByText("SELECT agency_name …")).toBeVisible();
  await expect(page.getByText(/^[2-9] s$/)).toBeVisible();
  await expect(page.getByText("Harbor sold $330K, down 16.4%.")).toBeVisible({ timeout: 10_000 });
  await expect(page.getByText("I am running a query on your data.")).toHaveCount(0);
});

test("the first screen says what is worth knowing, suggests questions from it, and a line's action asks", async ({ page }) => {
  await mock(page);
  await page.goto("/");
  await expect(page.getByText("Two pages wait for your decision in Delegate.")).toBeVisible();
  await expect(page.getByRole("heading", { name: "Worth knowing this month" })).toBeVisible();
  await expect(page.getByText(/Harbor Business Travel is at 96\.1% of its revenue commitment/)).toBeVisible();
  // the chips come from the signals while a model is connected
  await expect(page.getByRole("button", { name: "What does Harbor Business Travel's agreement say about its revenue commitment?" })).toBeVisible();
  // a checked number says what it is and where it came from (the webfont arriving reflows the line, so wait for it before hovering)
  await page.evaluate(() => document.fonts.ready);
  await page.getByText("$46K", { exact: true }).hover();
  await expect(page.getByRole("tooltip")).toContainText('It came from "agreement checks", which read ops.agreement_checks.');
  // a line's action sends its question; the answer about Harbor carries the related line about Harbor
  await page.getByRole("button", { name: "Ask about the market" }).click();
  await expect(page.locator("section").getByText("How did AA's seats on ORD-SFO change against last year?", { exact: true })).toBeVisible();
  await expect(page.getByText("Harbor sold $330K, down 16.4%.")).toBeVisible();
  await expect(page.getByText(/Worth knowing for September 2026: Harbor Business Travel is at 96\.1%/)).toBeVisible();
});

test("loading is a skeleton, not a line of text, and the mode switch lands on the Delegate overview", async ({ page }) => {
  await mock(page);
  const wait = (ms: number) => new Promise((r) => setTimeout(r, ms));
  await page.route("**/api/summary**", async (r) => { await wait(1200); await r.fulfill({ json: summary }); });
  await page.route("**/api/agents", async (r) => { await wait(2500); await r.fulfill({ json: catalog }); });
  await page.goto("/");
  const busy = page.locator('[aria-busy="true"]');
  await expect(busy.first()).toBeVisible();
  await expect(page.getByRole("heading", { name: summary.headline })).toBeVisible({ timeout: 5000 });
  await expect(page.getByRole("heading", { name: "Worth knowing this month" })).toBeVisible();
  await page.getByRole("button", { name: "Delegate", exact: true }).click();
  await expect(page.getByRole("button", { name: "Delegate", exact: true })).toHaveAttribute("aria-pressed", "true");
  await expect(busy.first()).toBeVisible();
  await expect(page.getByText("Loading the agents.")).toHaveCount(0);
  await expect(page.getByRole("heading", { name: "Overview" })).toBeVisible({ timeout: 5000 });
  await expect(page.getByRole("button", { name: /Agreement watch/ }).first()).toBeVisible();
  await expect(busy).toHaveCount(0);
});

test("an answer types itself out, and its checks and buttons appear once it has", async ({ page }) => {
  await mock(page);
  await page.goto("/");
  await page.getByLabel("Ask a question").fill("Why is Harbor down this month?");
  await page.keyboard.press("Enter");
  await expect(page.locator(".caret")).toBeVisible();
  await expect(page.getByRole("button", { name: "Show the query" })).toHaveCount(0);
  await expect(page.getByText("Harbor sold $330K, down 16.4%.")).toBeVisible();
  await expect(page.locator(".caret")).toHaveCount(0);
  await expect(page.getByRole("button", { name: "Show the query" })).toBeVisible();
});
