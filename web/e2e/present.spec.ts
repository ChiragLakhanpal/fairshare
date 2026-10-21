import { chromium, expect, test, type BrowserContext, type Locator, type Page } from "@playwright/test";
import { slides } from "../src/deck/slides";
import { copy } from "../src/copy";
import { FRAME_FALLBACK_MS, isTopic, KEYS, onPath, stepCount, TOPIC_ORDER, TOPICS, type PathName, type Slide } from "../src/lib/deck";

const FONTS = /fonts\.(googleapis|gstatic)\.com/;
test.beforeEach(async ({ context }) => {
  await context.route(FONTS, (r) => r.abort()); // the font stylesheet holds the controller back
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
/** The button in the notes window's outline that sends the deck to a slide. */
const outlined = (notes: Page, id: string) => notes.locator(`nav [data-outline="${id}"]`);
/** Sends the deck to a slide as the notes window's outline does, from a channel in the deck's own page. */
const goTo = (page: Page, id: string) =>
  page.evaluate((id) => {
    const channel = new BroadcastChannel("fairshare-deck");
    channel.postMessage({ t: "go", id });
    channel.close();
  }, id);
/** Keys sent from the notes window in one go, all queued on the channel before the deck renders once. */
const burst = (notes: Page, action: "next" | "prev", n: number) =>
  notes.evaluate(({ action, n }) => {
    const channel = new BroadcastChannel("fairshare-deck");
    for (let i = 0; i < n; i++) channel.postMessage({ t: "key", action });
    channel.close();
  }, { action, n });

// Every motion item of the framed diagram: its step, and its opacity as the deck shows it.
const itemStates = (page: Page) =>
  page.frameLocator("iframe[data-slide-frame]").locator("[data-motion-item]")
    .evaluateAll((els) => els.map((el) => ({ step: Number(el.getAttribute("data-step")), opacity: getComputedStyle(el).opacity })));

test("an animated slide takes as many presses as it has steps, then the deck moves", async ({ page }) => {
  await openSlide(page, "stack-opener");
  await page.keyboard.press("ArrowRight"); // a slide arrives on its first step going forward
  await expect(page).toHaveURL(/#system$/);
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

// What an animated slide paints, a frame at a time from the page's first one: whether its thumb (the finished figure) is visible, and where the
// frame's figure stands once the frame shows (its step of its count). A flash that lasts a frame is a sample, which one look at one moment
// would miss. The first sample is the slide's mount, the clock the fallback is measured from.
type Painted = { t: number; thumb: boolean; frame: string | null };
const watchFigure = (page: Page) => page.addInitScript(() => {
  const painted: Painted[] = [];
  (window as unknown as { __painted: Painted[] }).__painted = painted;
  const tick = () => {
    const iframe = document.querySelector<HTMLIFrameElement>("iframe[data-slide-frame]");
    if (iframe) {
      const thumb = iframe.parentElement?.querySelector<HTMLElement>("img[data-thumb]");
      let place: string | null = null;
      try {
        const root = iframe.contentDocument?.querySelector<HTMLElement>("[data-motion-root]");
        if (root && getComputedStyle(iframe).visibility === "visible") place = `${root.dataset.stepCurrent}/${root.dataset.stepCount}`;
      } catch {
        place = null;
      }
      painted.push({ t: performance.now(), thumb: !!thumb && getComputedStyle(thumb).visibility === "visible", frame: place });
    }
    requestAnimationFrame(tick);
  };
  requestAnimationFrame(tick);
});
const painted = (page: Page) => page.evaluate(() => (window as unknown as { __painted: Painted[] }).__painted);

/** Holds back the pipeline figure's page, the frame's document and nothing else (in dev the same file is also served as the ?url import
 * module), until the function this returns is called: a frame that is slow to start, whose time before it is ready a test can then look at. */
async function holdFrame(context: BrowserContext): Promise<() => void> {
  let release = () => {};
  const held = new Promise<void>((done) => (release = done));
  await context.route(/06-data-pipeline-animated[^/]*\.html/, async (r) => {
    if (r.request().resourceType() === "document") await held;
    await r.continue();
  });
  return release;
}

test("a frame that never starts shows the finished figure only after FRAME_FALLBACK_MS from its slide, and the first press moves the deck", async ({ page, context }) => {
  await watchFigure(page);
  // only the frame's page: in dev the same file is also served as the ?url import module
  await context.route(/-animated[^/]*\.html/, (r) => (r.request().resourceType() === "document" ? r.abort() : r.continue()));
  await page.goto("/present#system");
  await expect(slideAt(page, "system")).toBeVisible();
  const thumb = slideAt(page, "system").locator("img[data-thumb]");
  await expect(thumb, "nothing of the figure before the fallback").toBeHidden();
  await expect(thumb).toBeVisible({ timeout: FRAME_FALLBACK_MS + 5000 });
  const seen = await painted(page);
  const first = seen.find((x) => x.thumb);
  expect(first, "the finished figure showed").toBeTruthy();
  // from the slide's first painted frame, on the page's own clock: not a frame before the fallback, and not long after it (it comes 20 to 30ms
  // after FRAME_FALLBACK_MS here; the margin below is for a slow machine, and still tells the fallback from a thumb that shows early)
  const waited = first!.t - seen[0].t;
  expect(waited, "the finished figure waits for the fallback").toBeGreaterThanOrEqual(FRAME_FALLBACK_MS - 150);
  expect(waited, "and comes when it is due").toBeLessThan(FRAME_FALLBACK_MS + 1000);
  await page.keyboard.press("ArrowRight"); // a frame that is not ready counts as zero steps
  await expect(page).not.toHaveURL(/#system$/);
});

test("a frame that gets ready in time, even a slow one, never paints the finished figure, and its figure shows at its first step", async ({ page, context }) => {
  await watchFigure(page);
  const release = await holdFrame(context);
  await openSlide(page, "elevator-opener");
  await page.keyboard.press("ArrowRight");
  await expect(slideAt(page, "pipeline")).toBeVisible();
  await page.waitForTimeout(FRAME_FALLBACK_MS / 2); // slow, but inside the time it is given
  release();
  await expect(ready(page)).toBeVisible();
  await expect(root(page)).toHaveAttribute("data-step-current", "0");
  await page.waitForTimeout(300); // and a little of the frame showing, to sample
  const seen = await painted(page);
  expect(seen.length, "frames were sampled through the wait").toBeGreaterThan(30);
  expect(seen.filter((x) => x.thumb), "no frame painted the finished figure").toEqual([]);
  const shown = seen.filter((x) => x.frame !== null);
  expect(shown.length, "the frame was painted").toBeGreaterThan(5);
  expect(new Set(shown.map((x) => x.frame!.split("/")[0])), "and every frame of it painted the first step, never a later one").toEqual(new Set(["0"]));
});

test("a frame that gets ready after the finished figure has shown in its place arrives whole, with no step of it to come", async ({ page, context }) => {
  await watchFigure(page);
  const release = await holdFrame(context);
  await openSlide(page, "elevator-opener");
  await page.keyboard.press("ArrowRight");
  const thumb = slideAt(page, "pipeline").locator("img[data-thumb]");
  await expect(thumb, "the finished figure stands in for a frame that is late").toBeVisible({ timeout: FRAME_FALLBACK_MS + 5000 });
  release(); // the room has been looking at the whole figure, so the frame does not start it over at its first step
  await expect(ready(page)).toBeVisible();
  const count = (await root(page).getAttribute("data-step-count"))!;
  await expect(root(page)).toHaveAttribute("data-step-current", count); // the slide came going forward, and the frame is whole all the same
  await expect(thumb, "the frame has taken the thumb's place").toBeHidden();
  const seen = await painted(page);
  expect(new Set(seen.filter((x) => x.frame !== null).map((x) => x.frame)), "every frame of it painted the whole figure").toEqual(new Set([`${count}/${count}`]));
});

test("an animated slide shows nothing of its figure before its frame is ready, and once ready no step it has not reached", async ({ page, context }) => {
  const release = await holdFrame(context); // the time before the frame is ready can be looked at
  await openSlide(page, "elevator-opener");
  await page.keyboard.press("ArrowRight");
  await expect(slideAt(page, "pipeline")).toBeVisible();
  await expect(page.locator("iframe[data-slide-frame]")).not.toHaveAttribute("data-ready", "1");
  await expect(slideAt(page, "pipeline").locator("img[data-thumb]"), "no finished figure before the frame is ready").toBeHidden();
  release();
  await expect(ready(page)).toBeVisible();
  await expect(root(page)).toHaveAttribute("data-step-current", "0");
  for (const item of await itemStates(page)) expect(item.opacity, `step ${item.step} before its press`).toBe("0"); // invisible, not faded
  await expect(page.frameLocator("iframe[data-slide-frame]").locator('[data-brand="aa-logo"]'), "the deck's frame draws the one logo").toBeHidden();
  await page.keyboard.press("ArrowRight");
  await expect(root(page)).toHaveAttribute("data-step-current", "1");
  await expect.poll(async () => (await itemStates(page)).filter((i) => i.step === 1).map((i) => i.opacity)).toEqual(["1"]);
  for (const item of await itemStates(page)) if (item.step > 1) expect(item.opacity, `step ${item.step} before its press`).toBe("0");
});

test("arriving back on an animated slide shows its whole figure, on its last step, and a press forward from there moves on", async ({ page }) => {
  await openSlide(page, "sieve-opener");
  await page.keyboard.press("ArrowLeft");
  await expect(page).toHaveURL(/#moved$/);
  await expect(ready(page)).toBeVisible();
  const count = (await root(page).getAttribute("data-step-count"))!;
  await expect(root(page)).toHaveAttribute("data-step-current", count);
  expect((await itemStates(page)).map((i) => i.opacity).every((o) => o === "1"), "every step shows").toBe(true);
  await page.keyboard.press("ArrowRight"); // nothing is left to say here, so the press moves the deck
  await expect(page).toHaveURL(/#sieve-opener$/);
  await page.keyboard.press("ArrowLeft"); // and back again: whole, with a press back taking one step off
  await expect(page).toHaveURL(/#moved$/);
  await expect(ready(page)).toBeVisible();
  await expect(root(page)).toHaveAttribute("data-step-current", count);
  await page.keyboard.press("ArrowLeft");
  await expect(root(page)).toHaveAttribute("data-step-current", String(Number(count) - 1));
});

// revenue's notes recede as the next one comes, and the last one leads when the figure arrives whole: going back, and after a load. Its lines
// are drawn and its dots and years are in at once: the arrival finishes the page's animations (arrive in lib/deck.ts), which a figure that draws
// itself would otherwise play out in front of the room.
test("revenue arrives whole going back and after a load: its lines drawn at once, every note shown, and the last note leading in ink", async ({ page }) => {
  const [INK, MUTED] = ["rgb(54, 73, 90)", "rgb(90, 113, 129)"];
  const whole = async () => {
    await expect(ready(page)).toBeVisible();
    const figure = page.frameLocator("iframe[data-slide-frame]");
    const count = Number(await root(page).getAttribute("data-step-count"));
    await expect(root(page)).toHaveAttribute("data-step-current", String(count));
    const notes = figure.locator("[data-note]");
    await expect(notes).toHaveCount(count - 1);
    // all of it at the moment the frame shows, with no wait for a transition or a draw to end
    expect(await notes.evaluateAll((els) => els.map((el) => getComputedStyle(el).fill)), "the last note leads in ink, the others recede").toEqual(
      Array.from({ length: count - 1 }, (_, i) => (i === count - 2 ? INK : MUTED)),
    );
    expect((await itemStates(page)).every((i) => i.opacity === "1"), "every step shows").toBe(true);
    expect(await figure.locator("path.draw-line").evaluateAll((els) => els.map((el) => getComputedStyle(el).strokeDashoffset)), "both lines are drawn").toEqual(["0px", "0px"]);
    expect(await figure.locator(".draw-dot").evaluateAll((els) => els.map((el) => getComputedStyle(el).opacity === "1")).then((all) => all.length > 2 && all.every(Boolean)), "the dots and the years are in").toBe(true);
    expect(await figure.locator("*").evaluateAll((els) => els.flatMap((el) => el.getAnimations()).filter((a) => a.playState !== "finished" && Number.isFinite(a.effect?.getComputedTiming().endTime as number)).length), "nothing is left to play").toBe(0);
  };
  await openSlide(page, "checks"); // a load shows it complete, so a press for each point takes it back to its title, and one more goes back
  const points = await stepsOf(page, "checks");
  for (let i = 0; i <= points; i++) await page.keyboard.press("ArrowLeft");
  await expect(page).toHaveURL(/#revenue$/);
  await whole();
  await openSlide(page, "revenue"); // a load
  await whole();
});

test("revenue draws its two lines on arrival, then brings in the band and one note per press", async ({ page }) => {
  await openSlide(page, "seats");
  await page.keyboard.press("ArrowRight"); // revenue arrives on its first step going forward
  await expect(page).toHaveURL(/#revenue$/);
  await expect(ready(page)).toBeVisible();
  await expect(root(page)).toHaveAttribute("data-step-current", "0");
  const figure = page.frameLocator("iframe[data-slide-frame]");
  const lines = figure.locator("path.draw-line");
  await expect(lines).toHaveCount(2);
  // each line traces itself once and ends drawn, and the dots come in after it
  const names = await lines.evaluateAll((els) => els.map((el) => el.getAnimations().map((a) => (a as CSSAnimation).animationName)));
  expect(names, "the deck's embed mode plays the draw-in").toEqual([["aa-draw-line"], ["aa-draw-line"]]);
  await expect.poll(() => lines.evaluateAll((els) => els.map((el) => getComputedStyle(el).strokeDashoffset))).toEqual(["0px", "0px"]);
  await expect.poll(() => figure.locator("circle.draw-dot").evaluateAll((els) => els.length > 0 && els.every((el) => getComputedStyle(el).opacity === "1"))).toBe(true);
  // the dots and the two years come in after the lines: each waits out the lines' draw (900ms), then fades in over 300ms
  await expect(figure.locator("text.draw-dot"), "each line ends in its year").toHaveText(["2025", "2026"]);
  const timing = (sel: string) => figure.locator(sel).evaluateAll((els) => els.map((el) => {
    const a = el.getAnimations()[0] as CSSAnimation;
    const t = a.effect!.getTiming();
    return `${a.animationName} ${t.delay}ms then ${t.duration}ms`;
  }));
  expect(new Set(await timing("path.draw-line")), "the lines draw over 900ms").toEqual(new Set(["aa-draw-line 0ms then 900ms"]));
  expect(new Set(await timing("circle.draw-dot, text.draw-dot")), "the dots and the years follow the lines").toEqual(new Set(["aa-draw-dot 900ms then 300ms"]));
  for (const item of await itemStates(page)) expect(item.opacity, `step ${item.step} before its press`).toBe("0");
  const count = Number(await root(page).getAttribute("data-step-count"));
  // the note on the current press leads in ink, and an earlier one recedes to the muted text
  const [INK, MUTED] = ["rgb(54, 73, 90)", "rgb(90, 113, 129)"];
  const notes = figure.locator("[data-note]");
  await expect(notes).toHaveCount(count - 1);
  const fills = () => notes.evaluateAll((els) => els.map((el) => getComputedStyle(el).fill));
  for (let step = 1; step <= count; step++) {
    await page.keyboard.press("ArrowRight");
    await expect(root(page)).toHaveAttribute("data-step-current", String(step));
    const shown = async () => (await itemStates(page)).map((i) => (i.step <= step ? i.opacity === "1" : i.opacity === "0")).every(Boolean);
    await expect.poll(shown, `the band, then one note a press: step ${step}`).toBe(true);
    await expect.poll(fills, `step ${step}`).toEqual(Array.from({ length: count - 1 }, (_, i) => (i + 2 === step ? INK : MUTED)));
  }
  await page.keyboard.press("ArrowRight");
  await expect(page).toHaveURL(/#checks$/);
});

test("the seven numbers come one card a press over numbers and gaps, the newest in ink, and each page closes on where they live", async ({ page }) => {
  const [INK, MUTED] = ["rgb(54, 73, 90)", "rgb(90, 113, 129)"];
  await openSlide(page, "checks"); // a load lands complete, so the next press moves on
  for (const id of ["numbers", "gaps"]) {
    await page.keyboard.press("ArrowRight"); // each arrives on its first step going forward
    await expect(page).toHaveURL(new RegExp(`#${id}$`));
    await expect(ready(page)).toBeVisible();
    await expect(root(page)).toHaveAttribute("data-step-current", "0");
    for (const item of await itemStates(page)) expect(item.opacity, `${id}: step ${item.step} before its press`).toBe("0");
    const figure = page.frameLocator("iframe[data-slide-frame]");
    const count = Number(await root(page).getAttribute("data-step-count"));
    const cards = figure.locator("[data-motion-item][data-recede]");
    await expect(cards, `${id}: a card a press, then the close`).toHaveCount(count - 1);
    // each card's words as one color, and its blue outline: the card on the current press in ink and outlined, every other card muted
    const fills = () => cards.evaluateAll((els) => els.map((el) => [...new Set([...el.querySelectorAll("text")].map((t) => getComputedStyle(t).fill))]));
    const outlines = () => cards.evaluateAll((els) => els.map((el) => getComputedStyle(el.querySelector("[data-lead]")!).strokeOpacity));
    for (let step = 1; step <= count; step++) {
      await page.keyboard.press("ArrowRight");
      await expect(root(page)).toHaveAttribute("data-step-current", String(step));
      const shown = async () => (await itemStates(page)).every((i) => (i.step <= step ? i.opacity === "1" : i.opacity === "0"));
      await expect.poll(shown, `${id}: one card a press, step ${step}`).toBe(true);
      await expect.poll(fills, `${id}: the newest card leads, step ${step}`).toEqual(Array.from({ length: count - 1 }, (_, i) => [i + 1 === step ? INK : MUTED]));
      await expect.poll(outlines, `${id}: only the newest card is outlined, step ${step}`).toEqual(Array.from({ length: count - 1 }, (_, i) => (i + 1 === step ? "1" : "0")));
    }
    await expect(figure.locator("[data-where]").first()).toContainText("Six of the seven numbers"); // the last press is where they live
  }
  await page.keyboard.press("ArrowRight");
  await expect(page).toHaveURL(/#share-fair$/);
});

test("share against fair share shows its agencies on arrival, then one thing a press, the newest note leading and AA share's values in blue", async ({ page }) => {
  const [INK, MUTED, ACCENT] = ["rgb(54, 73, 90)", "rgb(90, 113, 129)", "rgb(0, 108, 191)"];
  await openSlide(page, "gaps"); // a load lands complete, so the next press moves on
  await page.keyboard.press("ArrowRight"); // share-fair arrives on its first step going forward
  await expect(page).toHaveURL(/#share-fair$/);
  await expect(ready(page)).toBeVisible();
  await expect(root(page)).toHaveAttribute("data-step-current", "0");
  const figure = page.frameLocator("iframe[data-slide-frame]");
  await expect(figure.locator("[data-row-label]"), "every agency's name shows on arrival").toHaveCount(12);
  await expect(figure.locator("[data-row-label]").first()).toBeVisible();
  for (const item of await itemStates(page)) expect(item.opacity, `step ${item.step} before its press`).toBe("0");
  const count = Number(await root(page).getAttribute("data-step-count"));
  // the notes that recede: each one's words without the values that keep their color, as one color
  const notes = figure.locator("[data-motion-item][data-recede]");
  const noteSteps = await notes.evaluateAll((els) => els.map((el) => Number(el.getAttribute("data-step"))));
  expect(noteSteps.length, "the sentence about the made-up seat shares and two callouts").toBe(3);
  const fills = () => notes.evaluateAll((els) => els.map((el) => [...new Set([...el.querySelectorAll("text:not([data-keep])")].map((t) => getComputedStyle(t).fill))]));
  const kept = () => figure.locator("text[data-keep]").evaluateAll((els) => els.map((el) => getComputedStyle(el).fill));
  for (let step = 1; step <= count; step++) {
    await page.keyboard.press("ArrowRight");
    await expect(root(page)).toHaveAttribute("data-step-current", String(step));
    const shown = async () => (await itemStates(page)).every((i) => (i.step <= step ? i.opacity === "1" : i.opacity === "0"));
    await expect.poll(shown, `one thing a press, step ${step}`).toBe(true);
    await expect.poll(fills, `the newest note leads, step ${step}`).toEqual(noteSteps.map((s) => [s === step ? INK : MUTED]));
    await expect.poll(kept, `AA share's values stay blue, step ${step}`).toEqual([ACCENT, ACCENT]);
  }
  await page.keyboard.press("ArrowRight");
  await expect(page).toHaveURL(/#moved$/);
});

test("delegate shows its lanes on arrival, then its flow one stage a press in the order it runs, and then the pre-call pack", async ({ page }) => {
  await openSlide(page, "riffle-opener");
  await page.keyboard.press("ArrowRight"); // delegate arrives on its first step going forward
  await expect(page).toHaveURL(/#delegate$/);
  await expect(ready(page)).toBeVisible();
  await expect(root(page)).toHaveAttribute("data-step-current", "0");
  const figure = page.frameLocator("iframe[data-slide-frame]");
  await expect(figure.locator("[data-lane]"), "the five lanes and their names show on arrival").toHaveCount(5);
  for (const lane of await figure.locator("[data-lane]").all()) await expect(lane).toBeVisible();
  for (const item of await itemStates(page)) expect(item.opacity, `step ${item.step} before its press`).toBe("0");
  // a step of the flow shows once the press that brings it has come, and not before
  const shownNodes = () => figure.locator("[data-node]").evaluateAll((els) =>
    els.filter((el) => getComputedStyle(el.closest("[data-motion-item]")!).opacity === "1").map((el) => el.getAttribute("data-node")));
  const flow = [["job"], ["queries"], ["writer"], ["verifier", "waits"], ["review", "decide"], ["crm", "mail"]];
  const count = Number(await root(page).getAttribute("data-step-count"));
  expect(count, "a press for each stage of the flow").toBe(flow.length);
  for (let step = 1; step <= count; step++) {
    await page.keyboard.press("ArrowRight");
    await expect(root(page)).toHaveAttribute("data-step-current", String(step));
    const shown = async () => (await itemStates(page)).every((i) => (i.step <= step ? i.opacity === "1" : i.opacity === "0"));
    await expect.poll(shown, `one stage a press, step ${step}`).toBe(true);
    await expect.poll(async () => (await shownNodes()).sort(), `step ${step}`).toEqual(flow.slice(0, step).flat().sort());
  }
  await expect(figure.getByText("Nothing reaches the CRM or Outlook until a person approves.")).toBeVisible(); // the last press brings the caption
  await page.keyboard.press("ArrowRight");
  await expect(page).toHaveURL(/#precall$/);
});

test("at-aa shows its five layers on arrival, then what runs, what is built and what waits a press each, then the feeds hardest first, and then Azure", async ({ page }) => {
  const [INK, MUTED] = ["rgb(54, 73, 90)", "rgb(90, 113, 129)"];
  await openSlide(page, "limits"); // a load lands complete, so the next press moves on
  await page.keyboard.press("ArrowRight"); // at-aa arrives on its first step going forward
  await expect(page).toHaveURL(/#at-aa$/);
  await expect(ready(page)).toBeVisible();
  await expect(root(page)).toHaveAttribute("data-step-current", "0");
  const figure = page.frameLocator("iframe[data-slide-frame]");
  // the five layers stand on arrival as 01's static page draws them: every slab shown and in place, none of them a step
  const slabs = figure.locator("[data-part]");
  await expect(slabs).toHaveCount(5);
  const atRest = await slabs.evaluateAll((els) => els.map((el) => [getComputedStyle(el).opacity, getComputedStyle(el).transform]));
  expect(atRest, "the stack, assembled and still").toEqual(Array.from({ length: 5 }, () => ["1", "none"]));
  await expect(figure.locator('[data-role="name"]')).toHaveText(["Data", "Definitions", "Agents", "Checks", "The app"]);
  for (const item of await itemStates(page)) expect(item.opacity, `step ${item.step} before its press`).toBe("0");
  // a press each: a kind of mark with its legend entry, then the feeds beside their tables, hardest first
  const plan: [string[], string[]][] = [[["run"], []], [["built"], []], [["wait"], []], [[], ["fact_agency_sales_monthly"]], [[], ["fact_market_capacity"]],
    [[], ["fact_corporate_bookings", "contract_clauses"]], [[], ["crm_contacts", "agency_goals"]]];
  const count = Number(await root(page).getAttribute("data-step-count"));
  expect(count, "a press for each kind of mark, then four for the feeds").toBe(plan.length);
  const shown = (attr: string) => () => figure.locator(`[${attr}]`).evaluateAll((els, attr) =>
    [...new Set(els.filter((el) => getComputedStyle(el.closest("[data-motion-item]")!).opacity === "1").map((el) => el.getAttribute(attr)))], attr);
  // each step's words but the legend's heading, which keeps its color: the current step's in ink, every other step's muted
  const fills = () => figure.locator("[data-motion-item]").evaluateAll((els) => els.map((el) =>
    [Number(el.getAttribute("data-step")), [...new Set([...el.querySelectorAll("text:not([data-keep])")].map((t) => getComputedStyle(t).fill))]] as [number, string[]]));
  const steps = (await fills()).map(([s]) => s);
  for (let step = 1; step <= count; step++) {
    await page.keyboard.press("ArrowRight");
    await expect(root(page)).toHaveAttribute("data-step-current", String(step));
    const reached = async () => (await itemStates(page)).every((i) => (i.step <= step ? i.opacity === "1" : i.opacity === "0"));
    await expect.poll(reached, `step ${step}`).toBe(true);
    const marks = plan.slice(0, step).flatMap(([m]) => m);
    await expect.poll(shown("data-piece"), `the marks by step ${step}`).toEqual(marks);
    await expect.poll(shown("data-key"), `the legend by step ${step}, an entry with its marks`).toEqual(marks);
    await expect.poll(shown("data-feed"), `the feeds by step ${step}`).toEqual(plan.slice(0, step).flatMap(([, f]) => f));
    await expect.poll(fills, `the newest press leads, step ${step}`).toEqual(steps.map((s) => [s, [s === step ? INK : MUTED]]));
  }
  await page.keyboard.press("ArrowRight");
  await expect(page).toHaveURL(/#azure$/);
});

test("a load on an animated slide, a reload or the way back from a demo, shows its whole figure, and the first press moves on", async ({ page }) => {
  await openSlide(page, "pipeline");
  await expect(ready(page)).toBeVisible();
  await expect(root(page)).toHaveAttribute("data-step-current", (await root(page).getAttribute("data-step-count"))!);
  await page.keyboard.press("ArrowRight");
  await expect(page).toHaveURL(/#row$/);
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
  await openSlide(page, "agenda"); // a load lands complete, so the next press moves on
  const [notes] = await Promise.all([context.waitForEvent("page"), page.keyboard.press("p")]);
  const now = notes.locator("[data-now]");
  await expect(now).toHaveAttribute("data-now", "agenda");
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
  await expect(page).toHaveURL(/#precall$/); // the short path goes from Ask's demo to Delegate's
  await expect(now).toHaveAttribute("data-now", "precall");
  expect(pings).toBeGreaterThan(0);
});

const pointsOf = (id: string) => stepCount(slides.find((s) => s.id === id)!);

// A burst lands mid-slide, where a key skipped or doubled shows as a step short or a step over: through guardrails (four points), into evals
// (two) and on into evals-more (three), and back.
test("keys the notes window sends in a burst are applied in order, through one slide's points and into the next, and land mid-slide where the same keys one at a time do", async ({ page, context }) => {
  await context.route("**/api/agencies", (r) => r.fulfill({ json: [] }));
  await openSlide(page, "agenda");
  const [notes] = await Promise.all([context.waitForEvent("page"), page.keyboard.press("p")]);
  await expect(notes.locator("[data-now]")).toHaveAttribute("data-now", "agenda");
  const [guardrails, evals, more] = [pointsOf("guardrails"), pointsOf("evals"), pointsOf("evals-more")];
  expect(guardrails, "guardrails has more points than evals").toBeGreaterThan(evals);
  expect(evals, "evals has a point to land on in the middle").toBeGreaterThan(1);
  expect(more, "so does evals-more").toBeGreaterThan(2);
  const point = (k: number, n: number) => notes.getByText(`Point ${k} of ${n}`, { exact: true });
  await goTo(page, "guardrails"); // an outline jump lands a slide of the path on its first step
  await expectAt(page, "guardrails", 0);
  for (let i = 0; i < guardrails + 2; i++) await page.keyboard.press("ArrowRight"); // every point, the move, and the first point of evals
  await expectAt(page, "evals", 1);
  const single = await where(page);
  // the same keys from the same start, all at once: none skipped, none doubled, and the notes window shows the same place
  await goTo(page, "guardrails");
  await expectAt(page, "guardrails", 0);
  await burst(notes, "next", guardrails + 2);
  await expectAt(page, "evals", 1);
  expect(await where(page)).toEqual(single);
  await expect(point(1, evals)).toBeVisible();
  await expect(notes.locator("main [data-step-current]")).toHaveAttribute("data-step-current", "1");
  // on from the middle of evals, through its last point and into evals-more's second
  await burst(notes, "next", evals - 1 + 1 + 2);
  await expectAt(page, "evals-more", 2);
  await expect(notes.locator("[data-now]")).toHaveAttribute("data-now", "evals-more");
  await expect(point(2, more)).toBeVisible();
  // and back: two points down to its title, the move back onto evals, complete, and one point down from there
  await burst(notes, "prev", 2 + 1 + 1);
  await expectAt(page, "evals", evals - 1);
  await expect(notes.locator("[data-now]")).toHaveAttribute("data-now", "evals");
  await expect(point(evals - 1, evals)).toBeVisible();
});

test("a burst that goes through a diagram's steps and into the next slide's points lands mid-slide and applies each key once", async ({ page, context }) => {
  await context.route("**/api/agencies", (r) => r.fulfill({ json: [] }));
  await openSlide(page, "seats");
  await page.keyboard.press("ArrowRight"); // onto revenue, on its first step
  await expect(ready(page)).toBeVisible();
  await expect(root(page)).toHaveAttribute("data-step-current", "0");
  const steps = Number(await root(page).getAttribute("data-step-count"));
  const checks = pointsOf("checks");
  expect(checks, "checks has a point to land on in the middle").toBeGreaterThan(2);
  const [notes] = await Promise.all([context.waitForEvent("page"), page.keyboard.press("p")]);
  await expect(notes.locator("[data-now]")).toHaveAttribute("data-now", "revenue");
  await burst(notes, "next", steps + 1 + 2); // every step of the diagram, the move to the next slide, and two of its points
  await expectAt(page, "checks", 2);
  await expect(notes.locator("[data-now]")).toHaveAttribute("data-now", "checks");
  await expect(notes.getByText(`Point 2 of ${checks}`, { exact: true })).toBeVisible();
});

// A frame gets ready some time after its slide arrives, so a burst that has only just reached a diagram finds no steps there and goes on to
// the next slide, as a press on a frame that never gets ready does (Present.tsx, act).
test("a burst that reaches a diagram before its frame is ready counts no steps there, and moves on", async ({ page, context }) => {
  await context.route("**/api/agencies", (r) => r.fulfill({ json: [] }));
  await openSlide(page, "ask"); // a load lands complete, so the next key moves on
  const [notes] = await Promise.all([context.waitForEvent("page"), page.keyboard.press("p")]);
  await expect(notes.locator("[data-now]")).toHaveAttribute("data-now", "ask");
  await burst(notes, "next", 2); // onto director, whose frame cannot be ready between two queued keys, and off it
  await expect(page).toHaveURL(/#riffle-opener$/);
  await expect(notes.locator("[data-now]")).toHaveAttribute("data-now", "riffle-opener");
});

test("keys that come before the deck has drawn the one before still take the place that one left", async ({ page }) => {
  await openSlide(page, "agenda");
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
  await page.goto("/present#welcome");
  await expect(page.locator("[data-deck-ready]")).toBeAttached();
  const [notes] = await Promise.all([context.waitForEvent("page"), page.keyboard.press("p")]);
  await expect(notes.getByText("The clock starts on the first move.")).toBeVisible();
  const before = await page.evaluate(() => Date.now());
  await page.keyboard.press("ArrowRight"); // the welcome's planned half minute is already behind the talk
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

test("the sidebar entry opens the deck on the welcome", async ({ page, context }) => {
  await mockApp(context);
  await page.goto("/");
  await page.getByRole("link", { name: "Present" }).click();
  await expect(page).toHaveURL(/\/present/);
  await expect(page.locator('[data-slide="welcome"]')).toBeVisible();
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
    await context.route(FONTS, (r) => r.abort());
    await mockApp(context);
    const page = await context.newPage();
    await page.goto("/present#query-opener");
    await expect(page.locator("[data-deck-ready]")).toBeAttached();
    await page.keyboard.press("ArrowRight"); // ask arrives on its title
    await page.keyboard.press("ArrowRight"); // and brings in its first line
    await expectAt(page, "ask", 1);
    const lines = await stepsOf(page, "ask");
    expect(lines, "more than one line, so the slide left at its first line is not already complete").toBeGreaterThan(1);
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

test("an animated slide the browser restores from its cache shows its whole figure, as a load does", async ({ baseURL }) => {
  type Kept = { kept?: string };
  const browser = await chromium.launch({ channel: "chromium", ignoreDefaultArgs: ["--disable-back-forward-cache"], args: ["--enable-features=BackForwardCache"] });
  try {
    const context = await browser.newContext({ baseURL, viewport: { width: 1440, height: 900 } });
    await context.route(FONTS, (r) => r.abort());
    await mockApp(context);
    const page = await context.newPage();
    await page.goto("/present#stack-opener");
    await expect(page.locator("[data-deck-ready]")).toBeAttached();
    await page.keyboard.press("ArrowRight"); // system arrives on its first step
    await expect(ready(page)).toBeVisible();
    await page.keyboard.press("ArrowRight");
    await expect(root(page)).toHaveAttribute("data-step-current", "1");
    const count = (await root(page).getAttribute("data-step-count"))!;
    expect(Number(count), "more than one step, so the figure left on its first step is not already whole").toBeGreaterThan(1);
    await page.evaluate(() => { (window as unknown as Kept).kept = "the same page"; }); // a page that loads again loses it
    await page.goto("/"); // the deck's tab goes to the app, as a demo jump does
    await expect(page.locator("#ask")).toBeVisible();
    await page.goBack({ waitUntil: "commit" }); // a restore from the cache fires no load event
    await expect.poll(() => page.evaluate(() => (window as unknown as Kept).kept ?? null).catch(() => null), { message: "the browser restored the deck from its cache" }).toBe("the same page");
    // Playwright does not attach to the frames of a restored page, so the deck's own document reads the figure's place
    const place = () => page.evaluate(() => {
      const r = document.querySelector<HTMLIFrameElement>("iframe[data-slide-frame]")?.contentDocument?.querySelector<HTMLElement>("[data-motion-root]");
      return r ? `${r.dataset.stepCurrent} of ${r.dataset.stepCount}` : null;
    });
    await expect.poll(place).toBe(`${count} of ${count}`);
    // the whole figure shows at once: no animation or transition of it is left to play out in front of the room
    const playing = () => page.evaluate(() => {
      const doc = document.querySelector<HTMLIFrameElement>("iframe[data-slide-frame]")?.contentDocument;
      return (doc?.getAnimations() ?? []).filter((a) => a.playState !== "finished" && Number.isFinite(a.effect?.getComputedTiming().endTime as number)).length;
    });
    expect(await playing(), "the restore finishes the figure's transitions").toBe(0);
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

// The frame at a small window and a big one (the deck scales its 1280 by 720 stage to the window), measured in the deck's own faces: the header
// and the footer span the stage, the logo sits where the frame puts it, and each of the five topic names is drawn whole inside its own column,
// clear of its neighbours. A name is measured where its text is drawn (a Range's rectangle), not by the box that holds it, which a long name
// would overflow. One slide from each topic, so each name is lit (heavier, so wider) once; the longest, Where the numbers come from, is the
// one at risk.
for (const size of [{ width: 1024, height: 768 }, { width: 1920, height: 1080 }]) {
  test(`at ${size.width} by ${size.height} the logo, the five topic names and the footer sit inside the stage, whole and clear of each other, whichever topic is lit`, async ({ page, context }) => {
    test.setTimeout(90_000);
    await page.setViewportSize(size);
    await inTheDecksFaces(page, context, "problem");
    const scale = Math.min(size.width / 1280, size.height / 720);
    const near = (got: number, want: number, what: string) => expect.soft(Math.abs(got - want), `${what}: ${got} for ${want}`).toBeLessThanOrEqual(0.75);
    for (const id of ["problem", "ask", "row", "guardrails", "know"]) {
      await openSlide(page, id);
      await loadFaces(page);
      const slide = slideAt(page, id);
      const stage = (await slide.boundingBox())!;
      expect.soft(stage.x >= 0 && stage.y >= 0 && stage.x + stage.width <= size.width + 0.5 && stage.y + stage.height <= size.height + 0.5, `${id}: the stage is in the window`).toBe(true);
      near(stage.width / scale, 1280, `${id}: the stage's width`);
      near(stage.height / scale, 720, `${id}: the stage's height`);
      // every box in stage pixels (1280 by 720), whatever the window's scale
      const [header, footer, logo] = await Promise.all(['[data-frame="header"]', '[data-frame="footer"]', '[data-frame="header"] img'].map((sel) => slide.locator(sel).boundingBox()));
      const inStage = (b: { x: number; y: number; width: number; height: number }) => ({ x: (b.x - stage.x) / scale, y: (b.y - stage.y) / scale, r: (b.x + b.width - stage.x) / scale, b: (b.y + b.height - stage.y) / scale });
      const h = inStage(header!);
      const f = inStage(footer!);
      const l = inStage(logo!);
      [h.x, h.y, h.r, h.b].forEach((got, i) => near(got, [0, 0, 1280, 64][i], `${id}: the header's ${["left", "top", "right", "bottom"][i]}`));
      [f.x, f.r, f.b, f.y].forEach((got, i) => near(got, [0, 1280, 720, 690][i], `${id}: the footer's ${["left", "right", "bottom", "top"][i]}`));
      [l.x, l.y, l.b].forEach((got, i) => near(got, [40, 22, 44][i], `${id}: the logo's ${["left", "top", "bottom"][i]}`));
      expect.soft(l.r, `${id}: the logo ends before the tracker begins`).toBeLessThanOrEqual(300);
      const text = await slide.evaluate((root, [x, y, unit]) => {
        const at = (r: DOMRect) => ({ x: (r.x - x) / unit, y: (r.y - y) / unit, r: (r.right - x) / unit, b: (r.bottom - y) / unit });
        const ink = (el: Element) => {
          const range = document.createRange();
          range.selectNodeContents(el);
          return at(range.getBoundingClientRect());
        };
        return {
          names: [...root.querySelectorAll("[data-topic-name]")].map((el) => ({ name: el.textContent ?? "", ink: ink(el), column: at(el.closest("li")!.getBoundingClientRect()), cut: el.scrollWidth > el.clientWidth })),
          footer: [...root.querySelectorAll('[data-frame="footer"] span')].map((el) => ({ text: el.textContent ?? "", ink: ink(el) })),
        };
      }, [stage.x, stage.y, scale]);
      expect(text.names.map((n) => n.name), `${id}: the five topics, in order`).toEqual(TOPIC_ORDER.map((t) => TOPICS[t].name));
      text.names.forEach((n, i) => {
        expect.soft(n.cut, `${id}: ${n.name} is cut off by its box`).toBe(false);
        expect.soft(n.ink.x >= n.column.x - 0.5 && n.ink.r <= n.column.r + 0.5, `${id}: ${n.name} (${n.ink.x} to ${n.ink.r}) is drawn inside its column (${n.column.x} to ${n.column.r})`).toBe(true);
        expect.soft(n.ink.y >= h.y && n.ink.b <= h.b, `${id}: ${n.name} is drawn inside the header`).toBe(true);
        if (i > 0) expect.soft(n.ink.x - text.names[i - 1].ink.r, `${id}: ${text.names[i - 1].name} and ${n.name} are clear of each other`).toBeGreaterThanOrEqual(8);
      });
      expect.soft(text.names[0].ink.x - l.r, `${id}: the first name is clear of the logo`).toBeGreaterThan(8);
      expect.soft(text.names[4].ink.r, `${id}: the last name ends inside the right margin`).toBeLessThanOrEqual(1240);
      // the footer's two texts: the label at the left margin, the number ending at the right one (its trailing letter-space hangs past 1240), and a gap between
      const [label, number] = text.footer;
      expect.soft(label.ink.x, `${id}: the label starts at the left margin`).toBeGreaterThanOrEqual(39.5);
      expect.soft(number.ink.r, `${id}: the number ends at the right margin`).toBeLessThanOrEqual(1242);
      expect.soft(number.ink.x - label.ink.r, `${id}: the label and the number are clear of each other`).toBeGreaterThanOrEqual(16);
      for (const t of text.footer) expect.soft(t.ink.y >= f.y && t.ink.b <= f.b, `${id}: "${t.text}" is drawn inside the footer, which is inside the stage`).toBe(true);
    }
  });
}

test("the welcome and the thanks show the logo alone, a still shows no frame at all, and a backup slide says Backup", async ({ page }) => {
  for (const id of ["welcome", "thanks"]) {
    await openSlide(page, id);
    await expect(slideAt(page, id).locator('[data-frame="header"] img[src="/aa-logo.svg"]'), id).toBeVisible();
    await expect(slideAt(page, id).locator("[data-tracker]"), id).toHaveCount(0);
    await expect(slideAt(page, id).locator('[data-frame="footer"]'), id).toHaveCount(0);
  }
  await openSlide(page, "revenue"); // a figure: the whole frame
  await expect(slideAt(page, "revenue").locator('[data-frame="header"] img[src="/aa-logo.svg"]')).toBeVisible();
  await expect(slideAt(page, "revenue").locator("[data-tracker]")).toBeVisible();
  await expect(slideAt(page, "revenue").locator('[data-frame="footer"]')).toBeVisible();
  for (const id of ["ask-still", "precall-still"]) {
    await openSlide(page, id);
    await expect(slideAt(page, id).locator("[data-frame]"), id).toHaveCount(0);
  }
  await openSlide(page, "manager"); // a backup slide that is not a still
  await expect(slideAt(page, "manager").locator('[data-frame="footer"]')).toContainText(/Backup$/i);
  await expect(slideAt(page, "manager").locator("[data-tracker] [aria-current]")).toHaveCount(0);
});

test("the welcome hides its page's caption and shows the talk's title, his name, the role and the made-up data line", async ({ page }) => {
  await openSlide(page, "welcome");
  await expect(page.locator('iframe[data-live-frame][data-shown="1"]')).toBeVisible();
  await expect(page.frameLocator("iframe[data-live-frame]").locator(".caption")).toBeHidden();
  const byline = slideAt(page, "welcome").locator("[data-byline]");
  await expect(byline.getByRole("heading", { level: 1 })).toHaveText("Fairshare: sales answers you can check");
  for (const line of slides.find((s) => s.id === "welcome")!.byline!) await expect(byline.getByText(line, { exact: true })).toBeVisible();
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
  await openSlide(page, "agenda");
  await page.keyboard.press("ArrowRight");
  await expectAt(page, "problem", 0);
  const count = await stepsOf(page, "problem");
  expect(count).toBeGreaterThan(1);
  await expect(slideAt(page, "problem").getByRole("heading", { level: 1 })).toBeVisible();
  const shown = stepRoot(page, "problem").locator("[data-step]:visible");
  const read = stepRoot(page, "problem").locator('[data-step]:not([aria-hidden="true"])'); // what a screen reader can reach: the points and the question
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
  await openSlide(page, "agenda");
  await page.keyboard.press("ArrowRight");
  await expectAt(page, "problem", 0);
  const slide = slideAt(page, "problem");
  const title = slide.getByRole("heading", { level: 1 });
  const points = slide.locator("[data-step]"); // the two points, then the question to the room
  const wording = (i: number) => points.nth(i).locator(":scope > span").last();
  const titleAt = (await title.boundingBox())!.y;
  const count = await stepsOf(page, "problem");
  await expect(points).toHaveCount(count);
  for (let i = 0; i < count; i++) {
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
  await openSlide(page, "agenda");
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
  await openSlide(page, "agenda");
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
  await page.keyboard.press("ArrowLeft"); // the title alone: the deck moves back, onto the agenda complete
  await expect(page).toHaveURL(/#agenda$/);
  await expectAt(page, "agenda", await stepsOf(page, "agenda"));
});

test("reloading on a stepped slide lands on it complete, with the clock kept", async ({ page }) => {
  await openSlide(page, "agenda");
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
  expect(await page.evaluate(() => sessionStorage.getItem("fairshare.deck.startedAt")), "the move after the reload keeps the clock").toBe(started);
});

test("returning from the Ask demo lands on ask complete, with the clock kept", async ({ page, context }) => {
  await mockApp(context);
  await openSlide(page, "query-opener");
  await page.keyboard.press("ArrowRight"); // the first move starts the clock, and ask arrives on its title
  await expectAt(page, "ask", 0);
  const count = await stepsOf(page, "ask");
  expect(count, "more than one line, so the slide left at its first line is not already complete").toBeGreaterThan(1);
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
  expect(await page.evaluate(() => sessionStorage.getItem("fairshare.deck.startedAt")), "the move after the way back keeps the clock").toBe(started);
});

test("returning from the pre-call demo lands on precall complete, with the clock kept", async ({ page, context }) => {
  await mockApp(context);
  await page.goto("/present#precall");
  await expect(page.locator("[data-deck-ready]")).toBeAttached();
  await page.keyboard.press("ArrowRight"); // the first move starts the clock
  await expect(page).toHaveURL(/#stack-opener$/);
  await page.keyboard.press("ArrowLeft"); // and the way back is complete
  const count = await stepsOf(page, "precall");
  expect(count, "more than two lines, so a slide left two lines back is not already complete").toBeGreaterThan(2);
  await expectAt(page, "precall", count);
  await page.keyboard.press("ArrowLeft");
  await page.keyboard.press("ArrowLeft");
  await expectAt(page, "precall", count - 2);
  const started = await page.evaluate(() => sessionStorage.getItem("fairshare.deck.startedAt"));
  expect(started).not.toBeNull();
  await page.getByRole("button", { name: "Open the pre-call pack" }).click();
  await expect(page).toHaveURL(/\/(\?.*)?$/);
  await back(page).click();
  await expectAt(page, "precall", count);
  await expect(stepRoot(page, "precall").locator("[data-step]:visible")).toHaveCount(count);
  expect(await page.evaluate(() => sessionStorage.getItem("fairshare.deck.startedAt"))).toBe(started);
  await page.keyboard.press("ArrowRight"); // from complete, one press moves on
  await expect(page).toHaveURL(/#stack-opener$/);
  expect(await page.evaluate(() => sessionStorage.getItem("fairshare.deck.startedAt")), "the move after the way back keeps the clock").toBe(started);
});

test("reloading on a figure mid-talk lands on it whole, with the clock kept, and the first press moves on", async ({ page }) => {
  await openSlide(page, "stack-opener");
  await page.keyboard.press("ArrowRight"); // system arrives on its first step, and the first move starts the clock
  await expect(ready(page)).toBeVisible();
  await page.keyboard.press("ArrowRight");
  await expect(root(page)).toHaveAttribute("data-step-current", "1");
  const count = (await root(page).getAttribute("data-step-count"))!;
  expect(Number(count), "more than one step, so a figure left on its first is not already whole").toBeGreaterThan(1);
  const started = await page.evaluate(() => sessionStorage.getItem("fairshare.deck.startedAt"));
  expect(started).not.toBeNull();
  await page.reload();
  await expect(page.locator("[data-deck-ready]")).toBeAttached();
  await expect(ready(page)).toBeVisible();
  await expect(root(page)).toHaveAttribute("data-step-current", count);
  expect(await page.evaluate(() => sessionStorage.getItem("fairshare.deck.startedAt"))).toBe(started);
  await page.keyboard.press("ArrowRight"); // from whole, one press moves on
  await expect(page).toHaveURL(/#elevator-opener$/);
  expect(await page.evaluate(() => sessionStorage.getItem("fairshare.deck.startedAt")), "the move after the reload keeps the clock").toBe(started);
});

test("the notes window says which point the deck is on, and draws the slide at that point", async ({ page, context }) => {
  await context.route("**/api/agencies", (r) => r.fulfill({ json: [] }));
  await openSlide(page, "welcome");
  const [notes] = await Promise.all([context.waitForEvent("page"), page.keyboard.press("p")]);
  const now = notes.locator("[data-now]");
  await expect(now).toHaveAttribute("data-now", "welcome");
  const point = notes.getByText(/^Point \d+ of \d+$/);
  await expect(point).toHaveCount(0); // the welcome has no points
  await page.keyboard.press("ArrowRight");
  await expect(now).toHaveAttribute("data-now", "agenda");
  const count = await stepsOf(page, "agenda");
  const small = notes.locator("main [data-step-current]"); // the slide on the screen, drawn small
  for (let k = 0; k <= count; k++) {
    if (k > 0) await page.keyboard.press("ArrowRight");
    await expectAt(page, "agenda", k);
    await expect(point).toHaveText(`Point ${k} of ${count}`);
    await expect(small).toHaveAttribute("data-step-current", String(k));
  }
  await notes.keyboard.press("ArrowLeft"); // a press in the notes window takes a point back in the deck, and the line follows
  await expectAt(page, "agenda", count - 1);
  await expect(point).toHaveText(`Point ${count - 1} of ${count}`);
  await expect(small).toHaveAttribute("data-step-current", String(count - 1));
  const next = notes.locator("aside [data-step-current]"); // the next slide is drawn complete
  await expect(next).toHaveAttribute("data-step-current", (await next.getAttribute("data-step-count"))!);
});

test("a jump from the notes window's outline lands a slide of the path on its first step and a backup slide complete, whichever way it lies", async ({ page, context }) => {
  await context.route("**/api/agencies", (r) => r.fulfill({ json: [] }));
  await openSlide(page, "welcome");
  const [notes] = await Promise.all([context.waitForEvent("page"), page.keyboard.press("p")]);
  await expect(notes.locator("[data-now]")).toHaveAttribute("data-now", "welcome");
  await outlined(notes, "ask").click(); // forward
  await expectAt(page, "ask", 0);
  await expect(notes.getByText(`Point 0 of ${await stepsOf(page, "ask")}`, { exact: true })).toBeVisible();
  await outlined(notes, "problem").click(); // back, and still on its first step
  await expectAt(page, "problem", 0);
  await outlined(notes, "agents").click(); // a backup slide, read at once in the questions
  const tiles = await stepsOf(page, "agents");
  expect(tiles).toBeGreaterThan(0);
  await expectAt(page, "agents", tiles);
  await outlined(notes, "words").click(); // an earlier backup slide, complete too
  await expectAt(page, "words", await stepsOf(page, "words"));
  await outlined(notes, "guardrails").click(); // back onto the path, on its first step again
  await expectAt(page, "guardrails", 0);
});

test("the notes window's outline groups every slide under its part, in the order of the talk, and the backup slides come last", async ({ context }) => {
  await context.route("**/api/agencies", (r) => r.fulfill({ json: [] }));
  const notes = await context.newPage();
  await notes.goto("/present?notes");
  const parts = ["Welcome", "Two slow steps", "Ask and Delegate", "Where the numbers come from", "Checks and misses", "Starting at AA", "Thank you", "Backup"];
  const heads = await notes.getByRole("navigation", { name: "Every slide" }).getByRole("heading", { level: 3 }).allTextContents();
  expect(heads, "every part has slides, so every part is listed, in the order of the talk").toEqual(parts);
  const under = (part: string) => notes.locator("nav section", { has: notes.getByRole("heading", { name: part, level: 3, exact: true }) });
  await expect(under("Two slow steps").locator('[data-outline="problem"]')).toBeVisible();
  await expect(under("Thank you").locator('[data-outline="thanks"]')).toBeVisible();
  await expect(under("Backup").locator('[data-outline="words"]')).toBeVisible();
  await expect(notes.locator("nav [data-outline]")).toHaveCount(slides.length);
});

/** The deck's own faces, where the network has them: the font stylesheet is let through (the other tests hold it back, since it holds the
 * controller back) and the faces the deck is set in are asked for. True when Inter, the widest face of the deck's stack, arrived. */
async function loadFaces(page: Page): Promise<boolean> {
  return page.evaluate(async () => {
    for (const face of ["400 20px Inter", "600 28px Inter", "400 28px Inter", "600 40px Inter", "500 12px Inter", "600 12px Inter", "500 20px 'Geist Mono'", "600 20px 'Geist Mono'"]) await document.fonts.load(face);
    await document.fonts.ready;
    // check() also says true when no face is named Inter at all, so look for a loaded one
    return [...document.fonts].some((f) => f.family.replace(/["']/g, "") === "Inter" && f.status === "loaded");
  });
}
/** Opens a slide in the deck's own faces for a test that measures type. The sizes the deck is held to are the ones it sets in Inter, and a run
 * in the system faces would pass for slides it did not measure, so the test skips when Inter did not arrive. It says so in its annotations and in
 * a warning, since the line reporter never prints the reason for a skip. */
async function inTheDecksFaces(page: Page, context: BrowserContext, id = "welcome") {
  await context.unroute(FONTS);
  await openSlide(page, id);
  const inter = await loadFaces(page);
  test.info().annotations.push({ type: "faces", description: inter ? "measured in Inter" : "Inter did not load" });
  if (!inter) console.warn(`SKIPPED, Inter did not load, so the type would be measured in the system faces: ${test.info().title}`);
  test.skip(!inter, "Inter did not load, so the type would be measured in the system faces");
}
/** The deck shows a slide the way the notes window's outline does, drawn and settled: every layout has fitted its box. */
async function showAt(page: Page, id: string) {
  await goTo(page, id);
  await expect(slideAt(page, id)).toBeVisible();
  await page.evaluate(() => new Promise((done) => requestAnimationFrame(() => requestAnimationFrame(done))));
}

// The layout under a native slide's title zooms out when it holds too much for the box (data-fit-zoom). A slide of the talk holds no more than
// its box, so none may shrink; a backup is read in the questions, so none may shrink below 0.8. Every slide is measured before the test
// judges, so a slide of the talk that shrinks does not hide a backup that does too.
test("every native slide of the main path sits at full size, and no native backup slide below 0.8", async ({ page, context }) => {
  test.setTimeout(90_000);
  await inTheDecksFaces(page, context);
  const zoomOn = async (id: string) => {
    await showAt(page, id);
    return Number(await slideAt(page, id).locator("[data-fit-zoom]").getAttribute("data-fit-zoom"));
  };
  const main = onPath(slides, "full").filter((s) => s.native);
  expect(main.length).toBeGreaterThan(10);
  for (const s of main) expect.soft(await zoomOn(s.id), s.id).toBe(1);
  const lowest = { id: "", zoom: 1 };
  for (const s of slides.filter((x) => x.part === "backup" && x.native)) {
    const zoom = await zoomOn(s.id);
    expect.soft(zoom, s.id).toBeGreaterThanOrEqual(0.8);
    if (zoom < lowest.zoom) Object.assign(lowest, { id: s.id, zoom });
  }
  test.info().annotations.push({ type: "lowest backup", description: `${lowest.id} at ${lowest.zoom}` });
});

// A column's example cell is as wide as its examples need to show whole in two lines (up to a cap that leaves the meanings their room), so no
// word of an example or a column name breaks in the middle, and no example is cut short by its two-line clamp. A character on a line lower than
// the one before it, with a letter, a digit or an underscore on each side of the break, is a word broken in two (a full stop does not count as
// part of a word, since a sentence can end a line). A character below the bottom of its own cell is not counted: the clamp hides it.
test("no table cell breaks a word in the middle, and no example is cut short by its clamp", async ({ page, context }) => {
  test.setTimeout(90_000);
  await inTheDecksFaces(page, context);
  const tables = slides.filter((s) => s.native?.layout === "table");
  expect(tables.length).toBeGreaterThan(10);
  for (const s of tables) {
    await showAt(page, s.id);
    const found = await slideAt(page, s.id).evaluate((root) => {
      const out: { broken: string[]; clamped: string[] } = { broken: [], clamped: [] };
      for (const cell of root.querySelectorAll<HTMLElement>('[data-cell="name"], [data-cell="example"]')) {
        const clip = cell.getBoundingClientRect();
        const text = document.createTreeWalker(cell, NodeFilter.SHOW_TEXT).nextNode() as Text | null;
        if (!text) continue;
        const rect = (i: number) => {
          const range = document.createRange();
          range.setStart(text, i);
          range.setEnd(text, i + 1);
          return range.getBoundingClientRect();
        };
        const word = (c: string) => /[A-Za-z0-9_]/.test(c);
        for (let i = 0; i + 1 < text.length; i++) {
          if (!word(text.data[i]) || !word(text.data[i + 1])) continue;
          const [a, b] = [rect(i), rect(i + 1)];
          if (b.bottom <= clip.bottom + 1 && b.top > a.top + a.height / 2) out.broken.push(text.data.slice(Math.max(0, i - 8), i + 9));
        }
        if (cell.dataset.cell === "example" && cell.scrollHeight > cell.clientHeight + 1) out.clamped.push(text.data);
      }
      return out;
    });
    expect.soft(found.broken, `${s.id}: a word broken in the middle`).toEqual([]);
    expect.soft(found.clamped, `${s.id}: an example cut short`).toEqual([]);
  }
});

// The box under a native slide's title clips what reaches past it (overflow hidden, which the zoom to fit needs), and a focus ring is drawn
// outside the button it rings. A demo button with no question stands first in that box, so the box keeps 8px clear around its layout.
test("the demo button that stands alone keeps room around it for its focus ring, and still lines up with the title", async ({ page }) => {
  await page.setViewportSize({ width: 1280, height: 720 }); // the stage at its own size, so a box's pixels are the deck's
  await openSlide(page, "precall");
  const slide = slideAt(page, "precall");
  const box = (await slide.locator("[data-fit-zoom]").boundingBox())!;
  const button = (await slide.getByRole("button", { name: "Open the pre-call pack" }).boundingBox())!;
  const title = (await slide.getByRole("heading", { level: 1 }).boundingBox())!;
  expect(button.x - box.x, "room to the left of the button inside the clip").toBeGreaterThanOrEqual(8);
  expect(button.y - box.y, "room above the button inside the clip").toBeGreaterThanOrEqual(8);
  expect(button.x, "the button lines up with the title, as before").toBeCloseTo(title.x, 0);
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

// ------------------------------------------------------------------------------------------------------------------------------------
// The whole talk. A walk presses through every slide of a path and every step of each, going forward and then back, and at every slide checks
// the hash, the frame (the topic the tracker lights, the marks of its slides, the number in the footer) and the step the slide stands on.
// The slides and their order are the deck's data (slides.ts, onPath) and the topic names are its TOPICS; the marks of each topic's slides and the
// numbers in the footer are worked out here from that order, not read from the code that draws them (frameInfo).

/** The steps of each figure's page, copied from the table in docs/diagrams/README.md. The walk checks each page's own step count against this
 * table, so a page that gains or loses a step fails it until the table here is changed. Nothing checks the README itself, so whoever changes a
 * page changes the README's table too. A native slide's steps are its layout's (stepCount), a live page has none. */
const FIGURE_STEPS: Record<string, number> = {
  director: 7, delegate: 6, system: 5, pipeline: 7, revenue: 4, numbers: 4, gaps: 5, "share-fair": 5, moved: 5, checked: 4, "at-aa": 7,
};

/** What the frame draws around the slide at line[i], on the path the line is: the logo; the tracker lighting the slide's topic (the welcome, the
 * agenda and the thanks light none) with a mark for each of every topic's slides on the path, passed, this one or to come; and the footer, which
 * numbers the slide on the path and is left off the welcome and the thanks. */
async function expectFrame(page: Page, line: Slide[], i: number) {
  const s = line[i];
  const slide = slideAt(page, s.id);
  await expect(slide.locator('[data-frame="header"] img[src="/aa-logo.svg"]'), `${s.id}: the logo`).toBeVisible();
  const footer = slide.locator('[data-frame="footer"]');
  if (i === 0 || i === line.length - 1) await expect(footer, `${s.id}: the ends of the path show the logo alone`).toHaveCount(0);
  else {
    await expect(footer.locator("span").last(), `${s.id}: its number on the path`).toHaveText(`${i + 1} / ${line.length}`);
    await expect(footer.locator("span").first(), `${s.id}: the label`).toHaveText(new RegExp(`^(${copy.deckFooter}|${copy.deckFooterData})$`, "i"));
  }
  const tracker = slide.locator("[data-tracker]");
  if (!isTopic(s.part)) return void (await expect(tracker, `${s.id}: no tracker`).toHaveCount(0));
  await expect(tracker.locator("[aria-current]"), `${s.id}: one topic lit`).toHaveCount(1);
  await expect(tracker.locator('[aria-current="step"]'), `${s.id}: its topic`).toHaveText(TOPICS[s.part].name);
  for (const topic of TOPIC_ORDER) {
    const marks = line.filter((x) => x.part === topic).map((x) => (x === s ? "current" : line.indexOf(x) < i ? "passed" : "later"));
    const got = await tracker.locator(`[data-topic="${topic}"] [data-segment]`).evaluateAll((els) => els.map((el) => el.getAttribute("data-segment")));
    expect(got, `${s.id}: the marks of ${topic}`).toEqual(marks);
  }
}

/** How many steps the slide on the screen takes. A figure's frame is ready by now; a live page has none. */
async function stepsOn(page: Page, s: Slide) {
  if (s.kind === "animated") return Number(await root(page).getAttribute("data-step-count"));
  return s.kind === "native" ? stepsOf(page, s.id) : 0;
}
/** The slide stands on its k-th step: its own root says so on a native slide, the frame's on a figure. */
async function expectStep(page: Page, s: Slide, k: number) {
  if (s.kind === "animated") await expect(root(page), `${s.id}: step ${k}`).toHaveAttribute("data-step-current", String(k));
  else if (s.kind === "native") await expect(stepRoot(page, s.id), `${s.id}: step ${k}`).toHaveAttribute("data-step-current", String(k));
}
/** The deck is on a slide of the line: its hash, its frame, and, on a figure, its frame ready. */
async function arriveAt(page: Page, line: Slide[], i: number) {
  const s = line[i];
  await expect(page, `slide ${i + 1} of ${line.length}`).toHaveURL(new RegExp(`#${s.id}$`));
  await expect(slideAt(page, s.id)).toBeVisible();
  await expectFrame(page, line, i);
  if (s.kind === "animated") await expect(ready(page)).toBeVisible();
  const count = await stepsOn(page, s);
  if (s.kind === "native") expect(count, `${s.id}: the steps its layout holds`).toBe(stepCount(s));
  if (s.kind === "animated") expect(count, `${s.id}: the steps of its page`).toBe(FIGURE_STEPS[s.id]);
  return count;
}
const onShortPath = (page: Page) => page.addInitScript((key) => { try { localStorage.setItem(key, "short"); } catch { /* about:blank has no storage */ } }, KEYS.path);

for (const path of ["full", "short"] as const satisfies PathName[]) {
  const line = onPath(slides, path);
  test.describe(`the ${path} path`, () => {
    test.beforeEach(async ({ page }) => {
      if (path === "short") await onShortPath(page);
    });

    test(`pressing forward through every slide and step of the ${path} path lands each on its first step, lights its topic and numbers it`, async ({ page }) => {
      test.setTimeout(240_000);
      await openSlide(page, line[0].id);
      let presses = 0;
      for (let i = 0; i < line.length; i++) {
        const s = line[i];
        const count = await arriveAt(page, line, i);
        if (i > 0) await expectStep(page, s, 0); // a slide pressed onto shows its title alone, or its figure at its first step
        for (let k = 1; k <= count; k++) {
          await page.keyboard.press("ArrowRight");
          presses += 1;
          await expectStep(page, s, k);
        }
        if (i < line.length - 1) {
          await page.keyboard.press("ArrowRight"); // the press after the last step moves the deck
          presses += 1;
        }
      }
      await page.keyboard.press("ArrowRight"); // the path stops at its end
      await expect(page).toHaveURL(new RegExp(`#${line.at(-1)!.id}$`));
      expect(presses, "a press for each step, and one for each move").toBeGreaterThan(line.length * 2);
      test.info().annotations.push({ type: "presses", description: `${presses} presses through ${line.length} slides` });
    });

    test(`pressing back through every slide of the ${path} path lands each complete, steps it down to its title, and then moves back`, async ({ page }) => {
      test.setTimeout(240_000);
      await openSlide(page, line.at(-1)!.id);
      for (let i = line.length - 1; i >= 0; i--) {
        const s = line[i];
        const count = await arriveAt(page, line, i);
        await expectStep(page, s, count); // a slide that is gone back to, or loaded, shows complete
        for (let k = count - 1; k >= 0; k--) {
          await page.keyboard.press("ArrowLeft");
          await expectStep(page, s, k);
        }
        await page.keyboard.press("ArrowLeft"); // from the title alone the deck moves back
      }
      await expect(page).toHaveURL(new RegExp(`#${line[0].id}$`)); // the path stops at its start
    });
  });
}
