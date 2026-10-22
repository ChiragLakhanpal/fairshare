"""12: AA share against fair share for every agency in Q3 2026, as a dumbbell. One row per agency, sorted by the signed gap (AA share
minus fair share, furthest above fair share first). Fair share is the hollow dot, AA share the solid one.

    .venv/bin/python docs/diagrams/src/share_fair.py   # writes docs/diagrams/12-share-vs-fair.html and 12-share-vs-fair-animated.html

diagram-design's dumbbell variant (references/type-bar.md): rows stack downward on one horizontal value axis, each row a hairline
between two dots, the reference end hollow and the focal end solid in the accent, so fill weight and not hue tells the two ends apart.
Where this figure leaves the reference, on purpose:
  - Twelve rows, one per agency, past the type's 4 to 8 (its pitch table stops at 8 rows of 48px); the pitch here is 30px.
  - Values are printed on two rows only, the top and the bottom, the two agencies that carry the story, because a slide holds four
    values at most. The other ten rows are read off the gridlines, one every ten points.
  - The two series are named over the top row's dots instead of in a legend, and each tick carries its unit, so the axis needs no title.
  - The axis runs 0 to 60. The reference anchors the floor at zero for positive data (scripts/verify-dumbbell.py resolve_domain agrees)
    and "rounds ceil up past hi"; its ladder (1, 2, 2.5, 5, 10) would end this axis at 100 and leave the right half of the plot empty,
    so it ends at the next ten above the largest share instead.
  - The connector is ink at 0.60. The reference's 0.55 clears 3:1 under its own ink; under AA's lighter slate it measures 2.83:1 and
    0.60 measures 3.18:1. check_claims() holds the connector and both dot strokes to 3:1 with the plugin's own contrast functions.
  - The connector stops at the hollow dot's ring instead of running under it: on the animated page it comes in with AA share, after the
    hollow dots, so it paints over them.
  - Pairs closer than the verifier's MIN_GAP_PX (16) overlap and nothing marks them: the solid dot sits on its ring, which reads as AA
    share at fair share, and check_claims() asserts those rows are within half a point of it, or are one of the two callout rows, whose
    values print on either side of the pair.
  - When the top row's two dots sit that close, the series' names over them could run into each other, so the one over the left-hand dot
    ends at it and the one over the right-hand dot starts at it.

The animated page is the same figure in steps for the /present deck. The title, the agencies' names and the axis show on arrival; then
one thing a press: fair share's dots, the note under the chart (why fair share barely moves, and where the seat shares come from), AA
share's dots with their connectors, and a callout for each agency that carries the story, the top row and then the bottom row, each with
its two values and a few words. In the deck the newest note leads and the earlier ones recede (aa.EMBED_CSS), while AA share's values keep
the accent of AA share's dots (data-keep). The static page shows it all at once.

Every number comes from deck_facts.py: the four values printed are agency_q3_* facts (the metric view's definitions written out in SQL),
and this file's own query orders the rows by the same definitions. check_claims() asserts on every build what the figure says about the
data. The note's reason is shown on the data: the routes' own seat shares are far apart (in Q3 2026 they run from under a fifth of the
seats to all of them, a wider spread than AA share's), every agency sells the same twelve routes and puts a part of its sales on each
that stays inside one band for every agency (BANDS), and mixing the same routes in those similar proportions brings every agency's fair
share within a tenth of AA share's spread. With the real seat shares the bands alone no longer guarantee that: some split inside them
could put fair share anywhere in a range wider than a fifth of AA share's spread (check_claims() says how wide, and asserts that every
agency sits inside it), so the closeness rests on the agencies' actual splits, which is what the note says. The note's second line is
the seats row's own words (deck_facts.SEATS_ARE): every seat share is T-100 data, one a route and month, and August and September 2026,
which the DOT has not published, repeat the same months of 2025. The callouts' agencies are the furthest above and below fair share.
"""
from __future__ import annotations

import aa
from deck_facts import AGENCIES, SEATS_ARE, display, fact, query

