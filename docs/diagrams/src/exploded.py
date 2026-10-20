"""01: the whole system as one exploded stack, data at the bottom and the app on top, the checks layer in AA blue.

    python3 docs/diagrams/src/exploded.py   # writes docs/diagrams/01-system-exploded.html and -animated.html

Every point comes from iso(x, y, z) through diagram-design's axonometry helpers; scripts/verify-exploded.py in the plugin
reprojects each part from the data-* attributes written here.
"""
from __future__ import annotations

import math
import re

import aa

import axonometry as ax  # noqa: E402  (aa put the plugin scripts on sys.path)
ex = aa.load("exploded_examples", "build-exploded-examples.py")
Proj, Rect, prism, outline, point, finish, styles, solid, f = ax.Proj, ax.Rect, ax.prism, ax.outline, ax.point, ax.finish, ax.styles, ax.solid, ax.f
Part, explode, levels_of, mini = ex.Part, ex.explode, ex.levels_of, ex.mini
SK = aa.SKIN
VW, VH = 1280, 720
S = 136  # footprint of every slab; with gap k 0.65 the stack fits under the logo band and the focal layer stays readable


def flat(P, rect, z, fill):
    return f'<path d="{outline(P, rect, z)}" fill="{fill}"/>'


def lines_on(P, card, z, widths, fill, pitch=9, h=2.5, pad=6):
    return [flat(P, Rect(card.x0 + pad, card.y0 + 8 + i * pitch, card.x0 + pad + w, card.y0 + 8 + i * pitch + h, 0), z, fill)
            for i, w in enumerate(widths)]


def data_detail(P, r, z, sk, focal):
    """Nine short cylinders: the tables in Unity Catalog."""
    out = [f'<path d="{outline(P, r.inset(10), z)}" fill="none" stroke="{sk["inner"]}" stroke-width="0.8"/>']
    at = (S * 0.25, S * 0.5, S * 0.75)
    cells = [(x, y) for y in at for x in at]
    for x, y in sorted(cells, key=lambda c: (c[0] + c[1], c[0])):
        out += mini(P, Rect(r.x0 + x - 12, r.y0 + y - 12, r.x0 + x + 12, r.y0 + y + 12, 12), z, z + 9, sk, sk["shade"], sk["sil"], sk["inner"])
    return out


def defs_detail(P, r, z, sk, focal):
    """The definitions desk: one card per tool, the same seven lines on each."""
    big = Rect(r.x0 + 14, r.y0 + 14, r.x0 + 80, r.y1 - 14, 3)
    twin = Rect(r.x0 + 92, r.y0 + 30, r.x1 - 14, r.y1 - 30, 3)
    out = []
    for card in (big, twin):  # the same seven lines on both cards: one definition, two tools
        w = card.x1 - card.x0 - 12
        widths = [round(w * k) for k in (0.70, 0.85, 0.60, 0.95, 0.50, 0.80, 0.65)]
        out += mini(P, card, z, z + 4, sk, sk["shade"], sk["sil"], sk["inner"])
        out += lines_on(P, card, z + 4, widths, f'rgba({sk["ink_rgb"]},0.30)', pitch=(card.y1 - card.y0 - 16) / 7)
    return out


