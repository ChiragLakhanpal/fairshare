"""Every number the data diagrams print, each from one query on the local lakehouse (opened read only).

    python3 docs/diagrams/src/data_numbers.py   # prints each number next to its query

The data is deterministic (data/make_data.py, seed 88201), so the Databricks build returns the same values.
"""
from __future__ import annotations

from pathlib import Path

import duckdb

DB = Path(__file__).resolve().parents[3] / "data" / "out" / "fairshare.duckdb"

# Summit Travel Partners on DFW-ORD in Q3 2026, the metric view's definitions written out: AA share is AA revenue over the
# agency's all-carrier revenue; fair share is AA's seat share (BTS T-100) weighted by that revenue; the gap is the difference.
FAIR = """
select round(100 * sum(s.aa_revenue) / sum(s.market_revenue), 1)                                     as aa_share_pct,
       round(100 * sum(s.market_revenue * c.aa_seat_share) / sum(s.market_revenue), 1)                as fair_share_pct,
       round(100 * (sum(s.aa_revenue) - sum(s.market_revenue * c.aa_seat_share)) / sum(s.market_revenue), 1) as gap_pts,
       round(sum(s.aa_revenue) - sum(s.market_revenue * c.aa_seat_share))                             as gap_usd,
       bool_or(c.is_projected)                                                                         as projected
from gold.fact_agency_sales_monthly s
join gold.dim_agency a using (agency_id)
join gold.dim_market m using (market_id)
join gold.fact_market_capacity c on c.market_id = s.market_id and c.sales_month = s.sales_month
where a.agency_name = 'Summit Travel Partners' and m.origin = 'DFW' and m.dest = 'ORD'
  and s.sales_month between date '2026-07-01' and date '2026-09-01'
"""

QUERIES = {
    "bronze_tables": "select count(*) from information_schema.tables where table_schema = 'bronze'",
    "bookings_delivered": "select count(*) from bronze.fact_corporate_bookings",
    "bookings_cleaned": "select count(*) from silver.fact_corporate_bookings",
    "tickets_distinct": "select count(distinct ticket_number) from bronze.fact_corporate_bookings",
    "channel_spellings_delivered": "select count(distinct channel) from bronze.fact_corporate_bookings",
    "channel_spellings_cleaned": "select count(distinct channel) from silver.fact_corporate_bookings",
    "gold_rows": "select count(*) from gold.fact_agency_sales_monthly",
    "gold_grain": "select count(distinct (agency_id, market_id, sales_month)) from gold.fact_agency_sales_monthly",
    "agreements": "select count(distinct file) from gold.contract_clauses",
    "kpis": "select count(*) from ops.kpi_definitions",
}


def numbers() -> dict:
    con = duckdb.connect(str(DB), read_only=True)
    try:
        out = {k: con.sql(q).fetchone()[0] for k, q in QUERIES.items()}
        row = con.sql(FAIR).fetchone()
        out.update(dict(zip(("aa_share_pct", "fair_share_pct", "gap_pts", "gap_usd", "projected"), row)))
    finally:
        con.close()
    # the pipeline diagram's claims, checked here so a rebuilt lakehouse cannot quietly change the story
    assert out["tickets_distinct"] == out["bookings_cleaned"], "silver should hold exactly one row per ticket"
    assert out["gold_rows"] == out["gold_grain"], "gold should hold one row per agency, route and month"
    assert not out["projected"], "Q3 2026 capacity should be published BTS data, not a projection"
    return out


if __name__ == "__main__":
    n = numbers()
    for k, q in {**QUERIES, "summit DFW-ORD Q3 2026": FAIR}.items():
        print(f"{k}: {n.get(k, {kk: n[kk] for kk in ('aa_share_pct', 'fair_share_pct', 'gap_pts', 'gap_usd')})}")
