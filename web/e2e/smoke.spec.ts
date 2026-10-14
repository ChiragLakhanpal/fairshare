import { expect, test, type Page } from "@playwright/test";

const me = {
  email: "dana@example.com", user: "dana", inside_app: true, scopes: ["sql", "genie", "model-serving"], backend: "databricks", model: "databricks/x",
  genie: null, data_through: "2026-09", regions: ["All", "Central", "East", "West"], months: ["2026-09", "2026-08"], links: {},
};
const summary = {
  region: "All", month: "2026-09", prior_month: "2025-09", headline: "September closed ahead of pace and a little under fair share.",
  kpis: { aa_revenue: 4492373, aa_revenue_prior_year: 4456241, yoy_pct: 0.8, aa_share_pct: 37.8, fair_share_pct: 39.0, share_gap_pts: -1.2, share_gap_usd: -143384, pace_pct: 139.1 },
  movers: [{ agency_id: 5, agency: "Harbor Business Travel", region: "East", share_now_pct: 34.2, share_prior_pct: 44.3, share_chg_pts: -10.1, revenue_now: 330114, yoy_pct: -16.4 }],
  behind_pace: [{ agency_id: 5, agency: "Harbor Business Travel", pace_pct: 96.1, aa_revenue: 330114, yoy_pct: -16.4 }], calls: [],
};
const sse = [
  'id: 1\nevent: status\ndata: {"type":"status","phase":"model","text":"I am writing the answer.","t_ms":0}\n\n',
  'id: 2\nevent: status\ndata: {"type":"status","phase":"sql","text":"I am running a query on your data.","t_ms":10}\n\n',
  'id: 3\nevent: answer\ndata: {"question":"Why is Harbor down this month?","text":"Harbor sold $330K, down 16.4%.","model":"x","kind":"numbers","sentences":[{"text":"Harbor sold $330K, down 16.4%.","status":"verified","numbers":[{"raw":"$330K","source":"run_sql#1","fact":"330114"},{"raw":"16.4%","source":"run_sql#1","fact":"-16.4"}]}],"removed":[],"could_not_verify":[],"verified_text":"Harbor sold $330K, down 16.4%.","calls":[{"i":1,"tool":"run_sql","args":{},"sql":"SELECT 1","rows":1,"note":"","preview":[{"aa_revenue":330114}],"genie":null,"ms":12}],"sources":["SQL"],"follow_ups":["Why did this change?"],"genie_conversation_id":null,"timing":{"total_ms":40,"tools_ms":12},"cached":null,"trace_url":null}\n\n',
  'id: 4\nevent: done\ndata: {"t_ms":41}\n\n',
].join("");

async function mock(page: Page) {
  await page.route("**/api/me", (r) => r.fulfill({ json: me }));
  await page.route("**/api/summary**", (r) => r.fulfill({ json: summary }));
  await page.route("**/api/definitions", (r) => r.fulfill({ json: { kpis: [{ kpi: "fair_share", display_name: "Fair share", definition_en: "The exact wording.", metric_view_expr: "SUM(x)", dax_twin: "", twin_sql: "" }], parity: { run_id: "a", run_at: "2026-10-12T07:49:32", kpis: 6, rows: 1500, drift: 0, grid: {}, drifting: [], source: "csv" }, runs: [] } }));
  await page.route("**/api/ask", (r) => r.fulfill({ status: 200, headers: { "content-type": "text/event-stream" }, body: sse }));
}

test("the summary is the first screen and folds into the strip on send", async ({ page }) => {
  await mock(page);
  await page.goto("/");
  await expect(page.getByRole("heading", { name: summary.headline })).toBeVisible();
  await expect(page.getByText("$4.49M")).toBeVisible();
  await expect(page.getByText("37.8%", { exact: true })).toBeVisible();
  await expect(page.getByText(/One agency is behind pace: Harbor Business Travel at 96.1%/)).toBeVisible();
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
  await expect(dialog).toContainText("all 1,500 values matched");
  await page.keyboard.press("Escape");
  await expect(dialog).toBeHidden();
});