def agents_detail(P, r, z, sk, focal):
    """The harness chip in the middle, the four Delegate agents around it on traces."""
    cx, cy = (r.x0 + r.x1) / 2, (r.y0 + r.y1) / 2
    out = []
    for a, b in (((cx, r.y0 + 40), (cx, cy - 24)), ((cx, cy + 24), (cx, r.y1 - 40)), ((r.x0 + 40, cy), (cx - 24, cy)), ((cx + 24, cy), (r.x1 - 40, cy))):
        pa, pb = P.iso(a[0], a[1], z), P.iso(b[0], b[1], z)
        out.append(f'<line x1="{f(pa[0])}" y1="{f(pa[1])}" x2="{f(pb[0])}" y2="{f(pb[1])}" stroke="{sk["inner"]}" stroke-width="0.8"/>')
    cards = [Rect(cx - 16, r.y0 + 12, cx + 16, r.y0 + 40, 3), Rect(r.x0 + 12, cy - 16, r.x0 + 40, cy + 16, 3),
             Rect(r.x1 - 40, cy - 16, r.x1 - 12, cy + 16, 3), Rect(cx - 16, r.y1 - 40, cx + 16, r.y1 - 12, 3)]
    for c in sorted(cards, key=lambda c: c.x0 + c.y0):
        out += mini(P, c, z, z + 5, sk, sk["shade"], sk["sil"], sk["inner"])
        out += lines_on(P, c, z + 5, (14, 18, 10), f'rgba({sk["ink_rgb"]},0.30)', pitch=6, h=2, pad=5)
    chip = Rect(cx - 24, cy - 24, cx + 24, cy + 24, 4)
    c = prism(P, chip, z, z + 7)
    out += [f'<path d="{c["sil"]}" fill="{sk["chip_side"]}"/>', f'<path d="{c["top"]}" fill="{sk["chip_top"]}"/>',
            f'<path d="{outline(P, chip.inset(9), z + 7)}" fill="none" stroke="{sk["lens_ring"]}" stroke-width="0.8"/>']
    return out


def checks_detail(P, r, z, sk, focal):
    """A sieve: every number passes through the mesh of the verifier."""
    out = [f'<path d="{outline(P, r.inset(12), z)}" fill="none" stroke="{sk["inner_acc"] if focal else sk["inner"]}" stroke-width="0.8"/>']
    step = (S - 48) / 6
    for j in range(7):
        for i in range(7):
            x, y = r.x0 + 24 + i * step, r.y0 + 24 + j * step
            out.append(f'<path d="{outline(P, Rect(x - 4, y - 4, x + 4, y + 4, 4), z)}" fill="rgba({sk["acc_rgb"]},0.28)"/>')
    return out


def app_detail(P, r, z, sk, focal):
    """The app on a navy screen: a header, checked numbers, the chat bar."""
    screen = r.inset(8)
    soft, strong = "rgba(255,255,255,0.40)", "rgba(255,255,255,0.88)"
    out = [flat(P, screen, z, sk["screen"])]
    x0, y0 = screen.x0 + 14, screen.y0 + 16
    out.append(flat(P, Rect(x0, y0, x0 + 64, y0 + 6, 0), z, strong))
    for i, w in enumerate((92, 76, 100)):
        out.append(flat(P, Rect(x0, y0 + 20 + i * 12, x0 + w, y0 + 24 + i * 12, 0), z, soft))
    for k in range(3):
        out.append(flat(P, Rect(x0 + k * 40, y0 + 62, x0 + k * 40 + 32, y0 + 80, 3), z, strong))
    bar = Rect(x0, screen.y1 - 30, screen.x1 - 14, screen.y1 - 14, 8)
    out.append(f'<path d="{outline(P, bar, z)}" fill="none" stroke="{strong}" stroke-width="1"/>')
    return out


DETAIL = {"data": data_detail, "defs": defs_detail, "agents": agents_detail, "checks": checks_detail, "app": app_detail}

PARTS = [  # bottom to top: (key, name, two sublabel lines, thickness, closed z)
    ("data", "Data", ("made-up seats · Dynamics 365 Sales (stand-in)", "4 agreements · Unity Catalog aa_demo"), 24, 0),
    ("defs", "Definitions", ("metric view gold.sales_metrics · 7 numbers", "6 of 7 checked nightly vs a SQL twin"), 12, 24),
    ("agents", "Agents", ("Genie space “fairshare sales metrics”", "Agent Framework · Qwen3-Next · Foundry writers"), 16, 36),
    ("checks", "Checks", ("verifier on every sentence · a person approves", "MLflow traces · Foundry content filter"), 12, 52),
    ("app", "The app", ("Databricks App “fairshare”", "AI/BI dashboard · Outlook drafts"), 10, 64),
]
FOCUS = "checks"
PLATFORMS = [("databricks", "Databricks"), ("azure", "AI Foundry"), ("microsoft", "Microsoft")]
LIVES = {  # layer -> {platform: "run" | "stand-in"}
    "app": {"databricks": "run", "microsoft": "run"},          # Databricks App + AI/BI dashboard; Outlook drafts
    "checks": {"databricks": "run", "azure": "run"},           # verifier in the app, MLflow traces; Foundry content filter
    "agents": {"databricks": "run", "azure": "run"},           # Genie and the harness; the four Foundry writers
    "defs": {"databricks": "run", "microsoft": "stand-in"},    # metric view; a SQL copy of each Power BI measure (Power BI itself does not run)
    "data": {"databricks": "run", "microsoft": "stand-in"},    # Unity Catalog; a CRM shaped like Dynamics 365 Sales
}
PITCH, TOP = 100, 72  # matrix column pitch; y of the stack's top vertex, under the logo band
CAPTION = ("FOCAL LAYER", "Every number is matched to the rows of a query before anyone sees it, and nothing goes out until a person approves.")


