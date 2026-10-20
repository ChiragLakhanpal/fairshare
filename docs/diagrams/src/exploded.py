"""01: the whole system as one exploded stack, data at the bottom and the app on top, the checks layer in AA blue. 15: the same five layers at AA,
with three marks for what runs today, what is built but not deployed and what waits on AA's Microsoft account, and each table beside the AA feed that
would replace it.

    python3 docs/diagrams/src/exploded.py   # writes docs/diagrams/01-system-exploded.html, 01-system-exploded-animated.html and 15-at-aa.html

Every point comes from iso(x, y, z) through diagram-design's axonometry helpers; scripts/verify-exploded.py in the plugin
reprojects each part from the data-* attributes written here. 01 and 15 draw their slabs through the same stack_svg().
"""
from __future__ import annotations

import math
import re
from html import unescape

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


def label_head(part, anchor, col_x, focal, cls=""):
    """The top of a label, shared by 01 and 15: the leader from the slab's right extreme, its dot, and the layer name. The caller adds what goes
    under the name and closes the group."""
    axx, ayy = anchor
    lead = SK["lead_acc"] if focal else SK["lead"]
    dot = SK["accent"] if focal else SK["ink"]
    return (f'<g data-role="label"{cls}>'
            f'<line data-role="leader" x1="{f(axx + 6)}" y1="{f(ayy)}" x2="{f(col_x - 12)}" y2="{f(ayy)}" stroke="{lead}" stroke-width="0.8"/>'
            f'<circle cx="{f(axx)}" cy="{f(ayy)}" r="2" fill="{dot}"/>'
            f'<text data-role="name" x="{f(col_x)}" y="{f(ayy)}" fill="{SK["ink"]}" font-size="16" font-weight="600" font-family="{aa.SANS}">{part.name}</text>')


def label(part, sub, anchor, col_x, focal, motion):
    ayy = anchor[1]
    cls = ' class="part-label"' if motion else ""
    tone = SK["accent"] if focal else SK["muted"]
    subs = "".join(f'<text x="{f(col_x)}" y="{f(ayy + 17 + 16 * i)}" fill="{tone}" font-size="12" font-family="{aa.MONO}" letter-spacing="0.02em">{aa.esc(s)}</text>'
                   for i, s in enumerate(sub))
    return label_head(part, anchor, col_x, focal, cls) + subs + "</g>"


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


def stack_geometry():
    """The five slabs lifted apart by the plugin's gap rule, and how far the stack reaches from its own origin: (minx, maxx, miny, maxy)."""
    parts = [Part(k, n, "", Rect(0, 0, S, S, 10), t=t, closed_z=cz) for k, n, _, t, cz in PARTS]
    gap = explode(parts, 0.65)
    pts = [pt for p in parts for pt in prism(Proj(0, 0), p.rect, p.z, p.z + p.t)["poly"]]
    return parts, gap, (min(p[0] for p in pts), max(p[0] for p in pts), min(p[1] for p in pts), max(p[1] for p in pts))


