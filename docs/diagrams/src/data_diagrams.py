"""06 and 07, the data section: where the numbers come from, and what fair share means.

    .venv/bin/python docs/diagrams/src/data_diagrams.py   # writes docs/diagrams/06-data-pipeline.html, 06-data-pipeline-animated.html and 07-fair-share.html

Every number comes from deck_facts.py, which runs one query per number on the local lakehouse (the deck reads the same file).
Generic icons are diagram-design's Tabler set, read from references/primitive-icons.md so they stay in step with the plugin.
"""
from __future__ import annotations

import re

import aa
from deck_facts import DATED, fact, query

VW, VH = 1280, 720
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


def eyebrow(x, y, s, anchor="start", color=aa.MUTED, size=8):
    """A small mono heading; 06's two headings over its sources and its readers are structure, so they take the ramp's 12px label."""
    return text(x, y, s.upper(), size=size, weight=500, color=color, anchor=anchor, mono=True, spacing="0.18em")


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


PIPELINE_STEPS = [  # the motion steps of 06, left to right; each arrow comes in with what it points at
    "The sources: seat shares, agency sales, agreements and the CRM",
    "Every source lands in bronze, as delivered",
    "Cleaning gives silver, with each ticket loaded once and one spelling per channel",
    "Shaping gives gold, one row per agency, route and month",
    "Defining writes each of the seven numbers once: six in the metric view gold.sales_metrics, and pace in gold.agency_pace",
    "The app, the dashboard, Genie and the Ask agent read the metric view; the Delegate agents run their own SQL on gold",
    "Every query runs as the person asking, under Unity Catalog",
]


