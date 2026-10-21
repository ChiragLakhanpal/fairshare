"""Every number the deck and the data figures print, each from one fixed query on the local lakehouse (opened read only).

    FAIRSHARE_BACKEND=duckdb .venv/bin/python docs/diagrams/src/deck_facts.py          # writes web/src/deck/facts.json
    FAIRSHARE_BACKEND=duckdb .venv/bin/python docs/diagrams/src/deck_facts.py --print  # every fact next to its SQL

FACTS     one row per number: (key, SQL that returns one row with a column `value`, format, grain in plain words).
DATED     numbers a local query cannot reproduce (a Databricks run, a results file), and the days of those runs; each keeps
          its source and date.
COLUMNS   the tables a slide shows: an example row, and what each column means in one plain sentence.
UNITS     the unit each example carries, so a slide never prints a bare 80582.47, 0.3805 or 2026-09-01.
CHECKS    sentences the data must keep true: (key, sentence, why it is checked, SQL that returns one value, the value it must return, the
          format a slide shows the value in).

Slides and notes write a number as a {key}; the deck fills it from facts.json. The figure builders call fact(key) for a value and
display(key) for the string a slide shows.
The data is deterministic (data/make_data.py, seed 88201), so a Databricks build returns the same values.
"""
from __future__ import annotations

import datetime
import decimal
import functools
import json
import math
import os
import sys
import textwrap
from pathlib import Path

os.environ["FAIRSHARE_BACKEND"] = "duckdb"  # the laptop's .env points at Databricks; these queries run on the local build
ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
import pandas as pd  # noqa: E402

from fairshare import db  # noqa: E402

OUT = ROOT / "web" / "src" / "deck" / "facts.json"


# ---------------------------------------------------------------- running a query

def _native(v):
    """A plain Python value for whatever pandas and numpy hand back: NULL is None, a DATE is a date."""
    if v is None or (not isinstance(v, (str, list, tuple, dict)) and pd.isna(v)):
        return None
    if isinstance(v, pd.Timestamp):
        return v.date() if v == v.normalize() else v.to_pydatetime()
    if isinstance(v, decimal.Decimal):
        return float(v)
    return v.item() if hasattr(v, "item") else v


def query(sql: str) -> list[dict]:
    """Run one SELECT through fairshare.db (DuckDB, read only) and return its rows as dicts. Three-part names: aa_demo.gold.table."""
    return [{c: _native(v) for c, v in row.items()} for row in db.query(sql).to_dict("records")]


def _json(v):
    """A JSON-native value: a date becomes its ISO string."""
    return v.isoformat() if isinstance(v, datetime.date) else v


# ---------------------------------------------------------------- formats: how a value is read from the query, and how it is shown

MONTHS = ("Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec")


def _whole(v, key):
    if isinstance(v, bool) or not isinstance(v, (int, float)) or v != int(v):
        raise ValueError(f"{key}: {v!r} is not a whole number; ROUND it in the SQL")
    return int(v)


def _places(n):
    def read(v, key):
        if isinstance(v, bool) or not isinstance(v, (int, float)) or round(v, n) != v:
            raise ValueError(f"{key}: {v!r} does not have {n} decimal places or fewer; ROUND it in the SQL")
        return float(v)
    return read


def _text(v, key):
    if not isinstance(v, str):
        raise ValueError(f"{key}: {v!r} is not text")
    return v


def _usd(v):
    return f"-${abs(v):,}" if v < 0 else f"${v:,}"


def _usd_cents(v):
    return f"-${abs(v):,.2f}" if v < 0 else f"${v:,.2f}"


def _usd_signed(v):
    return "$0" if v == 0 else f"+${v:,}" if v > 0 else f"-${abs(v):,}"


def _month(v):
    d = datetime.date.fromisoformat(v)
    return f"{MONTHS[d.month - 1]} {d.year}"


def _share(v):
    """A fraction of one as a percent with the decimals it has, to two places: 0.3805 is 38.05%, 0.42 is 42%."""
    return f"{v * 100:.2f}".rstrip("0").rstrip(".") + "%"


def _month_pair(v, key):
    """Two months joined by ' and ', each the first of its month, as the last_month check returns them: 2026-09-01 and 2026-09-01."""
    parts = _text(v, key).split(" and ")
    if len(parts) != 2:
        raise ValueError(f"{key}: {v!r} is not two dates joined by ' and '")
    for p in parts:
        datetime.date.fromisoformat(p)
    return v


FORMATS = {  # name: (read the value from the query, show it)
    "usd": (_whole, _usd),                            # $88,391
    "usd_cents": (_places(2), _usd_cents),            # $4,920.87
    "usd_signed": (_whole, _usd_signed),              # +$32,836, -$97,491
    "pct": (_places(1), lambda v: f"{v:.1f}%"),       # 53.5%: the value is already in percent
    "share": (_places(4), _share),                    # 38.05%: the value is a fraction of one, 0.3805 (pct expects percent, like 53.5)
    "pts": (_places(1), lambda v: f"{v:.1f}"),        # 1.7 (points, and also pace, where 100 is on pace)
    "int": (_whole, lambda v: f"{v:,}"),              # 27,967
    "month": (_text, _month),                         # the value is the first of the month, as 2026-01-01; shown as Jan 2026
    "months": (_month_pair, lambda v: " and ".join(_month(p) for p in v.split(" and "))),  # 2026-09-01 and 2026-09-01: Sep 2026 and Sep 2026
    "text": (_text, str),                             # as is
}


# ---------------------------------------------------------------- the facts

def _summit_q3(expr: str) -> str:
    """Summit Travel Partners on DFW-ORD in Q3 2026, one number. The metric view's definitions are written out here: AA share is
    AA revenue over everything the agency sold; fair share is AA's seat share (made up, one per route) weighted by that revenue."""
    return f"""
        SELECT {expr} AS value
        FROM aa_demo.gold.fact_agency_sales_monthly s
        JOIN aa_demo.gold.dim_agency a ON a.agency_id = s.agency_id
        JOIN aa_demo.gold.dim_market m ON m.market_id = s.market_id
        JOIN aa_demo.gold.fact_market_capacity c ON c.market_id = s.market_id AND c.sales_month = s.sales_month
        WHERE a.agency_name = 'Summit Travel Partners' AND m.origin = 'DFW' AND m.dest = 'ORD'
          AND s.sales_month BETWEEN DATE '2026-07-01' AND DATE '2026-09-01'"""


def _harbor_move(column: str, month: str) -> str:
    """One column of ops.decomposition for Harbor Business Travel: its AA revenue in `month` against the same month a year earlier."""
    return f"""
        SELECT ROUND(d.{column}) AS value
        FROM aa_demo.ops.decomposition d
        JOIN aa_demo.gold.dim_agency a ON a.agency_id = d.agency_id
        WHERE a.agency_name = 'Harbor Business Travel' AND d.sales_month = DATE '{month}'"""


def _harbor_share(month: str) -> str:
    return f"""
        SELECT ROUND(100 * SUM(s.aa_revenue) / NULLIF(SUM(s.market_revenue), 0), 1) AS value
        FROM aa_demo.gold.fact_agency_sales_monthly s
        JOIN aa_demo.gold.dim_agency a ON a.agency_id = s.agency_id
        WHERE a.agency_name = 'Harbor Business Travel' AND s.sales_month = DATE '{month}'"""


