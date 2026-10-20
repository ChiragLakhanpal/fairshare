import { expect, test, type Page, type Route } from "@playwright/test";

const me = {
  email: "dana@example.com", user: "dana", inside_app: true, scopes: ["sql", "genie", "model-serving"], backend: "databricks", model: "databricks/x",
  genie: null, data_through: "2026-09", regions: ["All", "Central", "East", "West"], months: ["2026-09", "2026-08"], links: {},
};
const summary = {
  region: "All", month: "2026-09", prior_month: "2025-09", headline: "September closed ahead of pace and a little under fair share.",
  kpis: { aa_revenue: 4492373, aa_revenue_prior_year: 4456241, yoy_pct: 0.8, aa_share_pct: 37.8, fair_share_pct: 39.0, share_gap_pts: -1.2, share_gap_usd: -143384, pace_pct: 139.1 },
  movers: [], behind_pace: [], calls: [], agency_count: 4,
};
const precallSteps = [
  { key: "numbers", title: "Numbers", sub: "Revenue, share, pace" }, { key: "why", title: "Why", sub: "Volume, mix, share since last year" },
  { key: "agreement", title: "Agreement", sub: "Clauses near their line" }, { key: "crm", title: "CRM", sub: "Last touch, open deals" },
  { key: "draft", title: "Draft", sub: "The page and the email" }, { key: "check", title: "Check", sub: "Every number against its query" }, { key: "approve", title: "Approve", sub: "Waits for you" },
];
const shortSteps = [
  { key: "clauses", title: "Clauses", sub: "Each promise, checked" }, { key: "draft", title: "Draft", sub: "The alert and the note" },
  { key: "check", title: "Check", sub: "Every number against its query" }, { key: "approve", title: "Approve", sub: "Waits for you" },
];
const numbersFact = { name: "numbers", label: "The month's numbers", sql: "SELECT 330114 AS aa_revenue", source: "gold.agency_pace", rows: [{ aa_revenue: 330114, yoy_pct: -16.4 }] };
const s1 = { text: "Harbor sold $330K of AA travel in September 2026, down 16.4% from September 2025.", status: "verified", numbers: [{ raw: "$330K", source: "numbers", fact: "aa_revenue=330114.0" }, { raw: "16.4%", source: "numbers", fact: "yoy_pct=-16.4" }] };
const s2 = { text: "The CRM stand-in says the renewal is on track, but share fell ten points.", status: "verified", numbers: [] };
const page1 = {
  item_id: "i1", kind: "page", title: "Harbor Business Travel", subtitle: "September 2026, Marcus Lee", severity: "risk", status: "draft",
  summary: "Share is down 10 points, and the CRM still says the renewal is on track.",
  sections: [{ title: "Where they stand", sentences: [s1] }, { title: "The CRM stand-in", sentences: [s2] }],
  email: { to: "avery.patel@harbor.example", to_name: "Avery Patel", subject: "Harbor Business Travel, September 2026: performance and next steps", sentences: [{ text: "Hello Avery, thank you for the time this month.", status: "verified", numbers: [] }, { text: "Could we find thirty minutes next week?", status: "verified", numbers: [] }] },
  note: "whether the agency changed a preferred-carrier setting or lost a client.", numbers_checked: 2,
  sentences: [s1, s2], removed: [{ sentence: "Harbor should recover by $50K next quarter.", reason: "no query supports $50K" }], verified_text: `${s1.text} ${s2.text}`, draft: "",
  facts: [numbersFact], sources: [], action: { type: "email", subject: "Pre-call pack: Harbor Business Travel, September 2026", body: "Hello Avery, thank you for the time this month. Could we find thirty minutes next week?", crm: { agency_id: 5, activity_type: "Pre-call pack", subject: "Pre-call pack approved for September 2026" } },
  decided_at: null, decided_by: null,
};
const renewal = {
  item_id: "i2", kind: "mismatch", title: "Harbor Business Travel 2027 renewal", subtitle: "September 2026, the CRM says on track; the data says share is down", severity: "risk", status: "draft",
  summary: "The CRM says on track; the data says AA share is down 10.1 points.",
  sections: [{ title: "", sentences: [{ text: "The CRM stand-in says this renewal is on track, and the data says AA share fell 10.1 points.", status: "verified", numbers: [{ raw: "10.1", source: "opportunity", fact: "share_chg_pts=-10.1" }] }] }],
  email: null, note: "why the opportunity was marked On track.", numbers_checked: 1,
  sentences: [{ text: "The CRM stand-in says this renewal is on track, and the data says AA share fell 10.1 points.", status: "verified", numbers: [{ raw: "10.1", source: "opportunity", fact: "share_chg_pts=-10.1" }] }],
  removed: [], verified_text: "The CRM stand-in says this renewal is on track, and the data says AA share fell 10.1 points.", draft: "",
  facts: [{ name: "opportunity", label: "The opportunity", sql: "SELECT * FROM aa_demo.gold.crm_opportunities WHERE opp_id = 7005", source: "gold.crm_opportunities", rows: [{ stage: "Negotiate", health: "On track" }] }],
  sources: [], action: { type: "crm", subject: "CRM update: Harbor Business Travel 2027 renewal", body: "Share fell 10.1 points while the CRM said On track.", crm: { agency_id: 5, activity_type: "CRM update", subject: "Health changed after review" } },
  decided_at: null, decided_by: null,
};

