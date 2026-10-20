import { expect, test, type BrowserContext, type Page } from "@playwright/test";

test.beforeEach(async ({ context }) => {
  await context.route(/fonts\.(googleapis|gstatic)\.com/, (r) => r.abort()); // the font stylesheet holds the controller back
});
const root = (page: Page) => page.frameLocator("iframe[data-slide-frame]").locator("[data-motion-root]");
const ready = (page: Page) => page.locator('iframe[data-slide-frame][data-ready="1"]');

test("an animated slide takes as many presses as it has steps, then the deck moves", async ({ page }) => {
  await page.goto("/present#system");
  await expect(ready(page)).toBeVisible();
  await expect(root(page)).toHaveAttribute("data-step-current", "0");
  const count = Number(await root(page).getAttribute("data-step-count"));
  for (let i = 1; i <= count; i++) {
    await page.keyboard.press("ArrowRight");
    await expect(root(page)).toHaveAttribute("data-step-current", String(i));
  }
  await page.keyboard.press("ArrowRight");
  await expect(page).not.toHaveURL(/#system$/);
  await page.keyboard.press("ArrowLeft");
  await expect(page).toHaveURL(/#system$/);
  await expect(ready(page)).toBeVisible();
  await page.keyboard.press("ArrowLeft"); // arriving backward lands on the end, so one press goes back one step
  await expect(root(page)).toHaveAttribute("data-step-current", String(count - 1));
});

test("a frame that never starts shows the figure and moves the deck on the first press", async ({ page, context }) => {
  // only the frame's page: in dev the same file is also served as the ?url import module
  await context.route(/-animated[^/]*\.html/, (r) => (r.request().resourceType() === "document" ? r.abort() : r.continue()));
  await page.goto("/present#system");
  await expect(page.getByRole("img", { name: "The system" })).toBeVisible();
  await page.keyboard.press("ArrowRight");
  await expect(page).not.toHaveURL(/#system$/);
});

test("with reduced motion an animated slide shows the whole figure and the first press moves the deck", async ({ page }) => {
  await page.emulateMedia({ reducedMotion: "reduce" });
  await page.goto("/present#system");
  await expect(ready(page)).toBeVisible();
  await page.keyboard.press("ArrowRight");
  await expect(page).not.toHaveURL(/#system$/);
});

test("the notes window follows the deck, drives it, keeps the warehouse awake, and resyncs after a reload", async ({ page, context }) => {
  let pings = 0;
  await context.route("**/api/agencies", (r) => { pings += 1; return r.fulfill({ json: [] }); });
  await page.goto("/present#title");
  await expect(page.locator("[data-deck-ready]")).toBeAttached();
  const [notes] = await Promise.all([context.waitForEvent("page"), page.keyboard.press("p")]);
  const now = notes.locator("[data-now]");
  await expect(now).toHaveAttribute("data-now", "title");
  await page.keyboard.press("ArrowRight");
  await expect(now).toHaveAttribute("data-now", "problem");
  await notes.keyboard.press("ArrowRight");
  await expect(page).toHaveURL(/#what$/);
  await notes.getByRole("button", { name: "Short" }).click();
  await notes.keyboard.press("Space"); // the switch lost focus, so Space moves the slide once and does not toggle back
  await expect(page).toHaveURL(/#ask$/);
  await page.reload();
  await expect(page.locator("[data-deck-ready]")).toBeAttached();
  await notes.keyboard.press("ArrowRight");
  await expect(page).toHaveURL(/#system$/);
  await expect(now).toHaveAttribute("data-now", "system");
  expect(pings).toBeGreaterThan(0);
});

test("keys the notes window sends in a burst all reach the deck", async ({ page, context }) => {
  await context.route("**/api/agencies", (r) => r.fulfill({ json: [] }));
  await page.goto("/present#title");
  await expect(page.locator("[data-deck-ready]")).toBeAttached();
  const [notes] = await Promise.all([context.waitForEvent("page"), page.keyboard.press("p")]);
  await expect(notes.locator("[data-now]")).toHaveAttribute("data-now", "title");
  await notes.evaluate(() => {
    const channel = new BroadcastChannel("fairshare-deck");
    for (let i = 0; i < 3; i++) channel.postMessage({ t: "key", action: "next" }); // queued before the deck renders once
    channel.close();
  });
  await expect(page).toHaveURL(/#query-opener$/);
  await expect(notes.locator("[data-now]")).toHaveAttribute("data-now", "query-opener");
});

test("the first move starts the clock on plan, so a talk on plan reads on time", async ({ page, context }) => {
  await context.route("**/api/agencies", (r) => r.fulfill({ json: [] }));
  await page.goto("/present#title");
  await expect(page.locator("[data-deck-ready]")).toBeAttached();
  const [notes] = await Promise.all([context.waitForEvent("page"), page.keyboard.press("p")]);
  await expect(notes.getByText("The clock starts on the first move.")).toBeVisible();
  const before = await page.evaluate(() => Date.now());
  await page.keyboard.press("ArrowRight"); // the title's planned half minute is already behind the talk
  const after = await page.evaluate(() => Date.now());
  const started = Number(await page.evaluate(() => sessionStorage.getItem("fairshare.deck.startedAt")));
  expect(started).toBeGreaterThanOrEqual(before - 30_000);
  expect(started).toBeLessThanOrEqual(after - 30_000);
  await expect(notes.getByText("On time", { exact: true })).toBeVisible();
});

// The demo jumps open the app in the deck's tab. Its routes are small copies of the fixtures in smoke.spec.ts, and the
// catalog has the pre-call agent with no pages.
const me = {
  email: "dana@example.com", user: "dana", inside_app: true, scopes: ["sql", "genie", "model-serving"], backend: "databricks", model: "databricks/x",
  genie: null, data_through: "2026-09", regions: ["All", "Central", "East", "West"], months: ["2026-09", "2026-08"], links: {},
};
const summary = {
  region: "All", month: "2026-09", prior_month: "2025-09", headline: "September closed ahead of pace and a little under fair share.",
  kpis: { aa_revenue: 4492373, aa_revenue_prior_year: 4456241, yoy_pct: 0.8, aa_share_pct: 37.8, fair_share_pct: 39.0, share_gap_pts: -1.2, share_gap_usd: -143384, pace_pct: 139.1 },
  movers: [], behind_pace: [], calls: [], agency_count: 4,
};
const signals = { region: "All", month: "2026-09", signals: [], calls: [] };
const catalog = {
  agents: [{
    key: "precall", name: "Monday pre-call pack", summary: "", one_liner: "Writes one page for each of your agencies before Monday's calls, with an email ready to send.", cadence: "It runs every Monday at 6:00.",
    steps: [{ key: "numbers", title: "Numbers", sub: "Revenue, share, pace" }, { key: "draft", title: "Draft", sub: "The page and the email" }, { key: "approve", title: "Approve", sub: "Waits for you" }],
    reads: ["the month's numbers"], writes: ["an email draft"], approver: "the account manager", scope_kind: "manager", last_run: null, waiting: 0, running: null, pages: [],
  }],
  managers: ["Marcus Lee"], markets: [], crm_label: "the CRM stand-in",
};
async function mockApp(context: BrowserContext) {
  await context.route("**/api/me", (r) => r.fulfill({ json: me }));
  await context.route("**/api/summary**", (r) => r.fulfill({ json: summary }));
  await context.route("**/api/signals**", (r) => r.fulfill({ json: signals }));
  await context.route("**/api/agents", (r) => r.fulfill({ json: catalog }));
}

const question = "Why is Harbor Business Travel down in September?";
const back = (page: Page) => page.getByRole("link", { name: "Back to the deck" });

test("the Ask jump fills and focuses the box, and the way back survives a reload", async ({ page, context }) => {
  await mockApp(context);
  await page.goto("/present#ask");
  await expect(page.locator("[data-deck-ready]")).toBeAttached(); // a key pressed before the deck listens is lost
  await page.keyboard.press("ArrowRight"); // the first move starts the clock
  await page.keyboard.press("ArrowLeft");
  const started = await page.evaluate(() => sessionStorage.getItem("fairshare.deck.startedAt"));
  await page.getByRole("button", { name: "Ask it live" }).click();
  await expect(page.locator("#ask")).toHaveValue(question);
  await expect(page.locator("#ask")).toBeFocused();
  expect(new URL(page.url()).searchParams.get("q")).toBeNull();
  await page.reload();
  await back(page).click();
  await expect(page).toHaveURL(/\/present#ask$/);
  expect(await page.evaluate(() => sessionStorage.getItem("fairshare.deck.startedAt"))).toBe(started);
  expect(await page.evaluate(() => sessionStorage.getItem("fairshare.deck.return"))).toBeNull();
  await page.goto("/");
  await expect(back(page)).toHaveCount(0);
});

test("the pre-call jump opens Delegate on the pre-call agent, with a way back", async ({ page, context }) => {
  await mockApp(context);
  await page.goto("/present#precall");
  await page.getByRole("button", { name: "Open the pre-call pack" }).click();
  await expect(page).toHaveURL(/\/(\?.*)?$/);
  expect(await page.evaluate(() => localStorage.getItem("fairshare.mode"))).toBe('"delegate"');
  expect(JSON.parse((await page.evaluate(() => localStorage.getItem("fairshare.delegate"))) ?? "{}").agent).toBe("precall");
  await back(page).click();
  await expect(page).toHaveURL(/\/present#precall$/);
});

test("the sidebar entry opens the deck on the title", async ({ page, context }) => {
  await mockApp(context);
  await page.goto("/");
  await page.getByRole("link", { name: "Present" }).click();
  await expect(page).toHaveURL(/\/present/);
  await expect(page.locator('[data-slide="title"]')).toBeVisible();
});

test("a demo button in the notes window jumps the deck's tab, and the way back lands on the same slide", async ({ page, context }) => {
  await mockApp(context);
  await context.route("**/api/agencies", (r) => r.fulfill({ json: [] }));
  await page.goto("/present#ask");
  await expect(page.locator("[data-deck-ready]")).toBeAttached();
  const [notes] = await Promise.all([context.waitForEvent("page"), page.keyboard.press("p")]);
  await expect(notes.locator("[data-now]")).toHaveAttribute("data-now", "ask");
  await notes.getByRole("button", { name: "Ask it live" }).click();
  await expect(page.locator("#ask")).toHaveValue(question);
  await back(page).click();
  await expect(page).toHaveURL(/\/present#ask$/);
  await expect(page.locator('[data-slide="ask"]')).toBeVisible();
});

test("the browser's Back button returns to the same slide with the clock kept, and the deck spends the way back", async ({ page, context }) => {
  await mockApp(context);
  await page.goto("/present#ask");
  await expect(page.locator("[data-deck-ready]")).toBeAttached();
  await page.keyboard.press("ArrowRight"); // the first move starts the clock
  await page.keyboard.press("ArrowLeft");
  const started = await page.evaluate(() => sessionStorage.getItem("fairshare.deck.startedAt"));
  expect(started).not.toBeNull();
  await page.getByRole("button", { name: "Ask it live" }).click();
  await expect(back(page)).toBeVisible();
  await page.goBack(); // the browser's Back skips the app's link
  await expect(page).toHaveURL(/\/present#ask$/);
  await expect(page.locator('[data-slide="ask"]')).toBeVisible();
  await expect(page.locator("[data-deck-ready]")).toBeAttached();
  expect(await page.evaluate(() => sessionStorage.getItem("fairshare.deck.startedAt"))).toBe(started);
  expect(await page.evaluate(() => sessionStorage.getItem("fairshare.deck.return"))).toBeNull();
  await page.goto("/");
  await expect(page.locator("#ask")).toBeVisible();
  await expect(back(page)).toHaveCount(0);
});

test("the sidebar's Present link shows in Ask and in Delegate, expanded and collapsed", async ({ page, context }) => {
  await mockApp(context);
  await page.goto("/");
  for (const sidebar of ["false", "true"]) {
    for (const mode of ['"ask"', '"delegate"']) {
      await page.evaluate(([s, m]) => { localStorage.setItem("fairshare.sidebar", s); localStorage.setItem("fairshare.mode", m); }, [sidebar, mode]);
      await page.reload();
      const link = page.getByRole("link", { name: "Present" });
      await expect(link, `sidebar ${sidebar}, mode ${mode}`).toBeVisible();
      await expect(link).toHaveAttribute("href", "/present");
    }
  }
});
