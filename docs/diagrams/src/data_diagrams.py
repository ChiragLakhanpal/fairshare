"""06 and 07, the data section: where the numbers come from, and what fair share means.

    python3 docs/diagrams/src/data_diagrams.py   # writes docs/diagrams/06-data-pipeline.html and 07-fair-share.html

Every number comes from data_numbers.py, which runs one query per number on the local lakehouse. Generic icons are
diagram-design's Tabler set, read from references/primitive-icons.md so they stay in step with the plugin.
"""
from __future__ import annotations

import re

import aa
from data_numbers import numbers

VW, VH = 1280, 720
N = numbers()
ICON_DOC = aa.SCRIPTS.parent / "skills" / "diagram-design" / "references" / "primitive-icons.md"


def tabler(name: str, x: float, y: float, size: float = 28, color: str = aa.INK) -> str:
    """One icon from diagram-design's library at (x, y), stroked or filled the way the library ships it."""
    doc = ICON_DOC.read_text(encoding="utf-8")
    block = re.search(r"^### " + re.escape(name) + r"\n.*?```svg\n(.*?)\n```", doc, re.S | re.M).group(1)
    inner = re.search(r"<svg[^>]*>(.*)</svg>", block, re.S).group(1)
    inner = re.sub(r"<title>.*?</title>", "", inner)
    stroked = 'stroke="currentColor"' in block
    paint = (f'fill="none" stroke="{color}" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"'
             if stroked else f'fill="{color}"')
    return f'<svg x="{x}" y="{y}" width="{size}" height="{size}" viewBox="0 0 24 24" aria-hidden="true" {paint}>{inner}</svg>'


def text(x, y, s, size=16, weight=600, color=aa.INK, anchor="start", mono=False, spacing=None, italic=False):
    fam = aa.MONO if mono else aa.SANS
    extra = (f' letter-spacing="{spacing}"' if spacing else "") + (' font-style="italic"' if italic else "")
    return (f'<text x="{x}" y="{y}" fill="{color}" font-size="{size}" font-weight="{weight}" font-family="{fam}" '
            f'text-anchor="{anchor}"{extra}>{aa.esc(s)}</text>')


def eyebrow(x, y, s, anchor="start", color=aa.MUTED):
    return text(x, y, s.upper(), size=8, weight=500, color=color, anchor=anchor, mono=True, spacing="0.18em")


def markers():
    return ("<defs>"
            f'<marker id="arrow" markerWidth="8" markerHeight="6" refX="7" refY="3" orient="auto"><polygon points="0 0, 8 3, 0 6" fill="{aa.MUTED}"/></marker>'
            f'<marker id="arrow-accent" markerWidth="8" markerHeight="6" refX="7" refY="3" orient="auto"><polygon points="0 0, 8 3, 0 6" fill="{aa.ACCENT}"/></marker>'
            "</defs>")


def fmt(n) -> str:
    return f"{int(n):,}"


# ---------------------------------------------------------------- 06 where the numbers come from

TIER_Y, TIER_H, TIER_W, TIER_GAP, TIER_X0 = 200, 332, 168, 28, 296  # low enough that arcs, cards and strip centre on the slide
ATTACH = [round((TIER_Y + TIER_H * k / 5) / 4) * 4 for k in (1, 2, 3, 4)]  # four ports on a tier edge, L * k / 5, 4px grid


def tier_x(i):
    return TIER_X0 + i * (TIER_W + TIER_GAP)


