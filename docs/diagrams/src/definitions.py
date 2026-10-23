"""09: the seven numbers as a visual glossary. One card per definition in ops.kpi_definitions (lakehouse/04_definitions.sql):
the name, a small picture of the idea, one plain sentence, and where it lives (the metric view measure; six are checked
every night against a SQL twin of the Power BI measure). A strip underneath tells the one time the nightly parity check
caught a drift.

09a and 09b: the same seven numbers over two slides for the /present deck, three and then four, each card saying how its number
is calculated in the spec's plain words beside its value for Harbor Business Travel in Sep 2026. Each page closes on where the
numbers live and why that matters. On the animated pages a card's frame and name show on arrival, its words and its value come
on its press, and in the deck the newest card leads while the earlier ones recede (aa.EMBED_CSS); the close is the last press.

    .venv/bin/python docs/diagrams/src/definitions.py   # writes 09-definitions.html, and 09a and 09b, each static and animated

09 prints only the counts of the Oct 12 replay (the drift story). They are dated facts in deck_facts.py, so a refreshed
app/cache/kpi_parity.csv cannot change this figure. 09a and 09b print the values of deck_facts.py's Harbor facts, and
check_claims() asserts on every build that they add up the way the cards say.
"""
from __future__ import annotations

import aa
from deck_facts import DATED, display, fact, query

VW, VH = 1280, 720
NO_TWIN = {"pace_pct"}  # the one number with no SQL twin, so no Power BI mark on its card
INK_A = lambda a: f"rgba(54,73,90,{a})"
TINT = "rgba(90,113,129,0.15)"
STROKE_ICON = 'fill="none" stroke="{c}" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"'
TABLER = {  # Tabler Icons (MIT), via diagram-design's references/primitive-icons.md; "check" is Tabler's check
    "file": '<path d="M14 3v4a1 1 0 0 0 1 1h4"/><path d="M17 21h-10a2 2 0 0 1 -2 -2v-14a2 2 0 0 1 2 -2h7l5 5v11a2 2 0 0 1 -2 2"/>',
    "alert": '<path d="M12 9v4"/><path d="M10.363 3.591l-8.106 13.534a1.914 1.914 0 0 0 1.636 2.871h16.214a1.914 1.914 0 0 0 1.636 -2.87l-8.106 -13.536a1.914 1.914 0 0 0 -3.274 0"/><path d="M12 16h.01"/>',
    "check": '<path d="M5 12l5 5l10 -10"/>',
}


def tabler(name, x, y, size=20, color=aa.INK):
    return (f'<svg x="{x}" y="{y}" width="{size}" height="{size}" viewBox="0 0 24 24" aria-hidden="true">'
            f'<g {STROKE_ICON.format(c=color)}>{TABLER[name]}</g></svg>')


def text(x, y, s, size=13, color=aa.INK, weight=None, family=None, anchor=None, italic=False, attrs=""):
    """One line of text; attrs, when given, starts with a space."""
    w = f' font-weight="{weight}"' if weight else ""
    a = f' text-anchor="{anchor}"' if anchor else ""
    i = ' font-style="italic"' if italic else ""
    return f'<text x="{x}" y="{y}" fill="{color}" font-size="{size}"{w}{i} font-family="{family or aa.SANS}"{a}{attrs}>{aa.esc(s)}</text>'


def wrap(s, max_px, size=13, em=0.57):
    """Greedy wrap on an Inter width estimate; the build measures the result in a browser afterwards."""
    lines, cur = [], ""
    for word in s.split():
        trial = f"{cur} {word}".strip()
        if cur and len(trial) * size * em > max_px:
            lines.append(cur)
            cur = word
        else:
            cur = trial
    lines.append(cur)
    assert len(lines) <= 2, f"too long for its card: {s!r}"
    return lines


SMALL = {"a", "an", "the", "of", "on", "in", "by", "to", "and", "how", "what"}


def balance(s, max_px, size, em):
    """One line if it fits, or two as even as they can be on an Inter width estimate: a break after a comma or a full stop wins a little,
    and a break after a small word such as "the" loses a little."""
    fits = lambda line: len(line) * size * em <= max_px  # noqa: E731
    if fits(s):
        return [s]
    words, best = s.split(), None
    for i in range(1, len(words)):
        a, b = " ".join(words[:i]), " ".join(words[i:])
        cost = max(len(a), len(b)) - (12 if a.endswith((",", ".")) else 0) + (12 if words[i - 1].lower() in SMALL else 0)
        if fits(a) and fits(b) and (best is None or cost < best[0]):
            best = (cost, [a, b])
    assert best, f"too long for two lines: {s!r}"
    return best[1]


