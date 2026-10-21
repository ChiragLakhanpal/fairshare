"""The American Airlines skin for the fairshare diagrams, shared by every builder in this folder.

Colors are the diagram-design profile `american-airlines` (~/.diagram-design/profiles/american-airlines.md), which takes
its tokens from web/src/styles.css. The geometry helpers come from the diagram-design plugin's own scripts, so every
exploded part is projected by the same iso() its verifier checks against.
"""
from __future__ import annotations

import glob
import importlib.util
import os
import sys
from pathlib import Path

OUT = Path(__file__).resolve().parent.parent  # docs/diagrams


def plugin_scripts() -> Path:
    env = os.environ.get("DIAGRAM_DESIGN_SCRIPTS")
    if env:
        return Path(env)
    found = sorted(glob.glob(str(Path.home() / ".claude/plugins/cache/diagram-design/diagram-design/*/scripts")))
    if not found:
        sys.exit("diagram-design plugin not found; set DIAGRAM_DESIGN_SCRIPTS to its scripts folder")
    return Path(found[-1])  # ponytail: newest by name, fine while versions sort lexically


SCRIPTS = plugin_scripts()
sys.path.insert(0, str(SCRIPTS))
MOTION_TEMPLATE = SCRIPTS.parent / "skills/diagram-design/assets/template-motion.html"


def load(name: str, file: str):
    spec = importlib.util.spec_from_file_location(name, SCRIPTS / file)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod  # dataclasses look the module up while the class is built
    spec.loader.exec_module(mod)
    return mod


INK, MUTED, SOFT, ACCENT, NAVY, PAPER, PAPER2 = "#36495a", "#5a7181", "#566d7b", "#006cbf", "#00467f", "#ffffff", "#f2f5f8"
RULE, RULE_SOLID, ACCENT_TINT = "rgba(54,73,90,0.14)", "#d0dae0", "rgba(0,108,191,0.10)"
SANS, MONO = "'Inter', system-ui, sans-serif", "'Geist Mono', ui-monospace, monospace"
FONT_LINK = "https://fonts.googleapis.com/css2?family=Inter:ital,wght@0,400;0,500;0,600;0,700;1,400&family=Geist+Mono:wght@400;500;600&display=swap"
# The /present deck draws its header over y 0 to 64 of a 1280 by 720 figure and its footer over y 690 to 720, so a figure it shows
# keeps every mark from STAGE_TOP to STAGE_BOTTOM, the logo band aside. evals/test_figures_in_deck.py measures each mark, a text by
# its font box: 1em over its baseline to TEXT_DESCENT under it.
STAGE_TOP, STAGE_BOTTOM, TEXT_DESCENT = 64, 680, 0.3

# face tones for the axonometry helpers, every value a profile role or an rgba() of one
SKIN = dict(
    paper=PAPER, ink=INK, muted=MUTED, soft=SOFT, accent=ACCENT,
    ink_rgb="54,73,90", acc_rgb="0,108,191", base="#ffffff", rule=RULE,
    shade=(None, "rgba(54,73,90,0.07)", "rgba(54,73,90,0.15)"),
    focal=("rgba(0,108,191,0.10)", "rgba(0,108,191,0.20)", "rgba(0,108,191,0.32)"),
    cavity="rgba(54,73,90,0.10)", floor="rgba(54,73,90,0.04)", well="rgba(54,73,90,0.14)",
    screen=NAVY, island=INK, chip_top=MUTED, chip_side=INK,
    sil=INK, inner="rgba(54,73,90,0.55)", trace="rgba(54,73,90,0.30)",
    lead="rgba(54,73,90,0.40)", lead_acc="rgba(0,108,191,0.60)", inner_acc="rgba(0,108,191,0.70)",
    lens=INK, lens_ring="rgba(255,255,255,0.35)",
)