async function mock(page: Page) {
  let lastSummaryUrl = "";
  await page.route("**/api/me", (r) => r.fulfill({ json: me }));
  await page.route("**/api/summary**", (r) => { lastSummaryUrl = r.request().url(); return r.fulfill({ json: summary }); });
  await page.route("**/api/definitions", (r) => r.fulfill({ json: { kpis: [], parity: null, runs: [] } }));
  let polls = 0;
  let started: unknown = null;
  const items: Record<string, Record<string, unknown>> = { i1: { ...page1 }, i2: { ...renewal } };
  const list = () => Object.values(items);
  const drafts = () => list().filter((i) => i.status === "draft");
  const done = () => !!started && polls >= 2;
  const status = () => (!done() ? "running" : drafts().length ? "needs_approval" : list().some((i) => i.status === "approved") ? "approved" : "rejected");
  const progress = () => (polls === 0 ? { done: 0, total: 2, text: "", phase: "facts", item: "Harbor Business Travel" } : polls === 1 ? { done: 1, total: 2, text: "", phase: "draft", item: "Harbor Business Travel 2027 renewal" } : { done: 2, total: 2, text: "", phase: "done", item: null });
  const run = () => ({
    run_id: "r1", agent: "precall", agent_name: "Monday pre-call pack", scope: { manager: "Marcus Lee", month: "2026-09" }, status: status(), requested_by: "dana@example.com", model: "azure/gpt-5-mini",
    created_at: "2026-10-14T22:10:00", finished_at: done() ? "2026-10-14T22:12:00" : null, progress: progress(), items: polls === 0 ? [] : polls === 1 ? [items.i1] : list(), error: null,
  });
  // The server lists the pages of a run in progress too, so the catalog's pages follow the run's items. Each page here has
  // one version, the item itself.
  const pageOf = (i: Record<string, unknown>) => {
    const at = "2026-10-14T22:10:00";
    const scope = { manager: "Marcus Lee", month: "2026-09" };
    const decision = { status: i.status, decided_at: i.decided_at, decided_by: i.decided_by };
    return {
      item_id: i.item_id, kind: i.kind, title: i.title, subtitle: i.subtitle, severity: i.severity, summary: i.summary, ...decision,
      run_id: "r1", created_at: at, scope, versions: [{ run_id: "r1", item_id: i.item_id, created_at: at, scope, ...decision }],
    };
  };
  const catalog = () => {
    const pages = started ? run().items.map(pageOf) : [];
    return {
      agents: [
        { key: "precall", name: "Monday pre-call pack", summary: "", one_liner: "Writes one page for each of your agencies before Monday's calls, with an email ready to send.", cadence: "It runs every Monday at 6:00. You can also run it now.", steps: precallSteps,
          reads: ["the month's numbers", "the agreements", "the CRM stand-in"], writes: ["an activity in the CRM stand-in", "an email draft"], approver: "the account manager", scope_kind: "manager",
          last_run: started ? { run_id: "r1", status: status(), created_at: "2026-10-14T22:10:00" } : null, waiting: pages.filter((p) => p.status === "draft").length, running: started && !done() ? { run_id: "r1", progress: progress() } : null, pages },
        { key: "watch", name: "Agreement watch", summary: "", one_liner: "Checks every promise in the agreements against this month's numbers and drafts a note when one is close to its line.", cadence: "It runs every night.", steps: shortSteps,
          reads: ["the agreements"], writes: ["an email draft"], approver: "the Sales Ops lead", scope_kind: "region", last_run: { run_id: "r0", status: "approved", created_at: "2026-10-13T06:10:00" }, waiting: 0, running: null, pages: [] },
        { key: "prospect", name: "Prospect research", summary: "", one_liner: "Picks a route, shows where the money is, and adds what the news says about it.", cadence: "It runs when you ask for a market.", steps: shortSteps,
          reads: ["the sales numbers", "public sources"], writes: ["a brief to read"], approver: "the account manager", scope_kind: "market", last_run: null, waiting: 0, running: null, pages: [] },
        { key: "mismatch", name: "CRM check", summary: "", one_liner: "Finds opportunities where the CRM stand-in says one thing and the numbers say another, and drafts the fix.", cadence: "It runs every night.", steps: shortSteps,
          reads: ["the CRM stand-in"], writes: ["a note in the CRM stand-in"], approver: "the account manager", scope_kind: "region", last_run: null, waiting: 0, running: null, pages: [] },
      ],
      managers: ["Dana Whitfield", "Marcus Lee", "Priya Raman", "Tom Okafor"],
      markets: [{ market_id: 3, market: "CLT-LGA" }, { market_id: 6, market: "DFW-DCA" }],
      crm_label: "the CRM stand-in",
    };
  };
  await page.route((u) => u.pathname.startsWith("/api/agents") || u.pathname.startsWith("/api/crm"), (r: Route) => {
    const u = new URL(r.request().url());
    const m = r.request().method();
    if (u.pathname === "/api/agents") return r.fulfill({ json: catalog() });
    if (u.pathname === "/api/agents/precall/run" && m === "POST") {
      started = r.request().postDataJSON();
      return r.fulfill({ json: run() });
    }
    if (u.pathname === "/api/agents/runs/r1" && m === "GET") {
      const body = run();
      polls += 1;
      return r.fulfill({ json: body });
    }
    const decide = u.pathname.match(/^\/api\/agents\/runs\/r1\/items\/(i\d)\/(approve|reject)$/);
    if (decide && m === "POST") {
      const it = items[decide[1]];
      Object.assign(it, { status: decide[2] === "approve" ? "approved" : "rejected", decided_at: "2026-10-14T22:15:00", decided_by: "dana@example.com" });
      return r.fulfill({ json: it });
    }
    return r.fulfill({ status: 404, json: { code: "not_found", message: "No such API route." } });
  });
  return { requested: () => started, summaryUrl: () => lastSummaryUrl };
}