def _yoy(month: str) -> str:
    """All agencies' AA revenue in `month` of 2026 against the same month of 2025, as a percent."""
    return f"""
        SELECT ROUND(100 * (SUM(CASE WHEN sales_month = DATE '2026-{month}-01' THEN aa_revenue END)
                            - SUM(CASE WHEN sales_month = DATE '2025-{month}-01' THEN aa_revenue END))
                         / NULLIF(SUM(CASE WHEN sales_month = DATE '2025-{month}-01' THEN aa_revenue END), 0), 1) AS value
        FROM aa_demo.gold.fact_agency_sales_monthly
        WHERE sales_month IN (DATE '2025-{month}-01', DATE '2026-{month}-01')"""


def _sunbelt_2025(month: str) -> str:
    return f"""
        SELECT ROUND(SUM(s.aa_revenue)) AS value
        FROM aa_demo.gold.fact_agency_sales_monthly s
        JOIN aa_demo.gold.dim_agency a ON a.agency_id = s.agency_id
        WHERE a.agency_name = 'Sunbelt Vacations' AND s.sales_month = DATE '2025-{month}-01'"""


def _others_move(month: str) -> str:
    """The change in AA revenue in `month` of 2026 against the same month of 2025, added up over every agency except Sunbelt
    Vacations (no rows in Mar and Apr 2026) and Harbor Business Travel (its own facts), so that the three parts can be added."""
    return f"""
        SELECT ROUND(SUM(CASE WHEN s.sales_month = DATE '2026-{month}-01' THEN s.aa_revenue END)
                   - SUM(CASE WHEN s.sales_month = DATE '2025-{month}-01' THEN s.aa_revenue END)) AS value
        FROM aa_demo.gold.fact_agency_sales_monthly s
        JOIN aa_demo.gold.dim_agency a ON a.agency_id = s.agency_id
        WHERE a.agency_name NOT IN ('Sunbelt Vacations', 'Harbor Business Travel')
          AND s.sales_month IN (DATE '2025-{month}-01', DATE '2026-{month}-01')"""


def _pace(agency: str, month: str, old_rule: bool = False) -> str:
    """gold.agency_pace for one agency and month. The old rule grew the goal with the calendar month number, so a month with no
    rows counted as zero revenue against a full month of goal: ytd_revenue / (revenue_goal_usd * month / 12)."""
    value = ("ROUND(100 * p.ytd_revenue / NULLIF(p.revenue_goal_usd * EXTRACT(MONTH FROM p.sales_month) / 12.0, 0), 1)"
             if old_rule else "p.pace_pct")
    return f"""
        SELECT {value} AS value
        FROM aa_demo.gold.agency_pace p
        JOIN aa_demo.gold.dim_agency a ON a.agency_id = p.agency_id
        WHERE a.agency_name = '{agency}' AND p.sales_month = DATE '{month}'"""


# The twelve agencies by the short name their per-agency keys use, in dim_agency order (data/make_data.py). A test keeps the list equal to the table.
AGENCIES = (("summit", "Summit Travel Partners"), ("bluesky", "BlueSky Corporate Travel"), ("farehub", "FareHub Online"),
            ("northstar", "Northstar Leisure"), ("harbor", "Harbor Business Travel"), ("pacific", "Pacific Gateway Travel"),
            ("lonestar", "Lone Star Travel Group"), ("capitol", "Capitol Corporate Travel"), ("sunbelt", "Sunbelt Vacations"),
            ("golden", "Golden Coast Travel"), ("midway", "Midway Travel Services"), ("atlantic", "Atlantic Premier Travel"))


def _agency_q3(agency: str, expr: str) -> str:
    """One agency's number for Q3 2026 over all routes together, one number. Like _summit_q3 for one route, the metric view's
    definitions are written out: AA share is AA revenue over everything the agency sold; fair share is AA's seat share (made up,
    one per route) weighted by that revenue."""
    return f"""
        SELECT {expr} AS value
        FROM aa_demo.gold.fact_agency_sales_monthly s
        JOIN aa_demo.gold.dim_agency a ON a.agency_id = s.agency_id
        JOIN aa_demo.gold.fact_market_capacity c ON c.market_id = s.market_id AND c.sales_month = s.sales_month
        WHERE a.agency_name = '{agency}'
          AND s.sales_month BETWEEN DATE '2026-07-01' AND DATE '2026-09-01'"""


def _agency_q3_facts() -> list[tuple[str, str, str, str]]:
    """AA share and fair share for every agency in Q3 2026, all routes together: the two ends of each row of figure 12."""
    out = []
    for slug, name in AGENCIES:
        out.append((f"agency_q3_aa_share_{slug}", _agency_q3(name, "ROUND(100 * SUM(s.aa_revenue) / NULLIF(SUM(s.market_revenue), 0), 1)"), "pct",
                    f"{name}, Q3 2026, all routes together: AA revenue over everything the agency sold."))
        out.append((f"agency_q3_fair_share_{slug}",
                    _agency_q3(name, "ROUND(100 * SUM(s.market_revenue * c.aa_seat_share) / NULLIF(SUM(s.market_revenue), 0), 1)"), "pct",
                    f"{name}, Q3 2026, all routes together: AA's seat share (made up, one per route) weighted by what the agency sold."))
    return out


def _corporate_low(corporate: str) -> str:
    """The lowest month of one corporate's bookings: fare times tickets, on the tickets booked in the month."""
    return f"""
        SELECT ROUND(MIN(t.usd)) AS value
        FROM (SELECT SUM(b.fare_usd * b.ticket_count) AS usd
              FROM aa_demo.gold.fact_corporate_bookings b
              JOIN aa_demo.gold.dim_corporate c ON c.corp_id = b.corp_id
              WHERE c.corp_name = '{corporate}'
              GROUP BY DATE_TRUNC('month', b.booking_date)) AS t"""


