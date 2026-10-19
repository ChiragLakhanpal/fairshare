// A Node port of diagram-design's scripts/export_png.py, step for step, for machines without Python Playwright:
// static motion frame, fonts loaded, the SVG sized to its viewBox, ancestors unclipped, the SVG alone at 2x.
//   NODE_PATH=web/node_modules node docs/diagrams/src/export_png.cjs <in.html> <out.png> [scale]
const { chromium } = require("playwright");
const { pathToFileURL } = require("url");
(async () => {
  const [src, out, s] = process.argv.slice(2);
  const scale = Number(s || 2);
  if (!src || !out || !(scale >= 1 && scale <= 4)) throw new Error("usage: export_png.cjs <in.html> <out.png> [scale 1..4]");
  const browser = await chromium.launch();
  try {
    const page = await browser.newPage({ deviceScaleFactor: scale });
    await page.goto(pathToFileURL(src).href + "?motion=static", { waitUntil: "domcontentloaded" });
    try { await page.waitForLoadState("networkidle", { timeout: 15000 }); }
    catch { await page.evaluate(() => window.stop()); await page.waitForTimeout(4000); console.error("warning: webfont request stalled; captured with fallback typography"); }
    await page.evaluate(() => document.fonts.ready);
    const ok = await page.locator("[data-motion-root]").evaluateAll(rs => rs.every(r => r.dataset.frame === "static"));
    if (!ok) throw new Error("motion export requires a complete static frame");
    const svg = page.locator("svg").first();
    await svg.evaluate(el => {
      const box = el.viewBox.baseVal;
      if (![box.width, box.height].every(n => Number.isFinite(n) && n > 0)) throw new Error("PNG export requires a nonzero finite viewBox");
      for (const [axis, size] of [["width", box.width], ["height", box.height]])
        for (const prefix of ["", "min-", "max-"]) el.style.setProperty(prefix + axis, size + "px", "important");
    });
    await svg.evaluate(el => { for (let a = el.parentElement; a; a = a.parentElement) a.style.setProperty("overflow", "visible", "important"); });
    // ponytail: the one change from the Python helper: clip to the viewBox size from a whole-pixel origin, because an element
    // screenshot rounds a fractional top edge outward and a 720 slide came out 721 tall
    const box = await svg.boundingBox();
    const [w, h] = await svg.evaluate(el => [el.viewBox.baseVal.width, el.viewBox.baseVal.height]);
    await page.setViewportSize({ width: Math.ceil(box.x + w) + 8, height: Math.ceil(box.y + h) + 8 });
    const b2 = await svg.boundingBox();
    await page.screenshot({ path: out, omitBackground: true, clip: { x: Math.round(b2.x), y: Math.round(b2.y), width: w, height: h } });
  } finally { await browser.close(); }
})().catch(e => { console.error(e.message); process.exit(1); });
