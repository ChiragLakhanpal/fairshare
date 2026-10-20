"""12: AA share against fair share for every agency in Q3 2026, as a dumbbell. One row per agency, sorted by the gap (AA share minus
fair share, the biggest gap above fair share first). Fair share is the hollow dot, AA share the solid one.

    .venv/bin/python docs/diagrams/src/share_fair.py   # writes docs/diagrams/12-share-vs-fair.html

diagram-design's dumbbell variant (references/type-bar.md): rows stack downward on one horizontal value axis, each row a hairline
between two dots, the reference end hollow and the focal end solid, so fill weight and not hue tells the two ends apart. Where this
figure leaves the reference, on purpose:
  - Twelve rows, one per agency, past the type's 4 to 8 (its pitch table stops at 8 rows of 48px); the pitch here is 28px.
  - Accent on the top and bottom rows only, as the brief asks. The reference accents the AA dot on every row; here that dot is ink on
    the ten middle rows and accent on the first and last, and the pairing is still told by hollow against solid.
  - The axis runs 0 to 60. The reference anchors the floor at zero for positive data (scripts/verify-dumbbell.py resolve_domain agrees)
    and "rounds ceil up past hi"; its ladder (1, 2, 2.5, 5, 10) would end this axis at 100 and leave the right half of the plot empty,
    so it ends at the next ten above the largest share instead.
  - The connector is ink at 0.60. The reference's 0.55 clears 3:1 under its own ink; under AA's lighter slate it measures 2.83:1 and
    0.60 measures 3.18:1. check_claims() holds the connector and both dot strokes to 3:1 with the plugin's own contrast functions.
  - Pairs closer than the verifier's MIN_GAP_PX (16) overlap. Dots keep their true positions, both values stay printed, and a bracket
    marks the rows as too close to show, which is the reference's "mark the row as too close to resolve".

Every number comes from deck_facts.py: the two values on each row are the 24 agency_q3_* facts (the metric view's definitions written
out in SQL), and the sentence under the chart is the brief's. check_claims() asserts on every build what the figure says about the data,
and the three parts of that sentence one at a time: every agency sells all the routes; fair share moves less than a tenth as much as AA
share; and the share of an agency's sales that a route takes depends on the agency's region and on whether the route starts at a hub
(agencies in one region split their sales alike, every hub route outweighs every other route), which is the sentence's reason.
"""
from __future__ import annotations

import aa
from deck_facts import AGENCIES, display, fact, query

