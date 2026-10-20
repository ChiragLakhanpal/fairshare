"""10: every agency, every month, as a grid. One cell for each agency and month, shaded by how many routes the agency has rows
for in that month, so a month with no rows is a hole.

    .venv/bin/python docs/diagrams/src/coverage.py   # writes docs/diagrams/10-coverage.html

diagram-design's heatmap grammar (references/type-heatmap.md): every row and column named, each cell a paper underlay plus a
data rect bound to its row, column and value, one ink ramp. This grid is far past the type's budget of 3 to 7 rows and 3 to 8
columns, so a cell is 44 by 24 and carries no text, and the ramp has two steps, because every agency-month that has rows has all
of the routes. The holes are the lowest step of the ramp and the accent is only their outline, so no cell is declared focal:
scripts/verify-heatmap.py allows one focal cell and rejects the pair if both are declared ("found 2 focal cells").

Every number comes from deck_facts.py or from this file's own queries on the same lakehouse; check_claims() asserts on every
build what the text says about the data.
"""
from __future__ import annotations

import aa
from deck_facts import FORMATS, MONTHS, display, fact, query

VW, VH = 1280, 720
GX, GY = 232, 200            # the grid's top-left corner
CW, CH, GAP = 44, 24, 4      # a cell, and the gap between cells
PX, PY = CW + GAP, CH + GAP
CALLOUT_X = 280              # where the callout's sentence starts, clear of its label
LOW, HIGH = 0.05, 0.20       # ink opacity of a cell with no routes, and of a cell with every route
INK_A = lambda a: f"rgba(54,73,90,{a})"  # noqa: E731
NUMBER_WORDS = ("zero", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine", "ten", "eleven", "twelve",
                "thirteen", "fourteen", "fifteen", "sixteen", "seventeen", "eighteen", "nineteen", "twenty")


def text(x, y, s, *, size=12, weight=400, fill=aa.INK, mono=False, anchor="start", italic=False, spacing=None, extra=""):
    extra += (f' letter-spacing="{spacing}"' if spacing else "") + (' font-style="italic"' if italic else "")
    return (f'<text x="{x}" y="{y}" fill="{fill}" font-size="{size}" font-weight="{weight}" font-family="{aa.MONO if mono else aa.SANS}" '
            f'text-anchor="{anchor}"{extra}>{aa.esc(s)}</text>')


def eyebrow(x, y, s, fill=aa.MUTED):
    return text(x, y, s.upper(), size=8, weight=500, fill=fill, mono=True, spacing="0.18em")


def key(month) -> str:
    """The column name, written the way deck_facts writes a month: Jan 2026."""
    return f"{MONTHS[month.month - 1]} {month.year}"


def span(months) -> str:
    """Two months of one year: Mar and Apr 2026."""
    assert len(months) == 2 and months[0].year == months[1].year, "the label under the holes is written for two months of one year"
    return f"{MONTHS[months[0].month - 1]} and {MONTHS[months[1].month - 1]} {months[0].year}"


# ---------------------------------------------------------------- the data

def load():
    """The agencies by name, the months that have sales rows, how many routes every agency-month that has rows holds, and the
    routes where AA's revenue is zero."""
    agencies = [r["agency_name"] for r in query("SELECT agency_name FROM aa_demo.gold.dim_agency ORDER BY agency_name")]
    months = [r["sales_month"] for r in query("SELECT DISTINCT sales_month FROM aa_demo.gold.fact_agency_sales_monthly ORDER BY sales_month")]
    routes = {(r["agency_name"], r["sales_month"]): r["routes"] for r in query("""
        SELECT a.agency_name, s.sales_month, COUNT(DISTINCT s.market_id) AS routes
        FROM aa_demo.gold.fact_agency_sales_monthly s
        JOIN aa_demo.gold.dim_agency a ON a.agency_id = s.agency_id
        GROUP BY a.agency_name, s.sales_month""")}
    zero = query("""
        SELECT a.agency_name, s.sales_month, CONCAT(m.origin, '-', m.dest) AS route, s.aa_revenue
        FROM aa_demo.gold.fact_agency_sales_monthly s
        JOIN aa_demo.gold.dim_agency a ON a.agency_id = s.agency_id
        JOIN aa_demo.gold.dim_market m ON m.market_id = s.market_id
        WHERE s.aa_revenue = 0""")
    return agencies, months, routes, zero