FACTS: list[tuple[str, str, str, str]] = [
    # --- the shape of the data
    ("agencies", "SELECT COUNT(*) AS value FROM aa_demo.gold.dim_agency", "int",
     "Rows in gold.dim_agency, one per agency."),
    ("routes", "SELECT COUNT(*) AS value FROM aa_demo.gold.dim_market", "int",
     "Rows in gold.dim_market, one per route."),
    ("months", "SELECT COUNT(DISTINCT sales_month) AS value FROM aa_demo.gold.fact_agency_sales_monthly", "int",
     "Distinct months that have sales rows."),
    ("sales_rows", "SELECT COUNT(*) AS value FROM aa_demo.gold.fact_agency_sales_monthly", "int",
     "Rows in gold.fact_agency_sales_monthly, one per agency, route and month."),
    ("capacity_rows", "SELECT COUNT(*) AS value FROM aa_demo.gold.fact_market_capacity", "int",
     "Rows in gold.fact_market_capacity, one per route and month."),
    ("agency_months_present", """
        SELECT COUNT(*) AS value
        FROM (SELECT DISTINCT agency_id, sales_month FROM aa_demo.gold.fact_agency_sales_monthly) AS t""", "int",
     "Agency-months that have sales rows, counted once however many routes they hold."),
    ("agency_months_total", """
        SELECT (SELECT COUNT(*) FROM aa_demo.gold.dim_agency)
             * (SELECT COUNT(DISTINCT sales_month) FROM aa_demo.gold.fact_agency_sales_monthly) AS value""", "int",
     "Every agency times every month, whether or not the agency has rows."),
    ("sunbelt_missing_rows", """
        SELECT COUNT(*) AS value
        FROM aa_demo.gold.dim_agency a
        CROSS JOIN aa_demo.gold.dim_market m
        CROSS JOIN (SELECT DISTINCT sales_month FROM aa_demo.gold.fact_agency_sales_monthly) d
        LEFT JOIN aa_demo.gold.fact_agency_sales_monthly s
               ON s.agency_id = a.agency_id AND s.market_id = m.market_id AND s.sales_month = d.sales_month
        WHERE a.agency_name = 'Sunbelt Vacations' AND s.agency_id IS NULL""", "int",
     "Agency, route and month rows that should exist for Sunbelt Vacations and do not."),
    ("kpis", "SELECT COUNT(*) AS value FROM aa_demo.ops.kpi_definitions", "int",
     "Rows in ops.kpi_definitions, one per number."),
    ("agreements", "SELECT COUNT(DISTINCT file) AS value FROM aa_demo.gold.contract_clauses", "int",
     "Agreement files that gold.contract_clauses was read from."),

    # --- bronze to silver: what cleaning did to the corporate bookings
    ("bronze_tables", """
        SELECT COUNT(*) AS value FROM information_schema.tables
        WHERE table_catalog = 'aa_demo' AND table_schema = 'bronze'""", "int",
     "Tables in the bronze schema, as sent."),
    ("bookings_delivered", "SELECT COUNT(*) AS value FROM aa_demo.bronze.fact_corporate_bookings", "int",
     "Rows in bronze.fact_corporate_bookings, as the file was delivered."),
    ("bookings_cleaned", "SELECT COUNT(*) AS value FROM aa_demo.silver.fact_corporate_bookings", "int",
     "Rows in silver.fact_corporate_bookings, after cleaning."),
    ("duplicate_tickets", """
        SELECT (SELECT COUNT(*) FROM aa_demo.bronze.fact_corporate_bookings)
             - (SELECT COUNT(*) FROM aa_demo.silver.fact_corporate_bookings) AS value""", "int",
     "Booking rows that cleaning dropped because the ticket was already loaded."),
    ("duplicate_usd", """
        SELECT ROUND(SUM(fare_usd * ticket_count), 2) AS value
        FROM (SELECT fare_usd, ticket_count,
                     ROW_NUMBER() OVER (PARTITION BY ticket_number ORDER BY booking_id) AS n
              FROM aa_demo.bronze.fact_corporate_bookings) AS t
        WHERE n > 1""", "usd_cents",
     "Fare times tickets on the rows that cleaning dropped, in dollars and cents."),
    ("channel_spellings_delivered", "SELECT COUNT(DISTINCT channel) AS value FROM aa_demo.bronze.fact_corporate_bookings", "int",
     "Distinct channel labels in bronze, counting capital letters and spaces."),
    ("channel_spellings_cleaned", "SELECT COUNT(DISTINCT channel) AS value FROM aa_demo.silver.fact_corporate_bookings", "int",
     "Distinct channel labels in silver."),
    ("channel_direct_rows", "SELECT COUNT(*) AS value FROM aa_demo.bronze.fact_corporate_bookings WHERE channel = 'Direct'", "int",
     "Bronze rows whose channel label is exactly Direct."),
    ("channel_ndc_rows", "SELECT COUNT(*) AS value FROM aa_demo.bronze.fact_corporate_bookings WHERE channel = ' ndc '", "int",
     "Bronze rows whose channel label is exactly ndc in small letters with a space on each side."),

    # --- planted on purpose: a gap is not a zero
    ("northstar_zero_route", """
        SELECT CONCAT(m.origin, '-', m.dest) AS value
        FROM aa_demo.gold.fact_agency_sales_monthly s
        JOIN aa_demo.gold.dim_agency a ON a.agency_id = s.agency_id
        JOIN aa_demo.gold.dim_market m ON m.market_id = s.market_id
        WHERE a.agency_name = 'Northstar Leisure' AND s.aa_revenue = 0""", "text",
     "The one route where Northstar Leisure reported a month with no AA revenue at all."),
    ("northstar_zero_month", """
        SELECT s.sales_month AS value
        FROM aa_demo.gold.fact_agency_sales_monthly s
        JOIN aa_demo.gold.dim_agency a ON a.agency_id = s.agency_id
        WHERE a.agency_name = 'Northstar Leisure' AND s.aa_revenue = 0""", "month",
     "The month of that zero."),
    ("northstar_other_usd", """
        SELECT ROUND(s.market_revenue - s.aa_revenue) AS value
        FROM aa_demo.gold.fact_agency_sales_monthly s
        JOIN aa_demo.gold.dim_agency a ON a.agency_id = s.agency_id
        WHERE a.agency_name = 'Northstar Leisure' AND s.aa_revenue = 0""", "usd",
     "What Northstar Leisure sold on other airlines on that route in that month, in dollars."),
    ("northstar_zero_aa_usd", """
        SELECT ROUND(s.aa_revenue) AS value
        FROM aa_demo.gold.fact_agency_sales_monthly s
        JOIN aa_demo.gold.dim_agency a ON a.agency_id = s.agency_id
        WHERE a.agency_name = 'Northstar Leisure' AND s.aa_revenue = 0""", "usd",
     "AA revenue in the one cell where Northstar Leisure reported none: a reported zero, not a missing row."),

    # --- Q3 2026: shares, and why a ratio is computed at the grain asked
    ("avg_of_shares_q3", """
        SELECT ROUND(100 * AVG(share), 1) AS value
        FROM (SELECT agency_id, SUM(aa_revenue) / NULLIF(SUM(market_revenue), 0) AS share
              FROM aa_demo.gold.fact_agency_sales_monthly
              WHERE sales_month BETWEEN DATE '2026-07-01' AND DATE '2026-09-01'
              GROUP BY agency_id) AS t""", "pct",
     "Q3 2026, all routes: the plain average of each agency's AA share, one share per agency."),
    ("share_of_total_q3", """
        SELECT ROUND(100 * SUM(aa_revenue) / NULLIF(SUM(market_revenue), 0), 1) AS value
        FROM aa_demo.gold.fact_agency_sales_monthly
        WHERE sales_month BETWEEN DATE '2026-07-01' AND DATE '2026-09-01'""", "pct",
     "Q3 2026, all routes: AA's share of the combined sales of all agencies, a ratio of sums."),
    ("summit_q3_aa_share", _summit_q3("ROUND(100 * SUM(s.aa_revenue) / NULLIF(SUM(s.market_revenue), 0), 1)"), "pct",
     "Summit Travel Partners on DFW-ORD, Q3 2026: AA revenue over everything Summit sold on the route."),
    ("summit_q3_fair_share", _summit_q3("ROUND(100 * SUM(s.market_revenue * c.aa_seat_share) / NULLIF(SUM(s.market_revenue), 0), 1)"), "pct",
     "Summit Travel Partners on DFW-ORD, Q3 2026: AA's seat share (made up) weighted by what Summit sold."),
    ("summit_q3_gap_pts", _summit_q3("ROUND(100 * (SUM(s.aa_revenue) - SUM(s.market_revenue * c.aa_seat_share)) / NULLIF(SUM(s.market_revenue), 0), 1)"), "pts",
     "Summit Travel Partners on DFW-ORD, Q3 2026: AA share minus fair share, in points. Fair share comes from made-up seat shares."),
    ("summit_q3_gap_usd", _summit_q3("ROUND(SUM(s.aa_revenue) - SUM(s.market_revenue * c.aa_seat_share))"), "usd",
     "Summit Travel Partners on DFW-ORD, Q3 2026: AA revenue minus the revenue fair share would bring. Fair share comes from made-up seat shares."),
    ("summit_q3_pax_share", _summit_q3("ROUND(100.0 * SUM(s.aa_pax) / NULLIF(SUM(s.market_pax), 0), 1)"), "pct",
     "Summit Travel Partners on DFW-ORD, Q3 2026: AA passengers over all passengers Summit booked on the route."),
    ("pax_rev_max_gap_pts", """
        SELECT ROUND(MAX(ABS(rev_share - pax_share)), 1) AS value
        FROM (SELECT agency_id,
                     100 * SUM(aa_revenue) / NULLIF(SUM(market_revenue), 0) AS rev_share,
                     100.0 * SUM(aa_pax) / NULLIF(SUM(market_pax), 0) AS pax_share
              FROM aa_demo.gold.fact_agency_sales_monthly
              WHERE sales_month BETWEEN DATE '2026-07-01' AND DATE '2026-09-01'
              GROUP BY agency_id) AS t""", "pts",
     "Q3 2026, all routes, per agency: the largest gap between passenger share and revenue share, in points."),

    # --- Q3 2026, every agency, all routes together (figure 12)
    *_agency_q3_facts(),

    # --- why Harbor's September moved (ops.decomposition, Sep 2025 to Sep 2026)
    ("harbor_delta_usd", _harbor_move("delta_revenue", "2026-09-01"), "usd_signed",
     "Harbor Business Travel, Sep 2025 to Sep 2026: the change in AA revenue."),
    ("harbor_volume_usd", _harbor_move("volume_effect", "2026-09-01"), "usd_signed",
     "Harbor Business Travel, Sep 2025 to Sep 2026: the part of the change from selling more or less travel overall."),
    ("harbor_mix_usd", _harbor_move("mix_effect", "2026-09-01"), "usd_signed",
     "Harbor Business Travel, Sep 2025 to Sep 2026: the part of the change from moving between routes."),
    ("harbor_share_usd", _harbor_move("share_effect", "2026-09-01"), "usd_signed",
     "Harbor Business Travel, Sep 2025 to Sep 2026: the part of the change from AA winning or losing share inside routes."),
    ("harbor_revenue_sep25_usd", _harbor_move("revenue_prior", "2026-09-01"), "usd",
     "Harbor Business Travel: AA revenue in Sep 2025, where the waterfall starts."),
    ("harbor_revenue_sep26_usd", _harbor_move("revenue_now", "2026-09-01"), "usd",
     "Harbor Business Travel: AA revenue in Sep 2026, where the waterfall ends."),
    ("harbor_fair_share_effect_usd", _harbor_move("fair_share_effect", "2026-09-01"), "usd_signed",
     "Harbor Business Travel, Sep 2025 to Sep 2026: the change the made-up seat shares would have predicted. A side check, not part of the total."),

    # --- Harbor's slow slide, by month
    ("harbor_share_sep25", _harbor_share("2025-09-01"), "pct", "Harbor Business Travel, Sep 2025: AA share, all routes together."),
    ("harbor_share_sep26", _harbor_share("2026-09-01"), "pct", "Harbor Business Travel, Sep 2026: AA share, all routes together."),
    ("harbor_share_jun26", _harbor_share("2026-06-01"), "pct", "Harbor Business Travel, Jun 2026: AA share, all routes together."),
    ("harbor_share_jul26", _harbor_share("2026-07-01"), "pct", "Harbor Business Travel, Jul 2026: AA share, all routes together."),

    # --- the two months Sunbelt is missing from, what Harbor did in them, and what the other agencies did
    ("yoy_mar26", _yoy("03"), "pct", "Mar 2026, all agencies: AA revenue against Mar 2025."),
    ("yoy_apr26", _yoy("04"), "pct", "Apr 2026, all agencies: AA revenue against Apr 2025."),
    ("sunbelt_mar25_usd", _sunbelt_2025("03"), "usd", "Sunbelt Vacations, Mar 2025: AA revenue, in the month it is missing from in 2026."),
    ("sunbelt_apr25_usd", _sunbelt_2025("04"), "usd", "Sunbelt Vacations, Apr 2025: AA revenue, in the month it is missing from in 2026."),
    ("harbor_mar26_chg_usd", _harbor_move("delta_revenue", "2026-03-01"), "usd_signed",
     "Harbor Business Travel, Mar 2026: the change in AA revenue against Mar 2025."),
    ("harbor_apr26_chg_usd", _harbor_move("delta_revenue", "2026-04-01"), "usd_signed",
     "Harbor Business Travel, Apr 2026: the change in AA revenue against Apr 2025."),
    ("others_mar26_chg_usd", _others_move("03"), "usd_signed",
     "Every agency except Sunbelt Vacations and Harbor Business Travel, added up, Mar 2026: the change in AA revenue against Mar 2025."),
    ("others_apr26_chg_usd", _others_move("04"), "usd_signed",
     "Every agency except Sunbelt Vacations and Harbor Business Travel, added up, Apr 2026: the change in AA revenue against Apr 2025."),

    # --- pace in Sep 2026, and Sunbelt's before and after counting only the months it reported
    ("harbor_pace_sep26", _pace("Harbor Business Travel", "2026-09-01"), "pts",
     "Harbor Business Travel, Sep 2026: revenue so far over the goal so far, where one hundred is on pace."),
    ("farehub_pace_sep26", _pace("FareHub Online", "2026-09-01"), "pts",
     "FareHub Online, Sep 2026: revenue so far over the goal so far, where one hundred is on pace."),
    ("network_pace_sep26", """
        SELECT ROUND(100 * SUM(ytd_revenue) / NULLIF(SUM(ytd_goal), 0), 1) AS value
        FROM aa_demo.gold.agency_pace
        WHERE sales_month = DATE '2026-09-01'""", "pts",
     "All agencies together, Sep 2026: revenue so far over the goal so far, where one hundred is on pace. A ratio of sums."),
    ("sunbelt_pace_may26", _pace("Sunbelt Vacations", "2026-05-01"), "pts",
     "Sunbelt Vacations, May 2026: pace now, counting only the months it reported."),
    ("sunbelt_pace_may26_before", _pace("Sunbelt Vacations", "2026-05-01", old_rule=True), "pts",
     "Sunbelt Vacations, May 2026: pace under the old rule, where a missing month counted as zero."),
    ("sunbelt_pace_sep26", _pace("Sunbelt Vacations", "2026-09-01"), "pts",
     "Sunbelt Vacations, Sep 2026: pace now, counting only the months it reported."),
    ("sunbelt_pace_sep26_before", _pace("Sunbelt Vacations", "2026-09-01", old_rule=True), "pts",
     "Sunbelt Vacations, Sep 2026: pace under the old rule, where a missing month counted as zero."),

    # --- two corporates whose bookings slip (planted in data/make_data.py): the lowest month of each
    ("northwind_low_usd", _corporate_low("Northwind Logistics"), "usd",
     "Northwind Logistics: its lowest month of corporate bookings, fare times tickets on the tickets booked in the month, in dollars."),
    ("coastal_low_usd", _corporate_low("Coastal Media Group"), "usd",
     "Coastal Media Group: its lowest month of corporate bookings, fare times tickets on the tickets booked in the month, in dollars."),
]