def replay() -> tuple[int, int]:
    """(red, all) agency-months of the retired passenger-based twin's run on Oct 12, counted once and kept as dated facts."""
    return DATED["parity_red"]["value"], DATED["parity_rows"]["value"]


def tag(x, y, s):  # a tiny word under a visual
    return text(x, y, s, 11, aa.MUTED)


# ---------------------------------------------------------------- the small pictures, each in a box (x, y, w, 72)

def v_revenue(x, y, w):
    """Three tickets fanned out: ticketed revenue."""
    out = []
    for i in range(3):
        tx, ty = x + i * 36, y + 8 + (2 - i) * 6
        out.append(f'<rect x="{tx}" y="{ty}" width="96" height="44" rx="4" fill="#ffffff" stroke="{aa.INK}" stroke-width="1.2"/>')
        out.append(f'<line x1="{tx + 68}" y1="{ty + 4}" x2="{tx + 68}" y2="{ty + 40}" stroke="{INK_A(0.45)}" stroke-width="1" stroke-dasharray="3,3"/>')
        out.append(f'<rect x="{tx + 10}" y="{ty + 12}" width="40" height="4" fill="{INK_A(0.30)}"/>')
        out.append(f'<rect x="{tx + 10}" y="{ty + 22}" width="28" height="4" fill="{INK_A(0.30)}"/>')
    out.append(text(x + 176, y + 40, "$", 22, aa.INK, 600))
    return out


def v_share(x, y, w):
    """One bar of everything the agency sold, AA's part filled."""
    bw = w - 8
    aa_w = round(bw * 0.46)
    return [f'<rect x="{x}" y="{y + 16}" width="{bw}" height="24" rx="3" fill="#ffffff" stroke="{aa.INK}" stroke-width="1.2"/>',
            f'<rect x="{x}" y="{y + 16}" width="{aa_w}" height="24" rx="3" fill="{aa.NAVY}"/>',
            tag(x, y + 60, "AA"), tag(x + aa_w + 8, y + 60, "every other airline")]


def v_fair(x, y, w):
    """A small seat map: AA's seats lit in AA blue."""
    out, n = [], 11
    for row in range(2):
        for i in range(n):
            sx, sy = x + i * 26, y + 6 + row * 30
            # a picture of "a share of the seats", about two in five like the markets in the data, not a printed value
            fill = aa.ACCENT if (row == 0 and i < 5) or (row == 1 and i < 4) else "#ffffff"
            stroke = aa.ACCENT if fill != "#ffffff" else aa.INK
            out.append(f'<rect x="{sx}" y="{sy}" width="18" height="20" rx="4" fill="{fill}" stroke="{stroke}" stroke-width="1.2"/>')
            out.append(f'<rect x="{sx + 3}" y="{sy + 15}" width="12" height="3" rx="1" fill="{"#ffffff" if fill != "#ffffff" else INK_A(0.35)}"/>')
    out.append(tag(x, y + 72, "AA seats on the route"))
    return out


def v_gap(x, y, w):
    """AA share against fair share; the bracket between their ends is the gap."""
    long_w = w - 72
    short_w = round(long_w * 0.62)
    return [f'<rect x="{x}" y="{y + 4}" width="{long_w}" height="14" rx="2" fill="{aa.NAVY}"/>',
            tag(x + long_w + 8, y + 15, "AA share"),
            f'<rect x="{x}" y="{y + 26}" width="{short_w}" height="14" rx="2" fill="#ffffff" stroke="{aa.INK}" stroke-width="1.2"/>',
            tag(x + short_w + 8, y + 37, "fair share"),
            f'<path d="M {x + short_w} {y + 50} L {x + short_w} {y + 56} L {x + long_w} {y + 56} L {x + long_w} {y + 50}" fill="none" stroke="{aa.ACCENT}" stroke-width="1.6"/>',
            text(x + (short_w + long_w) / 2, y + 72, "gap", 11, aa.ACCENT, anchor="middle")]


