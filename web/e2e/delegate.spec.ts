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
const catalog = {
  agents: [
    { key: "precall", name: "Monday pre-call pack", summary: "One page per agency an account manager owns, with talking points and a drafted follow-up email.", reads: ["the sales metrics", "the agreements", "the CRM stand-in"], writes: ["an activity in the CRM stand-in"], approver: "the account manager", scope_kind: "manager", last_run: null },
    { key: "watch", name: "Agreement watch", summary: "Every measurable promise in the agreements, checked for the month.", reads: ["the agreements", "the sales metrics"], writes: ["a notice or an upsell email"], approver: "the Sales Ops lead", scope_kind: "region", last_run: { run_id: "r0", status: "approved", created_at: "2026-10-13T06:10:00" } },
    { key: "prospect", name: "Prospect research", summary: "Where the headroom is on a market, what public sources say, and a suggested play.", reads: ["the sales metrics", "public sources"], writes: ["a brief to read"], approver: "the account manager", scope_kind: "market", last_run: null },
    { key: "mismatch", name: "CRM versus reality", summary: "Every open opportunity whose CRM health disagrees with the data.", reads: ["the CRM stand-in", "the sales metrics"], writes: ["a CRM update"], approver: "the account manager", scope_kind: "region", last_run: null },
  ],
  managers: ["Dana Whitfield", "Marcus Lee", "Priya Raman", "Tom Okafor"],
  markets: [{ market_id: 3, market: "CLT-LGA" }, { market_id: 6, market: "DFW-DCA" }],
  crm_label: "the CRM stand-in",
};
const numbersFact = { name: "numbers", label: "This month's numbers", sql: "SELECT 330114 AS aa_revenue", source: "gold.agency_pace", rows: [{ aa_revenue: 330114, yoy_pct: -16.4 }] };
const page1 = {
  item_id: "i1", kind: "page", title: "Harbor Business Travel", subtitle: "East region, Marcus Lee", severity: "risk", status: "draft",
  sentences: [{ text: "Harbor sold $330K in September 2026, down 16.4% from a year earlier.", status: "verified", numbers: [] }, { text: "Could not verify: whether a preferred-carrier setting changed.", status: "note", numbers: [] }],
  removed: [{ sentence: "Harbor should recover by $50K next quarter.", reason: "no query supports $50K" }], verified_text: "Harbor sold $330K in September 2026, down 16.4% from a year earlier.", draft: "",
  facts: [numbersFact], sources: [], action: { type: "email", subject: "Harbor: your September numbers", body: "Hello Avery, here are the September numbers.", crm: { agency_id: 5, activity_type: "Pre-call pack", subject: "Pre-call pack approved for September 2026" } },
  decided_at: null, decided_by: null,
};
const mismatch = {
  item_id: "i2", kind: "mismatch", title: "Harbor Business Travel 2027 renewal", subtitle: "Negotiate, On track in the CRM stand-in", severity: "risk", status: "draft",
  sentences: [{ text: "The CRM stand-in says this renewal is on track, and the data says AA share fell 10.1 points.", status: "verified", numbers: [] }],
  removed: [], verified_text: "The CRM stand-in says this renewal is on track, and the data says AA share fell 10.1 points.", draft: "",
  facts: [{ name: "opportunity", label: "The opportunity", sql: "SELECT * FROM aa_demo.gold.crm_opportunities WHERE opp_id = 7005", source: "gold.crm_opportunities", rows: [{ stage: "Negotiate", health: "On track" }] }],
  sources: [], action: { type: "crm", subject: "Health changed after review", body: "Share fell 10.1 points while the CRM said On track.", crm: { agency_id: 5, activity_type: "CRM update", subject: "Health changed after review" } },
  decided_at: null, decided_by: null,
};

