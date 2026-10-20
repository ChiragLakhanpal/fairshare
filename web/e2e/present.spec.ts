import { expect, test, type Page } from "@playwright/test";

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