# ---------------------------------------------------------------- numbers a local query cannot reproduce

def _dated(value, display, source, date, note=None) -> dict:
    return {"value": value, "display": display, "source": source, "date": date, **({"note": note} if note else {})}


_APP_RUN = "evals/results/2026-10-13T160143.json, harness run 5: Qwen3-Next, the model inside the Databricks App, judged by gpt-5-mini"
_LIMITS = "docs/limits.md, row dated 2026-10-15, "
_EVAL = "README.md, the Foundry evaluation paragraph: the first full run, agent version 3"
_PARITY = "aa_demo.ops.kpi_parity on Databricks, queried 2026-10-19"
_REHEARSAL = "rehearsal on the App"

DATED: dict[str, dict] = {
    "genie_benchmark": _dated(20, "20 of 20", "evals/results/2026-10-19T213612-genie-eval.json", "2026-10-19",
                              "One run on Oct 19, after five benchmark questions named their columns. Two earlier runs that day scored 17 of 20."),
    "genie_benchmark_earlier": _dated(17, "17 of 20", "evals/results/2026-10-19T211129-genie-eval.json and evals/results/2026-10-19T212948-genie-eval.json",
                                      "2026-10-19", "Two runs on Oct 19, each 17 of 20, before five benchmark questions named their columns. The first missed q09, q10 "
                                      "and q17. The rerun, with nothing changed, missed q07, q10 and q11."),
    "app_model_questions": _dated(20, "20", _APP_RUN, "2026-10-13", "The questions in that run."),
    "app_model_right": _dated(15, "15", _APP_RUN, "2026-10-13"),
    "app_model_partly": _dated(3, "3", _APP_RUN, "2026-10-13"),
    "app_model_wrong": _dated(2, "2", _APP_RUN, "2026-10-13"),
    "app_model_gave_up_passed": _dated(1, "1", _APP_RUN, "2026-10-13",
                                       "Question q14: an answer that gave up with no numbers to check, so the verifier had nothing to flag."),
    "app_answer_median_s": _dated(26, "26", _APP_RUN, "2026-10-13", "Seconds per question, the median of 20, rounded to a whole second."),
    "app_answer_max_s": _dated(37, "37", _APP_RUN, "2026-10-13", "Seconds for the slowest question, rounded to a whole second."),
    # the question the ask slide asks, sent ten times on the App, each in a fresh chat; each time runs from Enter to the full answer
    "harbor_runs": _dated(10, "10", _REHEARSAL, "2026-10-20", "Times the question was sent, each in a fresh chat in a signed-in browser. Each run was timed from the Enter key. "
                          "The test window was in the background, which pauses the page's typing animation, so a time is the moment the checked answer arrived "
                          "plus the half second the app spends typing a short answer out."),
    "harbor_runs_median_s": _dated(6, "6", _REHEARSAL, "2026-10-20", "Seconds from Enter to the full answer, the median of ten runs, rounded to a whole second (5.5 before rounding)."),
    "harbor_runs_max_s": _dated(7, "7", _REHEARSAL, "2026-10-20", "Seconds for the slowest of the ten runs, rounded to a whole second (6.6 before rounding). The fastest took 3.8."),
    "harbor_runs_removed": _dated(2, "2", _REHEARSAL, "2026-10-20", "Runs, out of ten, where the checker removed a sentence and the answer said so. Each of the two removed two sentences "
                                  "because the model had rounded a dollar figure."),
    # the days of the runs a slide quotes, so it can say which day without typing a number
    "app_model_date": _dated("2026-10-13", "Oct 13", _APP_RUN, "2026-10-13", "The day of that benchmark run."),
    "genie_benchmark_date": _dated("2026-10-19", "Oct 19", "evals/results/2026-10-19T213612-genie-eval.json", "2026-10-19",
                                   "The day of the Genie run in genie_benchmark."),
    "foundry_eval_date": _dated("2026-10-15", "Oct 15", _EVAL, "2026-10-15",
                                "The day of the Foundry evaluation runs behind the foundry_* numbers; docs/limits.md dates its Foundry rows the same day."),
    "parity_red": _dated(250, "250", "app/cache/kpi_parity.csv, the aa_share replay labeled v1 (retired), run 64fc8eecdd92", "2026-10-12",
                         "Agency-months where the retired passenger-based copy disagreed with the metric view."),
    "parity_rows": _dated(250, "250", "app/cache/kpi_parity.csv, the aa_share replay labeled v1 (retired), run 64fc8eecdd92", "2026-10-12",
                          "Agency-months in that replay."),
    "twins_checked": _dated(6, "6", "lakehouse/parity.py, the list of numbers it compares in run()", "2026-10-19",
                            "The numbers whose SQL copy of the Power BI measure is compared with the metric view in every parity run. Pace is not one of them: it has no measure in the metric view."),
    "nightly_parity_runs": _dated(5, "5", _PARITY, "2026-10-19",
                                  "The scheduled 6 am runs on Oct 15 to 19, all green. The same query counted 9 runs since Oct 14, "
                                  "which adds three one-time runs on Oct 14 and one manual run on Oct 19."),
    "nightly_parity_drift": _dated(0, "0", _PARITY, "2026-10-19", "Values that disagreed with the metric view, across those runs."),
    "nightly_parity_from": _dated("2026-10-15", "Oct 15", _PARITY, "2026-10-19", "The day of the first scheduled run counted in nightly_parity_runs."),
    "nightly_parity_to": _dated("2026-10-19", "Oct 19", _PARITY, "2026-10-19", "The day of the last scheduled run counted in nightly_parity_runs."),
    # the Foundry evaluation, only the numbers docs/limits.md and the README's record of the first full run state plainly
    "foundry_shield_pages": _dated(23, "23", _LIMITS + "Foundry prompt shield", "2026-10-15", "Real pages in the first evaluation runs."),
    "foundry_shield_refused": _dated(2, "2", _LIMITS + "Foundry prompt shield", "2026-10-15",
                                     "Of those pages, refused by the prompt shield although the message was legitimate."),
    "foundry_attack_notes": _dated(5, "5", _LIMITS + "Foundry evaluators", "2026-10-15", "Normal CRM correction notes the indirect_attack evaluator graded."),
    "foundry_attack_false_flags": _dated(2, "2", _LIMITS + "Foundry evaluators", "2026-10-15",
                                         "Of those notes, flagged as manipulated content although they were normal."),
    "foundry_clean_page_s": _dated(38, "38", _LIMITS + "Foundry guardrails", "2026-10-15", "Seconds for a clean page on the pre-call agent."),
    "foundry_refusal_s": _dated(3, "3", _LIMITS + "Foundry guardrails", "2026-10-15", "Seconds until a jailbreak was refused at the prompt."),
    "foundry_nightly_pages": _dated(20, "20", _LIMITS + "Databricks serverless jobs", "2026-10-15",
                                    "Pages the nightly agents task wrote through the four Foundry agents, every sentence verified."),
    "foundry_quality_pages": _dated(23, "23", _EVAL, "2026-10-15", "Real pages the quality evaluators graded in that run."),
    "foundry_groundedness_misses": _dated(1, "1", _EVAL, "2026-10-15",
                                          "Of those pages, the ones whose groundedness grade failed. Relevance, coherence, fluency and the four "
                                          "content harms passed on every page."),
    # a rule a note quotes: a constant in the SQL that applies it, so a note says it without typing the number
    "tier_watch_band_pts": _dated(3, "three", "lakehouse/07_agreement_watch.sql line 88: a tier row is Watch when it is within 3 points of its line",
                                  "2026-10-20", "A tier row closer than this to its line is Watch; at this distance or more it is Fine."),
}