def v_gap_usd(x, y, w):
    """AA revenue running past the fair-share line: the part past the line is the dollars."""
    line_x, end_x = x + round((w - 40) * 0.6), x + w - 40
    return [f'<rect x="{x}" y="{y + 14}" width="{line_x - x}" height="24" rx="2" fill="{TINT}" stroke="{aa.MUTED}" stroke-width="1"/>',
            f'<rect x="{line_x}" y="{y + 14}" width="{end_x - line_x}" height="24" fill="{aa.NAVY}"/>',
            f'<line x1="{line_x}" y1="{y + 4}" x2="{line_x}" y2="{y + 48}" stroke="{aa.INK}" stroke-width="1.2" stroke-dasharray="4,3"/>',
            text(end_x + 10, y + 34, "$", 22, aa.INK, 600),
            tag(x, y + 64, "revenue at fair share"), tag(line_x + 6, y + 64, "above it")]


def v_yoy(x, y, w):
    """The same month, a year apart."""
    return [f'<rect x="{x + 8}" y="{y + 20}" width="40" height="40" fill="#ffffff" stroke="{aa.MUTED}" stroke-width="1.2"/>',
            f'<rect x="{x + 64}" y="{y + 4}" width="40" height="56" fill="{TINT}" stroke="{aa.INK}" stroke-width="1.2"/>',
            f'<line x1="{x}" y1="{y + 60}" x2="{x + 112}" y2="{y + 60}" stroke="{INK_A(0.25)}" stroke-width="1"/>',
            tag(x + 124, y + 30, "same month,"), tag(x + 124, y + 46, "one year apart")]


def v_pace(x, y, w):
    """Year to date against the goal so far."""
    track, mark = w - 40, round((w - 40) * 0.74)
    fill = round(mark * 0.9)
    return [f'<rect x="{x}" y="{y + 18}" width="{track}" height="18" rx="9" fill="#ffffff" stroke="{aa.INK}" stroke-width="1.2"/>',
            f'<rect x="{x}" y="{y + 18}" width="{fill}" height="18" rx="9" fill="{aa.NAVY}"/>',
            f'<line x1="{x + mark}" y1="{y + 10}" x2="{x + mark}" y2="{y + 44}" stroke="{aa.INK}" stroke-width="1.6"/>',
            tag(x, y + 62, "revenue so far"), tag(x + mark - 30, y + 62, "goal so far")]


# ---------------------------------------------------------------- cards

CARDS = [  # row, width, name, picture, sentence (at most 12 words), measure, home
    (0, 260, "AA revenue", v_revenue, "Ticketed AA revenue the agency sold, in dollars.", "aa_revenue"),
    (0, 312, "AA share", v_share, "AA revenue divided by everything the agency sold there.", "aa_share"),
    (0, 336, "Fair share", v_fair, "What a neutral agency would sell: AA’s share of seats.", "fair_share"),
    (0, 244, "Share gap", v_gap, "AA share minus fair share, in points.", "share_gap_pts"),
    (1, 372, "Share gap in dollars", v_gap_usd, "The same gap in dollars, above or below fair share.", "share_gap_usd"),
    (1, 340, "Year over year", v_yoy, "This month against the same month last year.", "yoy_revenue_pct"),
    (1, 456, "Pace against goal", v_pace, "Revenue so far against the goal so far; 100 is on pace.", "pace_pct"),
]
ROW_Y, CARD_H, GAP = (144, 368), 208, 16


def card(x, y, w, name, picture, sentence, measure):
    out = [f'<rect x="{x}" y="{y}" width="{w}" height="{CARD_H}" rx="6" fill="#ffffff" stroke="{aa.RULE_SOLID}" stroke-width="1"/>',
           text(x + 20, y + 34, name, 16, aa.INK, 600)]
    out += picture(x + 20, y + 52, w - 40)
    for i, line in enumerate(wrap(sentence, w - 40)):
        out.append(text(x + 20, y + 146 + i * 18, line, 13, aa.INK))
    out.append(aa.icon("databricks", x + 20, y + 178, 14))
    out.append(text(x + 40, y + 190, measure, 11, aa.MUTED, family=aa.MONO))
    if measure not in NO_TWIN:
        out.append(aa.icon("powerbi", x + w - 34, y + 178, 14))
    return out