VW, VH = 1280, 720
L, R = 224, 1016              # the plot: value FLOOR sits at L, CEIL at R, 13.2px a point
FLOOR, CEIL, STEP = 0, 60, 10
ROW0, PITCH = 188, 30         # the first row's centre, and the pitch of a row
RADIUS = 6                    # the reference's dot
RING = RADIUS + 0.75          # the hollow dot's outer edge: its 1.5px stroke straddles the circle
CONNECTOR = 0.60              # ink opacity of the hairline between the two dots; see the docstring
INK_A = lambda a: f"rgba(54,73,90,{a})"  # noqa: E731
NAME_SIZE, LABEL_SIZE, TICK_SIZE, VALUE_SIZE, NOTE_SIZE, SEATS_SIZE, SOURCE_SIZE = 14, 12, 12, 13, 14, 15, 11
EM, EM_MONO = 0.5, 0.6        # Inter's advance per character, a little over what a browser measures, and Geist Mono's
SEATS_Y, SEATS_LEADING = 596, 22  # the note under the chart, two lines: why fair share barely moves, and where the seat shares come from
SOURCE_Y = 662                # the source line, the last on the stage
# The part of an agency's Q3 sales each route takes, in percent, for a route that starts at an AA hub (True) and for one that does not: one
# band for every agency, which is what "in similar proportions" means here. check_claims() holds every agency to it.
BANDS = {True: (7, 14), False: (2.5, 5.5)}
PROJECTED = (8, 9)            # the months of Q3 2026 the DOT has not published, whose seats repeat the same months of 2025
NUMBER_WORDS = ("zero", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine", "ten", "eleven", "twelve")
MONTH_NAMES = ("January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December")
SLUG = {name: slug for slug, name in AGENCIES}
dumbbell = aa.load("verify_dumbbell", "verify-dumbbell.py")  # the plugin's own domain and contrast functions

TITLE, EYEBROW = "AA share against fair share, Q3 2026", "fairshare · the data"
SUBTITLE = "One row per agency, all its routes together."  # on arrival
# the subtitle's second sentence, which comes in with AA share's dots: on arrival it would name the two agencies the callouts are about
ORDER = "The rows run from furthest above fair share to furthest below."
VERDICT = ("Furthest above fair share", "Furthest below fair share")  # the callouts' words, for the top row and the bottom row
SOURCE = "AA share and fair share for each agency, Jul to Sep 2026 · gold.fact_agency_sales_monthly, gold.fact_market_capacity"


def text(x, y, s, *, size=12, weight=400, fill=aa.INK, mono=False, anchor="start", attrs=""):
    """One line of text; attrs, when given, starts with a space."""
    return (f'<text x="{x}" y="{y}" fill="{fill}" font-size="{size}" font-weight="{weight}" font-family="{aa.MONO if mono else aa.SANS}" '
            f'text-anchor="{anchor}"{attrs}>{aa.esc(s)}</text>')


def width(s: str, size: float, mono: bool = False) -> float:
    """A line's width, from its advance per character: exact for Geist Mono, a little over for Inter."""
    return len(s) * size * (EM_MONO if mono else EM)


def x_of(v: float) -> int:
    """A value's x, rounded to the nearest pixel as the reference rounds endpoints; never snapped to the 4px grid, because that moves the data."""
    return round(L + (v - FLOOR) / (CEIL - FLOOR) * (R - L))


def series_names(column_x: int, fair_x: int, aa_x: int) -> dict[str, tuple]:
    """Where each series' name sits over the top row, as (x, anchor) for text(): fair share's over the column its dots make and AA share's
    over the top row's solid dot, both centred, while the two have room; when they would run into each other (the top row's dots sit close),
    the name over the left-hand dot ends at it and the one over the right-hand dot starts at it."""
    half = {key: width(words, LABEL_SIZE, mono=True) / 2 for key, words in (("fair", "Fair share"), ("aa", "AA share"))}
    if abs(aa_x - column_x) >= half["fair"] + half["aa"] + 8:
        return {"fair": (column_x, "middle"), "aa": (aa_x, "middle")}
    left, right = ("fair", "aa") if fair_x <= aa_x else ("aa", "fair")
    at = {"fair": fair_x, "aa": aa_x}
    return {left: (at[left], "end"), right: (at[right], "start")}


def because() -> str:
    """Why fair share barely moves from agency to agency, which check_claims() shows on the data on every build."""
    return f"because each one spreads its sales over the same {NUMBER_WORDS[fact('routes')]} routes in similar proportions"


def seats_note() -> tuple[str, str]:
    """The note under the chart, one step of its own, a sentence a line: why fair share barely moves, and where the seat shares come from,
    in the seats row's own words."""
    return f"Fair share is nearly the same for every agency {because()}.", SEATS_ARE


# ---------------------------------------------------------------- the data

def load():
    """Every agency's AA share and fair share in Q3 2026, all routes together (the metric view's definitions written out), and the routes it
    sold, sorted by the gap, biggest first; each route's seat shares in Q3, lowest and highest, with how many of its months are T-100 rows,
    how many the DOT has not published yet and how many of those repeat the same month of 2025; and the part of each agency's Q3 sales each
    route takes. These exact values order the rows; the facts print them."""
    rows = query("""
        SELECT a.agency_name AS name, COUNT(DISTINCT s.market_id) AS routes,
               100 * SUM(s.aa_revenue) / NULLIF(SUM(s.market_revenue), 0) AS aa,
               100 * SUM(s.market_revenue * c.aa_seat_share) / NULLIF(SUM(s.market_revenue), 0) AS fair
        FROM aa_demo.gold.fact_agency_sales_monthly s
        JOIN aa_demo.gold.dim_agency a ON a.agency_id = s.agency_id
        JOIN aa_demo.gold.fact_market_capacity c ON c.market_id = s.market_id AND c.sales_month = s.sales_month
        WHERE s.sales_month BETWEEN DATE '2026-07-01' AND DATE '2026-09-01'
        GROUP BY a.agency_name""")
    seats = query("""
        SELECT c.market_id, m.aa_hub_origin AS hub, COUNT(*) AS months, COUNT(*) FILTER (WHERE c.source = 't100') AS t100,
               STRING_AGG(CAST(EXTRACT(MONTH FROM c.sales_month) AS VARCHAR), ',' ORDER BY c.sales_month) FILTER (WHERE c.is_projected) AS projected,
               COUNT(*) FILTER (WHERE c.is_projected AND c.aa_seats = p.aa_seats AND c.total_seats = p.total_seats
                                AND c.aa_seat_share = p.aa_seat_share) AS repeats,
               100 * MIN(c.aa_seat_share) AS lo, 100 * MAX(c.aa_seat_share) AS hi
        FROM aa_demo.gold.fact_market_capacity c
        JOIN aa_demo.gold.dim_market m ON m.market_id = c.market_id
        LEFT JOIN aa_demo.gold.fact_market_capacity p ON p.market_id = c.market_id
         AND EXTRACT(YEAR FROM p.sales_month) = 2025 AND EXTRACT(MONTH FROM p.sales_month) = EXTRACT(MONTH FROM c.sales_month)
        WHERE c.sales_month BETWEEN DATE '2026-07-01' AND DATE '2026-09-01'
        GROUP BY c.market_id, m.aa_hub_origin""")
    mix = query("""
        SELECT a.agency_name AS name, s.market_id, m.aa_hub_origin AS hub,
               100 * SUM(s.market_revenue) / SUM(SUM(s.market_revenue)) OVER (PARTITION BY a.agency_name) AS pct
        FROM aa_demo.gold.fact_agency_sales_monthly s
        JOIN aa_demo.gold.dim_agency a ON a.agency_id = s.agency_id
        JOIN aa_demo.gold.dim_market m ON m.market_id = s.market_id
        WHERE s.sales_month BETWEEN DATE '2026-07-01' AND DATE '2026-09-01'
        GROUP BY a.agency_name, s.market_id, m.aa_hub_origin""")
    for r in rows:
        r["aa_printed"], r["fair_printed"] = fact(f"agency_q3_aa_share_{SLUG[r['name']]}"), fact(f"agency_q3_fair_share_{SLUG[r['name']]}")
    return sorted(rows, key=lambda r: r["aa"] - r["fair"], reverse=True), seats, mix


def fair_window(seats) -> tuple[float, float]:
    """The lowest and the highest fair share any agency could have with its Q3 sales split inside BANDS: the most room the bands leave fair
    share. Fair share is the seat shares weighted by the split, so the low end takes every route at its lowest month and fills the routes with
    the lowest seat shares to the top of their bands first, and the high end the other way round; for limits like these that is exact."""
    ends = []
    for side, highest_first in (("lo", False), ("hi", True)):
        part = {s["market_id"]: BANDS[s["hub"]][0] for s in seats}
        left = 100 - sum(part.values())
        for s in sorted(seats, key=lambda s: s[side], reverse=highest_first):
            more = min(BANDS[s["hub"]][1] - part[s["market_id"]], left)
            part[s["market_id"]] += more
            left -= more
        assert abs(left) < 1e-9, "the bands must hold all of an agency's sales"
        ends.append(sum(part[s["market_id"]] * s[side] for s in seats) / 100)
    return ends[0], ends[1]


def check_claims(rows, seats, mix) -> None:
    """What the figure says about the data, checked on every build so a rebuilt lakehouse cannot quietly change the story."""
    assert len(rows) == fact("agencies") and {r["name"] for r in rows} == set(SLUG), "one row for each of the agencies deck_facts names"
    # the note's first line: "nearly the same for every agency because each one spreads its sales over the same twelve routes in similar proportions"
    assert {r["routes"] for r in rows} == {fact("routes")}, "every agency should sell all the routes in Q3: 'the same twelve routes'"
    for m in mix:
        lo, hi = BANDS[m["hub"]]
        assert lo <= m["pct"] <= hi, (f"{m['name']} puts {m['pct']:.2f}% of its Q3 sales on route {m['market_id']}, outside the {lo}% to {hi}% every agency "
                                      f"should stay inside on a route that {'starts' if m['hub'] else 'does not start'} at an AA hub: 'in similar proportions'")
    fair, aa_share = [r["fair_printed"] for r in rows], [r["aa_printed"] for r in rows]
    spread = max(aa_share) - min(aa_share)
    routes_lo, routes_hi = min(s["lo"] for s in seats), max(s["hi"] for s in seats)
    assert routes_hi - routes_lo > spread, (f"the routes' own seat shares in Q3 run from {routes_lo:.1f}% to {routes_hi:.1f}%, which should be wider apart "
                                            f"than AA share's spread of {spread:.1f} points: fair share is close because of the mix, not because the routes are alike")
    assert max(fair) - min(fair) < spread / 10, "fair share should move less than a tenth as much as AA share: 'nearly the same'"
    # with the real seat shares the bands alone no longer cap fair share that tightly: a split inside them could land anywhere from low to high,
    # wider than a fifth of AA share's spread. Every agency's actual split puts it inside that range and, as asserted above, much closer together.
    low, high = fair_window(seats)
    assert low <= min(fair) and max(fair) <= high and high - low > spread / 5, \
        (f"a split inside the bands allows fair share from {low:.2f} to {high:.2f}; every agency should sit inside that, and the range should still be "
         f"wider than a fifth of AA share's spread, or the docstring's account of what the bands prove is out of date")
    # the note's second line, the seats row's words: "real T-100 data, and August and September 2026 repeat the same months of 2025"
    assert len(seats) == fact("routes") and all(s["t100"] == s["months"] == 3 for s in seats), \
        "every route should have a seat share for each of Q3's three months, and every one of them should be a T-100 row: 'real T-100 data'"
    assert all(s["projected"] == ",".join(map(str, PROJECTED)) and s["repeats"] == len(PROJECTED) for s in seats), \
        "on every route August and September 2026 should be the projected months, each with the same seats as that month of 2025: 'repeat the same months of 2025'"
    assert SEATS_ARE.startswith("The seat shares are real T-100 data, and August and September 2026 repeat") and [MONTH_NAMES[m - 1] for m in PROJECTED] == ["August", "September"], \
        "the sentence names the projected months"
    for r in rows:  # the facts and this file's own query are two statements of one definition
        assert abs(r["aa_printed"] - r["aa"]) <= 0.05 + 1e-9 and abs(r["fair_printed"] - r["fair"]) <= 0.05 + 1e-9, f"{r['name']}: a fact differs from the query"
    assert abs(sum(r["aa"] for r in rows) / len(rows) - fact("avg_of_shares_q3")) <= 0.05 + 1e-9, "the twelve AA shares should average to the Q3 fact the deck already says"
    order = [r["name"] for r in sorted(rows, key=lambda r: r["aa_printed"] - r["fair_printed"], reverse=True)]
    assert order == [r["name"] for r in rows], "the printed numbers should give the same row order as the exact ones"
    # the callouts: the top row is the furthest above fair share and the bottom row the furthest below it
    assert rows[0]["aa"] - rows[0]["fair"] > 0 > rows[-1]["aa"] - rows[-1]["fair"], "the top row is above fair share and the bottom row below it"
    # the axis and the marks
    values = fair + aa_share
    assert FLOOR == dumbbell.resolve_domain(values)[0], "positive data anchors the axis at zero"
    assert CEIL >= max(values) and (CEIL - FLOOR) % STEP == 0, "the axis ends on a gridline above the largest value"
    for what, color, alpha in (("connector", aa.INK, CONNECTOR), ("solid dot stroke", aa.INK, 1.0), ("hollow dot stroke", aa.MUTED, 1.0)):
        ratio = dumbbell.contrast(dumbbell.composite(color, alpha, aa.PAPER), aa.PAPER)
        assert ratio >= dumbbell.WCAG_NON_TEXT, f"the {what} should clear 3:1 on paper, and it measures {ratio:.2f}:1"
    close = [r for r in rows if abs(x_of(r["aa_printed"]) - x_of(r["fair_printed"])) < dumbbell.MIN_GAP_PX]
    called_out = {rows[0]["name"], rows[-1]["name"]}  # the callout rows print both values beside the pair
    assert all(abs(r["aa_printed"] - r["fair_printed"]) <= 0.5 or r["name"] in called_out for r in close), \
        "a solid dot on its ring reads as AA share at fair share, so those rows must be, unless a callout prints the two values beside them"


# ---------------------------------------------------------------- the figure

def build(rows, motion=False) -> str:
    """The figure. With motion, fair share's dots, the sentence, AA share's dots and the two callouts are the steps, one a press, and the
    sentence and the callouts recede once the next press comes; without it, the same marks, all at once."""
    step = lambda n, label, marks, recede=False: aa.motion_item(n, label, marks, recede) if motion else "\n        ".join(marks)  # noqa: E731
    ys = [ROW0 + i * PITCH for i in range(len(rows))]
    top, base = ROW0 - 16, ys[-1] + 16  # the gridlines run from just over the first row to just under the last
    out = [f'<rect width="100%" height="100%" fill="{aa.PAPER}"/>', aa.brand(tag="fairshare · synthetic data")]
    # what the chart is about, inside the image because a slide takes the SVG alone; how its rows run comes in with AA share, on the same line
    out.append(text(40, 100, TITLE, size=16, weight=600, attrs=" data-title"))  # the slide's title, since the deck draws none over a figure
    out.append(text(40, 120, SUBTITLE, mono=True, fill=aa.MUTED))
    order = text(40 + width(SUBTITLE + " ", 12, mono=True), 120, ORDER, mono=True, fill=aa.MUTED)
    assert 40 + width(f"{SUBTITLE} {ORDER}", 12, mono=True) <= VW - 40, "the subtitle runs off the page"
    # the axis: a gridline at every step, the axis line in place of the one at the floor, and each tick with its unit
    for v in range(FLOOR, CEIL + 1, STEP):
        if v == FLOOR:
            out.append(f'<line x1="{x_of(v)}" y1="{top - 4}" x2="{x_of(v)}" y2="{base + 4}" stroke="{INK_A(0.25)}" stroke-width="1" data-grid="{v}"/>')
        else:
            out.append(f'<line x1="{x_of(v)}" y1="{top}" x2="{x_of(v)}" y2="{base}" stroke="{INK_A(0.08)}" stroke-width="0.8" data-grid="{v}"/>')
        out.append(text(x_of(v), base + 22, f"{v}%", size=TICK_SIZE, fill=aa.MUTED, mono=True, anchor="middle", attrs=f' data-tick="{v}"'))
    # the agencies, one name a row: structure, so they show on arrival
    for y, r in zip(ys, rows):
        out.append(text(L - 16, y + 5, r["name"], size=NAME_SIZE, anchor="end", attrs=f' data-row-label="{r["name"]}"'))
    label_y = ROW0 - 24  # each series' name, over the top row's dot
    assert label_y - LABEL_SIZE > 120 + aa.TEXT_DESCENT * 12 + 8 and label_y + aa.TEXT_DESCENT * LABEL_SIZE < top, "the series' names sit between the subtitle and the plot"
    xf = [x_of(r["fair_printed"]) for r in rows]
    names = series_names(round(sum(xf) / len(xf)), x_of(rows[0]["fair_printed"]), x_of(rows[0]["aa_printed"]))
    # step 1: fair share for every agency, the hollow dots, named over the column they make
    fair = [text(names["fair"][0], label_y, "Fair share", size=LABEL_SIZE, weight=500, fill=aa.MUTED, mono=True, anchor=names["fair"][1], attrs=' data-label="fair"')]
    fair += [f'<circle data-agency="{r["name"]}" data-series="fair" data-value="{r["fair_printed"]}" cx="{x}" cy="{y}" r="{RADIUS}" '
             f'fill="{aa.PAPER}" stroke="{aa.MUTED}" stroke-width="1.5"/>' for x, y, r in zip(xf, ys, rows)]
    low, high = (display(f"agency_q3_fair_share_{SLUG[r['name']]}") for r in (min(rows, key=lambda r: r["fair_printed"]), max(rows, key=lambda r: r["fair_printed"])))
    out.append(step(1, f"Fair share for each agency, the hollow dots, all between {low} and {high}.", fair))
    # step 2: why fair share barely moves, and where the seat shares come from; under the chart, a note that leads on its press
    note = seats_note()
    assert all(40 + width(line, SEATS_SIZE) <= VW - 40 for line in note), "the note runs off the page"
    assert SEATS_Y - SEATS_SIZE > base + 22 + aa.TEXT_DESCENT * TICK_SIZE + 16 \
        and SEATS_Y + (len(note) - 1) * SEATS_LEADING + aa.TEXT_DESCENT * SEATS_SIZE < SOURCE_Y - SOURCE_SIZE - 16, "the note runs into the ticks or the source line"
    out.append(step(2, " ".join(note), [text(40, SEATS_Y + k * SEATS_LEADING, line, size=SEATS_SIZE, fill=aa.MUTED, attrs=' data-note="seats"')
                                        for k, line in enumerate(note)], recede=True))
    # step 3: AA share for every agency, the solid dots in the accent, each joined to its ring by the connector, which stops at the ring
    # because the ring is already drawn; a pair that overlaps gets no connector. The subtitle's line on how the rows run comes in with them.
    solid = [text(names["aa"][0], label_y, "AA share", size=LABEL_SIZE, weight=600, fill=aa.ACCENT, mono=True, anchor=names["aa"][1], attrs=' data-label="aa"'),
             order]
    for y, r in zip(ys, rows):
        xs, x0 = x_of(r["aa_printed"]), x_of(r["fair_printed"])
        sign = 1 if xs > x0 else -1
        if (xs - (x0 + sign * RING)) * sign > RADIUS:
            solid.append(f'<line data-agency="{r["name"]}" x1="{x0 + sign * RING:g}" y1="{y}" x2="{xs}" y2="{y}" stroke="{INK_A(CONNECTOR)}" stroke-width="1"/>')
    solid += [f'<circle data-agency="{r["name"]}" data-series="aa" data-value="{r["aa_printed"]}" cx="{x_of(r["aa_printed"])}" cy="{y}" r="{RADIUS}" '
              f'fill="{aa.ACCENT}" stroke="{aa.INK}" stroke-width="1"/>' for y, r in zip(ys, rows)]
    lo, hi = min(rows, key=lambda r: r["aa_printed"]), max(rows, key=lambda r: r["aa_printed"])
    out.append(step(3, f"AA share for each agency, the solid dots, from {display('agency_q3_aa_share_' + SLUG[lo['name']])} to "
                       f"{display('agency_q3_aa_share_' + SLUG[hi['name']])}. {ORDER}", solid))
    # steps 4 and 5: the two agencies that carry the story, the top row and then the bottom row. Each callout prints the row's two values
    # outside the pair, placed by geometry as the reference places them, and says where the row stands after the right-hand one, on a
    # paper patch so the gridline under the words does not show through. AA share's value keeps the accent in the deck (data-keep); the
    # rest of the callout is a note, which leads while it is the newest and recedes after.
    for k, (i, verdict) in enumerate(((0, VERDICT[0]), (len(rows) - 1, VERDICT[1]))):
        r, y = rows[i], ys[i]
        name, slug = r["name"], SLUG[r["name"]]
        (left, lx), (right, rx) = sorted((("aa", x_of(r["aa_printed"])), ("fair", x_of(r["fair_printed"]))), key=lambda end: end[1])
        shown = {series: display(f"agency_q3_{series}_share_{slug}") for series in ("aa", "fair")}
        assert lx - 12 - width(shown[left], VALUE_SIZE, mono=True) > L + 4, f"{name}: the left-hand value runs into the axis"
        marks = []
        for series, x, anchor in ((left, lx - 12, "end"), (right, rx + 12, "start")):
            accent = series == "aa"
            attrs = (f' data-agency="{name}" data-series="{series}" data-fact="agency_q3_{series}_share_{slug}" data-callout="{name}"'
                     + (" data-keep" if accent else ""))
            marks.append(text(x, y + 5, shown[series], size=VALUE_SIZE, weight=600 if accent else 400, fill=aa.ACCENT if accent else aa.MUTED,
                              mono=True, anchor=anchor, attrs=attrs))
        vx, vw = round(rx + 12 + width(shown[right], VALUE_SIZE, mono=True) + 16), width(verdict, NOTE_SIZE)
        assert vx + vw <= VW - 40, f"{name}: the callout's words run off the page"
        marks.append(f'<rect x="{vx - 6}" y="{y - 10}" width="{vw + 12:g}" height="20" fill="{aa.PAPER}"/>')
        marks.append(text(vx, y + 5, verdict, size=NOTE_SIZE, fill=aa.MUTED, attrs=f' data-note="{"above" if k == 0 else "below"}" data-callout="{name}"'))
        out.append(step(4 + k, f"{name}, AA share {display('agency_q3_aa_share_' + slug)} against a fair share of {display('agency_q3_fair_share_' + slug)}, "
                               f"{verdict[0].lower() + verdict[1:]}.", marks, recede=True))
    # where the numbers come from: the smallest text, in grey, last
    assert SOURCE_Y + aa.TEXT_DESCENT * SOURCE_SIZE <= aa.STAGE_BOTTOM and 60 + width(SOURCE, SOURCE_SIZE, mono=True) <= VW - 40, "the source line leaves the stage"
    out.append(aa.icon("databricks", 40, SOURCE_Y - 11, 14, aa.MUTED))
    out.append(text(60, SOURCE_Y, SOURCE, size=SOURCE_SIZE, mono=True, fill=aa.MUTED))
    return "\n        ".join(out)


def desc(rows) -> str:
    top, bottom = rows[0], rows[-1]
    keys = [f"agency_q3_fair_share_{SLUG[r['name']]}" for r in rows]
    low, high = min(keys, key=fact), max(keys, key=fact)  # the two ends of the fair share column
    pair = lambda r: f"{display('agency_q3_aa_share_' + SLUG[r['name']])} against {display('agency_q3_fair_share_' + SLUG[r['name']])}"  # noqa: E731
    return (f"Dumbbell chart of {NUMBER_WORDS[fact('agencies')]} agencies' AA share against fair share in Q3 2026, on all routes together, the rows "
            f"running from furthest above fair share to furthest below: {top['name']} at {pair(top)}, {bottom['name']} at {pair(bottom)}. Fair share stays "
            f"between {display(low)} and {display(high)} for every agency {because()}. {SEATS_ARE}")


if __name__ == "__main__":
    data, seat_rows, mix_rows = load()
    check_claims(data, seat_rows, mix_rows)
    common = dict(title=TITLE, desc=desc(data), eyebrow=EYEBROW, vw=VW, vh=VH)
    (aa.OUT / "12-share-vs-fair.html").write_text(aa.page(slug="12-share-vs-fair", body=build(data), **common), encoding="utf-8")
    html = aa.animated(slug="12-share-vs-fair-animated", body=build(data, motion=True), steps=5, css=aa.FADE_ONLY, **common)
    (aa.OUT / "12-share-vs-fair-animated.html").write_text(html, encoding="utf-8")
    print("wrote 12-share-vs-fair.html and 12-share-vs-fair-animated.html")