PAGE = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{title}</title>
  <link href="{font}" rel="stylesheet">
  <style>
    *, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}
    :root {{
      --color-paper:  {paper};
      --color-ink:    {ink};
      --color-muted:  {muted};
      --color-accent: {accent};
      --font-sans:    {sans};
      --font-mono:    {mono};
    }}
    body {{ font-family: var(--font-sans); background: var(--color-paper); color: var(--color-ink); min-height: 100vh;
           display: flex; align-items: center; justify-content: center; padding: 3rem 2rem; }}
    .frame {{ max-width: 1360px; width: 100%; }}
    .diagram-container {{ width: 100%; overflow-x: auto; }}
    .eyebrow {{ font-family: var(--font-mono); font-size: 0.66rem; font-weight: 500; letter-spacing: 0.18em;
               text-transform: uppercase; color: var(--color-muted); margin-bottom: 0.5rem; }}
    h1 {{ font-family: var(--font-sans); font-size: clamp(1.5rem, 2.4vw + 0.75rem, 2.25rem); font-weight: 600;
         letter-spacing: -0.02em; line-height: 1.15; color: var(--color-ink); margin-bottom: 1.5rem; }}
    svg {{ width: 100%; min-width: {vw}px; display: block; }}
    @media print {{
      .diagram-container {{ overflow-x: visible; }}
      svg {{ min-width: 0; }}
    }}
  </style>
</head>
<body>
  <div class="frame">
    <p class="eyebrow">{eyebrow}</p>
    <h1>{title}</h1>

    <div class="diagram-container">
      <svg viewBox="0 0 {vw} {vh}" xmlns="http://www.w3.org/2000/svg" role="img" aria-labelledby="{slug}-title {slug}-desc">
        <title id="{slug}-title">{title}</title>
        <desc id="{slug}-desc">{desc}</desc>
        {body}
      </svg>
    </div>
  </div>
</body>
</html>
"""


def page(*, slug, title, desc, eyebrow, body, vw=1280, vh=720) -> str:
    return PAGE.format(title=title, font=FONT_LINK, paper=PAPER, ink=INK, muted=MUTED, accent=ACCENT, sans=SANS, mono=MONO,
                       eyebrow=eyebrow, vw=vw, vh=vh, slug=slug, desc=desc, body=body)


# Embed mode for the /present deck. No script: verify-motion.py allows one per motion page (the controller) and lint-skin.py
# rejects on* attributes, so the deck sets data-embed itself once the controller is ready, then sends Home or End. In the deck a
# step the presenter has not reached shows nothing (the plugin's own reveal leaves it at .12, which still gives the end away), the
# figure's logo band goes (the deck's frame draws the one logo), and the draw-in classes below play. evals/test_figures_in_deck.py
# reads these rules in every animated page, so a change here means rebuilding them all.
EMBED_CSS = """    /* html[data-embed]: set by the /present deck once the controller is ready; only the figure shows, fitted to the frame */
    html[data-embed] body { margin: 0; padding: 0; min-height: 0; display: block; overflow: hidden; background: var(--color-paper); }
    html[data-embed] .eyebrow, html[data-embed] h1, html[data-embed] [data-motion-controls] { display: none !important; }
    html[data-embed] [data-motion-root] { width: 100vw; max-width: none; margin: 0; }
    html[data-embed] .diagram-container { overflow: hidden; }
    html[data-embed] [data-motion-root] svg { width: 100vw; min-width: 0; height: auto; display: block; }
    html[data-embed] [data-brand="aa-logo"] { display: none; }
    /* a step not reached yet is invisible, not faded; 01's slabs stay, assembled, and lift on each press. On step 0, where a
       slide arrives, nothing fades: the deck shows the frame at once, so a fade would play out in front of the room */
    html[data-embed] .motion-ready [data-motion-item]:not(.is-visible):not([data-part]) { opacity: 0; }
    html[data-embed] .motion-ready[data-frame="start"] [data-motion-item] { transition: none; }
    /* draw-in for charts, once, when the deck switches the page to embed mode: a line (a path with pathLength="1") traces
       left to right, a dot fades in after its line, and a bar grows from its baseline */
    html[data-embed] .draw-line { stroke-dasharray: 1; stroke-dashoffset: 1; animation: aa-draw-line 900ms ease-out forwards; }
    html[data-embed] .draw-dot { opacity: 0; animation: aa-draw-dot 300ms ease-out 900ms forwards; }
    html[data-embed] .draw-bar { transform-box: fill-box; transform-origin: 50% 100%; transform: scaleY(0); animation: aa-draw-bar 600ms ease-out forwards; }
    @keyframes aa-draw-line { to { stroke-dashoffset: 0; } }
    @keyframes aa-draw-dot { to { opacity: 1; } }
    @keyframes aa-draw-bar { to { transform: scaleY(1); } }
    @media (prefers-reduced-motion: reduce) {
      html[data-embed] .draw-line, html[data-embed] .draw-dot, html[data-embed] .draw-bar { animation: none; stroke-dashoffset: 0; opacity: 1; transform: none; }
    }