def build():
    out = [f'<rect width="100%" height="100%" fill="{aa.PAPER}"/>', aa.brand(tag="fairshare · synthetic data")]
    out.append(text(40, 100, "Seven numbers, each defined once", 16, aa.INK, 600))
    out.append(aa.icon("databricks", 40, 112, 14))
    out.append(text(60, 124, "metric view gold.sales_metrics (pace: gold.agency_pace)", 12, aa.MUTED, family=aa.MONO))
    out.append(aa.icon("powerbi", 532, 112, 14))
    out.append(text(552, 124, "SQL twin of the Power BI measure for six, checked every night", 12, aa.MUTED, family=aa.MONO))
    for row in (0, 1):
        x = 40
        for r, w, name, pic, sentence, measure in CARDS:
            if r != row:
                continue
            out += card(x, ROW_Y[row], w, name, pic, sentence, measure)
            x += w + GAP
    # the drift the nightly check caught, as three steps
    y = 600
    out.append(text(40, y, "HOW A DEFINITION STAYS HONEST", 8, aa.MUTED, 500, aa.MONO).replace("<text ", '<text letter-spacing="0.18em" ', 1))
    red, rows = replay()
    steps = [("file", "AA share v1 counted passengers", "twin_sql_retired", aa.MUTED),
             ("alert", f"Oct 12 replay: {red} of {rows} agency-months red", "ops.kpi_parity", aa.INK),
             ("check", "v2 counts revenue; nightly checks green", "twin_version v2", aa.INK)]
    xs, widths = (40, 420, 900), (340, 440, 340)
    for (ic, line, mono, color), sx, sw in zip(steps, xs, widths):
        dash = ' stroke-dasharray="4,3"' if ic == "file" else ""
        out.append(f'<rect x="{sx}" y="{y + 12}" width="{sw}" height="56" rx="6" fill="#ffffff" stroke="{aa.INK if ic != "file" else aa.MUTED}" stroke-width="1"{dash}/>')
        out.append(tabler(ic, sx + 16, y + 28, 22, color))
        out.append(text(sx + 50, y + 38, line, 14, aa.INK if ic != "file" else aa.MUTED, 600))
        out.append(text(sx + 50, y + 56, mono, 11, aa.MUTED, family=aa.MONO))
    for a, b in ((40 + 340, 420), (420 + 440, 900)):
        out.append(f'<line x1="{a + 8}" y1="{y + 40}" x2="{b - 10}" y2="{y + 40}" stroke="{aa.MUTED}" stroke-width="1.2" marker-end="url(#09-arrow)"/>')
    defs = (f'<defs><marker id="09-arrow" markerWidth="8" markerHeight="6" refX="7" refY="3" orient="auto">'
            f'<polygon points="0 0, 8 3, 0 6" fill="{aa.MUTED}"/></marker></defs>')
    return defs + "\n        " + "\n        ".join(out)


TITLE = "The seven numbers"
DESC = ("Visual glossary of the seven fairshare numbers, AA revenue, AA share, fair share, the share gap in points and dollars, "
        "year over year change and pace against goal, each defined once in the metric view; six are checked every night against a SQL twin of the Power BI measure.")


# ---------------------------------------------------------------- 09a and 09b: the seven numbers over two stepped slides

NUMBERS = [  # (key in ops.kpi_definitions, name, how it is calculated in the spec's plain words, the fact for Harbor in Sep 2026, its unit)
    ("aa_revenue", "AA revenue", "AA revenue is AA's revenue on the rows in question.", "harbor_revenue_sep26_usd", ""),
    ("aa_share", "AA share", "AA share is AA revenue divided by everything the agency sold on the same routes, all airlines together.",
     "harbor_share_sep26", ""),
    ("fair_share", "Fair share", "Fair share is AA's share of the seats on each route, weighted by how much the agency sold there. "
                                 "September's seats are last year's.", "harbor_fair_share_sep26", ""),
    ("share_gap_pts", "Share gap in points", "The share gap in points is AA share minus fair share.", "harbor_gap_pts_sep26", " points"),
    ("share_gap_usd", "Share gap in dollars", "The share gap in dollars is AA revenue minus what fair share would have brought in.",
     "harbor_gap_usd_sep26", ""),
    ("yoy_revenue_pct", "Year over year", "Year over year compares AA revenue with the same month last year.", "harbor_yoy_sep26", ""),
    ("pace_pct", "Pace", "Pace is revenue so far this year divided by the goal so far, counting only the months the agency reported. "
                         "The goals are made up.", "harbor_pace_sep26", "%"),  # pace_pct is a percent of the goal so far; the fact shows it bare
]
EXAMPLE = "Harbor, Sep 2026"  # whose values the cards print: the agency and month the Ask demo and figure 08 are about
WHERE = ("Six of the seven numbers are measures in the metric view gold.sales_metrics, worked out from the gold tables when a query runs, "
         "so a share comes out right at any grouping. Pace is stored in gold.agency_pace, because its goal is set per agency and year.",
         "Genie, the dashboard and Ask read the six from that one metric view, so their numbers agree.")