def label(part, sub, anchor, col_x, focal, motion):
    axx, ayy = anchor
    cls = ' class="part-label"' if motion else ""
    lead = SK["lead_acc"] if focal else SK["lead"]
    dot = SK["accent"] if focal else SK["ink"]
    tone = SK["accent"] if focal else SK["muted"]
    subs = "".join(f'<text x="{f(col_x)}" y="{f(ayy + 17 + 16 * i)}" fill="{tone}" font-size="12" font-family="{aa.MONO}" letter-spacing="0.02em">{aa.esc(s)}</text>'
                   for i, s in enumerate(sub))
    return (f'<g data-role="label"{cls}>'
            f'<line data-role="leader" x1="{f(axx + 6)}" y1="{f(ayy)}" x2="{f(col_x - 12)}" y2="{f(ayy)}" stroke="{lead}" stroke-width="0.8"/>'
            f'<circle cx="{f(axx)}" cy="{f(ayy)}" r="2" fill="{dot}"/>'
            f'<text data-role="name" x="{f(col_x)}" y="{f(ayy)}" fill="{SK["ink"]}" font-size="16" font-weight="600" font-family="{aa.SANS}">{part.name}</text>'
            f'{subs}</g>')


def where_it_lives(P, parts, left, stack_left):
    """Vendor columns left of the stack: a logo and a name on top, then one dot per layer that runs on that platform,
    on the layer's own height, with a faint guide to the slab's left corner. Hollow means a stand-in in the demo."""
    xs = [left + PITCH * i + PITCH / 2 for i in range(len(PLATFORMS))]
    rows = {p.key: prism(P, p.rect, p.z, p.z + p.t)["anchor"][1] for p in parts}
    head = min(rows.values()) - 56
    out = [f'<text x="{f(left)}" y="{f(head - 18)}" fill="{SK["muted"]}" font-size="8" font-weight="500" font-family="{aa.MONO}" letter-spacing="0.18em">WHERE IT LIVES</text>']
    for (key, name), x in zip(PLATFORMS, xs):
        out.append(aa.icon(key, x - 11, head - 4, 22))
        out.append(f'<text x="{f(x)}" y="{f(head + 34)}" text-anchor="middle" fill="{SK["ink"]}" font-size="14" font-weight="600" font-family="{aa.SANS}">{name}</text>')
    for key, y in rows.items():
        out.append(f'<line x1="{f(xs[0] - 20)}" y1="{f(y)}" x2="{f(stack_left - 10)}" y2="{f(y)}" stroke="{SK["rule"]}" stroke-width="1" stroke-dasharray="2,4"/>')
        for (pk, _), x in zip(PLATFORMS, xs):
            kind = LIVES[key].get(pk)
            if kind == "run":
                out.append(f'<circle cx="{f(x)}" cy="{f(y)}" r="6" fill="{SK["ink"]}"/>')
            elif kind == "stand-in":
                out.append(f'<circle cx="{f(x)}" cy="{f(y)}" r="5.25" fill="#ffffff" stroke="{SK["ink"]}" stroke-width="1.5"/>')
    key_y = max(rows.values()) + 44
    out.append(f'<circle cx="{f(left + 6)}" cy="{f(key_y - 4)}" r="4.5" fill="{SK["ink"]}"/>'
               f'<text x="{f(left + 18)}" y="{f(key_y)}" fill="{SK["muted"]}" font-size="11" font-family="{aa.SANS}">runs here</text>'
               f'<circle cx="{f(left + 92)}" cy="{f(key_y - 4)}" r="3.75" fill="#ffffff" stroke="{SK["ink"]}" stroke-width="1.5"/>'
               f'<text x="{f(left + 104)}" y="{f(key_y)}" fill="{SK["muted"]}" font-size="11" font-family="{aa.SANS}">stand-in in the demo</text>')
    return "".join(out)