"""

# Extra CSS for animated(): items fade in where they stand instead of rising 8px into place.
FADE_ONLY = ".motion-ready [data-motion-item] { transform: none; }"


def aa_motion(src: str) -> str:
    """Re-skin a page built from diagram-design's motion template: AA fonts and colors, a wider root for 1280 slides, and
    the embed CSS the /present deck switches on."""
    import re
    src = re.sub(r'<link href="https://fonts\.googleapis\.com/css2\?[^"]+" rel="stylesheet">', f'<link href="{FONT_LINK}" rel="stylesheet">', src, count=1)
    for old, new in (("--color-paper: #f5f5f5;", f"--color-paper: {PAPER};"), ("--color-ink: #2d3142;", f"--color-ink: {INK};"),
                     ("--color-muted: #4f5d75;", f"--color-muted: {MUTED};"), ("--color-soft: #5a6580;", f"--color-soft: {SOFT};"),
                     ("--color-accent: #bf4520;", f"--color-accent: {ACCENT};"), ("--color-rule: rgba(45,49,66,0.12);", f"--color-rule: {RULE};"),
                     ("--font-sans: 'Geist', system-ui, sans-serif;", f"--font-sans: {SANS};"),
                     ("[data-motion-root] { width: min(100%, 1000px); }", "[data-motion-root] { width: min(100%, 1360px); }"),
                     ("h1 { margin: 0 0 24px; font: 400 32px/1.15 var(--font-serif); }", "h1 { margin: 0 0 24px; font: 600 32px/1.15 var(--font-sans); letter-spacing: -0.02em; }"),
                     ("min-width: 1000px;", "min-width: 1280px;")):
        assert old in src, old
        src = src.replace(old, new, 1)
    assert "  </style>" in src, "  </style>"
    return src.replace("  </style>", EMBED_CSS + "  </style>", 1)


def animated(*, slug: str, title: str, desc: str, eyebrow: str, body: str, steps: int, css: str = "", vw: int = 1280, vh: int = 720) -> str:
    """diagram-design's motion template around one figure, re-skinned for AA and widened to the 1280 slide: the plugin's
    controller byte for byte, reveal mode (it plays once on open), and `css` added after the template's own rules."""
    import re
    src = MOTION_TEMPLATE.read_text(encoding="utf-8")
    src = src.replace("<title>Motion diagram template</title>", f"<title>{title}</title>", 1)
    src = src.replace("--motion-step: 480ms;", "--motion-step: 600ms;", 1).replace("--motion-hold: 720ms;", "--motion-hold: 900ms;", 1)
    src = src.replace("--motion-total: 3600ms;", f"--motion-total: {steps * 900}ms;", 1)
    src = src.replace("min-width: 960px;", "min-width: 1000px;", 1)
    if css and not css.endswith("\n"):
        css = f"    {css}\n"  # a one-line rule such as FADE_ONLY gets its own line
    src = src.replace("  </style>", css + "  </style>", 1)
    start, end = src.index("  <!-- Replace template-motion"), src.index("    <div data-motion-controls")
    main = (f'  <main data-motion-root data-motion-mode="reveal" data-step-count="{steps}" data-step-current="{steps}" data-frame="static" data-static-frame="complete">\n'
            f'    <p class="eyebrow">{eyebrow}</p>\n    <h1>{title}</h1>\n\n    <div class="diagram-container">\n'
            f'      <svg viewBox="0 0 {vw} {vh}" xmlns="http://www.w3.org/2000/svg" role="img" aria-labelledby="{slug}-title {slug}-desc">\n'
            f'        <title id="{slug}-title">{title}</title>\n        <desc id="{slug}-desc">{desc}</desc>\n'
            f'        {body}\n      </svg>\n    </div>\n\n')
    src = src[:start] + main + src[end:]
    src = re.sub(r'Step <span data-motion-step-label>\d+</span> of \d+', f'Step <span data-motion-step-label>{steps}</span> of {steps}', src, count=1)
    return aa_motion(src)