def stack_svg(P, parts, gap, col_x, focus, labeler, motion):
    """The <g data-exploded> figure, drawn the same way for 01 and 15: the trace lines, then every slab from the bottom up with its label inside
    its group. `labeler(part, anchor, focal, animated)` draws one label; the bottom slab's label never animates. Returns the markup pieces
    and the number of reveal steps."""
    lv = levels_of(parts)
    top = max(lv)
    steps = top + 1

    def attrs(i, p):
        a = (f'data-part="{p.key}" data-name="{p.name}" data-rect="{p.rect.attr()}" '
             f'data-z="{f(p.z)}" data-t="{f(p.t)}" data-level="{lv[i]}"')
        if p.key == focus:
            a += " data-focal"
        if motion:
            a += f' data-closed-z="{f(p.closed_z)}"'
        return a

    def draw(p):
        focal = p.key == focus
        tones, stroke, inner = styles(SK, focal)
        pr, body = solid(P, p.rect, p.z, p.z + p.t, SK, tones, stroke, inner)
        body += finish(pr, stroke, inner)
        body += DETAIL[p.key](P, p.rect, p.z + p.t, SK, focal)
        return pr, body

    out = [f'<g data-exploded data-origin="{f(P.ox)} {f(P.oy)}" data-gap="{f(gap)}">']
    b, t = parts[0], parts[-1]
    trace = "".join(
        f'<line data-role="trace" x1="{f(point(P, b.rect, th, b.z + b.t)[0])}" y1="{f(point(P, b.rect, th, b.z + b.t)[1])}" '
        f'x2="{f(point(P, b.rect, th, t.z)[0])}" y2="{f(point(P, b.rect, th, t.z)[1])}" stroke="{SK["trace"]}" stroke-width="0.8" stroke-dasharray="4,3"/>'
        for th in (135, -45))
    pr0, body0 = draw(b)
    lab0 = labeler(b, pr0["anchor"], b.key == focus, False)
    if motion:
        out.append(f'<g {attrs(0, b)}>' + "".join(body0) + "</g>")
        out.append(f'<g data-motion-item data-step="{steps}" data-reveal aria-label="{b.name} stays put; trace lines show where each part sat">' + trace + lab0 + "</g>")
    else:
        out.append(trace)
        out.append(f'<g {attrs(0, b)}>' + "".join(body0) + lab0 + "</g>")
    for i in range(1, len(parts)):
        p = parts[i]
        pr, body = draw(p)
        lab = labeler(p, pr["anchor"], p.key == focus, motion)
        if motion:
            out.append(f'<g {attrs(i, p)} data-motion-item data-step="{top - lv[i] + 1}" style="--lift:{f(p.z - p.closed_z)}px" '
                       f'aria-label="{p.name} lifts clear">' + "".join(body) + lab + "</g>")
        else:
            out.append(f'<g {attrs(i, p)}>' + "".join(body) + lab + "</g>")
    out.append("</g>")
    return out, steps


def build(motion: bool):
    parts, gap, (minx, maxx, miny, maxy) = stack_geometry()
    subs = {k: s for k, _, s, _, _ in PARTS}
    lead_w, label_w, matrix_w, matrix_gap = 64, 384, len(PLATFORMS) * PITCH, 36
    left = math.floor((VW - (matrix_w + matrix_gap + maxx - minx + lead_w + label_w)) / 2 / 4) * 4
    ox, oy = round((left + matrix_w + matrix_gap - minx) / 4) * 4, round((TOP - miny) / 4) * 4
    assert oy + maxy <= VH - 64, f"figure too tall for the slide: bottom at {oy + maxy}"
    P = Proj(ox, oy)
    col_x = ox + maxx + lead_w
    stack, steps = stack_svg(P, parts, gap, col_x, FOCUS, lambda p, anchor, focal, animated: label(p, subs[p.key], anchor, col_x, focal, animated), motion)
    out = [f'<rect width="100%" height="100%" fill="{SK["paper"]}"/>'] + stack
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


# ---------------------------------------------------------------- 15: the same layers at AA
#
# The same five slabs through the same stack_svg(). What changes is what stands next to them: 01 had a column of platform logos with a dot per
# layer; here every piece under a layer carries one of three marks, drawn in 01's own dot grammar (solid, half, hollow), and the right half lists
# each made-up table beside the AA feed that would replace it, hardest first. The focal slab is the data, because the feeds are the work and the
# first row of the list is the hard one. Nothing on it is a number from the data, so its logo band keeps the default tag.