async function mock(page: Page) {
  await page.route("**/api/me", (r) => r.fulfill({ json: me }));
  await page.route("**/api/summary**", (r) => r.fulfill({ json: summary }));
  await page.route("**/api/definitions", (r) => r.fulfill({ json: { kpis: [], parity: null, runs: [] } }));
  let polls = 0;
  let started: unknown = null;
  const items: Record<string, Record<string, unknown>> = { i1: { ...page1 }, i2: { ...mismatch } };
  const list = () => Object.values(items);
  const status = () => (polls < 2 ? "running" : list().some((i) => i.status === "draft") ? "needs_approval" : list().some((i) => i.status === "approved") ? "approved" : "rejected");
  const run = () => ({
    run_id: "r1", agent: "precall", agent_name: "Monday pre-call pack", scope: { manager: "Marcus Lee", month: "2026-09" }, status: status(), requested_by: "dana@example.com", model: "azure/gpt-5-mini",
    created_at: "2026-10-14T22:10:00", finished_at: polls < 2 ? null : "2026-10-14T22:11:00", progress: { done: Math.min(polls, 2), total: polls === 0 ? 0 : 2, text: "" },
    items: polls === 0 ? [] : polls === 1 ? [items.i1] : list(), error: null,
  });
  const header = () => ({ run_id: "r1", agent: "precall", agent_name: "Monday pre-call pack", scope: { manager: "Marcus Lee", month: "2026-09" }, status: status(), created_at: "2026-10-14T22:10:00", finished_at: null, items: 2, needs_approval: list().filter((i) => i.status === "draft").length });
  await page.route((u) => u.pathname.startsWith("/api/agents"), (r: Route) => {
    const u = new URL(r.request().url());
    const m = r.request().method();
    if (u.pathname === "/api/agents") return r.fulfill({ json: catalog });
    if (u.pathname === "/api/agents/runs") return r.fulfill({ json: started ? [header()] : [] });
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
  return { requested: () => started };
}

test("Delegate lists the agents, runs one, polls it to completion, and records decisions", async ({ page }) => {
  const m = await mock(page);
  await page.goto("/");
  await page.getByRole("button", { name: "Delegate" }).click();
  await expect(page.getByRole("heading", { name: "Hand work to an agent." })).toBeVisible();
  for (const a of catalog.agents) await expect(page.getByRole("heading", { name: a.name })).toBeVisible();
  await expect(page.getByText("Last run October 13 at 6:10 AM: approved.")).toBeVisible();
  await expect(page.getByText("No runs yet. Pick an agent above and press Run now.")).toBeVisible();
  await expect(page.getByLabel("Ask a question")).toHaveCount(0);
  const nav = page.getByRole("navigation", { name: "Sidebar" });
  await expect(nav.getByRole("button", { name: "Agreement watch" })).toBeVisible();
  await expect(nav.getByRole("button", { name: "Start a new chat" })).toHaveCount(0);

  await page.getByLabel("Account manager for Monday pre-call pack").selectOption("Marcus Lee");
  await page.getByRole("button", { name: "Run now: Monday pre-call pack" }).click();
  expect(m.requested()).toEqual({ scope: { manager: "Marcus Lee", month: "2026-09" } });
  await expect(page.getByRole("status")).toContainText(/Starting\.|1 of 2 written\./);
  await expect(page.getByRole("status")).toContainText("2 of 2 waiting for approval.", { timeout: 15_000 });
  await expect(page.getByRole("list", { name: "Runs" })).toContainText("Needs approval");

  const harbor = page.getByRole("article", { name: "Harbor Business Travel", exact: true });
  await expect(harbor.getByText("Harbor sold $330K in September 2026, down 16.4% from a year earlier.")).toBeVisible();
  await expect(harbor.getByText("I removed one sentence before showing you this draft.")).toBeVisible();
  await expect(harbor.getByText("At risk")).toBeVisible();
  await harbor.getByRole("button", { name: "Show the numbers" }).click();
  await expect(harbor.getByRole("cell", { name: "330,114" })).toBeVisible();
  await harbor.getByRole("button", { name: "Show the query" }).click();
  await expect(harbor.locator("pre.sql")).toHaveText("SELECT 330114 AS aa_revenue");

  const renewal = page.getByRole("article", { name: "Harbor Business Travel 2027 renewal" });
  await renewal.getByRole("button", { name: "Approve" }).click();
  await expect(renewal).toContainText("Approved by dana@example.com on October 14 at 10:15 PM. Approved and recorded in the CRM stand-in.");
  await expect(renewal.getByRole("button", { name: "Approve" })).toHaveCount(0);
  await expect(page.getByRole("status")).toContainText("1 of 2 waiting for approval.");

  await harbor.getByRole("button", { name: "Reject" }).click();
  await expect(harbor).toContainText("Rejected by dana@example.com on October 14 at 10:15 PM. Rejected. Nothing was sent or recorded.");
  await expect(page.getByRole("status")).toContainText("Every item has been decided.");

  await page.reload();
  await expect(page.getByRole("heading", { name: "Hand work to an agent." })).toBeVisible();
  await expect(page.getByRole("article", { name: "Harbor Business Travel", exact: true })).toBeVisible();

  await page.getByRole("button", { name: "Ask", exact: true }).click();
  await expect(page.getByRole("heading", { name: summary.headline })).toBeVisible();
  await expect(page.getByLabel("Ask a question")).toBeVisible();
});

test("an edit that adds an unsupported number is refused and explained", async ({ page }) => {
  await mock(page);
  await page.route((u) => u.pathname === "/api/agents/runs/r1/items/i1/approve", (r) => r.fulfill({ status: 422, json: { code: "unverified", message: "Your edit has a number no query supports, so it cannot be sent.", removed: [{ sentence: "Harbor sold $9.9M.", reason: "no query supports $9.9M" }] } }));
  await page.goto("/");
  await page.getByRole("button", { name: "Delegate" }).click();
  await page.getByRole("button", { name: "Run now: Monday pre-call pack" }).click();
  const harbor = page.getByRole("article", { name: "Harbor Business Travel", exact: true });
  await expect(harbor.getByRole("button", { name: "Edit" })).toBeVisible({ timeout: 15_000 });
  await harbor.getByRole("button", { name: "Edit" }).click();
  await harbor.getByLabel("Edit Harbor Business Travel").fill("Harbor sold $9.9M.");
  await harbor.getByRole("button", { name: "Approve" }).click();
  await expect(harbor.getByText(/Your edit has a number no query supports, so it cannot be sent\. "Harbor sold \$9\.9M\." \(no query supports \$9\.9M\)/)).toBeVisible();
  await expect(harbor.getByRole("button", { name: "Approve" })).toBeVisible();
});
