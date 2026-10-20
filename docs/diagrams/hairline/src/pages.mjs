// The presentation pages: each hairline figure on a white 1280 x 720 frame in the AA theme, the AA logo lockup top left
// (outside the figure: rule 10 keeps words and logos out of the drawing), the figure centred and playing its tour, one
// caption line under it. The frame scales to the window.
//   node docs/diagrams/hairline/src/pages.mjs      (after build.mjs has written the hairline-<name>.html bench pages)
// Add ?still=1 to any page for the rest pose, which is what the PNGs in png/ are taken from.
import { execFileSync } from "node:child_process";
import { readFileSync, rmSync, writeFileSync } from "node:fs";
import { fileURLToPath } from "node:url";

const here = (p) => fileURLToPath(new URL(p, import.meta.url));
const DIST = here("../../../../web/node_modules/@lucasmarkes/hairline/dist/index.js");
// the lockup is aa.brand() in docs/diagrams/src/aa.py, so the hairline pages and the diagrams carry the same markup
const BRAND = execFileSync("python3", ["-c", "import aa; print(aa.brand(0, 0, 22))"], { cwd: here("../../src/"), encoding: "utf8" }).trim();

const CUSTOM = {
  stack: ["stack.html", "Five layers under every answer. Point at one to lift it clear."],
  "flight-symbol": ["title-a-flight-symbol.html", "The Flight Symbol in line. Point at it and it turns and banks."],
  airliner: ["title-b-airliner.html", "A narrow-body in flight. Point at it and it banks and pitches."],
  seats: ["title-c-seats.html", "Fair share is AA's share of the seats on a route."],
};
const OPENERS = {
  sieve: "Every number passes through the checks.",
  riffle: "Pages wait for a person to decide.",
  query: "It starts with a question.",
  elevator: "Four floors: as delivered, cleaned, ready to use, and defined once.",
};

const page = (title, caption, scripts) => `<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>${title}</title>
<link rel="icon" href="data:,">
<link href="https://fonts.googleapis.com/css2?family=Inter:ital,wght@0,400;0,500;0,600;0,700;1,400&family=Geist+Mono:wght@400;500;600&display=swap" rel="stylesheet">
<style>
  :root { color-scheme: light; --hairline-plate: #ffffff; --hairline-hi: #006cbf; --hairline-edge: #36495a; --hairline-mid: #5a7181; --hairline-lo: #d0dae0; }
  * { box-sizing: border-box; }
  html, body { margin: 0; height: 100%; background: #ffffff; }
  body { display: grid; place-items: center; overflow: hidden; color: #36495a; font-family: Inter, system-ui, sans-serif; -webkit-font-smoothing: antialiased; }
  .frame { position: relative; width: 1280px; height: 720px; flex: none; background: #ffffff; }
  .brand { position: absolute; left: 40px; top: 24px; }
  .plate { position: absolute; left: 320px; top: 84px; width: 640px; }
  #read { position: absolute; top: 0; right: 0; z-index: 1; font: 500 12px/1 "Geist Mono", ui-monospace, monospace; letter-spacing: 0.02em;
          color: #5a7181; font-variant-numeric: tabular-nums; pointer-events: none; }
  .caption { position: absolute; left: 0; right: 0; top: 626px; margin: 0; text-align: center; font-size: 22px; font-weight: 500; line-height: 1.3; }
</style>
</head>
<body>
<div class="frame">
  <svg class="brand" width="400" height="22" viewBox="0 0 400 22" role="img" aria-label="American Airlines, fairshare">${BRAND}</svg>
  <div class="plate"><span id="read"></span><div id="stage"></div></div>
  <p class="caption">${caption}</p>
</div>
<script>
  // the frame keeps its 1280 x 720 layout and scales to the window, so a slide and the live page match
  const frame = document.querySelector(".frame");
  const fitFrame = () => { frame.style.transform = "scale(" + Math.min(innerWidth / 1280, innerHeight / 720) + ")"; };
  addEventListener("resize", fitFrame); fitFrame();
</script>
${scripts}
</body>
</html>
`;

const slot = (html, id) => {
  const m = new RegExp(`<script[^>]*id="${id}"[^>]*>\\n?([\\s\\S]*?)\\n?</script>`).exec(html);
  if (!m) throw new Error(`no ${id} script`);
  return m[1];
};

// the custom figures: the kernel and the figure exactly as build.mjs put them on the bench, on a host that plays the tour
for (const [name, [file, caption]] of Object.entries(CUSTOM)) {
  const bench = readFileSync(here(`../hairline-${name}.html`), "utf8");
  const host = `<script>
(() => {
  const still = new URLSearchParams(location.search).has("still");
  window.hairline = (figure) => {
    const stage = document.getElementById("stage"), out = document.getElementById("read");
    HL.inject(document);
    stage.setAttribute("data-hairline", figure.name);
    stage.setAttribute("role", "img");
    stage.setAttribute("aria-label", figure.means);
    const svg = HL.mk("svg", { viewBox: "0 0 400 320", "aria-hidden": "true" }, stage);
    let text = null;
    const read = { get textContent() { return text; }, set textContent(v) { text = v == null ? "" : String(v); out.textContent = text; } };
    figure.mount({ stage, svg, read }, figure.range[1]);
    if (text === null) read.textContent = "rest";
    if (!still) HL.tour(stage, figure.tour || HL.LAP);
  };
})();
</script>`;
  const scripts = `<script id="hl-kernel">\n${slot(bench, "hl-kernel")}\n</script>\n${host}\n<script type="module" id="hl-figure">\n${slot(bench, "hl-figure")}\n</script>`;
  writeFileSync(here(`../${file}`), page(`fairshare · ${name}`, caption, scripts));
  console.log(file);
}
rmSync(here("../seats.html"), { force: true }); // renamed to title-c-seats.html

// the openers: the package's own figures, its build inlined so nothing loads from elsewhere
const dist = readFileSync(DIST, "utf8").replace(/\nexport \{[\s\S]*?\};\s*/, "\n").replace(/\/\/# sourceMappingURL=.*\s*$/, "");
if (dist.includes("</script")) throw new Error("the package build holds a closing script tag");
for (const [fn, caption] of Object.entries(OPENERS)) {
  const scripts = `<script type="module">\n${dist}\nconst still = new URLSearchParams(location.search).has("still"), out = document.getElementById("read");\n${fn}(document.getElementById("stage"), { theme: "light", play: !still, onRead: (t) => { out.textContent = t; } });\n</script>`;
  writeFileSync(here(`../opener-${fn}.html`), page(`fairshare · ${fn}`, caption, scripts));
  console.log(`opener-${fn}.html`);
}