test("Delegate opens on the overview, runs an agent with live progress, opens a page beside the list, and records decisions", async ({ page }) => {
  const m = await mock(page);
  await page.goto("/");
  await page.getByRole("button", { name: "Delegate" }).click();
  await expect(page.getByRole("heading", { name: "Overview" })).toBeVisible();
  await expect(page.getByText("Nothing needs a decision right now.")).toBeVisible();
  await expect(page.getByLabel("Ask a question")).toHaveCount(0);
  const nav = page.getByRole("navigation", { name: "Sidebar" });
  const precall = nav.getByRole("button", { name: /Monday pre-call pack/ });
  await expect(precall).toContainText("Not run yet");
  await expect(nav.getByRole("button", { name: /Agreement watch/ })).toContainText("Last run needs nothing from you");

  await precall.click();
  await expect(page.getByRole("heading", { name: "Monday pre-call pack" })).toBeVisible();
  await expect(page.getByText("Writes one page for each of your agencies before Monday's calls, with an email ready to send.")).toBeVisible();
  const steps = page.getByRole("list", { name: "What it does, in order" });
  await expect(steps).toContainText("Numbers");
  await expect(steps).toContainText("Draft");
  await expect(steps).toContainText("Approve");
  await expect(page.getByText("This agent has not run yet. Press Run now to start it.")).toBeVisible();

  await page.getByRole("button", { name: /^Account manager:/ }).click();
  await page.getByRole("menuitemradio", { name: "Marcus Lee" }).click();
  await page.getByRole("button", { name: "Run now" }).click();
  expect(m.requested()).toEqual({ scope: { manager: "Marcus Lee", month: "2026-09" } });
  await expect(page.getByText(/^Started\./)).toBeVisible();
  await expect(page.getByText("Page 1 of 2: Harbor Business Travel", { exact: true })).toBeVisible();
  await expect(precall).toContainText("Running, page 1 of 2");
  await expect(page.getByText("Page 2 of 2: Harbor Business Travel 2027 renewal")).toBeVisible({ timeout: 15_000 });
  await expect(page.getByRole("button", { name: "Harbor Business Travel", exact: true })).toBeVisible();
  await expect(page.getByLabel("Harbor Business Travel 2027 renewal: writing")).toBeVisible();
  await expect(page.getByRole("button", { name: "Harbor Business Travel 2027 renewal", exact: true })).toBeVisible({ timeout: 15_000 });
  await expect(precall).toContainText("2 pages waiting");
  await expect(page.getByRole("button", { name: "Run now" })).toBeVisible();

  await page.getByRole("button", { name: "Harbor Business Travel", exact: true }).click();
  const doc = page.getByRole("article", { name: "Harbor Business Travel", exact: true });
  await expect(doc.getByRole("heading", { name: "Harbor Business Travel", exact: true })).toBeVisible();
  await expect(doc).toContainText("All 2 numbers on this page came from the queries, at the same rounding. One sentence was removed before you saw this page.");
  await expect(doc.getByRole("heading", { name: "Where they stand" })).toBeVisible();
  await expect(doc.getByText("Draft email")).toBeVisible();
  await expect(doc).toContainText("Avery Patel");
  await expect(doc).toContainText("Approving records a Pre-call pack in the CRM stand-in and opens this email in your mail app. Nothing is sent until you press send there.");
  await expect(doc.locator(".num").first()).toHaveText("$330K");
  await doc.getByRole("button", { name: "Show the numbers" }).click();
  await expect(doc.getByRole("cell", { name: "330,114" })).toBeVisible();
  await doc.getByRole("button", { name: "Show the queries" }).click();
  await expect(doc.locator("pre.sql")).toHaveText("SELECT 330114 AS aa_revenue");

  await page.getByRole("button", { name: "Harbor Business Travel 2027 renewal", exact: true }).click();
  const note = page.getByRole("article", { name: "Harbor Business Travel 2027 renewal" });
  await expect(note).toContainText("Approving records a note in the CRM stand-in. Nothing else is sent.");
  await note.getByRole("button", { name: "Approve" }).click();
  await expect(note).toContainText("Approved by dana@example.com on October 14 at 10:15 PM. Approved and recorded in the CRM stand-in.");
  await expect(note.getByRole("button", { name: "Approve" })).toHaveCount(0);
  await expect(precall).toContainText("1 page waiting");

  await page.getByRole("button", { name: "Harbor Business Travel", exact: true }).click();
  await doc.getByRole("button", { name: "Reject" }).click();
  await expect(doc).toContainText("Rejected by dana@example.com on October 14 at 10:15 PM. Rejected. Nothing was sent or recorded.");
  await expect(precall).toContainText("Last run needs nothing from you");

  await page.reload();
  await expect(page.getByRole("article", { name: "Harbor Business Travel", exact: true })).toBeVisible();
  await page.getByRole("button", { name: "Monday pre-call pack", exact: true }).first().click();
  await expect(page.getByRole("heading", { name: "Monday pre-call pack" })).toBeVisible();

  await page.getByRole("button", { name: "Ask", exact: true }).click();
  await expect(page.getByRole("heading", { name: summary.headline })).toBeVisible();
  await expect(page.getByLabel("Ask a question")).toBeVisible();
});

