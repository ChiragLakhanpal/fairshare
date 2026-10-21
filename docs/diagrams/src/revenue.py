"""11: AA revenue by calendar month, 2025 against 2026, as two lines. The two months Sunbelt sent nothing are marked.

    .venv/bin/python docs/diagrams/src/revenue.py   # writes docs/diagrams/11-revenue-by-month.html and 11-revenue-by-month-animated.html

diagram-design's line chart grammar (references/type-line.md): one line per year, dots only on the focal series (the newest
year), gridlines at even steps. Each line ends in its year, so there is no legend. The y axis starts at the step below the
lowest month instead of at zero, and says so, because the gaps that matter are 1 to 3 percent of a month and a zero baseline
would hide them. The band over March and April names its months and carries each month's net change against last year, and
three short notes beside it say what made the change. They sit under the title in size and weight, and the source line is
the smallest text, in grey.

The animated page is the same figure in steps for the /present deck. The title, the axes, the lines and the source line show on
arrival, and in the deck the lines trace left to right while their dots and year labels follow (aa.EMBED_CSS). The band with
its net change comes on the first press, then one note per press. The static page shows it all at once.

Every number comes from deck_facts.py or from this file's own queries on the same lakehouse; check_claims() asserts on every
build what the notes say about the data.
"""
from __future__ import annotations

import math

import aa
from deck_facts import MONTHS, display, fact, query