def esc(s: str) -> str:
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def motion_item(step: int, label: str, marks) -> str:
    """One step of an animated figure: its marks in a single group that the controller reveals together. The label is what
    the controller announces ("Step 2 of 7: ..."), so it says in plain words what the step shows."""
    marks = list(marks)
    assert marks, f"motion step {step} holds no marks"
    return f'<g data-motion-item data-step="{step}" aria-label="{esc(label)}">\n          ' + "\n          ".join(marks) + "\n        </g>"


# ---------------------------------------------------------------- brand and platform marks

# The official American Airlines logo (web/public/aa-logo.svg, the same file the app ships) keeps its own colors, so
# diagram-design's skin lint flags its gradient stops; every other color in a diagram stays on the profile.
LOGO_FILE = OUT.parent.parent / "web" / "public" / "aa-logo.svg"


def brand(x: float = 40, y: float = 24, h: float = 22, tag: str = "fairshare · sales ai & innovation") -> str:
    """The AA logo lockup for the top-left corner of every image: logo, a hairline, and the project tag. One line of
    markup on purpose, so a lint finding on the logo's gradients points at exactly this line."""
    import re
    src = LOGO_FILE.read_text(encoding="utf-8")
    inner = re.search(r"<svg[^>]*>(.*)</svg>", src, re.S).group(1)
    inner = re.sub(r'id="(\w+)"', r'id="aa-logo-\1"', inner)
    inner = re.sub(r"url\(#(\w+)\)", r"url(#aa-logo-\1)", inner).replace("\n", "")
    w = round(300 * h / 46, 2)
    lx = x + w + 14
    text = (f'<text x="{lx + 14}" y="{y + h / 2 + 3}" fill="{MUTED}" font-size="8" font-weight="500" font-family="{MONO}" '
            f'letter-spacing="0.18em">{esc(tag.upper())}</text>') if tag else ""
    rule = f'<line x1="{lx}" y1="{y + 3}" x2="{lx}" y2="{y + h - 3}" stroke="{RULE_SOLID}" stroke-width="1"/>' if tag else ""
    return (f'<g data-brand="aa-logo" aria-hidden="true"><svg x="{x}" y="{y}" width="{w}" height="{h}" viewBox="0 0 300 46" aria-hidden="true">'
            f'{inner}</svg>{rule}{text}</g>')