test("an edit that adds an unsupported number is refused and explained", async ({ page }) => {
  await mock(page);
  await page.route((u) => u.pathname === "/api/agents/runs/r1/items/i1/approve", (r) => r.fulfill({ status: 422, json: { code: "unverified", message: "Your edit has a number no fact supports, so it cannot be approved.", removed: [{ sentence: "Harbor sold $9.9M.", reason: "no query supports $9.9M" }] } }));
  await page.goto("/");
  await page.getByRole("button", { name: "Delegate" }).click();
  await page.getByRole("navigation", { name: "Sidebar" }).getByRole("button", { name: /Monday pre-call pack/ }).click();
  await page.getByRole("button", { name: "Run now" }).click();
  await page.getByRole("button", { name: "Harbor Business Travel", exact: true }).click({ timeout: 15_000 });
  const doc = page.getByRole("article", { name: "Harbor Business Travel", exact: true });
  await doc.getByRole("button", { name: "Edit" }).click();
  await doc.getByLabel("Edit Harbor Business Travel").fill("Harbor sold $9.9M.");
  await doc.getByRole("button", { name: "Approve" }).click();
  await expect(doc.getByText(/Your edit has a number no fact supports, so it cannot be approved\. "Harbor sold \$9\.9M\." \(no query supports \$9\.9M\)/)).toBeVisible();
  await expect(doc.getByRole("button", { name: "Approve" })).toBeVisible();
});

test("the month picker opens a year of months and greys out the ones without data", async ({ page }) => {
  const m = await mock(page);
  await page.goto("/");
  await expect(page.getByRole("heading", { name: summary.headline })).toBeVisible();
  await page.getByRole("button", { name: "Pick a month: September 2026" }).click();
  const dialog = page.getByRole("dialog", { name: "Pick a month" });
  await expect(dialog).toBeVisible();
  await expect(dialog.getByRole("button", { name: "Oct 2026" })).toBeDisabled();
  await expect(dialog.getByRole("button", { name: "Sep 2026" })).toHaveAttribute("aria-pressed", "true");
  await dialog.getByRole("button", { name: "Aug 2026" }).click();
  await expect(page.getByRole("button", { name: "Pick a month: August 2026" })).toBeVisible();
  await expect.poll(() => m.summaryUrl()).toContain("month=2026-08");
});
