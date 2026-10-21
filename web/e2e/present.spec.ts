import { chromium, expect, test, type BrowserContext, type Locator, type Page } from "@playwright/test";

test.beforeEach(async ({ context }) => {
  await context.route(/fonts\.(googleapis|gstatic)\.com/, (r) => r.abort()); // the font stylesheet holds the controller back
});
const root = (page: Page) => page.frameLocator("iframe[data-slide-frame]").locator("[data-motion-root]");
const ready = (page: Page) => page.locator('iframe[data-slide-frame][data-ready="1"]');
const slideAt = (page: Page, id: string) => page.locator(`[data-slide="${id}"]`);
async function openSlide(page: Page, id: string) {
  await page.goto("about:blank"); // a change of hash alone would leave the deck where it is
  await page.goto(`/present#${id}`);
  await expect(page.locator("[data-deck-ready]")).toBeAttached();
  await expect(slideAt(page, id)).toBeVisible();
}

// A native slide says where it stands on its root, as an animated slide's diagram does: data-step-current of data-step-count. A slide that
// loads (a reload, or the way back from a demo) shows complete, so a test that wants a slide's title alone arrives on it with a press.
const stepRoot = (page: Page, id: string) => slideAt(page, id).locator("[data-step-current]");
const stepsOf = async (page: Page, id: string) => Number(await stepRoot(page, id).getAttribute("data-step-count"));
/** The deck is on this slide, with this many of its items showing. */
async function expectAt(page: Page, id: string, step: number) {
  await expect(page).toHaveURL(new RegExp(`#${id}$`));
  await expect(stepRoot(page, id)).toHaveAttribute("data-step-current", String(step));
}
/** Where the deck is: the hash and, on a native slide, its step. */
const where = (page: Page) =>
  page.evaluate(() => ({ hash: location.hash, step: document.querySelector("[data-slide] [data-step-current]")?.getAttribute("data-step-current") ?? null }));