# Platform marks, 24x24 single paths from Simple Icons 16.35.0 (CC0), drawn in one profile color like diagram-design's
# brand icons. A mark says where a piece lives; the name beside it says what it is.
ICONS = {
    "databricks": "M.95 14.184L12 20.403l9.919-5.55v2.21L12 22.662l-10.484-5.96-.565.308v.77L12 24l11.05-6.218v-4.317l-.515-.309L12 19.118l-9.867-5.653v-2.21L12 16.805l11.05-6.218V6.32l-.515-.308L12 11.974 2.647 6.681 12 1.388l7.76 4.368.668-.411v-.566L12 0 .95 6.27v.72L12 13.207l9.919-5.55v2.26L12 15.52 1.516 9.56l-.565.308Z",
    "azure": "M22.379 23.343a1.62 1.62 0 0 0 1.536-2.14v.002L17.35 1.76A1.62 1.62 0 0 0 15.816.657H8.184A1.62 1.62 0 0 0 6.65 1.76L.086 21.204a1.62 1.62 0 0 0 1.536 2.139h4.741a1.62 1.62 0 0 0 1.535-1.103l.977-2.892 4.947 3.675c.28.208.618.32.966.32m-3.084-12.531 3.624 10.739a.54.54 0 0 1-.51.713v-.001h-.03a.54.54 0 0 1-.322-.106l-9.287-6.9h4.853m6.313 7.006c.116-.326.13-.694.007-1.058L9.79 1.76a1.722 1.722 0 0 0-.007-.02h6.034a.54.54 0 0 1 .512.366l6.562 19.445a.54.54 0 0 1-.338.684",
    "microsoft": "M0 0v11.408h11.408V0zm12.594 0v11.408H24V0zM0 12.594V24h11.408V12.594zm12.594 0V24H24V12.594z",
    "dynamics365": "M15.805 11.322v4.889a2.536 2.536 0 0 1-1.643 2.374l-1.732.652a.507.507 0 0 1-.686-.475v-5.956l-3.392 1.239a1.015 1.015 0 0 0-.664.953v7.986c0 .705.7 1.195 1.363.953l10.161-3.713a2.535 2.535 0 0 0 1.666-2.382V7.696a2.537 2.537 0 0 1-1.666 2.381l-3.407 1.245Zm0-.532V9.323a2.537 2.537 0 0 0-1.645-2.375l-1.728-.65a.508.508 0 0 0-.686.475v4.59c0 .701-.695 1.191-1.355.956L3.795 9.963a1.015 1.015 0 0 1-.674-.956V1.015c0-.701.695-1.191 1.356-.955l14.718 5.256A2.538 2.538 0 0 1 20.83 7.21c-.136.861-1.05 2.128-1.79 2.398l-3.235 1.182Z",
    "powerbi": "M10 12a1 1 0 0 1 1 1v11H4a1 1 0 0 1-1-1V13a1 1 0 0 1 1-1h6Zm-2-.5V7a1 1 0 0 1 1-1h6a1 1 0 0 1 1 1v17h-4.5V13a1.5 1.5 0 0 0-1.5-1.5H8Zm5-6V1a1 1 0 0 1 1-1h6a1 1 0 0 1 1 1v22a1 1 0 0 1-1 1h-3.5V7A1.5 1.5 0 0 0 15 5.5h-2Z",
    "outlook": "M7.88 12.04q0 .45-.11.87-.1.41-.33.74-.22.33-.58.52-.37.2-.87.2t-.85-.2q-.35-.21-.57-.55-.22-.33-.33-.75-.1-.42-.1-.86t.1-.87q.1-.43.34-.76.22-.34.59-.54.36-.2.87-.2t.86.2q.35.21.57.55.22.34.31.77.1.43.1.88zM24 12v9.38q0 .46-.33.8-.33.32-.8.32H7.13q-.46 0-.8-.33-.32-.33-.32-.8V18H1q-.41 0-.7-.3-.3-.29-.3-.7V7q0-.41.3-.7Q.58 6 1 6h6.5V2.55q0-.44.3-.75.3-.3.75-.3h12.9q.44 0 .75.3.3.3.3.75V10.85l1.24.72h.01q.1.07.18.18.07.12.07.25zm-6-8.25v3h3v-3zm0 4.5v3h3v-3zm0 4.5v1.83l3.05-1.83zm-5.25-9v3h3.75v-3zm0 4.5v3h3.75v-3zm0 4.5v2.03l2.41 1.5 1.34-.8v-2.73zM9 3.75V6h2l.13.01.12.04v-2.3zM5.98 15.98q.9 0 1.6-.3.7-.32 1.19-.86.48-.55.73-1.28.25-.74.25-1.61 0-.83-.25-1.55-.24-.71-.71-1.24t-1.15-.83q-.68-.3-1.55-.3-.92 0-1.64.3-.71.3-1.2.85-.5.54-.75 1.3-.25.74-.25 1.63 0 .85.26 1.56.26.72.74 1.23.48.52 1.17.81.69.3 1.56.3zM7.5 21h12.39L12 16.08V17q0 .41-.3.7-.29.3-.7.3H7.5zm15-.13v-7.24l-5.9 3.54Z",
    "mlflow": "M11.883.002a12.044 12.044 0 0 0-9.326 19.463l3.668-2.694A7.573 7.573 0 0 1 12.043 4.45v2.867l6.908-5.14A12.012 12.012 0 0 0 11.883.002zm9.562 4.533L17.777 7.23a7.573 7.573 0 0 1-5.818 12.322v-2.867l-6.908 5.14a12.046 12.046 0 0 0 16.394-17.29z",
    "teams": "M20.625 8.127q-.55 0-1.025-.205-.475-.205-.832-.563-.358-.357-.563-.832Q18 6.053 18 5.502q0-.54.205-1.02t.563-.837q.357-.358.832-.563.474-.205 1.025-.205.54 0 1.02.205t.837.563q.358.357.563.837.205.48.205 1.02 0 .55-.205 1.025-.205.475-.563.832-.357.358-.837.563-.48.205-1.02.205zm0-3.75q-.469 0-.797.328-.328.328-.328.797 0 .469.328.797.328.328.797.328.469 0 .797-.328.328-.328.328-.797 0-.469-.328-.797-.328-.328-.797-.328zM24 10.002v5.578q0 .774-.293 1.46-.293.685-.803 1.194-.51.51-1.195.803-.686.293-1.459.293-.445 0-.908-.105-.463-.106-.85-.329-.293.95-.855 1.729-.563.78-1.319 1.336-.756.557-1.67.861-.914.305-1.898.305-1.148 0-2.162-.398-1.014-.399-1.805-1.102-.79-.703-1.312-1.664t-.674-2.086h-5.8q-.411 0-.704-.293T0 16.881V6.873q0-.41.293-.703t.703-.293h8.59q-.34-.715-.34-1.5 0-.727.275-1.365.276-.639.75-1.114.475-.474 1.114-.75.638-.275 1.365-.275t1.365.275q.639.276 1.114.75.474.475.75 1.114.275.638.275 1.365t-.275 1.365q-.276.639-.75 1.113-.475.475-1.114.75-.638.276-1.365.276-.188 0-.375-.024-.188-.023-.375-.058v1.078h10.875q.469 0 .797.328.328.328.328.797zM12.75 2.373q-.41 0-.78.158-.368.158-.638.434-.27.275-.428.639-.158.363-.158.773 0 .41.158.78.159.368.428.638.27.27.639.428.369.158.779.158.41 0 .773-.158.364-.159.64-.428.274-.27.433-.639.158-.369.158-.779 0-.41-.158-.773-.159-.364-.434-.64-.275-.275-.639-.433-.363-.158-.773-.158zM6.937 9.814h2.25V7.94H2.814v1.875h2.25v6h1.875zm10.313 7.313v-6.75H12v6.504q0 .41-.293.703t-.703.293H8.309q.152.809.556 1.5.405.691.985 1.19.58.497 1.318.779.738.281 1.582.281.926 0 1.746-.352.82-.351 1.436-.966.615-.616.966-1.43.352-.815.352-1.752zm5.25-1.547v-5.203h-3.75v6.855q.305.305.691.452.387.146.809.146.469 0 .879-.176.41-.175.715-.48.304-.305.48-.715t.176-.879Z",
}


def icon(name: str, x: float, y: float, size: float = 20, color: str = INK) -> str:
    return (f'<svg x="{x}" y="{y}" width="{size}" height="{size}" viewBox="0 0 24 24" aria-hidden="true">'
            f'<path d="{ICONS[name]}" fill="{color}"/></svg>')