# ---------------------------------------------------------------- the tables a slide shows, column by column

SUMMIT = "(SELECT agency_id FROM aa_demo.gold.dim_agency WHERE agency_name = 'Summit Travel Partners')"
SUNBELT = "(SELECT agency_id FROM aa_demo.gold.dim_agency WHERE agency_name = 'Sunbelt Vacations')"
HARBOR = "(SELECT agency_id FROM aa_demo.gold.dim_agency WHERE agency_name = 'Harbor Business Travel')"
DFW_ORD = "(SELECT market_id FROM aa_demo.gold.dim_market WHERE origin = 'DFW' AND dest = 'ORD')"

TYPES = {"VARCHAR": "STRING", "INTEGER": "INT"}  # DuckDB's names for the types Databricks calls STRING and INT

COLUMNS: dict[str, tuple[str, dict[str, str]]] = {
    "gold.fact_agency_sales_monthly": (  # slide `row`: Summit Travel Partners on DFW-ORD in Sep 2026
        f"agency_id = {SUMMIT} AND market_id = {DFW_ORD} AND sales_month = DATE '2026-09-01'",
        {
            "agency_id": "Which agency made these sales. It matches agency_id in dim_agency.",
            "market_id": "Which route the sales were on. It matches market_id in dim_market.",
            "sales_month": "The month of the sales, stored as the first day of that month.",
            "aa_revenue": "Dollars of AA tickets the agency sold on this route in this month.",
            "aa_pax": "Passengers on those AA tickets.",
            "market_revenue": "Dollars of tickets the agency sold on this route in this month on all airlines, AA included.",
            "market_pax": "Passengers on all of the agency's tickets on this route in this month, on all airlines.",
        },
    ),
    "gold.fact_market_capacity": (
        f"market_id = {DFW_ORD} AND sales_month = DATE '2026-09-01'",
        {
            "market_id": "Which route the seats are on. It matches market_id in dim_market.",
            "sales_month": "The month of the seats, stored as the first day of that month.",
            "aa_seats": "Seats AA flies on this route in this month. Made up.",
            "total_seats": "Seats all airlines fly on this route in this month. Made up.",
            "aa_seat_share": "AA's seats divided by all seats on the route, which is the route's fair share. Made up: one base share per route, moved a little each month.",
            "is_projected": "True when this month's seat numbers are borrowed from last year because the seat file for the month is not in yet. It is never true for the made-up seat shares.",
            "source": "Where the seat numbers came from. Here it always says synthetic, which means made up.",
        },
    ),
    "gold.dim_agency": (  # slide `dict-agencies`
        "agency_name = 'Summit Travel Partners'",
        {
            "agency_id": "The agency's number. The other tables use it to point at the agency.",
            "agency_name": "The agency's name. All the agencies are made up.",
            "agency_type": "The kind of agency: a business travel agency (TMC), an online agency (OTA), a leisure agency or a consolidator.",
            "region": "The part of the country the agency sells in: East, Central or West.",
            "account_manager": "The AA account manager who looks after the agency. The names are made up.",
        },
    ),
    "gold.dim_market": (
        "origin = 'DFW' AND dest = 'ORD'",
        {
            "market_id": "The route's number. The sales and seat tables use it to point at the route.",
            "origin": "The airport code the route starts from.",
            "dest": "The airport code the route ends at.",
            "region": "The part of the country the route is in: East, Central or West.",
            "aa_hub_origin": "True when the route starts at an AA hub.",
        },
    ),
    "gold.agency_goals": (  # slide `dict-goals`
        f"agency_id = {SUNBELT} AND goal_year = 2026",
        {
            "agency_id": "The agency the goal is for.",
            "goal_year": "The year the goal covers.",
            "revenue_goal_usd": "The AA revenue the agency is asked to reach by the end of the year, in dollars. Made up.",
            "share_goal": "The share of its sales the agency is asked to send to AA, kept as a number between zero and one. Made up.",
        },
    ),
    "gold.agency_pace": (  # Sunbelt in May 2026, because its months_reported shows why a missing month must not count as zero
        f"agency_id = {SUNBELT} AND sales_month = DATE '2026-05-01'",
        {
            "agency_id": "The agency.",
            "goal_year": "The year of the goal.",
            "sales_month": "The month this row is for.",
            "aa_revenue": "Dollars of AA revenue the agency sold in this month, all routes together.",
            "ytd_revenue": "AA revenue the agency sold from the start of the year through this month.",
            "revenue_goal_usd": "The agency's AA revenue goal for the whole year, in dollars.",
            "ytd_goal": "The part of the yearly goal that counts so far: one twelfth for every month the agency reported.",
            "pace_pct": "Revenue so far divided by the goal so far, as a percent. One hundred means on pace.",
            "attainment_pct": "Revenue so far divided by the goal for the whole year, as a percent.",
            "months_reported": "How many months this year the agency has sales rows for, up to this month. A missing month is not counted.",
        },
    ),
    "gold.contract_clauses": (  # slide `dict-agreements`
        "clause_id = 'summit-4-4'",
        {
            "clause_id": "A short name for the clause: the agency, the clause number, and a count when one clause has several rows.",
            "agency_id": "The agency the agreement is with.",
            "file": "The agreement file the clause comes from.",
            "page": "The page of the agreement the clause is on.",
            "section": "The clause number as written in the agreement.",
            "clause_type": "What kind of clause it is, such as a goal, a share floor or an incentive tier. A promise the data cannot check is marked not_checkable.",
            "metric": "The number the clause is about, such as aa_share or aa_revenue.",
            "operator": "How the number is compared with the threshold: at least, below, or none.",
            "threshold": "The number the clause compares against, such as a percent of share or a dollar amount.",
            "threshold_2": "A second number the clause uses, such as the percent of revenue paid. Empty when the clause has only one number.",
            "window_quarters": "For how many quarters in a row the clause must hold. Empty when it does not say.",
            "consequence": "What happens under the clause, in the agreement's own words.",
            "quote": "The clause copied word for word from the page.",
        },
    ),
    "gold.crm_contacts": (  # slide `dict-crm`: the CRM is a made-up stand-in shaped like Dynamics 365 Sales
        "contact_id = 9001",
        {
            "contact_id": "The contact's number.",
            "agency_id": "The agency the contact works for.",
            "contact_name": "The contact's name. All the names are made up.",
            "title": "The contact's job title.",
            "email": "The contact's email address. Made up, and it ends in .example so it can never be a real address.",
        },
    ),
    "gold.crm_opportunities": (
        "opp_id = 7001",
        {
            "opp_id": "The deal's number.",
            "agency_id": "The agency the deal is with.",
            "opp_name": "A short name for the deal.",
            "stage": "How far along the deal is: Qualify, Propose or Negotiate.",
            "amount_usd": "What the deal is worth, in dollars.",
            "close_date": "The day the team expects the deal to close.",
            "health": "How the deal looks: On track, Stalled or At risk.",
            "owner": "The account manager who owns the deal.",
            "updated_at": "The last day anyone changed the deal.",
        },
    ),
    "gold.crm_activities": (
        "activity_id = 30001",
        {
            "activity_id": "The activity's number.",
            "agency_id": "The agency the activity was with.",
            "contact_id": "The contact the activity was with.",
            "activity_type": "What was done: an email, a call or a meeting.",
            "subject": "A short title for the activity.",
            "happened_at": "The day it happened.",
            "owner": "The account manager who did it.",
            "notes": "Free text about the activity, if anyone wrote any.",
        },
    ),
    "gold.fact_corporate_bookings": (  # slide `dict-bookings`
        "booking_id = 500001",
        {
            "booking_id": "The booking's number.",
            "ticket_number": "The ticket's number, kept as text so leading zeros stay. Each ticket appears once here; the delivered file had a few twice.",
            "corp_id": "The company that booked the trip. It matches corp_id in dim_corporate.",
            "booking_date": "The day the ticket was booked.",
            "travel_date": "The day of the trip.",
            "origin": "The airport the trip starts from.",
            "dest": "The airport the trip goes to.",
            "channel": "How the ticket was booked, cleaned to four labels: Direct, GDS, NDC or OTA.",
            "fare_usd": "The price of one ticket, in dollars.",
            "ticket_count": "How many tickets the booking holds.",
            "cabin": "The cabin: Economy, Premium Economy or Business.",
            "agency_id": "The agency that sold the ticket. Empty when the company booked without an agency.",
        },
    ),
    "gold.dim_corporate": (
        "corp_id = 101",
        {
            "corp_id": "The company's number.",
            "corp_name": "The company's name. All the companies are made up.",
            "industry": "The company's industry.",
            "hq_city": "The city where the company is based.",
            "contract_start": "The day the company's travel contract with AA starts.",
            "contract_end": "The day the contract ends.",
            "annual_commitment_usd": "The dollars of travel the company has promised to buy each year.",
        },
    ),
    "ops.decomposition": (  # slide `dict-ops`: why an agency's revenue moved against the same month a year earlier
        f"agency_id = {HARBOR} AND sales_month = DATE '2026-09-01'",
        {
            "agency_id": "The agency.",
            "sales_month": "The month being compared with the same month one year earlier.",
            "revenue_now": "AA revenue the agency sold in this month, in dollars.",
            "revenue_prior": "AA revenue the agency sold in the same month one year earlier.",
            "delta_revenue": "The change in AA revenue: this month minus the same month a year earlier, in dollars.",
            "delta_pct": "The same change as a percent of the year-earlier revenue.",
            "market_now": "Dollars the agency sold on all airlines in this month.",
            "market_prior": "Dollars the agency sold on all airlines in the same month one year earlier.",
            "market_delta_pct": "The change in the agency's all-airline sales, as a percent.",
            "aa_share_now": "AA's share of the agency's sales this month, kept as a number between zero and one.",
            "aa_share_prior": "AA's share of the agency's sales a year earlier, kept as a number between zero and one.",
            "fair_share_now": "Fair share this month: AA's seat share on the agency's routes, kept as a number between zero and one. The seat shares are made up.",
            "fair_share_prior": "Fair share a year earlier. The seat shares are made up.",
            "volume_effect": "The part of the change that comes from the agency selling more or less travel overall.",
            "mix_effect": "The part of the change that comes from the agency moving sales between routes.",
            "share_effect": "The part of the change that comes from AA winning or losing share inside the routes.",
            "fair_share_effect": "The change that the made-up seat shares would have predicted. A side check, not part of the total.",
            "residual": "What is left when volume, mix and share are added up and compared with the change. Zero means they add up exactly.",
        },
    ),
    "ops.kpi_definitions": (
        "kpi = 'aa_share'",
        {
            "kpi": "The number's short code name.",
            "display_name": "The name people see.",
            "definition_en": "The definition in plain English.",
            "owner": "The team that owns the definition.",
            "source_columns": "The table columns the number is built from.",
            "metric_view_expr": "The definition as written in the metric view, the one that Genie and the dashboard read, for six of the seven numbers; pace lives in gold.agency_pace.",
            "dax_twin": "The same definition written the way a Power BI measure would be, in DAX.",
            "twin_sql": "A SQL copy of the Power BI measure, compared with the metric view every night, for six of the seven numbers; pace lives in gold.agency_pace.",
            "twin_version": "Which version of the SQL copy is live. It moves up when a definition changes.",
            "twin_sql_retired": "The old SQL copy that the comparison with the metric view caught being wrong. Empty for numbers that never changed.",
            "retired_note": "Why the old copy was retired. Empty for numbers that never changed.",
        },
    ),
}