RUN, BUILT, WAIT = "run", "built", "wait"
MARKS = {RUN: "Running today", BUILT: "Built, not deployed", WAIT: "Waiting on AA's Microsoft account"}
KEY_W = {RUN: 88, BUILT: 115, WAIT: 212}  # the legend's text widths at 13px Inter, to space its three entries
AT_AA_FOCUS = "data"
AT_AA = {  # layer -> (mark, piece), in the order they print
    "app": [(RUN, "Databricks App and dashboard"), (WAIT, "Teams through Copilot Studio"), (WAIT, "Entra ID sign-in")],
    "checks": [(RUN, "Verifier in the Databricks App"), (RUN, "MLflow traces")],
    "agents": [(RUN, "Databricks Genie and the harness"), (RUN, "Foundry writers"), (BUILT, "Harness as a Foundry hosted agent")],
    "defs": [(RUN, "Databricks metric view")],
    "data": [(RUN, "Databricks Unity Catalog"), (WAIT, "Fabric and OneLake"), (WAIT, "Dataverse mirror")],
}
# Hardest first, in the data lead's order and words: (the demo's tables, the AA feed that would replace them, why it is the hard one).
# The lines are broken by hand to fit the 404px feed column at 14px Inter, and measured in a browser.
FEEDS = [
    (("fact_agency_sales_monthly",),
     ("AA's own agency sales from ARC and BSP;", "the agency's sales on other airlines from MIDT bookings,", "or ticketed sales with fares such as IATA DDS."),
     ("The hardest, because AA sees its own sales and not the", "agency's sales elsewhere, and MIDT carries no fares.")),
    (("fact_market_capacity",),
     ("One schedule source for every carrier (such as OAG or", "Cirium), then T-100 for every carrier once DOT publishes it,", "because the agreements define fair share by DOT data."), ()),
    (("fact_corporate_bookings",), ("AA ticketing, by corporate account.",), ()),
    (("contract_clauses",), ("The agency agreements, read the same way.",), ()),
    (("crm_contacts", "crm_opportunities", "crm_activities"), ("Dynamics 365 Sales, through the Dataverse mirror.",), ()),
    (("agency_goals",), ("The sales plan.",), ()),
]
STACK_LEFT, LEAD_AT_AA = 46, 40   # no platform matrix to make room for, so the stack sits at the left edge and the labels follow it
HEAD_Y, RULE_Y = 96, 108          # the baseline of both headings, and the line under the list's heading
STRIP_L, FEED_X, STRIP_R = 632, 836, 1240
ITEM_PITCH = 18                   # between the pieces under one layer name
ROW_PAD, FEED_LH, TBL_LH, WHY_GAP = 20, 20, 18, 6  # a list row's padding, its text line, its table-name line, and the space before the note
KEY_RULE_Y, KEY_BASE_Y = 664, 694  # the legend strip's rule and its text baseline, where 12's legend sits


def text(x, y, s, *, size=14, fill=None, mono=False, italic=False, weight=400):
    extra = (f' font-weight="{weight}"' if weight != 400 else "") + (' font-style="italic"' if italic else "")
    return (f'<text x="{f(x)}" y="{f(y)}" fill="{fill or SK["ink"]}" font-size="{size}"{extra} '
            f'font-family="{aa.MONO if mono else aa.SANS}">{aa.esc(s)}</text>')


def eyebrow(x, y, s, anchor="start"):
    end = ' text-anchor="end"' if anchor == "end" else ""
    return (f'<text x="{f(x)}" y="{f(y)}" fill="{SK["muted"]}" font-size="8" font-weight="500" font-family="{aa.MONO}" '
            f'letter-spacing="0.18em"{end}>{aa.esc(s.upper())}</text>')


def mark(kind, cx, cy, r=5):
    """One of the three status marks, the way 01 draws its dots: a solid ink dot, a ring with its left half filled, and a hollow ring."""
    assert kind in MARKS, f"no mark called {kind!r}"
    c, ring = f'cx="{f(cx)}" cy="{f(cy)}"', r - 0.75
    if kind == RUN:
        return f'<g data-mark="{kind}"><circle {c} r="{f(r)}" fill="{SK["ink"]}"/></g>'
    half = (f'<path d="M {f(cx)} {f(cy - ring)} A {f(ring)} {f(ring)} 0 0 0 {f(cx)} {f(cy + ring)} Z" fill="{SK["ink"]}"/>') if kind == BUILT else ""
    return (f'<g data-mark="{kind}"><circle {c} r="{f(ring)}" fill="#ffffff"/>{half}'
            f'<circle {c} r="{f(ring)}" fill="none" stroke="{SK["ink"]}" stroke-width="1.5"/></g>')


