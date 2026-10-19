"""The numbers printed on 08-why-it-moved and 09-definitions, re-run against the local build (read only).

    .venv/bin/python docs/diagrams/src/data_numbers_2.py
"""
from pathlib import Path

import duckdb

DB = Path(__file__).resolve().parents[3] / "data" / "out" / "fairshare.duckdb"

HARBOR = """
SELECT a.agency_name, d.sales_month, d.revenue_prior, d.revenue_now, d.delta_revenue,
       d.volume_effect, d.mix_effect, d.share_effect, d.fair_share_effect, d.residual
FROM ops.decomposition d JOIN gold.dim_agency a USING (agency_id)
WHERE a.agency_name = 'Harbor Business Travel' AND d.sales_month = DATE '2026-09-01'
"""
DEFINITIONS = "SELECT kpi, display_name, twin_version, retired_note FROM ops.kpi_definitions ORDER BY kpi"


def harbor(con):
    r = con.sql(HARBOR).fetchone()
    keys = ("agency", "month", "prior", "now", "delta", "volume", "mix", "share", "fair_share_effect", "residual")
    return dict(zip(keys, r))


def definitions(con):
    return con.sql(DEFINITIONS).fetchall()


if __name__ == "__main__":
    con = duckdb.connect(str(DB), read_only=True)
    h = harbor(con)
    for k, v in h.items():
        print(f"{k:18s} {v}")
    parts = h["volume"] + h["mix"] + h["share"]
    print(f"{'parts sum':18s} {parts}  (delta {h['delta']}, residual {h['residual']})")
    print("--- in $K, one decimal (the chart's unit)")
    print({k: round(h[k] / 1000, 1) for k in ("prior", "volume", "mix", "share", "now", "fair_share_effect")})
    d = definitions(con)
    print("--- definitions:", len(d))
    for row in d:
        print(row)