# The unit each example carries, by table and column: a name from FORMATS, which reads the stored value and shows it. A column that is not listed shows
# what is stored, which is right for ids, years, days, names and flags, and for threshold and threshold_2, whose unit changes from clause to clause.
# Dollars are usd where every row of the column holds whole dollars and usd_cents where a row can hold cents (a row that has none still shows .00).
# A share kept as a fraction of one is share; pct is only for a value that is already in percent.
UNITS: dict[str, dict[str, str]] = {
    "gold.fact_agency_sales_monthly": {"sales_month": "month", "aa_revenue": "usd_cents", "aa_pax": "int", "market_revenue": "usd_cents", "market_pax": "int"},
    "gold.fact_market_capacity": {"sales_month": "month", "aa_seats": "int", "total_seats": "int", "aa_seat_share": "share"},
    "gold.agency_goals": {"revenue_goal_usd": "usd", "share_goal": "share"},
    "gold.agency_pace": {"sales_month": "month", "aa_revenue": "usd_cents", "ytd_revenue": "usd_cents", "revenue_goal_usd": "usd", "ytd_goal": "usd",
                         "pace_pct": "pct", "attainment_pct": "pct", "months_reported": "int"},
    "gold.contract_clauses": {"window_quarters": "int"},
    "gold.crm_opportunities": {"amount_usd": "usd"},
    "gold.fact_corporate_bookings": {"fare_usd": "usd_cents", "ticket_count": "int"},
    "gold.dim_corporate": {"annual_commitment_usd": "usd"},
    "ops.decomposition": {"sales_month": "month", "revenue_now": "usd_cents", "revenue_prior": "usd_cents", "delta_revenue": "usd_cents", "delta_pct": "pct",
                          "market_now": "usd_cents", "market_prior": "usd_cents", "market_delta_pct": "pct", "aa_share_now": "share", "aa_share_prior": "share",
                          "fair_share_now": "share", "fair_share_prior": "share", "volume_effect": "usd_cents", "mix_effect": "usd_cents",
                          "share_effect": "usd_cents", "fair_share_effect": "usd_cents", "residual": "usd_cents"},
}