def pipeline(motion=False) -> str:
    tiers = [  # name, schema, big number, unit, chips; the last tier is the focal one
        ("As delivered", "bronze", fmt(fact("bookings_delivered")), "booking rows", [f"{fact('bronze_tables')} tables, as sent"]),
        ("Cleaned", "silver", fmt(fact("bookings_cleaned")), "booking rows",
         [f"−{fact('duplicate_tickets')} tickets loaded twice",
          f"{fact('channel_spellings_delivered')} channel spellings to {fact('channel_spellings_cleaned')}"]),
        ("Ready to use", "gold", fmt(fact("sales_rows")), "rows", ["per agency, route, month"]),
        ("Defined once", "gold.sales_metrics", str(fact("kpis")), "numbers", [f"{DATED['twins_checked']['value']} checked each night", "pace in gold.agency_pace"]),
    ]
    arcs = [("CLEAN", False), ("SHAPE", False), ("DEFINE", True)]
    # Every mark is kept with its motion step (1 to 7), in paint order. A mark with no step is structure, which shows on arrival: the
    # two headings, and each tier card's outline, name and schema line. Static flattens the marks as they are; motion paints the
    # structure first and then groups the rest by step, and inside a step the marks keep their order.
    parts = []

    def put(step, markup):
        """step: the motion step that brings the mark in, or None for structure."""
        parts.append((step, markup))

    # promotions as orthogonal bridges over the top, drawn before the cards (connector rule 1: no curves): up from the
    # left tier's top edge at 2/3 of its width, across, and down into the next tier's top edge at 1/3, r=8 corners, so
    # every tier edge has its own port for the bridge arriving and the bridge leaving
    run_y = TIER_Y - 48
    for i, (label, focal) in enumerate(arcs):
        sx, ex = tier_x(i) + TIER_W * 2 // 3, tier_x(i + 1) + TIER_W // 3
        stroke, width, marker = (aa.ACCENT, 1.6, "arrow-accent") if focal else (aa.MUTED, 1.4, "arrow")
        put(3 + i, f'<path d="M {sx},{TIER_Y} V {run_y + 8} A 8 8 0 0 1 {sx + 8},{run_y} H {ex - 8} A 8 8 0 0 1 {ex},{run_y + 8} V {TIER_Y}" '
                   f'fill="none" stroke="{stroke}" stroke-width="{width}" stroke-linejoin="round" marker-end="url(#{marker})"/>')
        mid, w = (sx + ex) / 2, -(-(len(label) * 0.70 * 12 + 16) // 4) * 4  # 0.62em mono + 0.08em tracking per char, padded
        put(3 + i, f'<rect x="{mid - w / 2}" y="{run_y - 26}" width="{w}" height="18" fill="{aa.PAPER}"/>')  # mask, 8px above the run
        put(3 + i, text(mid, run_y - 13, label, size=12, weight=400, color=stroke, anchor="middle", mono=True, spacing="0.08em"))

    # sources into the first tier, and the readers out of the last, on straight runs at the shared ports
    sources = [("csv", None, "Seat shares", "real, from DOT T-100"), ("users", None, "Agency sales", "synthetic"),
               ("file", None, f"{fact('agreements')} agreements", "clauses by page"), (None, "dynamics365", "CRM", "Dynamics 365, stand-in")]
    readers = [("desktop", "The app"), ("monitoring", "Dashboard"), ("search", "Genie"), ("robot", "Agents")]
    put(None, eyebrow(40, ATTACH[0] - 44, "Sources", size=12))
    put(None, eyebrow(tier_x(3) + TIER_W + 52, ATTACH[0] - 44, "Read by", size=12))
    for y, (tab, brand, name, tag) in zip(ATTACH, sources):
        put(2, f'<line x1="260" y1="{y}" x2="{TIER_X0 - 2}" y2="{y}" stroke="{aa.MUTED}" stroke-width="1.4" marker-end="url(#arrow)"/>')  # into bronze
        put(1, tabler(tab, 40, y - 14, 28) if tab else aa.icon(brand, 42, y - 12, 24))
        put(1, text(80, y - 2, name, size=16))
        put(1, text(80, y + 16, tag, size=12, weight=400, color=aa.MUTED, mono=True))
    rx = tier_x(3) + TIER_W
    for y, (tab, name) in zip(ATTACH, readers):
        put(6, f'<line x1="{rx + 2}" y1="{y}" x2="{rx + 42}" y2="{y}" stroke="{aa.MUTED}" stroke-width="1.4" marker-end="url(#arrow)"/>')
        put(6, tabler(tab, rx + 52, y - 14, 28))
        put(6, text(rx + 92, y + 6, name, size=16))

    # the tier cards
    for i, (name, schema, big, unit, chips) in enumerate(tiers):
        x, focal = tier_x(i), i == len(tiers) - 1
        cx = x + TIER_W / 2
        fill, stroke, sw, band = (("rgba(0,108,191,0.07)", aa.ACCENT, 1.6, "rgba(0,108,191,0.14)") if focal
                                  else ("#ffffff", aa.MUTED if i == 0 else aa.INK, 1, "rgba(90,113,129,0.10)" if i == 0 else "rgba(54,73,90,0.06)"))
        # the card is structure: its outline, its band, its name and its schema show on arrival
        put(None, f'<g data-tier="{schema}"><rect x="{x}" y="{TIER_Y}" width="{TIER_W}" height="{TIER_H}" rx="6" fill="{fill}" stroke="{stroke}" stroke-width="{sw}"/>')
        put(None, f'<path d="M {x + 6},{TIER_Y} H {x + TIER_W - 6} A 6 6 0 0 1 {x + TIER_W},{TIER_Y + 6} V {TIER_Y + 48} H {x} V {TIER_Y + 6} A 6 6 0 0 1 {x + 6},{TIER_Y} Z" fill="{band}"/>')
        put(None, text(cx, TIER_Y + 30, name, size=16, anchor="middle"))
        put(None, text(cx, TIER_Y + 76, schema, size=12, weight=400, color=aa.ACCENT if focal else aa.MUTED, anchor="middle", mono=True))
        put(None, "</g>")
        # what the tier holds waits for its step: its number and what the step did
        put(2 + i, text(cx, TIER_Y + 156, big, size=40, color=aa.ACCENT if focal else aa.INK, anchor="middle"))
        put(2 + i, text(cx, TIER_Y + 182, unit, size=12, weight=400, color=aa.MUTED, anchor="middle", mono=True))
        for k, chip in enumerate(chips):
            cy = TIER_Y + 232 + k * 36
            put(2 + i, f'<rect x="{x + 8}" y="{cy}" width="{TIER_W - 16}" height="24" rx="2" fill="#ffffff" stroke="{aa.RULE_SOLID}" stroke-width="1"/>')
            put(2 + i, text(cx, cy + 16, chip, size=11, weight=400, color=aa.INK, anchor="middle"))  # plain words, so Inter, not mono

    # who can see what: the one sentence of governance, on a quiet strip under the tiers
    sy = TIER_Y + TIER_H + 36
    put(7, f'<rect x="{TIER_X0}" y="{sy}" width="{tier_x(3) + TIER_W - TIER_X0}" height="40" rx="6" fill="{aa.PAPER2}"/>')
    put(7, tabler("lock", TIER_X0 + 16, sy + 8, 24))
    put(7, text(TIER_X0 + 52, sy + 26, "Every query runs as the person asking", size=16))
    put(7, text(tier_x(3) + TIER_W - 16, sy + 26, "Unity Catalog aa_demo", size=12, weight=400, color=aa.MUTED, anchor="end", mono=True))
    out = [f'<rect width="100%" height="100%" fill="{aa.PAPER}"/>', markers()]
    if motion:
        assert {n for n, _ in parts if n is not None} == set(range(1, len(PIPELINE_STEPS) + 1)), "every motion step needs its marks"
        out += [m for step, m in parts if step is None]
        out += [aa.motion_item(n, words, [m for step, m in parts if step == n]) for n, words in enumerate(PIPELINE_STEPS, 1)]
    else:
        out += [m for _, m in parts]
    out.append(aa.brand(tag="fairshare · synthetic data"))
    return "\n        ".join(out)


# ---------------------------------------------------------------- 07 what fair share means

PITCH, CELL = 26, 20
QUARTER_REPEATS = "Aug and Sep"  # the months of Q3 2026 whose seats repeat 2025 until the DOT publishes them; check_claims() holds it to the data
GRID = 10 * PITCH - (PITCH - CELL)  # 254


# How a cell is drawn: AA, AA beyond fair share (above it), a dollar fair share would send AA that went to another airline (below it), or another
# airline. The last two only ever show in the sales grid, and only one of them at a time.
STATES = {"aa": (aa.ACCENT, aa.ACCENT, 1, ""), "premium": ("rgba(0,108,191,0.16)", aa.ACCENT, 1.4, ""),
          "short": ("#ffffff", aa.ACCENT, 1.4, ' stroke-dasharray="3 2"'), "other": ("#ffffff", aa.RULE_SOLID, 1, "")}


def seat(x, y, state):
    """A seat: a back and a cushion. AA, or another airline."""
    fill, stroke, sw, dash = STATES[state]
    return (f'<rect x="{x + 3}" y="{y}" width="14" height="13" rx="3" fill="{fill}" stroke="{stroke}" stroke-width="{sw}"{dash}/>'
            f'<rect x="{x + 1}" y="{y + 13}" width="18" height="7" rx="2" fill="{fill}" stroke="{stroke}" stroke-width="{sw}"{dash}/>')


def square(x, y, state):
    """One dollar of every hundred the agency sold on the route."""
    fill, stroke, sw, dash = STATES[state]
    return f'<rect x="{x + 1}" y="{y + 1}" width="18" height="18" rx="4" fill="{fill}" stroke="{stroke}" stroke-width="{sw}"{dash}/>'


def grid(x0, y0, aa_cells, extra, glyph, extra_state="premium"):
    """A hundred cells: aa_cells of AA, then extra cells drawn as extra_state, then the rest as another airline."""
    out = []
    for k in range(100):
        state = "aa" if k < aa_cells else extra_state if k < aa_cells + extra else "other"
        out.append(glyph(x0 + (k % 10) * PITCH, y0 + (k // 10) * PITCH, state))
    return "".join(out)


def fair_share() -> str:
    fair, share, gap, usd = fact("summit_q3_fair_share"), fact("summit_q3_aa_share"), fact("summit_q3_gap_pts"), fact("summit_q3_gap_usd")
    fair_cells, share_cells = round(fair), round(share)  # ponytail: a 100-cell grid rounds to whole cells; the labels carry the decimals
    above = gap >= 0  # Summit sends AA more than fair share would, or less; the grids, the payoff and the legend follow
    assert above == (usd >= 0) == (share >= fair) == (share_cells >= fair_cells), "the gap in points, the gap in dollars and the two grids should agree"
    side, extra = ("premium", "above fair share") if above else ("short", "below fair share")
    gy, ax, bx = 168, 96, 456
    out = [f'<rect width="100%" height="100%" fill="{aa.PAPER}"/>', aa.brand(tag="fairshare · synthetic data")]
    # A: seats on the route, the fair share; two of the quarter's three months repeat 2025, which the line under the heading says
    out.append(text(ax, gy - 46, "Seats on DFW to Chicago", size=16))
    out.append(text(ax, gy - 24, f"T-100 seats · Q3 2026, {QUARTER_REPEATS} from 2025", size=12, weight=400, color=aa.MUTED, mono=True))
    out.append(f'<g data-grid="seats">{grid(ax, gy, fair_cells, 0, seat)}</g>')
    out.append(text(ax, gy + GRID + 56, f"{fair}%", size=40, color=aa.ACCENT))
    out.append(text(ax, gy + GRID + 84, "AA's share of the seats: the fair share", size=16, color=aa.MUTED))
    # B: the agency's sales on the same route, the AA share, and the gap to fair share above or below it
    out.append(text(bx, gy - 46, "Summit's sales on the same route", size=16))
    out.append(text(bx, gy - 24, "Summit Travel Partners · Q3 2026", size=12, weight=400, color=aa.MUTED, mono=True))
    out.append(f'<g data-grid="sales">{grid(bx, gy, min(fair_cells, share_cells), abs(share_cells - fair_cells), square, side)}</g>')
    out.append(text(bx, gy + GRID + 56, f"{share}%", size=40, color=aa.ACCENT))
    out.append(text(bx, gy + GRID + 84, "went to AA: the AA share", size=16, color=aa.MUTED))
    # the payoff
    px = 836
    out.append(f'<line x1="{px - 36}" y1="{gy}" x2="{px - 36}" y2="{gy + GRID + 84}" stroke="{aa.RULE_SOLID}" stroke-width="1"/>')
    out.append(eyebrow(px, gy + 8, "Share gap"))
    out.append(text(px, gy + 64, f"{'+' if above else ''}{abs(gap)} points", size=40, color=aa.ACCENT))
    out.append(text(px, gy + 92, extra, size=16, color=aa.MUTED))
    out.append(text(px, gy + 172, f"${fmt(abs(usd))}", size=40))
    out.append(text(px, gy + 200, f"{'more' if above else 'less'} AA revenue than", size=16, color=aa.MUTED))
    out.append(text(px, gy + 222, "fair share would bring", size=16, color=aa.MUTED))
    out.append(text(px, gy + 252, "same route, same quarter", size=12, weight=400, color=aa.MUTED, mono=True))
    # the one sentence that defines it
    cy = gy + GRID + 140
    out.append(text(ax, cy, f"An agency that sold every airline in proportion to its seats would give AA {fair}% here. Summit gives {share}%.",
                    size=14, weight=400, color=aa.INK, italic=True))
    # legend strip, its keys ending 8px above the bottom of the deck's stage
    ly = aa.STAGE_BOTTOM - 16
    out.append(f'<line x1="{ax}" y1="{ly - 28}" x2="{VW - 40}" y2="{ly - 28}" stroke="{aa.RULE}" stroke-width="1"/>')
    out.append(eyebrow(ax, ly + 4, "Legend"))
    keys = [(seat, "aa", "AA seat"), (square, "aa", "$1 of every $100 to AA"), (square, side, extra),
            (square, "other", "another airline")]
    kx = ax + 96
    for glyph, state, label in keys:
        out.append(glyph(kx, ly - 12, state))
        out.append(text(kx + 28, ly + 4, label, size=11, weight=400, color=aa.MUTED))
        kx += 52 + 7 * len(label)
    return "\n        ".join(out)


def check_claims() -> None:
    """What these two figures say about the data, checked on every build so a rebuilt lakehouse cannot quietly change the story."""
    one = lambda sql: query(sql)[0]["value"]  # noqa: E731
    assert one("SELECT COUNT(DISTINCT ticket_number) AS value FROM aa_demo.silver.fact_corporate_bookings") == fact("bookings_cleaned"), \
        "silver should hold exactly one row per ticket"
    assert one("""SELECT COUNT(*) AS value FROM (SELECT DISTINCT agency_id, market_id, sales_month
                                               FROM aa_demo.gold.fact_agency_sales_monthly) AS t""") == fact("sales_rows"), \
        "gold should hold one row per agency, route and month"
    # 07's line under its heading: of Q3 2026's three months, August and September repeat 2025's seats, on every route
    projected = query("""SELECT EXTRACT(MONTH FROM c.sales_month) AS month, COUNT(*) AS routes,
                                 COUNT(*) FILTER (WHERE c.aa_seats = p.aa_seats AND c.total_seats = p.total_seats) AS repeats
                          FROM aa_demo.gold.fact_market_capacity c
                          JOIN aa_demo.gold.fact_market_capacity p ON p.market_id = c.market_id
                           AND EXTRACT(YEAR FROM p.sales_month) = 2025 AND EXTRACT(MONTH FROM p.sales_month) = EXTRACT(MONTH FROM c.sales_month)
                          WHERE c.is_projected AND c.sales_month BETWEEN DATE '2026-07-01' AND DATE '2026-09-01'
                          GROUP BY ALL ORDER BY month""")
    assert [(r["month"], r["routes"], r["repeats"]) for r in projected] == [(8, fact("routes"), fact("routes")), (9, fact("routes"), fact("routes"))] \
        and QUARTER_REPEATS == "Aug and Sep", "Q3 2026's projected seats should be August and September on every route, each the same as that month of 2025"


if __name__ == "__main__":
    check_claims()
    pages = [("06-data-pipeline", "Where the numbers come from", "fairshare · the data",
              "Four sources pass through three Unity Catalog tiers, delivered, cleaned and ready to use, before seven numbers are defined once, six in the metric view that Genie, the dashboard, the app and the Ask agent read and pace in gold.agency_pace.",
              pipeline()),
             ("07-fair-share", "What fair share means", "fairshare · the data",
              f"Two grids of one hundred: AA's share of the seats on DFW to Chicago in Q3 2026, {fact('summit_q3_fair_share')}% from T-100 with August and September repeating 2025, "
              f"and the {fact('summit_q3_aa_share')}% of Summit Travel Partners' sales on that route that went to AA, {abs(fact('summit_q3_gap_pts'))} points "
              f"{'above' if fact('summit_q3_gap_pts') >= 0 else 'below'} fair share.",
              fair_share())]
    for slug, title, eyebrow_text, desc, body in pages:
        (aa.OUT / f"{slug}.html").write_text(aa.page(slug=slug, title=title, desc=desc, eyebrow=eyebrow_text, body=body), encoding="utf-8")
        print("wrote", f"{slug}.html")
    slug, title, eyebrow_text, desc, _ = pages[0]  # 06 also steps forward, one tier at a time
    page = aa.animated(slug=f"{slug}-animated", title=title, desc=desc, eyebrow=eyebrow_text, body=pipeline(True), steps=len(PIPELINE_STEPS), css=aa.FADE_ONLY)
    (aa.OUT / f"{slug}-animated.html").write_text(page, encoding="utf-8")
    print("wrote", f"{slug}-animated.html")