VW, VH = 1280, 720
L, R = 296, 1176              # the plot: value FLOOR sits at L, CEIL at R
FLOOR, CEIL, STEP = 0, 60, 10
ROW0, PITCH = 176, 28         # the first row's centre, and the pitch of a row
GRID_TOP, GRID_BASE = 152, 508
RADIUS = 6                    # the reference's dot
CONNECTOR = 0.60              # ink opacity of the hairline between the two dots; see the docstring
INK_A = lambda a: f"rgba(54,73,90,{a})"  # noqa: E731
NUMBER_WORDS = ("zero", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine", "ten", "eleven", "twelve")
SLUG = {name: slug for slug, name in AGENCIES}
dumbbell = aa.load("verify_dumbbell", "verify-dumbbell.py")  # the plugin's own domain and contrast functions

TITLE = "AA share against fair share, Q3 2026"
SUBTITLE = ("AA share is the part of an agency's sales that went to AA. Fair share is AA's share of the seats on the same routes. "
            "The seat shares are made up.")
SOURCE = ("fair share uses made-up seat shares, one per route; the T-100 loader (data/t100.py) has never run "
          "· gold.fact_agency_sales_monthly, gold.fact_market_capacity")
ORDER = "Rows run from the biggest gap above fair share to the biggest gap below it"


def text(x, y, s, *, size=12, weight=400, fill=aa.INK, mono=False, anchor="start", italic=False, spacing=None, extra=""):
    extra += (f' letter-spacing="{spacing}"' if spacing else "") + (' font-style="italic"' if italic else "")
    return (f'<text x="{x}" y="{y}" fill="{fill}" font-size="{size}" font-weight="{weight}" font-family="{aa.MONO if mono else aa.SANS}" '
            f'text-anchor="{anchor}"{extra}>{aa.esc(s)}</text>')


def eyebrow(x, y, s, fill=aa.MUTED, anchor="start"):
    return text(x, y, s.upper(), size=8, weight=500, fill=fill, mono=True, spacing="0.18em", anchor=anchor)


def x_of(v: float) -> int:
    """A value's x, rounded to the nearest pixel as the reference rounds endpoints; never snapped to the 4px grid, because that moves the data."""
    return round(L + (v - FLOOR) / (CEIL - FLOOR) * (R - L))


# ---------------------------------------------------------------- the data

def load():
    """Every agency's AA share and fair share in Q3 2026, all routes together (the metric view's definitions written out), the routes it
    sold, its region, and how its sales spread over the routes (each route's percent of its sales, and whether the route starts at an AA
    hub); sorted by the gap, biggest first. These exact values order the rows; the facts print them."""
    rows = query("""
        SELECT a.agency_name AS name, a.region, COUNT(DISTINCT s.market_id) AS routes,
               100 * SUM(s.aa_revenue) / NULLIF(SUM(s.market_revenue), 0) AS aa,
               100 * SUM(s.market_revenue * c.aa_seat_share) / NULLIF(SUM(s.market_revenue), 0) AS fair
        FROM aa_demo.gold.fact_agency_sales_monthly s
        JOIN aa_demo.gold.dim_agency a ON a.agency_id = s.agency_id
        JOIN aa_demo.gold.fact_market_capacity c ON c.market_id = s.market_id AND c.sales_month = s.sales_month
        WHERE s.sales_month BETWEEN DATE '2026-07-01' AND DATE '2026-09-01'
        GROUP BY a.agency_name, a.region""")
    spread = query("""
        SELECT a.agency_name AS name, m.market_id, m.aa_hub_origin AS hub, SUM(s.market_revenue) AS revenue
        FROM aa_demo.gold.fact_agency_sales_monthly s
        JOIN aa_demo.gold.dim_agency a ON a.agency_id = s.agency_id
        JOIN aa_demo.gold.dim_market m ON m.market_id = s.market_id
        WHERE s.sales_month BETWEEN DATE '2026-07-01' AND DATE '2026-09-01'
        GROUP BY a.agency_name, m.market_id, m.aa_hub_origin""")
    for r in rows:
        r["aa_printed"], r["fair_printed"] = fact(f"agency_q3_aa_share_{SLUG[r['name']]}"), fact(f"agency_q3_fair_share_{SLUG[r['name']]}")
        mine = [x for x in spread if x["name"] == r["name"]]
        total = sum(x["revenue"] for x in mine)
        r["mix"] = [(x["market_id"], x["hub"], 100 * x["revenue"] / total) for x in mine]
    return sorted(rows, key=lambda r: r["aa"] - r["fair"], reverse=True)


def pairs_too_close(rows) -> list[int]:
    """The rows whose two dots sit closer than the plugin's minimum drawn gap."""
    return [i for i, r in enumerate(rows) if abs(x_of(r["aa_printed"]) - x_of(r["fair_printed"])) < dumbbell.MIN_GAP_PX]


def check_claims(rows) -> None:
    """What the figure says about the data, checked on every build so a rebuilt lakehouse cannot quietly change the story."""
    assert len(rows) == fact("agencies") and {r["name"] for r in rows} == set(SLUG), "one row for each of the agencies deck_facts names"
    assert {r["routes"] for r in rows} == {fact("routes")}, "every agency should sell all the routes in Q3: 'the same routes'"
    for r in rows:  # the facts and this file's own query are two statements of one definition
        assert abs(r["aa_printed"] - r["aa"]) <= 0.05 + 1e-9 and abs(r["fair_printed"] - r["fair"]) <= 0.05 + 1e-9, f"{r['name']}: a fact differs from the query"
    assert abs(sum(r["aa"] for r in rows) / len(rows) - fact("avg_of_shares_q3")) <= 0.05 + 1e-9, "the twelve AA shares should average to the Q3 fact the deck already says"
    order = [r["name"] for r in sorted(rows, key=lambda r: r["aa_printed"] - r["fair_printed"], reverse=True)]
    assert order == [r["name"] for r in rows], "the printed numbers should give the same row order as the exact ones"
    assert rows[0]["aa"] - rows[0]["fair"] > 0 > rows[-1]["aa"] - rows[-1]["fair"], "the top row is above fair share and the bottom row below it"
    # the caption: "fair share is nearly the same for every agency, ... weighted only by hub and region"
    fair, aa_share = [r["fair_printed"] for r in rows], [r["aa_printed"] for r in rows]
    spread = max(fair) - min(fair)
    assert spread < (max(aa_share) - min(aa_share)) / 10, "fair share should move less than a tenth as much as AA share"
    # "weighted only by hub and region": inside one region every route takes nearly the same share of every agency's sales, across regions it
    # does not, and in every agency the routes that start at an AA hub take more of the sales than the ones that do not
    inside: dict[tuple, list[float]] = {}
    overall: dict[int, list[float]] = {}
    for r in rows:
        for market_id, _hub, pct in r["mix"]:
            inside.setdefault((r["region"], market_id), []).append(pct)
            overall.setdefault(market_id, []).append(pct)
        hubs, others = [p for _m, hub, p in r["mix"] if hub], [p for _m, hub, p in r["mix"] if not hub]
        assert hubs and others and max(others) < min(hubs), f"{r['name']}: every hub route should take more of its sales than any other route"
    assert max(max(v) - min(v) for v in inside.values()) < max(max(v) - min(v) for v in overall.values()) / 2, \
        "agencies in one region should split their sales over the routes alike, and agencies overall should not"
    # the axis and the marks
    values = [v for r in rows for v in (r["aa_printed"], r["fair_printed"])]
    assert FLOOR == dumbbell.resolve_domain(values)[0], "positive data anchors the axis at zero"
    assert CEIL >= max(values) and (CEIL - FLOOR) % STEP == 0, "the axis ends on a gridline above the largest value"
    for what, color, alpha in (("connector", aa.INK, CONNECTOR), ("solid dot stroke", aa.INK, 1.0), ("hollow dot stroke", aa.MUTED, 1.0)):
        ratio = dumbbell.contrast(dumbbell.composite(color, alpha, aa.PAPER), aa.PAPER)
        assert ratio >= dumbbell.WCAG_NON_TEXT, f"the {what} should clear 3:1 on paper, and it measures {ratio:.2f}:1"
    close = pairs_too_close(rows)
    assert close and close == list(range(close[0], close[-1] + 1)), "the rows too close to show should be neighbours, so one bracket covers them"
    assert all(abs(r["aa_printed"] - r["fair_printed"]) < 2 for r in (rows[i] for i in close)), "and they should be rows at fair share"


# ---------------------------------------------------------------- the figure

def build(rows) -> str:
    out = [f'<rect width="100%" height="100%" fill="{aa.PAPER}"/>', aa.brand(tag="fairshare · synthetic data")]
    # what the chart is about, inside the image because a slide takes the SVG alone
    out.append(text(40, 100, TITLE, size=16, weight=600))
    out.append(text(40, 120, SUBTITLE, mono=True, fill=aa.MUTED))
    # the axis: a gridline at every step, the axis line in place of the one at the floor, ticks and the axis title below
    for v in range(FLOOR, CEIL + 1, STEP):
        if v == FLOOR:
            out.append(f'<line x1="{x_of(v)}" y1="{GRID_TOP - 4}" x2="{x_of(v)}" y2="{GRID_BASE + 4}" stroke="{INK_A(0.25)}" stroke-width="1"/>')
        else:
            out.append(f'<line x1="{x_of(v)}" y1="{GRID_TOP}" x2="{x_of(v)}" y2="{GRID_BASE}" stroke="{INK_A(0.08)}" stroke-width="0.8"/>')
        out.append(text(x_of(v), GRID_BASE + 20, str(v), size=11, fill=aa.MUTED, mono=True, anchor="middle"))
    out.append(eyebrow((L + R) / 2, GRID_BASE + 40, "AA share and fair share, percent", anchor="middle"))
    # rows that are too close to show: one bracket and one note, on a paper mask so the gridlines do not run through the words
    close = pairs_too_close(rows)
    if close:
        top, bottom = ROW0 + close[0] * PITCH - 10, ROW0 + close[-1] * PITCH + 10
        bx = max(max(x_of(rows[i]["aa_printed"]), x_of(rows[i]["fair_printed"])) for i in close) + 12 + 36 + 16  # past the longest right-hand label
        out.append(f'<path d="M {bx},{top} h 6 V {bottom} h -6" fill="none" stroke="{aa.MUTED}" stroke-width="1.2" stroke-linejoin="round"/>')
        out.append(f'<rect x="{bx + 12}" y="{(top + bottom) / 2 - 9}" width="156" height="18" fill="{aa.PAPER}"/>')
        out.append(text(bx + 16, (top + bottom) / 2 + 4, "gap too small to show", size=11, fill=aa.MUTED, mono=True))
    # the rows: the hairline first so the dots cap it, then fair share (hollow), then AA share (solid) on top
    for i, r in enumerate(rows):
        y, name, slug = ROW0 + i * PITCH, r["name"], SLUG[r["name"]]
        focal = i in (0, len(rows) - 1)
        xs, xf = x_of(r["aa_printed"]), x_of(r["fair_printed"])
        out.append(text(L - 16, y + 5, name, size=14, weight=600 if focal else 400, fill=aa.ACCENT if focal else aa.INK, anchor="end", extra=f' data-row-label="{name}"'))
        out.append(f'<line data-agency="{name}" x1="{xf}" y1="{y}" x2="{xs}" y2="{y}" stroke="{INK_A(CONNECTOR)}" stroke-width="1"/>')
        out.append(f'<circle data-agency="{name}" data-series="fair" data-value="{r["fair_printed"]}" cx="{xf}" cy="{y}" r="{RADIUS}" fill="{aa.PAPER}" stroke="{aa.MUTED}" stroke-width="1.5"/>')
        out.append(f'<circle data-agency="{name}" data-series="aa" data-value="{r["aa_printed"]}" cx="{xs}" cy="{y}" r="{RADIUS}" fill="{aa.ACCENT if focal else aa.INK}" stroke="{aa.INK}" stroke-width="1"/>')
        # the value labels sit outside the pair, placed by geometry and not by series: the left one right-anchored 12px before its dot, the
        # right one left-anchored 12px after its dot, each carrying its own series' value (a row where AA sits below fair share swaps sides)
        (lseries, lx), (rseries, rx) = sorted((("aa", xs), ("fair", xf)), key=lambda end: end[1])
        for series, x, anchor, dx in ((lseries, lx, "end", -12), (rseries, rx, "start", 12)):
            out.append(text(x + dx, y + 4, display(f"agency_q3_{series}_share_{slug}"), weight=600 if series == "aa" else 400,
                            fill=aa.INK if series == "aa" else aa.MUTED, mono=True, anchor=anchor, extra=f' data-agency="{name}" data-series="{series}"'))
    # the one sentence, and where the numbers come from
    cy = 588
    out.append(text(40, cy, f"Fair share is nearly the same for every agency, because all {NUMBER_WORDS[fact('agencies')]} sell the same "
                            f"{NUMBER_WORDS[fact('routes')]} routes, weighted only by hub and region.", size=16, italic=True))
    out.append(aa.icon("databricks", 40, cy + 15, 16))
    out.append(text(64, cy + 28, SOURCE, mono=True, fill=aa.MUTED))
    # legend strip: the two ends, the accent, and the order of the rows
    out.append(f'<line x1="40" y1="664" x2="1240" y2="664" stroke="{aa.RULE}" stroke-width="0.8"/>')
    out.append(eyebrow(40, 694, "Legend"))
    keys = [(aa.PAPER, aa.MUTED, 1.5, "Fair share"), (aa.INK, aa.INK, 1, "AA share"), (aa.ACCENT, aa.INK, 1, "AA share, biggest gap above and below fair share")]
    kx = 144
    for fill, stroke, width, label in keys:
        out.append(f'<circle cx="{kx + 6}" cy="689" r="{RADIUS}" fill="{fill}" stroke="{stroke}" stroke-width="{width}"/>')
        out.append(text(kx + 20, 694, label, size=11))
        kx += 20 + round(len(label) * 5.9) + 28
    out.append(text(1240, 694, ORDER, size=11, fill=aa.MUTED, anchor="end"))
    return "\n        ".join(out)


def desc(rows) -> str:
    top, bottom = rows[0], rows[-1]
    keys = [f"agency_q3_fair_share_{SLUG[r['name']]}" for r in rows]
    low, high = min(keys, key=fact), max(keys, key=fact)  # the two ends of the fair share column
    return (f"Dumbbell chart of {NUMBER_WORDS[fact('agencies')]} agencies' AA share against fair share in Q3 2026, sorted by the gap: {top['name']} is highest at "
            f"{display('agency_q3_aa_share_' + SLUG[top['name']])} against {display('agency_q3_fair_share_' + SLUG[top['name']])}, {bottom['name']} lowest at "
            f"{display('agency_q3_aa_share_' + SLUG[bottom['name']])} against {display('agency_q3_fair_share_' + SLUG[bottom['name']])}, "
            f"while fair share stays between {display(low)} and {display(high)} for every agency.")


if __name__ == "__main__":
    data = load()
    check_claims(data)
    html = aa.page(slug="12-share-vs-fair", title=TITLE, desc=desc(data), eyebrow="fairshare · the data", body=build(data), vw=VW, vh=VH)
    (aa.OUT / "12-share-vs-fair.html").write_text(html, encoding="utf-8")
    print("wrote 12-share-vs-fair.html")
