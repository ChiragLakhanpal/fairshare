"""Builds the lakehouse from the CSVs.

  python lakehouse/run.py                      # local: data/out/fairshare.duckdb (bronze from CSVs, then silver, gold, ops)
  FAIRSHARE_BACKEND=databricks python lakehouse/run.py   # Databricks: 00_bronze (volume to bronze), silver, gold, metric view, ops

Databricks-only files (00_bronze.sql, 03_metric_view.sql) are skipped locally; everything else is portable SQL.
"""
import sys
import time
from pathlib import Path

import os

os.environ["FAIRSHARE_WRITE"] = "1"  # the one process allowed to write the DuckDB file; stop the app first
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from fairshare import db  # noqa: E402

HERE = Path(__file__).parent
OUT = ROOT / "data" / "out"
PORTABLE = ["01_silver.sql", "02_gold.sql", "04_definitions.sql", "06_decomposition.sql"]
DATABRICKS_ONLY = {"00_bronze.sql": "before", "03_metric_view.sql": "after_gold"}
BRONZE_TABLES = ["dim_agency", "dim_corporate", "dim_market", "fact_agency_sales_monthly", "fact_market_capacity", "agency_goals", "fact_corporate_bookings",
                 "crm_contacts", "crm_opportunities", "crm_activities"]


def local_bronze():
    if db.DUCKDB_FILE.exists():
        db.DUCKDB_FILE.unlink()
    for s in ["bronze", "silver", "gold", "ops"]:
        db.execute(f"CREATE SCHEMA IF NOT EXISTS aa_demo.{s}")
    for t in BRONZE_TABLES:
        types = ", types={'ticket_number': 'VARCHAR'}" if t == "fact_corporate_bookings" else ""
        db.execute(f"CREATE OR REPLACE TABLE aa_demo.bronze.{t} AS SELECT * FROM read_csv('{OUT / (t + '.csv')}', header=true{types})")


def run_file(name):
    t0 = time.time()
    for stmt in db.statements(HERE / name):
        t1 = time.time()
        db.execute(stmt)
        if db.is_databricks():
            print(f"  {stmt.splitlines()[0][:70]:70s} {time.time() - t1:4.0f}s")
    print(f"{name}: ok ({time.time() - t0:.1f}s)")


def upload_landing():
    """CSVs to /Volumes/aa_demo/bronze/landing and the agreements to /Volumes/aa_demo/ops/contracts, through the Files API."""
    from fairshare.dbx import workspace_client
    w = workspace_client()
    for t in BRONZE_TABLES:
        f = OUT / f"{t}.csv"
        with open(f, "rb") as fh:
            w.files.upload(f"/Volumes/aa_demo/bronze/landing/{f.name}", fh, overwrite=True)
        print(f"  uploaded {f.name} ({f.stat().st_size // 1024} KB)")
    for f in sorted((ROOT / "data" / "contracts").glob("*.md")):
        with open(f, "rb") as fh:
            w.files.upload(f"/Volumes/aa_demo/ops/contracts/{f.name}", fh, overwrite=True)
        print(f"  uploaded {f.name}")


def run_bronze_databricks():
    """00_bronze.sql in two halves: the objects (catalog, schemas, volumes), the uploads, then the loads."""
    stmts = db.statements(HERE / "00_bronze.sql")
    setup = [x for x in stmts if x.upper().startswith(("CREATE CATALOG", "CREATE SCHEMA", "CREATE VOLUME"))]
    loads = [x for x in stmts if x not in setup]
    for x in setup:
        t1 = time.time()
        db.execute(x)
        print(f"  {x[:70]:70s} {time.time() - t1:4.0f}s")
    print("00_bronze.sql: catalog, schemas, volumes ok")
    upload_landing()
    t0 = time.time()
    for x in loads:
        t1 = time.time()
        db.execute(x)
        print(f"  {x.splitlines()[0][:70]:70s} {time.time() - t1:4.0f}s")
    print(f"00_bronze.sql: bronze tables ok ({time.time() - t0:.1f}s)")


def main():
    if db.is_databricks():
        run_bronze_databricks()
    else:
        local_bronze()
        print("bronze: loaded from CSVs")
    run_file("01_silver.sql")
    run_file("02_gold.sql")
    if db.is_databricks():
        run_file("03_metric_view.sql")
    run_file("04_definitions.sql")
    run_file("06_decomposition.sql")
    for t in ["gold.fact_agency_sales_monthly", "gold.fact_corporate_bookings", "gold.fact_corporate_bookings_weekly", "gold.agency_pace", "ops.kpi_definitions", "ops.decomposition"]:
        n = db.query(f"SELECT COUNT(*) AS n FROM aa_demo.{t}")["n"].iloc[0]
        print(f"  aa_demo.{t}: {n} rows")


if __name__ == "__main__":
    main()