# ---------------------------------------------------------------- the checks the data must keep passing

CHECKS: list[tuple[str, str, str, str, object, str]] = [  # (key, sentence, why, SQL, expected, format); a why is one plain sentence on what the check
    # guards against, and the format is a FORMATS name for how a slide prints the expected and actual values
    # twelve agencies by twelve routes by twenty-one months is 3,024 cells; Sunbelt's two missing months take away twelve routes each
    ("sales_row_count", "Sales rows equal every agency, route and month, minus Sunbelt's two missing months",
     "Catches sales rows lost or added on the way in, because the expected count is known.", """
        SELECT COUNT(s.agency_id) AS value
        FROM aa_demo.gold.dim_agency a
        CROSS JOIN aa_demo.gold.dim_market m
        CROSS JOIN (SELECT DISTINCT sales_month FROM aa_demo.gold.fact_agency_sales_monthly) d
        LEFT JOIN aa_demo.gold.fact_agency_sales_monthly s
               ON s.agency_id = a.agency_id AND s.market_id = m.market_id AND s.sales_month = d.sales_month""", 3000, "int"),
    ("no_repeated_rows", "One row per agency, route and month, with no repeats",
     "Catches an agency, route and month with more than one row, because a sum would count it twice.", """
        SELECT COUNT(*) AS value
        FROM (SELECT agency_id, market_id, sales_month FROM aa_demo.gold.fact_agency_sales_monthly
              GROUP BY agency_id, market_id, sales_month HAVING COUNT(*) > 1) AS t""", 0, "int"),
    ("sales_have_seats", "Every sales row has a seats row",
     "Catches a sale with no seats row for its route and month, which fair share would leave out.", """
        SELECT COUNT(*) AS value
        FROM aa_demo.gold.fact_agency_sales_monthly s
        LEFT JOIN aa_demo.gold.fact_market_capacity c ON c.market_id = s.market_id AND c.sales_month = s.sales_month
        WHERE c.market_id IS NULL""", 0, "int"),
    ("no_empty_sales", "No empty sales numbers",
     "Catches an empty sales number, which a sum skips without an error, so the share comes out wrong.", """
        SELECT COUNT(*) AS value FROM aa_demo.gold.fact_agency_sales_monthly
        WHERE aa_revenue IS NULL OR aa_pax IS NULL OR market_revenue IS NULL OR market_pax IS NULL""", 0, "int"),
    ("aa_within_market", "AA is never above the market in revenue or passengers",
     "Catches swapped columns, because the market includes AA and so can never be smaller than AA.", """
        SELECT COUNT(*) AS value FROM aa_demo.gold.fact_agency_sales_monthly
        WHERE aa_revenue > market_revenue OR aa_pax > market_pax""", 0, "int"),
    ("last_month", "Both facts end in September 2026",
     "Catches a table that stops early, because fair share needs sales and seats for the same month.", """
        SELECT CONCAT(CAST((SELECT MAX(sales_month) FROM aa_demo.gold.fact_agency_sales_monthly) AS STRING), ' and ',
                      CAST((SELECT MAX(sales_month) FROM aa_demo.gold.fact_market_capacity) AS STRING)) AS value""", "2026-09-01 and 2026-09-01", "months"),
    ("duplicates_removed", "Cleaning removed the duplicates' revenue",
     "Catches cleaning that removes more or less than the fares of the duplicate tickets.", """
        SELECT ROUND((SELECT SUM(fare_usd * ticket_count) FROM aa_demo.bronze.fact_corporate_bookings)
                   - (SELECT SUM(fare_usd * ticket_count) FROM aa_demo.silver.fact_corporate_bookings), 2) AS value""", 4920.87, "usd_cents"),
    ("pace_month_count", "Pace never counts more months than the calendar has",
     "Catches a month counted twice in pace, since no agency reports more months than the year has had.", """
        SELECT COUNT(*) AS value FROM aa_demo.gold.agency_pace
        WHERE months_reported > EXTRACT(MONTH FROM sales_month)""", 0, "int"),
]