def holes_of(agencies, months, routes):
    """The agency-months with no rows at all."""
    return [(a, m) for a in agencies for m in months if (a, m) not in routes]


def check_claims(agencies, months, routes, zero) -> None:
    """What this figure says about the data, checked on every build so a rebuilt lakehouse cannot quietly change the story."""
    assert len(routes) == fact("agency_months_present"), "agency-months with rows should match the fact"
    assert len(agencies) * len(months) == fact("agency_months_total"), "agencies times months should match the fact"
    assert set(routes.values()) == {fact("routes")}, "every agency-month that has rows should have all the routes"
    holes = holes_of(agencies, months, routes)
    assert len({a for a, _m in holes}) == 1, "the holes should be one agency's months"
    assert holes[0][0] == agencies[-1], "the label under the holes sits under the last row, so that agency must sort last"
    assert len(zero) == 1 and (zero[0]["agency_name"], zero[0]["sales_month"]) in routes, "one reported month should hold the zero"
    assert zero[0]["route"] == fact("northstar_zero_route") and key(zero[0]["sales_month"]) == display("northstar_zero_month"), \
        "the zero should be on the route and in the month the facts name"


# ---------------------------------------------------------------- the figure

def build(agencies, months, routes, zero) -> str:
    total = fact("routes")
    holes = holes_of(agencies, months, routes)
    hole_agency, hole_months = holes[0][0], [m for _a, m in holes]
    z = zero[0]
    zero_usd = FORMATS["usd"][1](int(z["aa_revenue"]))
    grid_h = len(agencies) * PY - GAP
    out = [f'<rect width="100%" height="100%" fill="{aa.PAPER}"/>', aa.brand(tag="fairshare · synthetic data")]
    # what the chart is about, inside the image because a slide takes the SVG alone
    out.append(text(40, 100, "Every agency, every month", size=16, weight=600))
    out.append(text(40, 120, f"{display('agency_months_present')} of {display('agency_months_total')} agency-months have rows, "
                             f"each with all {NUMBER_WORDS[total]} routes", mono=True, fill=aa.MUTED))
    # the columns: a rule and the year over each year's months, then every month
    for year in sorted({m.year for m in months}):
        cols = [c for c, m in enumerate(months) if m.year == year]
        x0, x1 = GX + cols[0] * PX, GX + cols[-1] * PX + CW
        out.append(text(x0, GY - 36, str(year), size=12, weight=600))
        out.append(f'<line x1="{x0}" y1="{GY - 30}" x2="{x1}" y2="{GY - 30}" stroke="{aa.RULE_SOLID}" stroke-width="1"/>')
    for c, m in enumerate(months):
        out.append(text(GX + c * PX + CW / 2, GY - 10, MONTHS[m.month - 1], size=12, fill=aa.MUTED, mono=True, anchor="middle", extra=f' data-col="{key(m)}"'))
    # the rows and their cells; the two agencies the figure is about get a bold name
    for r, agency in enumerate(agencies):
        y = GY + r * PY
        out.append(text(GX - 12, y + CH / 2 + 5, agency, size=14, weight=600 if agency in (hole_agency, z["agency_name"]) else 400,
                        fill=aa.ACCENT if agency == hole_agency else aa.INK, anchor="end", extra=f' data-row-label="{agency}"'))
        for c, m in enumerate(months):
            x, n = GX + c * PX, routes.get((agency, m), 0)
            stroke = f' stroke="{aa.ACCENT}" stroke-width="1.6"' if n == 0 else ""
            out.append(f'<rect x="{x}" y="{y}" width="{CW}" height="{CH}" fill="{aa.PAPER}"/>')
            out.append(f'<rect data-row="{agency}" data-col="{key(m)}" data-value="{n}" x="{x}" y="{y}" width="{CW}" height="{CH}" rx="3" '
                       f'fill="{INK_A(round(LOW + (HIGH - LOW) * n / total, 2))}"{stroke}/>')
    # the zero: a reported month, marked with a dot
    zr, zc = agencies.index(z["agency_name"]), months.index(z["sales_month"])
    out.append(f'<circle cx="{GX + zc * PX + CW / 2}" cy="{GY + zr * PY + CH / 2}" r="4.5" fill="{aa.INK}"/>')
    # the holes: one bracket under the pair, and what it is
    c0, c1 = months.index(hole_months[0]), months.index(hole_months[-1])
    bx0, bx1, by = GX + c0 * PX, GX + c1 * PX + CW, GY + grid_h + 8
    out.append(f'<path d="M {bx0},{by} v 6 H {bx1} v -6" fill="none" stroke="{aa.ACCENT}" stroke-width="1.4" stroke-linejoin="round"/>')
    out.append(text((bx0 + bx1) / 2, by + 36, f"{hole_agency} sent nothing for {span(hole_months)}", size=14, weight=600, fill=aa.ACCENT, anchor="middle"))
    # the one callout, and where the cells come from
    cy = GY + grid_h + 84
    out.append(f'<circle cx="46" cy="{cy - 4}" r="4.5" fill="{aa.INK}"/>')
    out.append(text(58, cy, f"{z['agency_name']}, {key(z['sales_month'])}", mono=True))
    out.append(text(CALLOUT_X, cy, f"Reported, with AA at {zero_usd} on {z['route']}: a zero is not a gap", size=16, italic=True))
    out.append(aa.icon("databricks", CALLOUT_X, cy + 15, 16))
    out.append(text(CALLOUT_X + 24, cy + 28, "a cell is shaded by how many routes an agency has rows for · gold.fact_agency_sales_monthly", mono=True, fill=aa.MUTED))
    # legend strip
    out.append(f'<line x1="40" y1="664" x2="1240" y2="664" stroke="{aa.RULE}" stroke-width="0.8"/>')
    out.append(eyebrow(40, 694, "Legend"))
    for i, (fill, stroke, label) in enumerate([(INK_A(HIGH), None, "Has rows"), (INK_A(LOW), aa.ACCENT, "No rows")]):
        kx = 144 + i * 160
        line = f' stroke="{stroke}" stroke-width="1.6"' if stroke else ""
        out.append(f'<rect x="{kx}" y="682" width="20" height="14" rx="2" fill="{fill}"{line}/>')
        out.append(text(kx + 28, 694, label, size=11))
    return "\n        ".join(out)


TITLE = "Every agency, every month"


def desc(agencies, months, routes, zero) -> str:
    z = zero[0]
    holes = holes_of(agencies, months, routes)
    return (f"Grid of {display('agencies')} agencies by {display('months')} months, {key(months[0])} to {key(months[-1])}, where "
            f"{display('agency_months_present')} of {display('agency_months_total')} agency-months have rows with all {NUMBER_WORDS[fact('routes')]} routes: "
            f"{holes[0][0]} has none for {span([m for _a, m in holes])}, and {z['agency_name']}'s {key(z['sales_month'])} is reported "
            f"with AA at {FORMATS['usd'][1](int(z['aa_revenue']))} on {z['route']}.")


if __name__ == "__main__":
    data = load()
    check_claims(*data)
    html = aa.page(slug="10-coverage", title=TITLE, desc=desc(*data), eyebrow="fairshare · the data", body=build(*data), vw=VW, vh=VH)
    (aa.OUT / "10-coverage.html").write_text(html, encoding="utf-8")
    print("wrote 10-coverage.html")