def build(motion: bool):
    parts = [Part(k, n, "", Rect(0, 0, S, S, 10), t=t, closed_z=cz) for k, n, _, t, cz in PARTS]
    subs = {k: s for k, _, s, _, _ in PARTS}
    gap = explode(parts, 0.65)
    pts = [pt for p in parts for pt in prism(Proj(0, 0), p.rect, p.z, p.z + p.t)["poly"]]
    minx, maxx = min(p[0] for p in pts), max(p[0] for p in pts)
    miny, maxy = min(p[1] for p in pts), max(p[1] for p in pts)
    lead_w, label_w, matrix_w, matrix_gap = 64, 384, len(PLATFORMS) * PITCH, 36
    left = math.floor((VW - (matrix_w + matrix_gap + maxx - minx + lead_w + label_w)) / 2 / 4) * 4
    ox, oy = round((left + matrix_w + matrix_gap - minx) / 4) * 4, round((TOP - miny) / 4) * 4
    assert oy + maxy <= VH - 64, f"figure too tall for the slide: bottom at {oy + maxy}"
    P = Proj(ox, oy)
    col_x = ox + maxx + lead_w
    lv = levels_of(parts)
    top = max(lv)
    steps = top + 1

    def attrs(i, p):
        a = (f'data-part="{p.key}" data-name="{p.name}" data-rect="{p.rect.attr()}" '
             f'data-z="{f(p.z)}" data-t="{f(p.t)}" data-level="{lv[i]}"')
        if p.key == FOCUS:
            a += " data-focal"
        if motion:
            a += f' data-closed-z="{f(p.closed_z)}"'
        return a

    def draw(p):
        focal = p.key == FOCUS
        tones, stroke, inner = styles(SK, focal)
        pr, body = solid(P, p.rect, p.z, p.z + p.t, SK, tones, stroke, inner)
        body += finish(pr, stroke, inner)
        body += DETAIL[p.key](P, p.rect, p.z + p.t, SK, focal)
        return pr, body

    out = [f'<rect width="100%" height="100%" fill="{SK["paper"]}"/>', f'<g data-exploded data-origin="{f(ox)} {f(oy)}" data-gap="{f(gap)}">']
    b, t = parts[0], parts[-1]
    trace = "".join(
        f'<line data-role="trace" x1="{f(point(P, b.rect, th, b.z + b.t)[0])}" y1="{f(point(P, b.rect, th, b.z + b.t)[1])}" '
        f'x2="{f(point(P, b.rect, th, t.z)[0])}" y2="{f(point(P, b.rect, th, t.z)[1])}" stroke="{SK["trace"]}" stroke-width="0.8" stroke-dasharray="4,3"/>'
        for th in (135, -45))
    pr0, body0 = draw(b)
    lab0 = label(b, subs[b.key], pr0["anchor"], col_x, b.key == FOCUS, False)
    if motion:
        out.append(f'<g {attrs(0, b)}>' + "".join(body0) + "</g>")
        out.append(f'<g data-motion-item data-step="{steps}" data-reveal aria-label="{b.name} stays put; trace lines show where each part sat">' + trace + lab0 + "</g>")
    else:
        out.append(trace)
        out.append(f'<g {attrs(0, b)}>' + "".join(body0) + lab0 + "</g>")
    for i in range(1, len(parts)):
        p = parts[i]
        pr, body = draw(p)
        lab = label(p, subs[p.key], pr["anchor"], col_x, p.key == FOCUS, motion)
        if motion:
            out.append(f'<g {attrs(i, p)} data-motion-item data-step="{top - lv[i] + 1}" style="--lift:{f(p.z - p.closed_z)}px" '
                       f'aria-label="{p.name} lifts clear">' + "".join(body) + lab + "</g>")
        else:
            out.append(f'<g {attrs(i, p)}>' + "".join(body) + lab + "</g>")
    out.append("</g>")
    lives = where_it_lives(P, parts, left, ox + minx)
    if motion:  # the dots line up with the exploded frame, so they arrive with the last step
        out.append(f'<g data-motion-item data-step="{steps}" data-reveal aria-label="where each layer lives">{lives}</g>')
    else:
        out.append(lives)
    out.append(aa.brand())
    cy = VH - 40
    out.append(f'<text x="{left}" y="{cy}" fill="{SK["muted"]}" font-size="8" font-family="{aa.MONO}" letter-spacing="0.18em">{CAPTION[0]}</text>')
    out.append(f'<text x="{left + 104}" y="{cy}" fill="{SK["ink"]}" font-size="14" font-family="{aa.SANS}" font-style="italic">{aa.esc(CAPTION[1])}</text>')
    return "\n        ".join(out), steps