PAGES = [  # slug, title, the numbers on the page
    ("09a-numbers-share", "Three of the seven numbers, and what goes into each", NUMBERS[:3]),
    ("09b-numbers-gaps", "The other four numbers, and what goes into each", NUMBERS[3:]),
]
CARDS_TOP, CARDS_BOTTOM, CARD_X, CARD_W = 168, 526, 40, 1200    # the cards fill the same band on both pages
NAME_X, DEF_X, DEF_W, VALUE_X = 64, 320, 680, 1216               # the name, how it is calculated, and the value, right aligned
EM, EM_BOLD = 0.5, 0.55  # Inter's advance per character at 400 and 600, a little over what a browser measures here (0.47 to 0.50, 0.48 to 0.54)
NAME_SIZE, DEF_SIZE, DEF_LEADING, VALUE_SIZE = 22, 20, 27, 26
WHERE_Y, WHERE_H, WHERE_SIZE, WHERE_LEADING = 544, 128, 17, 24  # the close, under the cards and over the deck's footer


def check_claims() -> None:
    """What the cards say about Harbor's numbers, checked on every build so a rebuilt lakehouse cannot quietly change the story: the gap in
    points is AA share minus fair share, the two gaps point the same way, year over year matches the two Septembers figure 08 starts
    and ends on, and September 2026's seats are September 2025's, as the fair share card says."""
    share, fair, gap = fact("harbor_share_sep26"), fact("harbor_fair_share_sep26"), fact("harbor_gap_pts_sep26")
    assert abs(share - fair - gap) <= 0.1 + 1e-9, f"the share gap in points should be AA share minus fair share: {share} - {fair} against {gap}"
    assert (gap < 0) == (fact("harbor_gap_usd_sep26") < 0), "the share gap in dollars should point the same way as the gap in points"
    now, prior = fact("harbor_revenue_sep26_usd"), fact("harbor_revenue_sep25_usd")
    assert abs(100 * (now - prior) / prior - fact("harbor_yoy_sep26")) <= 0.1, "year over year should match Harbor's two Septembers"
    # the fair share card says September's seats are last year's: the DOT has not published September 2026, so its seats repeat September 2025
    (r,) = query("""SELECT COUNT(*) AS routes, COUNT(*) FILTER (WHERE c.is_projected AND c.aa_seats = p.aa_seats AND c.total_seats = p.total_seats) AS repeats
                     FROM aa_demo.gold.fact_market_capacity c
                     JOIN aa_demo.gold.fact_market_capacity p ON p.market_id = c.market_id AND p.sales_month = DATE '2025-09-01'
                     WHERE c.sales_month = DATE '2026-09-01'""")
    assert r["routes"] == r["repeats"] == fact("routes"), "the fair share card says September 2026's seats are September 2025's, on every route"


