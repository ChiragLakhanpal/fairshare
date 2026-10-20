"""14: What I planted in the data, and what cleaning did. Six panels in a 3 by 2 grid, each a title, its numbers and a verdict line.

    .venv/bin/python docs/diagrams/src/planted.py   # writes docs/diagrams/14-what-was-planted.html

Four traps the pipeline handles (channel spellings, tickets loaded twice, Sunbelt's missing months, Northstar's zero) and two drops
(Harbor's share, two corporates), one panel each, read left to right and top to bottom. The two drops are planted in
data/make_data.py (its docstring, lines 16 and 17, for the corporates). Harbor is the app's to catch and it does; no single corporate
is flagged yet, and the sixth verdict says so.

diagram-design has no six-panel type, so this follows its summary card pattern (references/layout-budget.md: a white card, a 1px
hairline, a 6px radius, no shadow, varied content) with the line chart grammar (references/type-line.md) for the two small charts:
the focal series in the accent, the other muted, direct labels, dots only where a number is printed. Accent marks two things: Sunbelt's
empty months, as it does in figures 10 and 11, and Harbor's AA share line. The verdict sits on a paper-2 band at the foot of the card.

Every number comes from deck_facts.py (the stored display strings) or from this file's own queries on the same lakehouse, which
supply the shapes: the months, the series and the names. check_claims() asserts on every build what each panel says about the data,
and check_app() asserts what the verdicts say about the app, by running the app's own home page query on the same build.
"""
from __future__ import annotations

from datetime import date

import aa
from deck_facts import MONTHS, display, fact, query