VW, VH = 1280, 720
L, R = 128, 1176             # the plot's left and right edges, as in figure 08
TOP, BASE = 148, 588         # the plot's top, and its floor
STEP = 500_000               # one gridline, in dollars
INK_A = lambda a: f"rgba(54,73,90,{a})"
FOCAL_TINT = "rgba(0,108,191,0.08)"
NOTE_SIZE, NOTE_LEADING = 13, 19   # the notes beside the band: under the 16px title in size and weight
SOURCE_Y = 662               # the source line's baseline, the last line on the stage
NUMBER_WORDS = ("zero", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine", "ten", "eleven", "twelve")
TITLE, EYEBROW = "AA revenue by month", "fairshare · the data"
# The animated page's own rules, after the plugin's: its items fade in where they stand, and in the deck the note on the current
# press leads in ink while an earlier one recedes to the muted text it is drawn in, over the plugin's step time. On its own the
# page keeps every note muted, as the static page does.
MOTION_CSS = (f"    {aa.FADE_ONLY}\n"
              "    html[data-embed] .motion-ready [data-motion-item] [data-note] { transition: fill var(--motion-step) var(--motion-ease); }\n"
              "    html[data-embed] .motion-ready [data-motion-item].is-current [data-note] { fill: var(--color-ink); }\n")


def text(x, y, s, *, size=12, weight=400, fill=aa.INK, mono=False, anchor="start", attrs=""):
    """One line of text; attrs, when given, starts with a space."""
    return (f'<text x="{x}" y="{y}" fill="{fill}" font-size="{size}" font-weight="{weight}" font-family="{aa.MONO if mono else aa.SANS}" '
            f'text-anchor="{anchor}"{attrs}>{aa.esc(s)}</text>')


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
    """What the notes say about the data, checked on every build so a rebuilt lakehouse cannot quietly change the story."""
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

def notes(by_year) -> list[tuple[str, str]]:
    """What made the two months' change, as (key, sentence): one note per press beside the band."""
    prior_year = sorted(by_year)[-2]
    others = fact("agencies") - 2  # the other agencies are all but Sunbelt and Harbor
    return [("sunbelt", f"Sunbelt sent nothing: it sold {display('sunbelt_mar25_usd')} and {display('sunbelt_apr25_usd')} in those months of {prior_year}."),
            ("harbor", f"Harbor's AA revenue fell: {display('harbor_mar26_chg_usd')} and {display('harbor_apr26_chg_usd')} against {prior_year}."),
            ("others", f"The other {NUMBER_WORDS[others]} agencies grew in total: {display('others_mar26_chg_usd')} and "
                       f"{display('others_apr26_chg_usd')} against {prior_year}.")]


def build(by_year, holes, shares, motion=False) -> str:
    """The figure. With motion, the band and the three notes are the steps, and the lines, the dots and the year labels carry the
    deck's draw-in classes; without it, the same marks, all at once."""
    years = sorted(by_year)
    prior_year, focal_year = years[-2], years[-1]
    gap_months = [h["sales_month"] for h in holes]
    values = [v for yr in years for v in by_year[yr].values()]
    lo, hi = math.floor(min(values) / STEP) * STEP, math.ceil(max(values) / STEP) * STEP
    slot = (R - L) / len(MONTHS)
    x = lambda month: L + (month - 0.5) * slot                         # noqa: E731  the middle of a month's slot
    y = lambda v: BASE - (v - lo) * (BASE - TOP) / (hi - lo)           # noqa: E731
    millions = lambda v: f"${v / 1e6:.1f}M"                            # noqa: E731
    out = [f'<rect width="100%" height="100%" fill="{aa.PAPER}"/>', aa.brand(tag="fairshare · synthetic data")]
    # what the chart is about, inside the image because a slide takes the SVG alone
    out.append(text(40, 100, TITLE, size=16, weight=600))
    out.append(text(40, 120, f"AA revenue per month in $ millions, all agencies and routes. The axis starts at {millions(lo)}, not at zero.",
                    mono=True, fill=aa.MUTED))
    # step 1: the band over the two months with no Sunbelt rows, behind everything else. It names its months at its top and carries
    # each month's net change against last year at its foot.
    band_x, band_w = L + (gap_months[0].month - 1) * slot, len(gap_months) * slot
    label_y = TOP + 18  # the band's name, and the first note beside it, on one baseline
    band = [f'<rect x="{band_x:.1f}" y="{TOP}" width="{band_w:.1f}" height="{BASE - TOP}" fill="{FOCAL_TINT}" data-role="band"/>',
            text(f"{band_x + band_w / 2:.1f}", label_y, span(gap_months), mono=True, fill=aa.ACCENT, anchor="middle"),
            text(f"{band_x + band_w / 2:.1f}", BASE - 44, f"Net, {focal_year} vs {prior_year}", mono=True, fill=aa.MUTED, anchor="middle")]
    for h, key in zip(gap_months, ("yoy_mar26", "yoy_apr26")):
        band.append(text(f"{x(h.month):.1f}", BASE - 14, display(key), size=14, weight=600, fill=aa.ACCENT, mono=True, anchor="middle"))
    out += [aa.motion_item(1, f"{span(gap_months)}: AA revenue against {prior_year}, net {display('yoy_mar26')} and {display('yoy_apr26')}", band)] \
        if motion else band
    # grid, axes, ticks
    for v in range(lo + STEP, hi + 1, STEP):
        out.append(f'<line x1="{L}" y1="{y(v):.2f}" x2="{R}" y2="{y(v):.2f}" stroke="{INK_A(0.08)}" stroke-width="0.8"/>')
    for v in range(lo, hi + 1, STEP):
        out.append(text(L - 8, f"{y(v) + 4:.2f}", millions(v), size=11, fill=aa.MUTED, mono=True, anchor="end"))
    out.append(f'<line x1="{L}" y1="{TOP}" x2="{L}" y2="{BASE}" stroke="{INK_A(0.25)}" stroke-width="1"/>')
    out.append(f'<line x1="{L}" y1="{BASE}" x2="{R}" y2="{BASE}" stroke="{INK_A(0.25)}" stroke-width="1"/>')
    for m, name in enumerate(MONTHS, 1):
        out.append(text(f"{x(m):.1f}", BASE + 24, name, size=12, fill=aa.MUTED, mono=True, anchor="middle"))
    # the lines: last year muted, this year in the accent with a dot on every point, each ending in its year. On the animated page,
    # the deck's embed mode makes each line trace itself (pathLength 1 makes one dash the whole line), and its dots and its year come
    # in after it.
    trace, follow = (' class="draw-line" pathLength="1"', ' class="draw-dot"') if motion else ("", "")
    for year, color, width in ((prior_year, aa.MUTED, 1.6), (focal_year, aa.ACCENT, 2.2)):
        d = "M " + " L ".join(f"{x(m):.1f},{y(v):.1f}" for m, v in sorted(by_year[year].items()))
        out.append(f'<path d="{d}" fill="none" stroke="{color}" stroke-width="{width}" stroke-linejoin="round" data-series="{year}"{trace}/>')
    for m, v in sorted(by_year[focal_year].items()):
        out.append(f'<circle cx="{x(m):.1f}" cy="{y(v):.1f}" r="4" fill="{aa.ACCENT}" stroke="{aa.PAPER}" stroke-width="1.5"{follow}/>')
    for year, color in ((prior_year, aa.MUTED), (focal_year, aa.ACCENT)):
        m = max(by_year[year])
        out.append(text(f"{x(m) + 12:.1f}", f"{y(by_year[year][m]) + 4:.1f}", str(year), weight=600, fill=color, mono=True, attrs=follow))
    # steps 2 to 4: what made the change, one note per press, beside the band and clear of the lines' highest points to its right,
    # in the muted text of a note (in the deck the newest one leads, MOTION_CSS)
    nx = band_x + band_w + 16
    said = notes(by_year)
    peak = min(y(v) for yr in years for m, v in by_year[yr].items() if x(m) > nx) - 4.75  # a dot's top, with its stroke
    assert label_y + (len(said) - 1) * NOTE_LEADING + aa.TEXT_DESCENT * NOTE_SIZE + 6 <= peak, "the notes run into the lines"
    for k, (key, sentence) in enumerate(said):
        mark = text(f"{nx:.1f}", label_y + k * NOTE_LEADING, sentence, size=NOTE_SIZE, fill=aa.MUTED, attrs=f' data-note="{key}"')
        out.append(aa.motion_item(k + 2, sentence, [mark]) if motion else mark)
    # where the lines come from: the smallest text, in grey, last
    assert SOURCE_Y + aa.TEXT_DESCENT * 11 <= aa.STAGE_BOTTOM, "the source line runs under the deck's footer"
    out.append(aa.icon("databricks", 40, SOURCE_Y - 11, 14, aa.MUTED))
    out.append(text(60, SOURCE_Y, "AA revenue summed over all agencies and routes · gold.fact_agency_sales_monthly", size=11, mono=True, fill=aa.MUTED))
    return "\n        ".join(out)


def desc(by_year, holes) -> str:
    years = sorted(by_year)
    return (f"Two lines of AA revenue by calendar month, {years[-2]} against {years[-1]}: {years[-1]} runs above {years[-2]} except in "
            f"{span([h['sales_month'] for h in holes])}, when Sunbelt sent nothing and Harbor's AA revenue fell, though the other agencies grew in total.")


if __name__ == "__main__":
    data = load()
    check_claims(*data)
    common = dict(title=TITLE, desc=desc(data[0], data[1]), eyebrow=EYEBROW, vw=VW, vh=VH)
    html = aa.page(slug="11-revenue-by-month", body=build(*data), **common)
    (aa.OUT / "11-revenue-by-month.html").write_text(html, encoding="utf-8")
    html = aa.animated(slug="11-revenue-by-month-animated", body=build(*data, motion=True), steps=1 + len(notes(data[0])), css=MOTION_CSS, **common)
    (aa.OUT / "11-revenue-by-month-animated.html").write_text(html, encoding="utf-8")
    print("wrote 11-revenue-by-month.html and 11-revenue-by-month-animated.html")
