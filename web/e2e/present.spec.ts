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
