"""09: the seven numbers as a visual glossary. One card per definition in ops.kpi_definitions (lakehouse/04_definitions.sql):
the name, a small picture of the idea, one plain sentence, and where it lives (the metric view measure; six are checked
every night against a SQL twin of the Power BI measure). A strip underneath tells the one time the nightly parity check
caught a drift.

    python3 docs/diagrams/src/definitions.py   # writes docs/diagrams/09-definitions.html

No data numbers are printed; the count of seven and the drift story come from data_numbers_2.py (ops.kpi_definitions).
"""
from __future__ import annotations

import csv

import aa

VW, VH = 1280, 720
PARITY_CSV = aa.OUT.parents[1] / "app" / "cache" / "kpi_parity.csv"
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


def text(x, y, s, size=13, color=aa.INK, weight=None, family=None, anchor=None, italic=False):
    w = f' font-weight="{weight}"' if weight else ""
    a = f' text-anchor="{anchor}"' if anchor else ""
    i = ' font-style="italic"' if italic else ""
    return f'<text x="{x}" y="{y}" fill="{color}" font-size="{size}"{w}{i} font-family="{family or aa.SANS}"{a}>{aa.esc(s)}</text>'


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


def replay() -> tuple[int, int]:
    """(red, all) agency-months of the retired passenger-based twin's run, counted from the offline parity file."""
    with open(PARITY_CSV, newline="", encoding="utf-8") as fh:
        rows = [r for r in csv.DictReader(fh) if r["twin_version"] == "v1 (retired)"]
    return sum(r["status"] != "ok" for r in rows), len(rows)


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

if __name__ == "__main__":
    html = aa.page(slug="09-definitions", title=TITLE, desc=DESC, eyebrow="fairshare · the data", body=build())
    (aa.OUT / "09-definitions.html").write_text(html, encoding="utf-8")
    print("wrote 09-definitions.html")