TITLE = "What sits under an answer"
DESC = ("Exploded view of fairshare in five layers: data at the base, then one definition per number, the agents, the checks, "
        "and the app on top, with the checks layer as the focal layer.")
EYEBROW = "fairshare · the system"


def animated(body, steps):
    """diagram-design's motion template, re-skinned for AA and widened to the 1280 slide."""
    src = ax.MOTION_TEMPLATE.read_text(encoding="utf-8")
    src = src.replace("<title>Motion diagram template</title>", f"<title>{TITLE}</title>", 1)
    src = src.replace("--motion-step: 480ms;", "--motion-step: 600ms;", 1).replace("--motion-hold: 720ms;", "--motion-hold: 900ms;", 1)
    src = src.replace("--motion-total: 3600ms;", f"--motion-total: {steps * 900}ms;", 1)
    src = src.replace("min-width: 960px;", "min-width: 1000px;", 1)
    src = src.replace("  </style>", ex.MOTION_CSS + "  </style>", 1)
    start, end = src.index("  <!-- Replace template-motion"), src.index("    <div data-motion-controls")
    main = (f'  <main data-motion-root data-motion-mode="reveal" data-step-count="{steps}" data-step-current="{steps}" data-frame="static" data-static-frame="complete">\n'
            f'    <p class="eyebrow">{EYEBROW}</p>\n    <h1>{TITLE}</h1>\n\n    <div class="diagram-container">\n'
            f'      <svg viewBox="0 0 {VW} {VH}" xmlns="http://www.w3.org/2000/svg" role="img" aria-labelledby="01-system-exploded-animated-title 01-system-exploded-animated-desc">\n'
            f'        <title id="01-system-exploded-animated-title">{TITLE}</title>\n        <desc id="01-system-exploded-animated-desc">{DESC}</desc>\n'
            f'        {body}\n      </svg>\n    </div>\n\n')
    src = src[:start] + main + src[end:]
    src = re.sub(r'Step <span data-motion-step-label>\d+</span> of \d+', f'Step <span data-motion-step-label>{steps}</span> of {steps}', src, count=1)
    src = src.replace("The complete final diagram is shown above.", "The complete exploded diagram is shown above.", 1)
    return aa.aa_motion(src)


if __name__ == "__main__":
    body, _ = build(False)
    (aa.OUT / "01-system-exploded.html").write_text(aa.page(slug="01-system-exploded", title=TITLE, desc=DESC, eyebrow=EYEBROW, body=body), encoding="utf-8")
    body, steps = build(True)
    (aa.OUT / "01-system-exploded-animated.html").write_text(animated(body, steps), encoding="utf-8")
    print("wrote 01-system-exploded.html and 01-system-exploded-animated.html")