/** Keys sent from the notes window in one go, all queued on the channel before the deck renders once. */
const burst = (notes: Page, action: "next" | "prev", n: number) =>
  notes.evaluate(({ action, n }) => {
    const channel = new BroadcastChannel("fairshare-deck");
    for (let i = 0; i < n; i++) channel.postMessage({ t: "key", action });
    channel.close();
  }, { action, n });

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
  const points = await stepsOf(page, "problem");
  await notes.keyboard.press("ArrowRight"); // a press in the notes window brings in a point, as one in the deck does
  await expectAt(page, "problem", 1);
  for (let k = 1; k < points; k++) await notes.keyboard.press("ArrowRight");
  await expectAt(page, "problem", points);
  await notes.keyboard.press("ArrowRight"); // and the press after the last point moves the deck
  await expect(page).toHaveURL(/#what$/);
  await notes.getByRole("button", { name: "Short" }).click();
  await notes.keyboard.press("Space"); // the switch lost focus, so Space brings in one tile and does not toggle the path back
  await expectAt(page, "what", 1);
  await expect(notes.getByRole("button", { name: "Short" })).toHaveAttribute("aria-pressed", "true");
  const tiles = await stepsOf(page, "what");
  for (let k = 1; k <= tiles; k++) await notes.keyboard.press("Space"); // the rest of the tiles, and then the slide
  await expect(page).toHaveURL(/#ask$/);
  await page.reload();
  await expect(page.locator("[data-deck-ready]")).toBeAttached();
  const lines = await stepsOf(page, "ask");
  await expectAt(page, "ask", lines); // a reload lands on the slide complete, and the notes window follows
  await expect(notes.getByText(`Point ${lines} of ${lines}`, { exact: true })).toBeVisible();
  await notes.keyboard.press("ArrowRight");
  await expect(page).toHaveURL(/#system$/);
  await expect(now).toHaveAttribute("data-now", "system");
  expect(pings).toBeGreaterThan(0);
});

test("keys the notes window sends in a burst are applied in order, through a slide's points and on, as the same keys one at a time are", async ({ page, context }) => {
  await context.route("**/api/agencies", (r) => r.fulfill({ json: [] }));
  await openSlide(page, "title");
  const [notes] = await Promise.all([context.waitForEvent("page"), page.keyboard.press("p")]);
  await expect(notes.locator("[data-now]")).toHaveAttribute("data-now", "title");
  await page.keyboard.press("ArrowRight");
  await expectAt(page, "problem", 0);
  const points = await stepsOf(page, "problem");
  for (let i = 0; i <= points; i++) await page.keyboard.press("ArrowRight"); // a press for each point, and one to move on
  await expectAt(page, "what", 0);
  const single = await where(page);
  // the same keys from the same start, all at once: none skipped, none doubled, and the notes window shows the same place
  await openSlide(page, "title");
  await page.keyboard.press("ArrowRight");
  await expectAt(page, "problem", 0);
  await burst(notes, "next", points + 1);
  await expectAt(page, "what", 0);
  expect(await where(page)).toEqual(single);
  const tiles = await stepsOf(page, "what");
  await expect(notes.getByText(`Point 0 of ${tiles}`, { exact: true })).toBeVisible();
  // on through the next slide's tiles and off it, and back: into it on its last tile, and one tile back
  await burst(notes, "next", tiles + 1);
  await expect(page).toHaveURL(/#query-opener$/);
  await expect(notes.locator("[data-now]")).toHaveAttribute("data-now", "query-opener");
  await burst(notes, "prev", 2);
  await expectAt(page, "what", tiles - 1);
  await expect(notes.getByText(`Point ${tiles - 1} of ${tiles}`, { exact: true })).toBeVisible();
});

test("a burst that goes through a diagram's steps and into the next slide's points applies each key once", async ({ page, context }) => {
  await context.route("**/api/agencies", (r) => r.fulfill({ json: [] }));
  await page.goto("/present#pipeline");
  await expect(ready(page)).toBeVisible();
  await expect(root(page)).toHaveAttribute("data-step-current", "0");
  const steps = Number(await root(page).getAttribute("data-step-count"));
  const [notes] = await Promise.all([context.waitForEvent("page"), page.keyboard.press("p")]);
  await expect(notes.locator("[data-now]")).toHaveAttribute("data-now", "pipeline");
  await burst(notes, "next", steps + 2); // every step of the diagram, the move to the next slide, and its first point
  await expectAt(page, "row", 1);
  await expect(notes.locator("[data-now]")).toHaveAttribute("data-now", "row");
  await expect(notes.getByText(`Point 1 of ${await stepsOf(page, "row")}`, { exact: true })).toBeVisible();
});

test("keys that come before the deck has drawn the one before still take the place that one left", async ({ page }) => {
  await openSlide(page, "title");
  await page.keyboard.press("ArrowRight");
  await expectAt(page, "problem", 0);
  const points = await stepsOf(page, "problem");
  // the keys of one task, so the deck draws nothing between one and the next
  const keys = (key: string, n: number) =>
    page.evaluate(({ key, n }) => {
      for (let i = 0; i < n; i++) dispatchEvent(new KeyboardEvent("keydown", { key, cancelable: true }));
    }, { key, n });
  await keys("ArrowRight", points + 1);
  await expectAt(page, "what", 0);
  await keys("ArrowLeft", 2); // back into problem, complete, and one point back
  await expectAt(page, "problem", points - 1);
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
    key: "precall", name: "Monday pre-call pack", summary: "", one_liner: "Writes one page for each of your agencies before Monday's calls, with an email ready to send.", cadence: "Runs every night. You can also run it now.",
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

// The way back must not sit on the question bar or the top bar, at the sizes a projector runs (1024 by 768, 1280 by 720)
// and up to a big screen, with the sidebar open or collapsed. The question box and the bar are checked as well as the input
// itself, because the input is only a part of the box a corner can cover.
type Box = { x: number; y: number; width: number; height: number };
const touches = (a: Box, b: Box) => a.x < b.x + b.width && b.x < a.x + a.width && a.y < b.y + b.height && b.y < a.y + a.height;
for (const size of [{ width: 1024, height: 768 }, { width: 1280, height: 720 }, { width: 1920, height: 1080 }]) {
  for (const collapsed of [false, true]) {
    test(`the way back stays clear of the question bar and the top bar at ${size.width} by ${size.height}, sidebar ${collapsed ? "collapsed" : "open"}`, async ({ page, context }) => {
      await mockApp(context);
      await context.route("**/api/me", (r) => r.fulfill({ json: { ...me, links: { dashboard: "https://example.com/dashboard" } } })); // the top bar as the app has it
      await page.setViewportSize(size);
      await page.addInitScript((c) => localStorage.setItem("fairshare.sidebar", String(c)), collapsed);
      await page.goto("/present#ask");
      await expect(page.locator("[data-deck-ready]")).toBeAttached();
      await page.getByRole("button", { name: "Ask it live" }).click();
      await expect(page.locator("#ask")).toBeFocused();
      await expect(back(page)).toBeVisible();
      const link = (await back(page).boundingBox())!;
      expect(link.x >= 0 && link.y >= 0 && link.x + link.width <= size.width && link.y + link.height <= size.height, `the link is on the screen: ${JSON.stringify(link)}`).toBe(true);
      const ask = page.locator("#ask");
      const keepClear: Record<string, Locator> = {
        "the question input": ask,
        "the question box": page.locator("form:has(#ask)"),
        "the question bar": ask.locator("xpath=ancestor::form/.."),
        "the top bar": page.getByText("The data runs through September 2026.").locator("xpath=ancestor::div[contains(@class,'h-14')][1]"),
      };
      for (const [name, where] of Object.entries(keepClear)) {
        const box = (await where.boundingBox())!;
        expect(touches(link, box), `the link ${JSON.stringify(link)} touches ${name} ${JSON.stringify(box)}`).toBe(false);
      }
    });
  }
}

// The browser may restore the deck from its back/forward cache, and then nothing mounts again. Playwright launches Chromium
// with that cache off, and its headless shell cannot restore a page at all, so this test starts full Chromium with it on
// (it needs the full build: bunx playwright install chromium). The restored deck is the page as it was left, so it brings its slide back
// to complete itself, as a load would.
test("a deck the browser restores from its cache spends the way back too, and shows the slide complete", async ({ baseURL }) => {
  type Kept = { kept?: string };
  const browser = await chromium.launch({ channel: "chromium", ignoreDefaultArgs: ["--disable-back-forward-cache"], args: ["--enable-features=BackForwardCache"] });
  try {
    const context = await browser.newContext({ baseURL, viewport: { width: 1440, height: 900 } });
    await context.route(/fonts\.(googleapis|gstatic)\.com/, (r) => r.abort());
    await mockApp(context);
    const page = await context.newPage();
    await page.goto("/present#query-opener");
    await expect(page.locator("[data-deck-ready]")).toBeAttached();
    await page.keyboard.press("ArrowRight"); // ask arrives on its title
    await page.keyboard.press("ArrowRight"); // and brings in its first line
    await expectAt(page, "ask", 1);
    const lines = await stepsOf(page, "ask");
    await page.evaluate(() => { (window as unknown as Kept).kept = "the same page"; }); // a page that loads again loses it
    await page.getByRole("button", { name: "Ask it live" }).click();
    await expect(back(page)).toBeVisible();
    await page.goBack({ waitUntil: "commit" }); // a restore from the cache fires no load event
    await expect.poll(() => page.evaluate(() => (window as unknown as Kept).kept ?? null).catch(() => null), { message: "the browser restored the deck from its cache" }).toBe("the same page");
    await expect.poll(() => page.evaluate(() => sessionStorage.getItem("fairshare.deck.return"))).toBeNull();
    await expectAt(page, "ask", lines);
    await page.goto("/");
    await expect(page.locator("#ask")).toBeVisible();
    await expect(back(page)).toHaveCount(0);
  } finally {
    await browser.close();
  }
});

// The frame: the AA logo and the five topics along the top, and along the bottom the talk's title (or "Synthetic data") and the slide's
// number on the path. A still is a screenshot of the app, which has its own top bar, so it gets no frame at all.
test("the tracker lights the slide's topic and marks the slide, and the footer numbers it on the path", async ({ page }) => {
  await openSlide(page, "ask");
  const tracker = slideAt(page, "ask").locator("[data-tracker]");
  await expect(tracker.locator('[aria-current="step"]')).toHaveText("Ask and Delegate");
  await expect(tracker.locator("[aria-current]")).toHaveCount(1);
  await expect(tracker.locator('[data-segment="current"]')).toHaveCount(1);
  await expect(slideAt(page, "ask").locator('[data-frame="footer"]')).toContainText(/^Fairshare: sales answers you can check\s*\d+ \/ \d+$/i);
});

// One slide from each topic, so each name is drawn lit (heavier, so wider) once; the longest, Where the numbers come from, is the one at risk.
for (const size of [{ width: 1024, height: 768 }, { width: 1920, height: 1080 }]) {
  test(`at ${size.width} by ${size.height} no two topic names overlap and none is cut off, whichever topic is lit`, async ({ page }) => {
    await page.setViewportSize(size);
    for (const id of ["problem", "ask", "row", "measured", "know"]) {
      await openSlide(page, id);
      const names = slideAt(page, id).locator("[data-topic-name]");
      await expect(names).toHaveCount(5);
      await expect(slideAt(page, id).locator('[data-tracker] [aria-current="step"]')).toHaveCount(1);
      const got = await names.evaluateAll((els) => els.map((el) => {
        const r = el.getBoundingClientRect();
        return { text: el.textContent ?? "", x: r.x, y: r.y, width: r.width, height: r.height, scroll: el.scrollWidth, client: el.clientWidth };
      }));
      for (const n of got) expect(n.scroll, `on ${id}, ${n.text} is cut off: ${n.scroll} > ${n.client}`).toBeLessThanOrEqual(n.client);
      got.forEach((a, i) => got.slice(i + 1).forEach((b) => expect(touches(a, b), `on ${id}, ${a.text} overlaps ${b.text}`).toBe(false)));
    }
  });
}

test("the welcome shows the logo alone, a still shows no frame at all, and a backup slide says Backup", async ({ page }) => {
  await openSlide(page, "title");
  await expect(slideAt(page, "title").locator('[data-frame="header"] img[src="/aa-logo.svg"]')).toBeVisible();
  await expect(slideAt(page, "title").locator("[data-tracker]")).toHaveCount(0);
  await expect(slideAt(page, "title").locator('[data-frame="footer"]')).toHaveCount(0);
  await openSlide(page, "coverage"); // a figure: the whole frame
  await expect(slideAt(page, "coverage").locator('[data-frame="header"] img[src="/aa-logo.svg"]')).toBeVisible();
  await expect(slideAt(page, "coverage").locator("[data-tracker]")).toBeVisible();
  await expect(slideAt(page, "coverage").locator('[data-frame="footer"]')).toBeVisible();
  await openSlide(page, "ask-still");
  await expect(slideAt(page, "ask-still").locator("[data-frame]")).toHaveCount(0);
  await page.keyboard.press("ArrowRight"); // the next backup slide
  await expect(slideAt(page, "precall-still")).toBeVisible();
  await expect(slideAt(page, "precall-still").locator("[data-frame]")).toHaveCount(0);
  await page.keyboard.press("ArrowRight"); // a backup slide that is not a still
  await expect(slideAt(page, "manager").locator('[data-frame="footer"]')).toContainText(/Backup$/i);
  await expect(slideAt(page, "manager").locator("[data-tracker] [aria-current]")).toHaveCount(0);
});

test("a live page in the deck drops its own logo, since the frame draws one, and keeps its caption", async ({ page }) => {
  await openSlide(page, "query-opener");
  await expect(page.locator('iframe[data-live-frame][data-shown="1"]')).toBeVisible();
  const live = page.frameLocator("iframe[data-live-frame]");
  await expect(live.locator(".caption")).toBeVisible();
  await expect(live.locator(".brand")).toBeHidden();
});

// Native steps. A native slide shows its title on arrival, and each point, tile, table, check, result or topic comes in on a press; the press
// after the last one moves the deck. Going back into a slide, a reload and the way back from a demo show it complete.
test("a native slide shows its title on arrival, takes a press for each point, and then the deck moves on", async ({ page }) => {
  await openSlide(page, "title");
  await page.keyboard.press("ArrowRight");
  await expectAt(page, "problem", 0);
  const count = await stepsOf(page, "problem");
  expect(count).toBeGreaterThan(1);
  await expect(slideAt(page, "problem").getByRole("heading", { level: 1 })).toBeVisible();
  const shown = stepRoot(page, "problem").locator("[data-step]:visible");
  const read = stepRoot(page, "problem").getByRole("listitem"); // what a screen reader can reach
  await expect(shown).toHaveCount(0);
  await expect(read).toHaveCount(0);
  for (let k = 1; k <= count; k++) {
    await page.keyboard.press("ArrowRight");
    await expectAt(page, "problem", k); // the deck stays
    await expect(shown).toHaveCount(k);
    await expect(read).toHaveCount(k);
  }
  await page.keyboard.press("ArrowRight");
  await expectAt(page, "what", 0); // the next slide arrives on its title
});

test("an unreached point is invisible and keeps its place, a point arrives over 320ms, and the points before it recede to the muted color", async ({ page }) => {
  await openSlide(page, "title");
  await page.keyboard.press("ArrowRight");
  await expectAt(page, "problem", 0);
  const slide = slideAt(page, "problem");
  const title = slide.getByRole("heading", { level: 1 });
  const points = slide.locator("li[data-step]");
  const wording = (i: number) => points.nth(i).locator(":scope > span").last();
  const titleAt = (await title.boundingBox())!.y;
  for (let i = 0; i < 3; i++) {
    await expect(points.nth(i), `point ${i + 1} before it is said`).toHaveCSS("visibility", "hidden"); // invisible, not faded
    await expect(points.nth(i)).toHaveCSS("opacity", "0");
    await expect(points.nth(i)).toHaveAttribute("aria-hidden", "true");
    expect((await points.nth(i).boundingBox())!.height, `point ${i + 1} keeps its space`).toBeGreaterThan(20);
  }
  await page.keyboard.press("ArrowRight");
  await expect(points.nth(0)).toHaveCSS("visibility", "visible");
  await expect(points.nth(0)).toHaveCSS("opacity", "1");
  const arrival = await points.nth(0).evaluate((el) => ({ property: getComputedStyle(el).transitionProperty, duration: getComputedStyle(el).transitionDuration }));
  expect(arrival.property).toContain("opacity");
  expect(arrival.duration).toBe("0.32s");
  await expect(points.nth(1)).toHaveCSS("visibility", "hidden"); // the next one is still to come
  await page.keyboard.press("ArrowRight"); // the second arrives, and the first recedes to #5a7181 while the newest keeps its ink
  await expect(points.nth(0)).toHaveAttribute("data-receded", "");
  await expect(wording(0)).toHaveCSS("color", "rgb(90, 113, 129)");
  await expect(wording(1)).toHaveCSS("color", "rgb(54, 73, 90)");
  expect((await title.boundingBox())!.y, "nothing moves as points arrive").toBeCloseTo(titleAt, 0);
});

test("with reduced motion the points still step, with no fade", async ({ page }) => {
  await page.emulateMedia({ reducedMotion: "reduce" });
  await openSlide(page, "title");
  await page.keyboard.press("ArrowRight");
  await expectAt(page, "problem", 0);
  const first = slideAt(page, "problem").locator("li[data-step]").first();
  await expect(first).toHaveCSS("visibility", "hidden");
  await page.keyboard.press("ArrowRight");
  await expectAt(page, "problem", 1);
  await expect(first).toHaveCSS("visibility", "visible");
  expect(await first.evaluate((el) => getComputedStyle(el).transitionProperty), "nothing fades or moves").toBe("none");
});

test("going back into a stepped slide lands on its last step, a press forward from there moves on, and a press back takes the points back one at a time", async ({ page }) => {
  await openSlide(page, "title");
  await page.keyboard.press("ArrowRight");
  const count = await stepsOf(page, "problem");
  for (let i = 0; i <= count; i++) await page.keyboard.press("ArrowRight"); // every point, and on
  await expectAt(page, "what", 0);
  await page.keyboard.press("ArrowLeft");
  await expectAt(page, "problem", count);
  await expect(stepRoot(page, "problem").locator("[data-step]:visible")).toHaveCount(count);
  await page.keyboard.press("ArrowRight"); // nothing left to say here
  await expectAt(page, "what", 0);
  await page.keyboard.press("ArrowLeft");
  await expectAt(page, "problem", count);
  for (let k = count - 1; k >= 0; k--) {
    await page.keyboard.press("ArrowLeft");
    await expectAt(page, "problem", k);
  }
  await page.keyboard.press("ArrowLeft"); // the title alone: the deck moves back
  await expect(page).toHaveURL(/#title$/);
});

test("reloading on a stepped slide lands on it complete, with the clock kept", async ({ page }) => {
  await openSlide(page, "title");
  await page.keyboard.press("ArrowRight"); // the first move starts the clock
  await page.keyboard.press("ArrowRight");
  await expectAt(page, "problem", 1);
  const count = await stepsOf(page, "problem");
  const started = await page.evaluate(() => sessionStorage.getItem("fairshare.deck.startedAt"));
  expect(started).not.toBeNull();
  await page.reload();
  await expect(page.locator("[data-deck-ready]")).toBeAttached();
  await expectAt(page, "problem", count);
  await expect(stepRoot(page, "problem").locator("[data-step]:visible")).toHaveCount(count);
  expect(await page.evaluate(() => sessionStorage.getItem("fairshare.deck.startedAt"))).toBe(started);
  await page.keyboard.press("ArrowRight"); // from complete, one press moves on
  await expectAt(page, "what", 0);
});

test("returning from the Ask demo lands on ask complete, with the clock kept", async ({ page, context }) => {
  await mockApp(context);
  await openSlide(page, "query-opener");
  await page.keyboard.press("ArrowRight"); // the first move starts the clock, and ask arrives on its title
  await expectAt(page, "ask", 0);
  const count = await stepsOf(page, "ask");
  await page.keyboard.press("ArrowRight");
  await expectAt(page, "ask", 1);
  const started = await page.evaluate(() => sessionStorage.getItem("fairshare.deck.startedAt"));
  expect(started).not.toBeNull();
  await page.getByRole("button", { name: "Ask it live" }).click();
  await expect(page.locator("#ask")).toHaveValue(question);
  await back(page).click();
  await expectAt(page, "ask", count);
  await expect(stepRoot(page, "ask").locator("[data-step]:visible")).toHaveCount(count);
  expect(await page.evaluate(() => sessionStorage.getItem("fairshare.deck.startedAt"))).toBe(started);
  await page.keyboard.press("ArrowRight"); // from complete, one press moves on
  await expect(page).not.toHaveURL(/#ask$/);
});

test("the notes window says which point the deck is on, and draws the slide at that point", async ({ page, context }) => {
  await context.route("**/api/agencies", (r) => r.fulfill({ json: [] }));
  await openSlide(page, "title");
  const [notes] = await Promise.all([context.waitForEvent("page"), page.keyboard.press("p")]);
  const now = notes.locator("[data-now]");
  await expect(now).toHaveAttribute("data-now", "title");
  const point = notes.getByText(/^Point \d+ of \d+$/);
  await expect(point).toHaveCount(0); // the welcome has no points
  await page.keyboard.press("ArrowRight");
  await expect(now).toHaveAttribute("data-now", "problem");
  const count = await stepsOf(page, "problem");
  const small = notes.locator("main [data-step-current]"); // the slide on the screen, drawn small
  for (let k = 0; k <= count; k++) {
    if (k > 0) await page.keyboard.press("ArrowRight");
    await expectAt(page, "problem", k);
    await expect(point).toHaveText(`Point ${k} of ${count}`);
    await expect(small).toHaveAttribute("data-step-current", String(k));
  }
  await notes.keyboard.press("ArrowLeft"); // a press in the notes window takes a point back in the deck, and the line follows
  await expectAt(page, "problem", count - 1);
  await expect(point).toHaveText(`Point ${count - 1} of ${count}`);
  await expect(small).toHaveAttribute("data-step-current", String(count - 1));
  const next = notes.locator("aside [data-step-current]"); // the next slide is drawn complete
  await expect(next).toHaveAttribute("data-step-current", (await next.getAttribute("data-step-count"))!);
});

test("a jump from the notes window's outline arrives on a slide's title going forward, and complete going back", async ({ page, context }) => {
  await context.route("**/api/agencies", (r) => r.fulfill({ json: [] }));
  await openSlide(page, "title");
  const [notes] = await Promise.all([context.waitForEvent("page"), page.keyboard.press("p")]);
  await expect(notes.locator("[data-now]")).toHaveAttribute("data-now", "title");
  await notes.getByRole("button", { name: "A live question in Ask", exact: true }).click();
  await expectAt(page, "ask", 0);
  await expect(notes.getByText(`Point 0 of ${await stepsOf(page, "ask")}`, { exact: true })).toBeVisible();
  await notes.getByRole("button", { name: "Two slow steps today", exact: true }).click();
  await expectAt(page, "problem", await stepsOf(page, "problem"));
});

test("the notes window's outline groups every slide under its part, in the order of the talk, and the backup slides come last", async ({ context }) => {
  await context.route("**/api/agencies", (r) => r.fulfill({ json: [] }));
  const notes = await context.newPage();
  await notes.goto("/present?notes");
  const parts = ["Welcome", "Two slow steps", "Ask and Delegate", "Where the numbers come from", "Checks and misses", "Starting at AA", "Thank you", "Backup"];
  const heads = await notes.getByRole("navigation", { name: "Every slide" }).getByRole("heading", { level: 3 }).allTextContents();
  const at = heads.map((h) => parts.indexOf(h));
  expect(at, `the headings ${heads.join(", ")}`).not.toContain(-1);
  expect(at, "in the order of the talk").toEqual([...at].sort((a, b) => a - b));
  expect([heads[0], heads.at(-1)]).toEqual(["Welcome", "Backup"]);
  expect(heads.filter((h) => parts.slice(1, 6).includes(h)), "the five topics").toEqual(parts.slice(1, 6));
  const under = (part: string) => notes.locator("nav section", { has: notes.getByRole("heading", { name: part, level: 3, exact: true }) });
  await expect(under("Two slow steps").getByRole("button", { name: "Two slow steps today", exact: true })).toBeVisible();
  await expect(under("Backup").getByRole("button", { name: "Five words in plain English", exact: true })).toBeVisible();
});

test("a checkpoint's time stays on one line in the notes window, and its name wraps instead", async ({ context }) => {
  await context.route("**/api/agencies", (r) => r.fulfill({ json: [] }));
  const notes = await context.newPage();
  await notes.goto("/present?notes");
  const rows = notes.locator("li", { hasText: /by \d+:\d\d$/ });
  await expect(rows).toHaveCount(5);
  // a wider face than the test browser's, so its longest name and its time do not both fit the 280px column on one line
  await notes.addStyleTag({ content: "[data-now] li * { letter-spacing: 0.08em !important; }" });
  const lines = await rows.evaluateAll((lis) => lis.map((li) => ({ row: li.textContent ?? "", time: li.lastElementChild!.getBoundingClientRect().height })));
  for (const l of lines) expect(l.time, `${l.row}: the time wraps`).toBeLessThan(30);
});

// The notes window pings the warehouse when it opens and every eight minutes, and a failed ping used to say nothing. Its
// timers are fake here, so the test can make eight minutes pass; the window is opened on its own, which it allows.
test("the notes window says when the warehouse last answered, and says so when a ping fails", async ({ context }) => {
  let down = false;
  await context.route("**/api/agencies", (r) => (down ? r.fulfill({ status: 500, json: { message: "down" } }) : r.fulfill({ json: [] })));
  const notes = await context.newPage();
  await notes.clock.install();
  await notes.goto("/present?notes");
  const line = notes.getByRole("status").filter({ hasText: /warehouse/i });
  await expect(line).toHaveText(/^The warehouse is awake\. It last answered at \d{1,2}:\d{2} [AP]M\.$/);
  const first = (await line.textContent())!;
  down = true;
  await notes.clock.fastForward("08:01"); // the eight-minute ping fires and fails
  await expect(line).toHaveText(/^The last check failed\. The warehouse last answered at \d{1,2}:\d{2} [AP]M\.$/);
  await expect(line).toHaveClass(/text-red/);
  down = false;
  await notes.clock.fastForward("08:01");
  await expect(line).toHaveText(/^The warehouse is awake\. It last answered at \d{1,2}:\d{2} [AP]M\.$/);
  expect(await line.textContent(), "the second good ping is a later one").not.toBe(first);
});

test("a window whose first ping fails says the warehouse has not answered", async ({ context }) => {
  await context.route("**/api/agencies", (r) => r.fulfill({ status: 500, json: { message: "down" } }));
  const notes = await context.newPage();
  await notes.goto("/present?notes");
  await expect(notes.getByRole("status").filter({ hasText: /warehouse/i })).toHaveText("The warehouse has not answered yet.");
});

// The mode Pane holds the chats or the agent list; the way back, Present and the signed-in line sit under it. In a short window
// the Pane scrolls inside its own box, so no row runs over the rows under it, with the sidebar open or collapsed. 600 is a
// laptop window with its toolbars; 400 makes even the collapsed rail overflow.
for (const height of [600, 400]) {
  for (const collapsed of [false, true]) {
    test(`at 1280 by ${height} the sidebar's agent list scrolls in its pane and the Present row stays clear, sidebar ${collapsed ? "collapsed" : "open"}`, async ({ page, context }) => {
      const first = catalog.agents[0];
      const four = [["precall", "Monday pre-call pack"], ["watch", "Agreement watch"], ["prospect", "Prospect research"], ["mismatch", "CRM check"]]
        .map(([key, name]) => ({ ...first, key, name }));
      await mockApp(context);
      await context.route("**/api/agents", (r) => r.fulfill({ json: { ...catalog, agents: four } }));
      await page.setViewportSize({ width: 1280, height });
      await page.addInitScript(([c]) => {
        localStorage.setItem("fairshare.sidebar", c);
        localStorage.setItem("fairshare.mode", '"delegate"');
        sessionStorage.setItem("fairshare.deck.return", "ask"); // the way back shows
      }, [String(collapsed)]);
      await page.goto("/");
      const pane = page.locator("nav [data-pane]");
      await expect(pane).toBeVisible();
      await expect(pane.getByRole("button", { name: /CRM check/ })).toHaveCount(1);
      const box = async (l: Locator) => (await l.boundingBox())!;
      const p = await box(pane);
      const way = await box(page.getByRole("link", { name: "Back to the deck" }));
      const present = await box(page.getByRole("link", { name: "Present" }));
      expect(await pane.evaluate((el) => getComputedStyle(el).overflowY), "the pane scrolls").toBe("auto");
      expect(p.y + p.height, "the pane ends above the way back").toBeLessThanOrEqual(way.y + 0.5);
      expect(way.y + way.height, "the way back ends above Present").toBeLessThanOrEqual(present.y + 0.5);
      expect(present.y + present.height, "Present is on the screen").toBeLessThanOrEqual(height);
      // the last agent is inside the pane's box once scrolled to, and never down on the rows below it
      const last = pane.getByRole("button", { name: /CRM check/ });
      await last.scrollIntoViewIfNeeded();
      const l = await box(last);
      expect(l.y >= p.y - 0.5 && l.y + l.height <= p.y + p.height + 0.5, `the last agent ${JSON.stringify(l)} is inside the pane ${JSON.stringify(p)}`).toBe(true);
    });
  }
}