def label_at_aa(part, anchor, col_x, focal):
    """01's label with the sublabels replaced by one line per piece, each behind its mark."""
    ayy = anchor[1]
    rows = "".join(mark(kind, col_x + 5, ayy + 14.5 + ITEM_PITCH * i) + text(col_x + 18, ayy + 19 + ITEM_PITCH * i, piece, size=13)
                   for i, (kind, piece) in enumerate(AT_AA[part.key]))
    return label_head(part, anchor, col_x, focal) + rows + "</g>"


def feed_strip():
    """The right half: each made-up table beside the AA feed that would replace it, hardest first. A row is as tall as its text, to the 4px grid."""
    out = [eyebrow(STRIP_L, HEAD_Y, "Table of made-up data"), eyebrow(FEED_X, HEAD_Y, "AA feed that would replace it"), eyebrow(STRIP_R, HEAD_Y, "Hardest first", "end"),
           f'<line x1="{STRIP_L}" y1="{RULE_Y}" x2="{STRIP_R}" y2="{RULE_Y}" stroke="{aa.RULE_SOLID}" stroke-width="1"/>']
    y = RULE_Y
    for i, (tables, feed, why) in enumerate(FEEDS):
        height = 2 * ROW_PAD + max(len(feed) * FEED_LH + (WHY_GAP + len(why) * FEED_LH if why else 0), len(tables) * TBL_LH)
        height = -(-height // 4) * 4
        base = y + ROW_PAD + 15
        row = [text(STRIP_L, base + TBL_LH * j, t, size=12, mono=True, fill=aa.ACCENT if i == 0 else None, weight=500 if i == 0 else 400) for j, t in enumerate(tables)]
        row += [text(FEED_X, base + FEED_LH * j, line) for j, line in enumerate(feed)]
        row += [text(FEED_X, base + len(feed) * FEED_LH + WHY_GAP + FEED_LH * j, line, italic=True) for j, line in enumerate(why)]
        out.append(f'<g data-feed="{tables[0]}">{"".join(row)}</g>')
        y += height
        if i < len(FEEDS) - 1:
            out.append(f'<line x1="{STRIP_L}" y1="{y}" x2="{STRIP_R}" y2="{y}" stroke="{aa.RULE}" stroke-width="0.8"/>')
    return "".join(out)


def mark_key():
    """The three marks, named, in the bottom strip every data figure uses."""
    out = [f'<line x1="40" y1="{KEY_RULE_Y}" x2="1240" y2="{KEY_RULE_Y}" stroke="{aa.RULE}" stroke-width="0.8"/>', eyebrow(40, KEY_BASE_Y, "Legend")]
    x = 144
    for kind in (RUN, BUILT, WAIT):
        out += [mark(kind, x + 5, KEY_BASE_Y - 4.5), text(x + 18, KEY_BASE_Y, MARKS[kind], size=13)]
        x += 18 + KEY_W[kind] + 36
    return "".join(out)


def build_at_aa():
    parts, gap, (minx, maxx, miny, maxy) = stack_geometry()
    ox, oy = round((STACK_LEFT - minx) / 4) * 4, round((TOP - miny) / 4) * 4
    assert oy + maxy <= KEY_RULE_Y - 12, f"the stack runs into the legend: bottom at {oy + maxy}"
    P = Proj(ox, oy)
    col_x = ox + maxx + LEAD_AT_AA
    stack, _ = stack_svg(P, parts, gap, col_x, AT_AA_FOCUS, lambda p, anchor, focal, animated: label_at_aa(p, anchor, col_x, focal), False)
    out = [f'<rect width="100%" height="100%" fill="{SK["paper"]}"/>'] + stack
    out += [eyebrow(col_x, HEAD_Y, "Where it stands in the demo"), feed_strip(), aa.brand(), mark_key()]
    return "\n        ".join(out)


def check_at_aa(body: str):
    """What the figure says, held to what the repo says, on every build."""
    root = aa.OUT.parent.parent
    gold = set(re.findall(r"CREATE OR REPLACE TABLE aa_demo\.gold\.(\w+)", (root / "lakehouse/02_gold.sql").read_text(encoding="utf-8")))
    tables = [t for ts, _, _ in FEEDS for t in ts]
    assert all(t in gold for t in tables), f"the list names a table that gold does not build: {[t for t in tables if t not in gold]}"
    assert [ts[0] for ts, _, _ in FEEDS] == ["fact_agency_sales_monthly", "fact_market_capacity", "fact_corporate_bookings", "contract_clauses",
                                             "crm_contacts", "agency_goals"], "the feeds keep the data lead's order, hardest first"
    # every piece the brief names, under the one mark the brief gives it
    pieces = [(kind, piece) for rows in AT_AA.values() for kind, piece in rows]
    want = {"Databricks": RUN, "Foundry writers": RUN, "MLflow": RUN, "Foundry hosted agent": BUILT, "Fabric and OneLake": WAIT, "Dataverse": WAIT,
            "Teams through Copilot Studio": WAIT, "Entra ID": WAIT}
    for name, kind in want.items():
        found = {k for k, p in pieces if name in p}
        assert found == {kind}, f"{name} should print under {MARKS[kind]!r} and nothing else; it prints under {sorted(found)}"
    assert all(any(k == RUN and "Databricks" in p for k, p in rows) for rows in AT_AA.values()), "Databricks runs under every layer"
    # Foundry: the writers run in the nightly job's task, and the harness as a hosted agent is built (its host and its image); that it was never deployed no file can show
    assert re.search(r'parameters:\s*\["agents",\s*"foundry"', (root / "databricks.yml").read_text(encoding="utf-8")), "the nightly job no longer runs the Foundry writers"
    assert (root / "harness/foundry/host.py").exists() and (root / "harness/foundry/Dockerfile").exists(), "the Foundry hosted agent is not built"
    words = " ".join(unescape(t) for t in re.findall(r"<text[^>]*>(.*?)</text>", body))
    assert not re.search(r"possible|not built", words, re.I), "Foundry is neither possible nor not built"
    assert not re.search("[\u2013\u2014\u2212]", words), "the only dash is the hyphen"
    assert not re.search(r"\d", words.replace("T-100", "").replace("Dynamics 365", "")), "this figure prints no number from the data"


AT_AA_TITLE = "The same layers at AA"
AT_AA_DESC = ("The five layers of fairshare with a mark on each piece for what runs today, what is built but not deployed and what waits on AA's Microsoft "
              "account, beside each made-up table and the AA feed that would replace it, hardest first.")
AT_AA_EYEBROW = "fairshare · at AA"


TITLE = "What sits under an answer"
DESC = ("Exploded view of fairshare in five layers: data at the base, then one definition per number, the agents, the checks, "
        "and the app on top, with the checks layer as the focal layer.")
EYEBROW = "fairshare · the system"


if __name__ == "__main__":
    body, _ = build(False)
    (aa.OUT / "01-system-exploded.html").write_text(aa.page(slug="01-system-exploded", title=TITLE, desc=DESC, eyebrow=EYEBROW, body=body), encoding="utf-8")
    body, steps = build(True)
    page = aa.animated(slug="01-system-exploded-animated", title=TITLE, desc=DESC, eyebrow=EYEBROW, body=body, steps=steps, css=ex.MOTION_CSS)
    (aa.OUT / "01-system-exploded-animated.html").write_text(page, encoding="utf-8")
    body = build_at_aa()
    check_at_aa(body)
    (aa.OUT / "15-at-aa.html").write_text(aa.page(slug="15-at-aa", title=AT_AA_TITLE, desc=AT_AA_DESC, eyebrow=AT_AA_EYEBROW, body=body), encoding="utf-8")
    print("wrote 01-system-exploded.html, 01-system-exploded-animated.html and 15-at-aa.html")