def pipeline() -> str:
    tiers = [  # name, schema, big number, unit, chips; the last tier is the focal one
        ("As delivered", "bronze", fmt(N["bookings_delivered"]), "booking rows", [f"{N['bronze_tables']} tables, as sent"]),
        ("Cleaned", "silver", fmt(N["bookings_cleaned"]), "booking rows",
         [f"−{N['bookings_delivered'] - N['bookings_cleaned']} tickets loaded twice",
          f"{N['channel_spellings_delivered']} channel spellings → {N['channel_spellings_cleaned']}"]),
        ("Ready to use", "gold", fmt(N["gold_rows"]), "rows", ["per agency, route, month"]),
        ("Defined once", "gold.sales_metrics", str(N["kpis"]), "numbers", ["6 checked each night"]),
    ]
    arcs = [("CLEAN", False), ("SHAPE", False), ("DEFINE", True)]
    out = [f'<rect width="100%" height="100%" fill="{aa.PAPER}"/>', markers()]

    # promotions as orthogonal bridges over the top, drawn before the cards (connector rule 1: no curves): up from the
    # left tier's top edge at 2/3 of its width, across, and down into the next tier's top edge at 1/3, r=8 corners, so
    # every tier edge has its own port for the bridge arriving and the bridge leaving
    run_y = TIER_Y - 48
    for i, (label, focal) in enumerate(arcs):
        sx, ex = tier_x(i) + TIER_W * 2 // 3, tier_x(i + 1) + TIER_W // 3
        stroke, width, marker = (aa.ACCENT, 1.6, "arrow-accent") if focal else (aa.MUTED, 1.4, "arrow")
        out.append(f'<path d="M {sx},{TIER_Y} V {run_y + 8} A 8 8 0 0 1 {sx + 8},{run_y} H {ex - 8} A 8 8 0 0 1 {ex},{run_y + 8} V {TIER_Y}" '
                   f'fill="none" stroke="{stroke}" stroke-width="{width}" stroke-linejoin="round" marker-end="url(#{marker})"/>')
        mid, w = (sx + ex) / 2, -(-(len(label) * 0.70 * 12 + 16) // 4) * 4  # 0.62em mono + 0.08em tracking per char, padded
        out.append(f'<rect x="{mid - w / 2}" y="{run_y - 26}" width="{w}" height="18" fill="{aa.PAPER}"/>')  # mask, 8px above the run
        out.append(text(mid, run_y - 13, label, size=12, weight=400, color=stroke, anchor="middle", mono=True, spacing="0.08em"))

    # sources into the first tier, and the readers out of the last, on straight runs at the shared ports
    sources = [("csv", None, "Seat shares", "made up, one per route"), ("users", None, "Agency sales", "synthetic"),
               ("file", None, f"{N['agreements']} agreements", "clauses by page"), (None, "dynamics365", "CRM", "Dynamics 365, stand-in")]
    readers = [("desktop", "The app"), ("monitoring", "Dashboard"), ("search", "Genie"), ("robot", "Agents")]
    out.append(eyebrow(40, ATTACH[0] - 44, "Sources"))
    out.append(eyebrow(tier_x(3) + TIER_W + 52, ATTACH[0] - 44, "Read by"))
    for y, (tab, brand, name, tag) in zip(ATTACH, sources):
        out.append(f'<line x1="260" y1="{y}" x2="{TIER_X0 - 2}" y2="{y}" stroke="{aa.MUTED}" stroke-width="1.4" marker-end="url(#arrow)"/>')
        out.append(tabler(tab, 40, y - 14, 28) if tab else aa.icon(brand, 42, y - 12, 24))
        out.append(text(80, y - 2, name, size=16))
        out.append(text(80, y + 16, tag, size=12, weight=400, color=aa.MUTED, mono=True))
    rx = tier_x(3) + TIER_W
    for y, (tab, name) in zip(ATTACH, readers):
        out.append(f'<line x1="{rx + 2}" y1="{y}" x2="{rx + 42}" y2="{y}" stroke="{aa.MUTED}" stroke-width="1.4" marker-end="url(#arrow)"/>')
        out.append(tabler(tab, rx + 52, y - 14, 28))
        out.append(text(rx + 92, y + 6, name, size=16))

    # the tier cards
    for i, (name, schema, big, unit, chips) in enumerate(tiers):
        x, focal = tier_x(i), i == len(tiers) - 1
        cx = x + TIER_W / 2
        fill, stroke, sw, band = (("rgba(0,108,191,0.07)", aa.ACCENT, 1.6, "rgba(0,108,191,0.14)") if focal
                                  else ("#ffffff", aa.MUTED if i == 0 else aa.INK, 1, "rgba(90,113,129,0.10)" if i == 0 else "rgba(54,73,90,0.06)"))
        out.append(f'<g data-tier="{schema}"><rect x="{x}" y="{TIER_Y}" width="{TIER_W}" height="{TIER_H}" rx="6" fill="{fill}" stroke="{stroke}" stroke-width="{sw}"/>')
        out.append(f'<path d="M {x + 6},{TIER_Y} H {x + TIER_W - 6} A 6 6 0 0 1 {x + TIER_W},{TIER_Y + 6} V {TIER_Y + 48} H {x} V {TIER_Y + 6} A 6 6 0 0 1 {x + 6},{TIER_Y} Z" fill="{band}"/>')
        out.append(text(cx, TIER_Y + 30, name, size=16, anchor="middle"))
        out.append(text(cx, TIER_Y + 76, schema, size=12, weight=400, color=aa.ACCENT if focal else aa.MUTED, anchor="middle", mono=True))
        out.append(text(cx, TIER_Y + 156, big, size=40, color=aa.ACCENT if focal else aa.INK, anchor="middle"))
        out.append(text(cx, TIER_Y + 182, unit, size=12, weight=400, color=aa.MUTED, anchor="middle", mono=True))
        for k, chip in enumerate(chips):
            cy = TIER_Y + 232 + k * 36
            out.append(f'<rect x="{x + 8}" y="{cy}" width="{TIER_W - 16}" height="24" rx="2" fill="#ffffff" stroke="{aa.RULE_SOLID}" stroke-width="1"/>')
            out.append(text(cx, cy + 16, chip, size=11, weight=400, color=aa.INK, anchor="middle"))  # plain words, so Inter, not mono
        out.append("</g>")

    # who can see what: the one sentence of governance, on a quiet strip under the tiers
    sy = TIER_Y + TIER_H + 36
    out.append(f'<rect x="{TIER_X0}" y="{sy}" width="{tier_x(3) + TIER_W - TIER_X0}" height="40" rx="6" fill="{aa.PAPER2}"/>')
    out.append(tabler("lock", TIER_X0 + 16, sy + 8, 24))
    out.append(text(TIER_X0 + 52, sy + 26, "Every query runs as the person asking", size=16))
    out.append(text(tier_x(3) + TIER_W - 16, sy + 26, "Unity Catalog aa_demo", size=12, weight=400, color=aa.MUTED, anchor="end", mono=True))
    out.append(aa.brand(tag="fairshare · synthetic data"))
    return "\n        ".join(out)


# ---------------------------------------------------------------- 07 what fair share means

PITCH, CELL = 26, 20
GRID = 10 * PITCH - (PITCH - CELL)  # 254


def seat(x, y, state):
    """A seat: a back and a cushion. AA, AA above fair share, or another airline."""
    fill, stroke, sw = {"aa": (aa.ACCENT, aa.ACCENT, 1), "premium": ("rgba(0,108,191,0.16)", aa.ACCENT, 1.4),
                        "other": ("#ffffff", aa.RULE_SOLID, 1)}[state]
    return (f'<rect x="{x + 3}" y="{y}" width="14" height="13" rx="3" fill="{fill}" stroke="{stroke}" stroke-width="{sw}"/>'
            f'<rect x="{x + 1}" y="{y + 13}" width="18" height="7" rx="2" fill="{fill}" stroke="{stroke}" stroke-width="{sw}"/>')


def square(x, y, state):
    """One dollar of every hundred the agency sold on the route."""
    fill, stroke, sw = {"aa": (aa.ACCENT, aa.ACCENT, 1), "premium": ("rgba(0,108,191,0.16)", aa.ACCENT, 1.4),
                        "other": ("#ffffff", aa.RULE_SOLID, 1)}[state]
    return f'<rect x="{x + 1}" y="{y + 1}" width="18" height="18" rx="4" fill="{fill}" stroke="{stroke}" stroke-width="{sw}"/>'


def grid(x0, y0, aa_cells, premium, glyph):
    out = []
    for k in range(100):
        state = "aa" if k < aa_cells else "premium" if k < aa_cells + premium else "other"
        out.append(glyph(x0 + (k % 10) * PITCH, y0 + (k // 10) * PITCH, state))
    return "".join(out)


def fair_share() -> str:
    fair, share, gap, usd = N["fair_share_pct"], N["aa_share_pct"], N["gap_pts"], N["gap_usd"]
    fair_cells, share_cells = round(fair), round(share)  # ponytail: a 100-cell grid rounds to whole cells; the labels carry the decimals
    gy, ax, bx = 168, 96, 456
    out = [f'<rect width="100%" height="100%" fill="{aa.PAPER}"/>', aa.brand(tag="fairshare · synthetic data")]
    # A: seats on the route, the fair share
    out.append(text(ax, gy - 46, "Seats on DFW to Chicago", size=16))
    out.append(text(ax, gy - 24, "made-up seat shares · Q3 2026", size=12, weight=400, color=aa.MUTED, mono=True))
    out.append(f'<g data-grid="seats">{grid(ax, gy, fair_cells, 0, seat)}</g>')
    out.append(text(ax, gy + GRID + 56, f"{fair}%", size=40, color=aa.ACCENT))
    out.append(text(ax, gy + GRID + 84, "are AA's: the fair share", size=16, color=aa.MUTED))
    # B: the agency's sales on the same route, the AA share and the premium above fair share
    out.append(text(bx, gy - 46, "Summit's sales on the same route", size=16))
    out.append(text(bx, gy - 24, "Summit Travel Partners · Q3 2026", size=12, weight=400, color=aa.MUTED, mono=True))
    out.append(f'<g data-grid="sales">{grid(bx, gy, fair_cells, share_cells - fair_cells, square)}</g>')
    out.append(text(bx, gy + GRID + 56, f"{share}%", size=40, color=aa.ACCENT))
    out.append(text(bx, gy + GRID + 84, "went to AA: the AA share", size=16, color=aa.MUTED))
    # the payoff
    px = 836
    out.append(f'<line x1="{px - 36}" y1="{gy}" x2="{px - 36}" y2="{gy + GRID + 84}" stroke="{aa.RULE_SOLID}" stroke-width="1"/>')
    out.append(eyebrow(px, gy + 8, "Share premium"))
    out.append(text(px, gy + 64, f"+{gap} points", size=40, color=aa.ACCENT))
    out.append(text(px, gy + 92, "above fair share", size=16, color=aa.MUTED))
    out.append(text(px, gy + 172, f"${fmt(usd)}", size=40))
    out.append(text(px, gy + 200, "more AA revenue than", size=16, color=aa.MUTED))
    out.append(text(px, gy + 222, "fair share would bring", size=16, color=aa.MUTED))
    out.append(text(px, gy + 252, "same route, same quarter", size=12, weight=400, color=aa.MUTED, mono=True))
    # the one sentence that defines it
    cy = gy + GRID + 140
    out.append(text(ax, cy, f"An agency that sold every airline in proportion to its seats would give AA {fair}% here. Summit gives {share}%.",
                    size=14, weight=400, color=aa.INK, italic=True))
    # legend strip
    ly = VH - 40
    out.append(f'<line x1="{ax}" y1="{ly - 28}" x2="{VW - 40}" y2="{ly - 28}" stroke="{aa.RULE}" stroke-width="1"/>')
    out.append(eyebrow(ax, ly + 4, "Legend"))
    keys = [(seat, "aa", "AA seat"), (square, "aa", "$1 of every $100 to AA"), (square, "premium", "above fair share"),
            (square, "other", "another airline")]
    kx = ax + 96
    for glyph, state, label in keys:
        out.append(glyph(kx, ly - 12, state))
        out.append(text(kx + 28, ly + 4, label, size=11, weight=400, color=aa.MUTED))
        kx += 52 + 7 * len(label)
    return "\n        ".join(out)


if __name__ == "__main__":
    pages = [("06-data-pipeline", "Where the numbers come from", "fairshare · the data",
              "Four sources pass through three Unity Catalog tiers, delivered, cleaned and ready to use, before seven numbers are defined once in the metric view that the app, the dashboard, Genie and the agents all read.",
              pipeline()),
             ("07-fair-share", "What fair share means", "fairshare · the data",
              f"Two grids of one hundred: AA's {N['fair_share_pct']}% share of the seats on DFW to Chicago in Q3 2026, and the {N['aa_share_pct']}% of Summit Travel Partners' sales on that route that went to AA, a premium of {N['gap_pts']} points.",
              fair_share())]
    for slug, title, eyebrow_text, desc, body in pages:
        (aa.OUT / f"{slug}.html").write_text(aa.page(slug=slug, title=title, desc=desc, eyebrow=eyebrow_text, body=body), encoding="utf-8")
        print("wrote", f"{slug}.html")
