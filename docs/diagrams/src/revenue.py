"""11: AA revenue by calendar month, 2025 against 2026, as two lines. The two months Sunbelt sent nothing are marked.

    .venv/bin/python docs/diagrams/src/revenue.py   # writes docs/diagrams/11-revenue-by-month.html

diagram-design's line chart grammar (references/type-line.md): one polyline per year, dots only on the focal series (the
newest year), gridlines at even steps, a legend strip. The y axis starts at the step below the lowest month instead of at
zero, and says so, because the gaps that matter are 1 to 3 percent of a month and a zero baseline would hide them.

Every number comes from deck_facts.py or from this file's own queries on the same lakehouse; check_claims() asserts on every
build what the callout says about the data.
"""
from __future__ import annotations

import math

import aa
from deck_facts import MONTHS, display, fact, query

VW, VH = 1280, 720
L, R = 128, 1176             # the plot's left and right edges, as in figure 08
TOP, BASE = 140, 500         # the plot's top, and its floor
STEP = 500_000               # one gridline, in dollars
INK_A = lambda a: f"rgba(54,73,90,{a})"
FOCAL_TINT = "rgba(0,108,191,0.08)"
CALLOUT_X = 280              # where the callout's sentences start, clear of its label
NUMBER_WORDS = ("zero", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine", "ten", "eleven", "twelve")


def text(x, y, s, *, size=12, weight=400, fill=aa.INK, mono=False, anchor="start", italic=False, spacing=None):
    extra = (f' letter-spacing="{spacing}"' if spacing else "") + (' font-style="italic"' if italic else "")
    return (f'<text x="{x}" y="{y}" fill="{fill}" font-size="{size}" font-weight="{weight}" font-family="{aa.MONO if mono else aa.SANS}" '
            f'text-anchor="{anchor}"{extra}>{aa.esc(s)}</text>')


def eyebrow(x, y, s, fill=aa.MUTED):
    return text(x, y, s.upper(), size=8, weight=500, fill=fill, mono=True, spacing="0.18em")


def span(months) -> str:
    """Two months of one year: Mar and Apr 2026."""
    assert len(months) == 2 and months[0].year == months[1].year, "the band and its label are written for two months of one year"
    return f"{MONTHS[months[0].month - 1]} and {MONTHS[months[1].month - 1]} {months[0].year}"


# ---------------------------------------------------------------- the data

def load():
    """Revenue by year and month number (all agencies, all routes), the agency-months that have no rows, and Harbor's AA share in
    those months against the same months a year earlier."""
    by_year: dict[int, dict[int, float]] = {}
    for r in query("""
            SELECT sales_month, SUM(aa_revenue) AS revenue
            FROM aa_demo.gold.fact_agency_sales_monthly
            GROUP BY sales_month ORDER BY sales_month"""):
        by_year.setdefault(r["sales_month"].year, {})[r["sales_month"].month] = r["revenue"]
    holes = query("""
        SELECT a.agency_name, d.sales_month
        FROM aa_demo.gold.dim_agency a
        CROSS JOIN (SELECT DISTINCT sales_month FROM aa_demo.gold.fact_agency_sales_monthly) d
        LEFT JOIN aa_demo.gold.fact_agency_sales_monthly s ON s.agency_id = a.agency_id AND s.sales_month = d.sales_month
        WHERE s.agency_id IS NULL
        ORDER BY d.sales_month""")
    dates = ", ".join(f"DATE '{h['sales_month']}'" for h in holes)
    shares = {r["sales_month"].month: (r["aa_share_now"], r["aa_share_prior"]) for r in query(f"""
        SELECT d.sales_month, d.aa_share_now, d.aa_share_prior
        FROM aa_demo.ops.decomposition d
        JOIN aa_demo.gold.dim_agency a ON a.agency_id = d.agency_id
        WHERE a.agency_name = 'Harbor Business Travel' AND d.sales_month IN ({dates})""")}
    return by_year, holes, shares


def check_claims(by_year, holes, shares) -> None:
    """What the callout says about the data, checked on every build so a rebuilt lakehouse cannot quietly change the story."""
    prior, now = (by_year[y] for y in sorted(by_year)[-2:])
    assert [h["agency_name"] for h in holes] == ["Sunbelt Vacations"] * len(holes), "the only agency with no rows should be Sunbelt"
    assert [h["sales_month"].month for h in holes] == [3, 4] and {h["sales_month"].year for h in holes} == {max(by_year)}, \
        "the facts name March and April, and the holes should be those months of the newest year"
    below = [m for m in now if now[m] < prior[m]]
    assert below == [3, 4], "2026 should fall below 2025 in March and April only"
    for month, key in ((3, "yoy_mar26"), (4, "yoy_apr26")):
        assert round(100 * (now[month] - prior[month]) / prior[month], 1) == fact(key), f"{key} should match the two lines"
    assert fact("sunbelt_mar25_usd") > 0 and fact("sunbelt_apr25_usd") > 0, "Sunbelt sold something in those months of 2025"
    assert all(a < b for a, b in shares.values()) and len(shares) == 2, "Harbor's share should be lower than a year earlier in both months"
    assert fact("harbor_mar26_chg_usd") < 0 and fact("harbor_apr26_chg_usd") < 0, "Harbor's AA revenue should be down in both months"
    assert fact("others_mar26_chg_usd") > 0 and fact("others_apr26_chg_usd") > 0, "the other agencies should have grown in total in both months"
    # Sunbelt's change is what it sold a year earlier, taken away; each part is rounded to the dollar, so the sum may be a dollar or two off
    for month, sunbelt, harbor, others in ((3, "sunbelt_mar25_usd", "harbor_mar26_chg_usd", "others_mar26_chg_usd"),
                                           (4, "sunbelt_apr25_usd", "harbor_apr26_chg_usd", "others_apr26_chg_usd")):
        parts, net = -fact(sunbelt) + fact(harbor) + fact(others), now[month] - prior[month]
        assert abs(parts - net) <= 2, f"Sunbelt, Harbor and the other agencies should add up to month {month}'s change: {parts} against {net:.0f}"


# ---------------------------------------------------------------- the figure

def build(by_year, holes, shares) -> str:
    years = sorted(by_year)
    prior_year, focal_year = years[-2], years[-1]
    gap_months = [h["sales_month"] for h in holes]
    values = [v for y in years for v in by_year[y].values()]
    lo, hi = math.floor(min(values) / STEP) * STEP, math.ceil(max(values) / STEP) * STEP
    slot = (R - L) / len(MONTHS)
    x = lambda month: L + (month - 0.5) * slot                         # noqa: E731  the middle of a month's slot
    y = lambda v: BASE - (v - lo) * (BASE - TOP) / (hi - lo)           # noqa: E731
    millions = lambda v: f"${v / 1e6:.1f}M"                            # noqa: E731
    out = [f'<rect width="100%" height="100%" fill="{aa.PAPER}"/>', aa.brand(tag="fairshare · synthetic data")]
    # what the chart is about, inside the image because a slide takes the SVG alone
    out.append(text(40, 100, "AA revenue by month", size=16, weight=600))
    out.append(text(40, 120, f"AA revenue per month in $ millions, all agencies and routes. The axis starts at {millions(lo)}, not at zero.",
                    mono=True, fill=aa.MUTED))
    # the band over the months with no rows, behind everything else
    band_x, band_w = L + (gap_months[0].month - 1) * slot, len(gap_months) * slot
    out.append(f'<rect x="{band_x:.1f}" y="{TOP}" width="{band_w:.1f}" height="{BASE - TOP}" fill="{FOCAL_TINT}"/>')
    # grid, axes, ticks
    for v in range(lo + STEP, hi + 1, STEP):
        out.append(f'<line x1="{L}" y1="{y(v):.2f}" x2="{R}" y2="{y(v):.2f}" stroke="{INK_A(0.08)}" stroke-width="0.8"/>')
    for v in range(lo, hi + 1, STEP):
        out.append(text(L - 8, f"{y(v) + 4:.2f}", millions(v), size=11, fill=aa.MUTED, mono=True, anchor="end"))
    out.append(f'<line x1="{L}" y1="{TOP}" x2="{L}" y2="{BASE}" stroke="{INK_A(0.25)}" stroke-width="1"/>')
    out.append(f'<line x1="{L}" y1="{BASE}" x2="{R}" y2="{BASE}" stroke="{INK_A(0.25)}" stroke-width="1"/>')
    for m, name in enumerate(MONTHS, 1):
        out.append(text(f"{x(m):.1f}", BASE + 24, name, size=12, fill=aa.MUTED, mono=True, anchor="middle"))
    # the lines: last year muted, this year in the accent with a dot on every point
    pts = lambda series: " ".join(f"{x(m):.1f},{y(v):.1f}" for m, v in sorted(series.items()))  # noqa: E731
    out.append(f'<polyline points="{pts(by_year[prior_year])}" fill="none" stroke="{aa.MUTED}" stroke-width="1.6" stroke-linejoin="round"/>')
    out.append(f'<polyline points="{pts(by_year[focal_year])}" fill="none" stroke="{aa.ACCENT}" stroke-width="2.2" stroke-linejoin="round"/>')
    for m, v in sorted(by_year[focal_year].items()):
        out.append(f'<circle cx="{x(m):.1f}" cy="{y(v):.1f}" r="4" fill="{aa.ACCENT}" stroke="{aa.PAPER}" stroke-width="1.5"/>')
    for year, series, color in ((prior_year, by_year[prior_year], aa.MUTED), (focal_year, by_year[focal_year], aa.ACCENT)):
        m = max(series)
        out.append(text(f"{x(m) + 12:.1f}", f"{y(series[m]) + 4:.1f}", str(year), size=12, weight=600, fill=color, mono=True))
    # the two months, against last year
    out.append(text(f"{band_x + band_w / 2:.1f}", BASE - 44, f"Net, {focal_year} vs {prior_year}", mono=True, fill=aa.ACCENT, anchor="middle"))
    for h, key in zip(gap_months, ("yoy_mar26", "yoy_apr26")):
        out.append(text(f"{x(h.month):.1f}", BASE - 14, display(key), size=14, weight=600, fill=aa.ACCENT, mono=True, anchor="middle"))
    # the one callout, and where the lines come from
    cy = 562
    others = fact("agencies") - 2  # the other agencies are all but Sunbelt and Harbor
    out.append(text(40, cy, span(gap_months), mono=True, fill=aa.ACCENT))
    out.append(text(CALLOUT_X, cy, f"Sunbelt sent nothing: it sold {display('sunbelt_mar25_usd')} and {display('sunbelt_apr25_usd')} in those months of {prior_year}.",
                    size=16, italic=True))
    out.append(text(CALLOUT_X, cy + 24, f"Harbor's AA revenue fell: {display('harbor_mar26_chg_usd')} and {display('harbor_apr26_chg_usd')} against {prior_year}.",
                    size=16, italic=True))
    out.append(text(CALLOUT_X, cy + 48, f"The other {NUMBER_WORDS[others]} agencies grew in total: {display('others_mar26_chg_usd')} and {display('others_apr26_chg_usd')} against {prior_year}.",
                    size=16, italic=True))
    out.append(aa.icon("databricks", CALLOUT_X, 630, 16))
    out.append(text(CALLOUT_X + 24, 643, "AA revenue summed over all agencies and routes · gold.fact_agency_sales_monthly", mono=True, fill=aa.MUTED))
    # legend strip
    out.append(f'<line x1="40" y1="664" x2="1240" y2="664" stroke="{aa.RULE}" stroke-width="0.8"/>')
    out.append(eyebrow(40, 694, "Legend"))
    kx = 144
    out.append(f'<line x1="{kx}" y1="689" x2="{kx + 24}" y2="689" stroke="{aa.MUTED}" stroke-width="1.6"/>')
    out.append(text(kx + 32, 694, str(prior_year), size=11))
    kx += 112
    out.append(f'<line x1="{kx}" y1="689" x2="{kx + 24}" y2="689" stroke="{aa.ACCENT}" stroke-width="2.2"/>')
    out.append(f'<circle cx="{kx + 12}" cy="689" r="4" fill="{aa.ACCENT}" stroke="{aa.PAPER}" stroke-width="1.5"/>')
    out.append(text(kx + 32, 694, str(focal_year), size=11))
    kx += 112
    out.append(f'<rect x="{kx}" y="682" width="20" height="14" fill="{FOCAL_TINT}" stroke="{aa.ACCENT}" stroke-width="1"/>')
    out.append(text(kx + 28, 694, span(gap_months), size=11))
    return "\n        ".join(out)


TITLE = "AA revenue by month"


def desc(by_year, holes) -> str:
    years = sorted(by_year)
    return (f"Two lines of AA revenue by calendar month, {years[-2]} against {years[-1]}: {years[-1]} runs above {years[-2]} except in "
            f"{span([h['sales_month'] for h in holes])}, when Sunbelt sent nothing and Harbor's AA revenue fell, though the other agencies grew in total.")


if __name__ == "__main__":
    data = load()
    check_claims(*data)
    html = aa.page(slug="11-revenue-by-month", title=TITLE, desc=desc(data[0], data[1]), eyebrow="fairshare · the data", body=build(*data), vw=VW, vh=VH)
    (aa.OUT / "11-revenue-by-month.html").write_text(html, encoding="utf-8")
    print("wrote 11-revenue-by-month.html")