VW, VH = 1280, 720
PX, PY = (40, 448, 856), (140, 404)    # panel origins: three columns, two rows
PW, PH, PAD = 384, 248, 20             # panel size, and the padding inside it
BAND = 64                              # the verdict band at the foot of a panel
PLANTED = (104, 108)                   # the two corporates planted to slip: data/make_data.py, docstring lines 16 and 17
LOW_KEYS = ("northwind_low_usd", "coastal_low_usd")  # the fact for the lowest month of each, in the order of PLANTED
INK_A = lambda a: f"rgba(54,73,90,{a})"  # noqa: E731
NUMBER_WORDS = ("zero", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine", "ten", "eleven", "twelve")
TITLE = "What I planted, and what cleaning did"
HARBOR_POINTS = (("harbor_share_sep25", date(2025, 9, 1)), ("harbor_share_jun26", date(2026, 6, 1)), ("harbor_share_sep26", date(2026, 9, 1)))


def text(x, y, s, *, size=12, weight=400, fill=aa.INK, mono=False, anchor="start", italic=False, extra=""):
    extra += ' font-style="italic"' if italic else ""
    return (f'<text x="{x}" y="{y}" fill="{fill}" font-size="{size}" font-weight="{weight}" font-family="{aa.MONO if mono else aa.SANS}" '
            f'text-anchor="{anchor}"{extra}>{aa.esc(s)}</text>')


def big(x, y, s, fill=aa.INK):
    """A number that is the point of its panel."""
    return text(x, y, s, size=36, weight=600, fill=fill)


def note(x, y, s, fill=aa.MUTED, anchor="start", size=12):
    """What a number or a line is, in the mono voice."""
    return text(x, y, s, size=size, fill=fill, mono=True, anchor=anchor)


def month_name(d: date) -> str:
    """A month the way deck_facts writes it: Jun 2026."""
    return f"{MONTHS[d.month - 1]} {d.year}"


def span(months) -> str:
    """Two months of one year: Mar and Apr 2026."""
    assert len(months) == 2 and months[0].year == months[1].year, "the sentence is written for two months of one year"
    return f"{MONTHS[months[0].month - 1]} and {MONTHS[months[1].month - 1]} {months[0].year}"


# ---------------------------------------------------------------- the data

def missing_months(d: dict) -> list[date]:
    """The months of the newest year in the data that Sunbelt Vacations has no rows for."""
    return [m for m in d["months"] if m.year == d["months"][-1].year and m not in d["sunbelt_present"]]


def load() -> dict:
    """The shapes the panels draw: names, months and series. The numbers they print are facts."""
    d: dict = {}
    d["spellings"] = query("SELECT channel, COUNT(*) AS n FROM aa_demo.bronze.fact_corporate_bookings GROUP BY channel ORDER BY n DESC, channel")
    d["cleaned"] = [r["channel"] for r in query("SELECT DISTINCT channel FROM aa_demo.silver.fact_corporate_bookings ORDER BY channel")]
    d["tickets"] = query("""
        SELECT (SELECT COUNT(*) FROM aa_demo.bronze.fact_corporate_bookings) AS bronze_rows,
               (SELECT COUNT(DISTINCT ticket_number) FROM aa_demo.bronze.fact_corporate_bookings) AS bronze_tickets,
               (SELECT COUNT(*) FROM aa_demo.silver.fact_corporate_bookings) AS silver_rows,
               (SELECT COUNT(*) FROM aa_demo.silver.fact_corporate_bookings s
                  JOIN (SELECT ticket_number, MIN(CAST(booking_id AS BIGINT)) AS first_id
                        FROM aa_demo.bronze.fact_corporate_bookings GROUP BY ticket_number) b
                    ON b.ticket_number = s.ticket_number AND b.first_id = s.booking_id) AS silver_first_copies,
               (SELECT COUNT(*) FROM (SELECT ticket_number FROM aa_demo.bronze.fact_corporate_bookings
                                      GROUP BY ticket_number HAVING COUNT(*) > 1) AS t) AS repeated,
               (SELECT MAX(c) FROM (SELECT COUNT(*) AS c FROM aa_demo.bronze.fact_corporate_bookings GROUP BY ticket_number) AS t) AS most_copies""")[0]
    d["months"] = [r["sales_month"] for r in query("SELECT DISTINCT sales_month FROM aa_demo.gold.fact_agency_sales_monthly ORDER BY sales_month")]
    d["sunbelt_present"] = {r["sales_month"] for r in query("""
        SELECT DISTINCT s.sales_month FROM aa_demo.gold.fact_agency_sales_monthly s
        JOIN aa_demo.gold.dim_agency a ON a.agency_id = s.agency_id WHERE a.agency_name = 'Sunbelt Vacations'""")}
    d["sunbelt_pace_months"] = query("""
        SELECT p.months_reported FROM aa_demo.gold.agency_pace p JOIN aa_demo.gold.dim_agency a ON a.agency_id = p.agency_id
        WHERE a.agency_name = 'Sunbelt Vacations' AND p.sales_month = DATE '2026-05-01'""")[0]["months_reported"]
    d["zero"] = query("""
        SELECT a.agency_name, s.sales_month, CONCAT(m.origin, '-', m.dest) AS route, s.aa_revenue, s.market_revenue
        FROM aa_demo.gold.fact_agency_sales_monthly s
        JOIN aa_demo.gold.dim_agency a ON a.agency_id = s.agency_id
        JOIN aa_demo.gold.dim_market m ON m.market_id = s.market_id
        WHERE s.aa_revenue = 0""")
    d["zero_rows"] = {layer: query(f"SELECT COUNT(*) AS n FROM aa_demo.{layer}.fact_agency_sales_monthly WHERE CAST(aa_revenue AS DOUBLE) = 0")[0]["n"]
                      for layer in ("bronze", "silver", "gold")}
    d["harbor"] = {r["sales_month"]: (r["aa"], r["fair"]) for r in query("""
        SELECT s.sales_month,
               100 * SUM(s.aa_revenue) / NULLIF(SUM(s.market_revenue), 0) AS aa,
               100 * SUM(s.market_revenue * c.aa_seat_share) / NULLIF(SUM(s.market_revenue), 0) AS fair
        FROM aa_demo.gold.fact_agency_sales_monthly s
        JOIN aa_demo.gold.dim_agency a ON a.agency_id = s.agency_id
        JOIN aa_demo.gold.fact_market_capacity c ON c.market_id = s.market_id AND c.sales_month = s.sales_month
        WHERE a.agency_name = 'Harbor Business Travel'
        GROUP BY s.sales_month ORDER BY s.sales_month""")}
    ids = ", ".join(str(i) for i in PLANTED)
    d["corporates"] = query(f"SELECT corp_id, corp_name, contract_end FROM aa_demo.gold.dim_corporate WHERE corp_id IN ({ids}) ORDER BY corp_id")
    d["all_corporates"] = [r["corp_name"] for r in query("SELECT corp_name FROM aa_demo.gold.dim_corporate")]
    bookings = query(f"""
        SELECT corp_id, DATE_TRUNC('month', booking_date) AS month, SUM(fare_usd * ticket_count) AS usd
        FROM aa_demo.gold.fact_corporate_bookings WHERE corp_id IN ({ids})
        GROUP BY corp_id, DATE_TRUNC('month', booking_date) ORDER BY corp_id, month""")
    for c in d["corporates"]:
        c["series"] = {r["month"]: r["usd"] for r in bookings if r["corp_id"] == c["corp_id"]}
        c["low_month"] = min(c["series"], key=c["series"].get)
    return d


def check_claims(d: dict) -> None:
    """What each panel says about the data, checked on every build so a rebuilt lakehouse cannot quietly change the story."""
    # 1 channel names: sixteen spellings of four labels, from the most common spelling to the rarest
    sp = d["spellings"]
    assert len(sp) == fact("channel_spellings_delivered") and len(d["cleaned"]) == fact("channel_spellings_cleaned"), "spellings delivered and cleaned"
    assert (sp[0]["channel"], sp[0]["n"]) == ("Direct", fact("channel_direct_rows")), "Direct is the most common spelling"
    assert (sp[-1]["channel"], sp[-1]["n"]) == (" ndc ", fact("channel_ndc_rows")) and sp[-1]["n"] != 1, "' ndc ' is the rarest spelling, and its count is plural"
    assert {r["channel"].strip().upper() for r in sp} == {c.upper() for c in d["cleaned"]}, "cleaning only trims and re-cases: the same four labels"
    # 2 tickets loaded twice: each repeated ticket sat on two rows, and silver keeps the first one loaded
    t = d["tickets"]
    assert t["repeated"] == fact("duplicate_tickets") and t["most_copies"] == 2, "each repeated ticket should be on exactly two rows"
    assert t["bronze_rows"] - t["silver_rows"] == fact("duplicate_tickets"), "silver should hold the delivered rows minus the repeats"
    assert t["silver_rows"] == t["bronze_tickets"] == t["silver_first_copies"], "silver keeps one row per ticket, the first one loaded"
    # 3 Sunbelt: no rows for two months of the newest year, pace counts the months it reported
    year = d["months"][-1].year
    missing = missing_months(d)
    assert [m.month for m in missing] == [3, 4] and all(m.year == 2026 for m in missing), "the facts name March and April 2026"
    assert d["sunbelt_pace_months"] == len([m for m in d["sunbelt_present"] if date(year, 1, 1) <= m <= date(year, 5, 1)]), \
        "pace in May counts the months Sunbelt reported through May, and not the two it did not"
    assert fact("sunbelt_pace_may26_before") < fact("sunbelt_pace_may26"), "the pace after the fix is higher than before"
    # 4 Northstar: one reported zero, on the route and month the facts name, with sales on other airlines, and cleaning kept it
    z = d["zero"]
    assert len(z) == 1 and z[0]["agency_name"] == "Northstar Leisure", "the only zero should be Northstar's"
    assert z[0]["route"] == fact("northstar_zero_route") and month_name(z[0]["sales_month"]) == display("northstar_zero_month"), "route and month of the zero"
    assert z[0]["aa_revenue"] == 0 == fact("northstar_zero_aa_usd") and round(z[0]["market_revenue"]) == fact("northstar_other_usd") > 0, \
        "the agency sold on other airlines that month and none on AA"
    assert d["zero_rows"] == {"bronze": 1, "silver": 1, "gold": 1}, "cleaning should keep the zero"
    # 5 Harbor: 21 months, the three printed points are the facts, and June 2026 is the lowest month
    h = d["harbor"]
    assert len(h) == fact("months") == len(d["months"]), "one point for each month"
    for key, month in HARBOR_POINTS:
        assert round(h[month][0], 1) == fact(key), f"{key} should be the AA share in that month"
    assert min(h, key=lambda m: h[m][0]) == HARBOR_POINTS[1][1], "the low point is June 2026"
    # 6 the corporates: the lowest month is the printed one, and the first one's contract ends in it
    for c, key in zip(d["corporates"], LOW_KEYS):
        assert round(c["series"][c["low_month"]]) == fact(key), f"{c['corp_name']}: the lowest month should be the fact"
    northwind, coastal = d["corporates"]
    assert (northwind["corp_name"], coastal["corp_name"]) == ("Northwind Logistics", "Coastal Media Group"), "corporates 104 and 108 by name"
    assert max(northwind["series"]) == northwind["low_month"] == date(northwind["contract_end"].year, northwind["contract_end"].month, 1), \
        "Northwind's last month is its lowest, and its contract ends in that month"
    assert northwind["series"][northwind["low_month"]] < min(v for m, v in northwind["series"].items() if m.year == 2025), "Northwind's low is under every month of 2025"
    assert date(2026, 3, 1) <= coastal["low_month"] <= date(2026, 7, 1), "Coastal's low is inside the planted window, March to July 2026"
    assert max(coastal["series"]) == d["months"][-1], "Coastal books in every month to the end of the data"


def check_app(d: dict) -> None:
    """The two verdicts about the app, checked against the app: its home page query for the newest month, the same one `python -m harness.signals` runs."""
    from harness import agents, facts, signals, summary  # the app's own code; only a build that checks these claims needs it
    month = agents.latest_month()
    facts.reset()
    lines = signals.build("All", month)
    harbor = [s for s in lines if s["agency"] == "Harbor Business Travel" and s["severity"] == "risk"]
    fell = round(fact("harbor_share_sep25") - fact("harbor_share_sep26"), 1)
    assert harbor and f"AA share fell {fell} points against last year" in harbor[0]["sentence"]["text"], "the home page should flag Harbor's drop as a risk"
    assert "marked On track in the CRM stand-in" in harbor[0]["sentence"]["text"], "and it flags it because the deal in the CRM stand-in is marked On track while share fell"
    named = [(s["sentence"]["text"], c) for s in lines for c in d["all_corporates"] if c in s["sentence"]["text"]]
    assert not named, f"no home page line should name a corporate: {named}"
    weekly = summary.weekly_block(f"{month}-01")[0]
    assert not {"corp_id", "corp_name"} & set(weekly.columns), "the corporate bookings line should only add every corporate up"


# ---------------------------------------------------------------- the panels

def frame(n: int, title: str, sub: str, lead: str, detail: list[str]) -> list[str]:
    """The card: a title and what it is about, then the verdict on a band at the foot. Returns the opening markup; the caller adds the body and closes the group."""
    x, y = PX[(n - 1) % 3], PY[(n - 1) // 3]
    by = y + PH - BAND
    out = [f'<g data-panel="{n}">',
           f'<rect x="{x}" y="{y}" width="{PW}" height="{PH}" rx="6" fill="{aa.PAPER}" stroke="{aa.RULE_SOLID}" stroke-width="1"/>',
           f'<path d="M {x + 1},{by} H {x + PW - 1} V {y + PH - 7} A 6 6 0 0 1 {x + PW - 7},{y + PH - 1} H {x + 7} A 6 6 0 0 1 {x + 1},{y + PH - 7} Z" fill="{aa.PAPER2}"/>',
           text(x + PAD, y + 32, title, size=16, weight=600),
           note(x + PAD, y + 50, sub, size=11),
           text(x + PAD, by + (26 if len(detail) == 1 else 21), lead, size=14, weight=600)]
    out += [text(x + PAD, by + (44 if len(detail) == 1 else 38) + 15 * i, line, fill=aa.MUTED) for i, line in enumerate(detail)]
    return out


def p1(d: dict) -> list[str]:
    x, y = PX[0], PY[0]
    most, least = d["spellings"][0], d["spellings"][-1]
    out = frame(1, "Channel names", "the channel on each corporate booking", "Cleaned in silver.", ["Letter case and extra spaces are ignored."])
    out += [big(x + PAD, y + 104, display("channel_spellings_delivered")), note(x + PAD, y + 122, "spellings delivered"),
            text(x + 176, y + 102, "→", size=28, fill=aa.MUTED, anchor="middle"),
            big(x + 204, y + 104, display("channel_spellings_cleaned")), note(x + 204, y + 122, "labels after cleaning"),
            note(x + PAD, y + 146, "the most common spelling, and the rarest", size=11)]
    for i, (spelling, rows) in enumerate(((most["channel"], display("channel_direct_rows")), (least["channel"], display("channel_ndc_rows")))):
        cx = x + PAD + i * 176
        out += [f'<rect x="{cx}" y="{y + 154}" width="168" height="24" rx="3" fill="{aa.PAPER}" stroke="{aa.RULE_SOLID}" stroke-width="1"/>',
                note(cx + 10, y + 170, f'"{spelling}"', fill=aa.INK), note(cx + 158, y + 170, f"{rows} rows", anchor="end")]
    return out + ["</g>"]


def p2(d: dict) -> list[str]:
    x, y = PX[1], PY[0]
    out = frame(2, "Tickets loaded twice", "corporate bookings, by ticket number", "Removed in silver.", ["Only the first copy of each ticket stays."])
    out += [big(x + PAD, y + 104, display("duplicate_tickets")), note(x + PAD, y + 122, "tickets"),
            big(x + 120, y + 104, display("duplicate_usd")), note(x + 120, y + 122, "in fares, counted twice"),
            text(x + PAD, y + 158, f"Each one sat on {NUMBER_WORDS[d['tickets']['most_copies']]} rows of the file.", fill=aa.INK)]
    return out + ["</g>"]


def p3(d: dict) -> list[str]:
    x, y = PX[2], PY[0]
    year = d["months"][-1].year
    months = [m for m in d["months"] if m.year == year]
    missing = missing_months(d)
    out = frame(3, "Sunbelt's missing months", f"Sunbelt Vacations: no rows for {span(missing)}", "Left missing.",
                ["Pace counts only the months it reported.", "The old rule counted a missing month as zero."])
    step = 36
    for i, m in enumerate(months):
        hole = m in missing
        stroke = f' stroke="{aa.ACCENT}" stroke-width="1.6"' if hole else ""
        out += [f'<rect x="{x + PAD + i * step}" y="{y + 62}" width="32" height="20" fill="{aa.PAPER}"/>',
                f'<rect data-month="{month_name(m)}" data-rows="{0 if hole else 1}" x="{x + PAD + i * step}" y="{y + 62}" width="32" height="20" rx="3" '
                f'fill="{INK_A(0.05 if hole else 0.2)}"{stroke}/>',
                note(x + PAD + i * step + 16, y + 96, MONTHS[m.month - 1], anchor="middle", size=11)]
    out += [note(x + PAD, y + 118, f"pace in May {year}, as a percent of the goal so far", size=11),
            big(x + PAD, y + 154, display("sunbelt_pace_may26_before"), fill=aa.MUTED), note(x + PAD, y + 172, "old rule", size=11),
            text(x + 120, y + 152, "→", size=28, fill=aa.MUTED, anchor="middle"),
            big(x + 148, y + 154, display("sunbelt_pace_may26")), note(x + 148, y + 172, "new rule", size=11)]
    return out + ["</g>"]


def p4(d: dict) -> list[str]:
    x, y = PX[0], PY[1]
    z = d["zero"][0]
    out = frame(4, "Northstar's zero", f"Northstar Leisure on {z['route']} in {month_name(z['sales_month'])}", "Kept, because it is a true zero.",
                ["A reported month with no AA sales is not a gap."])
    out += [big(x + PAD, y + 104, display("northstar_zero_aa_usd")), note(x + PAD, y + 122, "AA revenue"),
            big(x + 130, y + 104, display("northstar_other_usd")), note(x + 130, y + 122, "other airlines, same month"),
            text(x + PAD, y + 158, "The agency sold on the route that month, just none on AA.", fill=aa.INK)]
    return out + ["</g>"]


def p5(d: dict) -> list[str]:
    x, y = PX[1], PY[1]
    months = sorted(d["harbor"])
    left, right, top, base, ceil = x + PAD, x + 312, y + 68, y + 160, 60
    step = (right - left) / (len(months) - 1)
    px = lambda m: left + months.index(m) * step                          # noqa: E731
    py = lambda v: base - v / ceil * (base - top)                         # noqa: E731
    pts = lambda i: " ".join(f"{px(m):.1f},{py(d['harbor'][m][i]):.1f}" for m in months)  # noqa: E731
    out = frame(5, "Harbor's share", f"Harbor Business Travel, all {display('months')} months", "The app catches it.",
                ["The home page flags Harbor as a risk.", "Its deal in the CRM stand-in is marked On track."])
    out += [f'<line x1="{left}" y1="{base}" x2="{right}" y2="{base}" stroke="{INK_A(0.25)}" stroke-width="1"/>',
            f'<polyline data-series="fair" points="{pts(1)}" fill="none" stroke="{aa.MUTED}" stroke-width="1.4" stroke-linejoin="round"/>',
            f'<polyline data-series="aa" points="{pts(0)}" fill="none" stroke="{aa.ACCENT}" stroke-width="2.2" stroke-linejoin="round"/>']
    for key, month in HARBOR_POINTS:
        out.append(f'<circle data-month="{month_name(month)}" data-value="{fact(key)}" cx="{px(month):.1f}" cy="{py(d["harbor"][month][0]):.1f}" r="3.5" '
                   f'fill="{aa.ACCENT}" stroke="{aa.PAPER}" stroke-width="1.5"/>')
    (k1, m1), (k2, m2), (k3, m3) = HARBOR_POINTS
    out += [note(left, py(d["harbor"][months[0]][0]) - 8, "AA share", fill=aa.ACCENT, size=11),
            note(left, py(d["harbor"][months[0]][1]) + 16, "fair share", size=11),
            note(px(m1), py(d["harbor"][m1][0]) - 9, display(k1), fill=aa.ACCENT, anchor="middle", size=11),
            note(px(m2), py(d["harbor"][m2][0]) + 18, display(k2), fill=aa.ACCENT, anchor="middle", size=11),
            note(px(m3) + 9, py(d["harbor"][m3][0]) + 4, display(k3), fill=aa.ACCENT, size=11)]
    for m, anchor in ((months[0], "start"), (date(2026, 1, 1), "middle"), (months[-1], "end")):
        out.append(note({"start": left, "middle": px(m), "end": right}[anchor], base + 15, month_name(m), anchor=anchor, size=11))
    return out + ["</g>"]


def p6(d: dict) -> list[str]:
    x, y = PX[2], PY[1]
    months = d["months"]
    left, right, height = x + 184, x + 364, 44
    step = (right - left) / (len(months) - 1)
    top = max(v for c in d["corporates"] for v in c["series"].values())
    ceil = -(-top // 20_000) * 20_000                                        # the next $20K above the biggest month, one scale for both
    out = frame(6, "Two corporates slipping", "bookings per month, both on one scale from zero", "The app does not flag a single corporate yet.",
                ["It only watches the total of all corporate bookings."])
    for i, (c, low_key) in enumerate(zip(d["corporates"], LOW_KEYS)):
        base = y + 112 + i * 58
        px = lambda m: left + months.index(m) * step                         # noqa: E731
        py = lambda v: base - v / ceil * height                              # noqa: E731
        pts = " ".join(f"{px(m):.1f},{py(c['series'][m]):.1f}" for m in months if m in c["series"])
        low = c["low_month"]
        out += [text(x + PAD, base - 32, c["corp_name"], size=12, weight=600),
                note(x + PAD, base - 17, f"contract ends {month_name(c['contract_end'])}", size=11),
                note(x + PAD, base - 3, f"low {display(low_key)}, {month_name(low)}", fill=aa.INK, size=11),
                f'<line x1="{left}" y1="{base}" x2="{right}" y2="{base}" stroke="{INK_A(0.25)}" stroke-width="1"/>',
                f'<polyline data-corporate="{c["corp_name"]}" points="{pts}" fill="none" stroke="{aa.INK}" stroke-width="1.6" stroke-linejoin="round"/>',
                f'<circle data-corporate="{c["corp_name"]}" data-month="{month_name(low)}" cx="{px(low):.1f}" cy="{py(c["series"][low]):.1f}" r="3.5" fill="{aa.INK}" stroke="{aa.PAPER}" stroke-width="1.5"/>']
    return out + ["</g>"]


# ---------------------------------------------------------------- the figure

def build(d: dict) -> str:
    out = [f'<rect width="100%" height="100%" fill="{aa.PAPER}"/>', aa.brand(tag="fairshare · synthetic data")]
    traps, drops = (p1, p2, p3, p4), (p5, p6)  # four data traps the pipeline handles, then two drops the app is for
    subtitle = f"{NUMBER_WORDS[len(traps)].capitalize()} traps planted to test the cleaning, then {NUMBER_WORDS[len(drops)]} drops the app should catch."
    # what the figure is about, inside the image because a slide takes the SVG alone
    out += [text(40, 100, TITLE, size=16, weight=600), note(40, 120, subtitle, fill=aa.MUTED)]
    for panel in (*traps, *drops):
        out += panel(d)
    # where the numbers come from
    out.append(aa.icon("databricks", 40, 674, 16))
    out.append(note(64, 687, "bronze, silver and gold tables in aa_demo: corporate bookings, agency sales, pace and corporates", size=11))
    out.append(note(64, 705, "Harbor's fair share uses made-up seat shares, one per route; the T-100 loader (data/t100.py) has never run", size=11))
    return "\n        ".join(out)


def desc(d: dict) -> str:
    return (f"Six panels about what was planted in the synthetic data: {display('channel_spellings_delivered')} channel spellings cleaned to "
            f"{display('channel_spellings_cleaned')}, {display('duplicate_tickets')} tickets loaded twice and removed, Sunbelt's {NUMBER_WORDS[len(missing_months(d))]} missing months "
            f"left missing, Northstar's true zero kept, Harbor's falling AA share, which the app catches, and {NUMBER_WORDS[len(PLANTED)]} corporates whose bookings slip, "
            f"which the app does not flag.")


if __name__ == "__main__":
    data = load()
    check_claims(data)
    check_app(data)
    html = aa.page(slug="14-what-was-planted", title=TITLE, desc=desc(data), eyebrow="fairshare · the data", body=build(data), vw=VW, vh=VH)
    (aa.OUT / "14-what-was-planted.html").write_text(html, encoding="utf-8")
    print("wrote 14-what-was-planted.html")
