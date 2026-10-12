"""Parity: the metric view versus the Power BI twin, KPI by KPI, month by month.

  FAIRSHARE_BACKEND=databricks python lakehouse/parity.py             # current twins (expected green)
  FAIRSHARE_BACKEND=databricks python lakehouse/parity.py --retired   # the retired aa_share twin (passenger based): the red run on record

Appends one run to aa_demo.ops.kpi_parity. Needs the metric view, so Databricks only; the app shows the last exported
run offline (app/cache/kpi_parity.csv, written by harness/cache.py).
"""
import sys
import uuid
from datetime import datetime
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from fairshare import db  # noqa: E402

MV = "SELECT agency, sales_month, MEASURE({kpi}) AS value FROM aa_demo.gold.sales_metrics GROUP BY ALL"
TOL = {"aa_revenue": 0.01, "share_gap_usd": 0.01, "aa_share": 1e-6, "fair_share": 1e-6, "share_gap_pts": 1e-4, "yoy_revenue_pct": 1e-6}


def run(retired: bool = False) -> pd.DataFrame:
    if not db.is_databricks():
        raise SystemExit("parity compares against MEASURE() and needs FAIRSHARE_BACKEND=databricks")
    defs = db.query("SELECT kpi, twin_sql, twin_version, twin_sql_retired FROM aa_demo.ops.kpi_definitions WHERE kpi IN ('aa_revenue','aa_share','fair_share','share_gap_pts','share_gap_usd','yoy_revenue_pct')")
    run_id, run_at = uuid.uuid4().hex[:12], datetime.now().isoformat(timespec="seconds")
    out = []
    for d in defs.itertuples():
        twin_sql, version = d.twin_sql, d.twin_version
        if retired and d.twin_sql_retired:
            twin_sql, version = d.twin_sql_retired, "v1 (retired)"
        mv = db.query(MV.format(kpi=d.kpi)).rename(columns={"value": "mv_value"})
        tw = db.query(twin_sql).rename(columns={"value": "twin_value"})
        for f in (mv, tw):
            f["sales_month"] = pd.to_datetime(f["sales_month"]).dt.date
        j = mv.merge(tw, on=["agency", "sales_month"], how="outer")
        j["abs_diff"] = (j["mv_value"].astype(float) - j["twin_value"].astype(float)).abs()
        j["status"] = j["abs_diff"].map(lambda x: "ok" if pd.notna(x) and x <= TOL[d.kpi] else "drift")
        j.loc[j["mv_value"].isna() & j["twin_value"].isna(), "status"] = "ok"   # neither side has a value (first year's YoY)
        j.insert(0, "twin_version", version)
        j.insert(0, "kpi", d.kpi)
        j.insert(0, "run_at", run_at)
        j.insert(0, "run_id", run_id)
        out.append(j)
        print(f"{d.kpi:16s} {version:14s} {len(j):4d} rows  drift: {(j['status'] == 'drift').sum()}")
    res = pd.concat(out, ignore_index=True)
    db.execute("""CREATE TABLE IF NOT EXISTS aa_demo.ops.kpi_parity (
        run_id STRING, run_at STRING, kpi STRING, twin_version STRING, agency STRING, sales_month DATE,
        mv_value DOUBLE, twin_value DOUBLE, abs_diff DOUBLE, status STRING)""")
    values = ", ".join(
        "(" + ", ".join([f"'{r.run_id}'", f"'{r.run_at}'", f"'{r.kpi}'", f"'{r.twin_version}'", "'" + str(r.agency).replace("'", "''") + "'",
                         f"DATE '{r.sales_month}'", "NULL" if pd.isna(r.mv_value) else repr(float(r.mv_value)),
                         "NULL" if pd.isna(r.twin_value) else repr(float(r.twin_value)),
                         "NULL" if pd.isna(r.abs_diff) else repr(float(r.abs_diff)), f"'{r.status}'"]) + ")"
        for r in res.itertuples())
    db.execute(f"INSERT INTO aa_demo.ops.kpi_parity VALUES {values}")
    print(f"run {run_id}: {len(res)} rows, {(res['status'] == 'drift').sum()} drift")
    return res


if __name__ == "__main__":
    run(retired="--retired" in sys.argv)