def numbers_page(title: str, cards, motion: bool = False) -> str:
    """One page of the seven numbers. Structure shows on arrival: the title, the heading over the values, and each card's frame and name.
    With motion, each card's words and value are one press, marked to recede once the next comes, and where the numbers live is the
    last press; without it, every mark at once."""
    out = [f'<rect width="100%" height="100%" fill="{aa.PAPER}"/>', aa.brand(tag="fairshare · synthetic data")]
    out.append(text(40, 100, title, 16, aa.INK, 600, attrs=" data-title"))  # the slide's title, since the deck draws none over a figure
    # the heading over the values, as the deck's native slides set a label: 12px mono, upper case, tracked
    out.append(text(VALUE_X, CARDS_TOP - 16, EXAMPLE.upper(), 12, aa.MUTED, 500, aa.MONO, "end").replace("<text ", '<text letter-spacing="0.14em" ', 1))
    gap = 14 if len(cards) < 4 else 10
    h = (CARDS_BOTTOM - CARDS_TOP - gap * (len(cards) - 1)) / len(cards)
    for k, (key, name, words, fact_key, unit) in enumerate(cards):
        y = CARDS_TOP + k * (h + gap)
        cy = y + h / 2
        out.append(f'<g data-card="{key}"><rect x="{CARD_X}" y="{y:g}" width="{CARD_W}" height="{h:g}" rx="6" fill="#ffffff" stroke="{aa.RULE_SOLID}" stroke-width="1"/>'
                   + text(NAME_X, f"{cy + 8:g}", name, NAME_SIZE, aa.INK, 600, attrs=f' data-name="{key}"') + "</g>")
        lines = balance(words, DEF_W, DEF_SIZE, EM)
        first = cy - (len(lines) - 1) * DEF_LEADING / 2 + 7
        assert first - DEF_SIZE > y + 6 and first + (len(lines) - 1) * DEF_LEADING + aa.TEXT_DESCENT * DEF_SIZE < y + h - 6, f"{name}: its words overflow the card"
        value = display(fact_key) + unit
        assert NAME_X + len(name) * NAME_SIZE * EM_BOLD < DEF_X - 8 and VALUE_X - len(value) * VALUE_SIZE * EM_BOLD > DEF_X + DEF_W + 8, \
            f"{name}: its name or its value runs into how it is calculated"
        # on the animated page, the card's outline again with no stroke: in the deck it is blue while this card is the newest, as a native
        # slide's newest tile is
        marks = [f'<rect x="{CARD_X}" y="{y:g}" width="{CARD_W}" height="{h:g}" rx="6" fill="none" stroke="none" stroke-width="1.5" data-lead/>'] if motion else []
        marks += [text(DEF_X, f"{first + i * DEF_LEADING:g}", line, DEF_SIZE, aa.INK, attrs=f' data-def="{key}"') for i, line in enumerate(lines)]
        marks.append(text(VALUE_X, f"{cy + 9:g}", value, VALUE_SIZE, aa.INK, 600, anchor="end", attrs=f' data-value="{key}"'))
        out.append(aa.motion_item(k + 1, f"{name}. {words} {EXAMPLE}: {value}.", marks, recede=True) if motion else "\n        ".join(marks))
    # where the numbers live and why that matters, on a quiet band under the cards: the last press, and the last word on the page
    assert WHERE_Y + WHERE_H <= aa.STAGE_BOTTOM - 4, "the close runs under the deck's footer"
    close = [f'<rect x="{CARD_X}" y="{WHERE_Y}" width="{CARD_W}" height="{WHERE_H}" rx="6" fill="{aa.PAPER2}"/>',
             aa.icon("databricks", NAME_X, WHERE_Y + 22, 20, aa.MUTED)]
    where, why = WHERE
    assert len(why) * WHERE_SIZE * EM_BOLD <= VALUE_X - 100, "why the numbers matter runs past the band"
    lines = [(line, 400) for line in balance(where, VALUE_X - 100, WHERE_SIZE, EM)] + [(why, 600)]
    base = WHERE_Y + (WHERE_H - (len(lines) - 1) * WHERE_LEADING) / 2 + 6
    assert base - WHERE_SIZE > WHERE_Y + 8 and base + (len(lines) - 1) * WHERE_LEADING + aa.TEXT_DESCENT * WHERE_SIZE < WHERE_Y + WHERE_H - 8, "the close overflows its band"
    close += [text(100, f"{base + i * WHERE_LEADING:g}", line, WHERE_SIZE, aa.INK, weight, attrs=" data-where") for i, (line, weight) in enumerate(lines)]
    out.append(aa.motion_item(len(cards) + 1, f"Where the numbers live. {where} {why}", close) if motion else "\n        ".join(close))
    return "\n        ".join(out)


def numbers_desc(cards) -> str:
    named = [name if name.startswith("AA") else name[0].lower() + name[1:] for _, name, *_ in cards]
    said = (f"{', '.join(named[:-1])} and {named[-1]}, each beside how it is calculated and its value for Harbor Business Travel in Sep 2026, "
            "then where the seven numbers live: six as measures in the metric view gold.sales_metrics and pace in gold.agency_pace, read by Genie, the dashboard and Ask.")
    return said[0].upper() + said[1:]


if __name__ == "__main__":
    html = aa.page(slug="09-definitions", title=TITLE, desc=DESC, eyebrow="fairshare · the data", body=build())
    (aa.OUT / "09-definitions.html").write_text(html, encoding="utf-8")
    print("wrote 09-definitions.html")
    check_claims()
    for slug, title, cards in PAGES:
        common = dict(title=title, desc=numbers_desc(cards), eyebrow="fairshare · the data", vw=VW, vh=VH)
        (aa.OUT / f"{slug}.html").write_text(aa.page(slug=slug, body=numbers_page(title, cards), **common), encoding="utf-8")
        page = aa.animated(slug=f"{slug}-animated", body=numbers_page(title, cards, motion=True), steps=len(cards) + 1, css=aa.FADE_ONLY, **common)
        (aa.OUT / f"{slug}-animated.html").write_text(page, encoding="utf-8")
        print(f"wrote {slug}.html and {slug}-animated.html")