# ---------------------------------------------------------------- putting it together

def _sql(text: str) -> str:
    return textwrap.dedent(text).strip()


def _run_fact(key: str, sql: str, fmt: str, grain: str) -> dict:
    sql = _sql(sql)
    rows = query(sql)
    if len(rows) != 1 or "value" not in rows[0]:
        raise ValueError(f"{key}: the query must return one row with a column named value, and it returned {len(rows)} rows")
    read, show = FORMATS[fmt]
    value = read(_json(rows[0]["value"]), key)
    return {"value": value, "display": show(value), "sql": sql, "grain": grain}


def _example(v) -> str:
    """An example value as a short string a table cell can hold."""
    if v is None:
        return "NULL"
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, datetime.date):
        return v.isoformat()
    if isinstance(v, float):
        return str(int(v)) if v.is_integer() else repr(v)
    s = " ".join(str(v).split())
    return s if len(s) <= 60 else s[:59].rstrip() + "…"


def _shown(table: str, column: str, v) -> str:
    """An example as the slide shows it. A column with a unit in UNITS goes through that format's read and show, so a value the format cannot
    show raises instead of being rounded. A missing value stays NULL, and a column with no unit shows what is stored."""
    fmt = UNITS.get(table, {}).get(column)
    if fmt is None or v is None:
        return _example(v)
    read, show = FORMATS[fmt]
    return show(read(_json(v), f"{table}.{column}"))


def _check_units() -> None:
    """UNITS may name only tables and columns that COLUMNS describes and formats that FORMATS has; a typo would leave an example without its unit."""
    for table, units in UNITS.items():
        if table not in COLUMNS:
            raise ValueError(f"UNITS: {table} is not a table in COLUMNS")
        if set(units) - set(COLUMNS[table][1]):
            raise ValueError(f"UNITS: no such column in {table}: {sorted(set(units) - set(COLUMNS[table][1]))}")
        if set(units.values()) - set(FORMATS):
            raise ValueError(f"UNITS: no such format for {table}: {sorted(set(units.values()) - set(FORMATS))}")


def _columns() -> dict:
    _check_units()
    out = {}
    for table, (where, meanings) in COLUMNS.items():
        schema, name = table.split(".")
        cols = query(f"""SELECT column_name, data_type FROM information_schema.columns
                         WHERE table_catalog = 'aa_demo' AND table_schema = '{schema}' AND table_name = '{name}' ORDER BY ordinal_position""")
        row = query(f"SELECT * FROM aa_demo.{table} WHERE {where}")
        if len(row) != 1:
            raise ValueError(f"{table}: the example row must match one row, and it matched {len(row)}")
        unknown = set(meanings) - {c["column_name"] for c in cols}
        if unknown:
            raise ValueError(f"{table}: no such column: {sorted(unknown)}")
        out[table] = [{"name": c["column_name"], "type": TYPES.get(c["data_type"], c["data_type"]),
                       "meaning": meanings[c["column_name"]], "example": _shown(table, c["column_name"], row[0][c["column_name"]])}
                      for c in cols if c["column_name"] in meanings]
    return out


def _same(actual, expected) -> bool:
    numbers = all(isinstance(x, (int, float)) and not isinstance(x, bool) for x in (actual, expected))
    return math.isclose(actual, expected, rel_tol=0, abs_tol=1e-9) if numbers else actual == expected


def _check_shown(fmt: str, v) -> str:
    """A check's value the way a slide prints it, in the check's format. A value the format cannot read (a NULL, or another kind of value that
    a failing check returned) shows as stored, because a check that fails must still say what came back."""
    read, show = FORMATS[fmt]
    try:
        return show(read(v, fmt))
    except (TypeError, ValueError):
        return _example(v)


def _checks() -> list[dict]:
    out = []
    for key, name, why, sql, expected, fmt in CHECKS:
        rows = query(_sql(sql))
        if len(rows) != 1 or "value" not in rows[0]:
            raise ValueError(f"{key}: the query must return one row with a column named value")
        actual = _json(rows[0]["value"])
        read, show = FORMATS[fmt]
        display = {"expected": show(read(expected, key)), "actual": _check_shown(fmt, actual)}  # the expected value is written here, so it must read
        out.append({"key": key, "name": name, "why": why, "expected": expected, "actual": actual, "ok": _same(actual, expected), "display": display})
    return out


def collect() -> dict:
    """Run every query. JSON-native values only, so the result can be written as it is and compared with the file."""
    return {"facts": {key: _run_fact(key, sql, fmt, grain) for key, sql, fmt, grain in FACTS},
            "columns": _columns(), "checks": _checks()}


_BY_KEY = {f[0]: f for f in FACTS}


@functools.cache
def fact(key: str):
    """One fact's value, for the figure builders. Runs only that fact's query, once per process."""
    return _run_fact(*_BY_KEY[key])["value"]


def display(key: str) -> str:
    """One fact the way a slide shows it: the `display` string facts.json stores for the key, from the same formatter."""
    return FORMATS[_BY_KEY[key][2]][1](fact(key))


def _print_all() -> None:
    data = collect()
    for key, f in data["facts"].items():
        print(f"{key} = {f['display']}\n  {f['grain']}\n" + textwrap.indent(f["sql"], "    ") + "\n")
    print("dated (a local query cannot reproduce these)")
    for key, d in DATED.items():
        print(f"{key} = {d['display']}   {d['source']}, {d['date']}")
    print("\nchecks")
    for c in data["checks"]:
        print(f"{'ok  ' if c['ok'] else 'FAIL'} {c['name']}: expected {c['expected']!r}, got {c['actual']!r}")


def main(argv: list[str]) -> int:
    if "--print" in argv:
        _print_all()
        return 0
    data = {**collect(), "dated": DATED}
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(data, indent=1, sort_keys=True, ensure_ascii=False, allow_nan=False) + "\n", encoding="utf-8")
    print(f"wrote {OUT.relative_to(ROOT)}: {len(data['facts'])} facts, {len(DATED)} dated, {len(data['columns'])} tables, {len(data['checks'])} checks")
    failed = [c for c in data["checks"] if not c["ok"]]
    for c in failed:
        print(f"CHECK FAILED: {c['name']}: expected {c['expected']!r}, got {c['actual']!r}", file=sys.stderr)
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
