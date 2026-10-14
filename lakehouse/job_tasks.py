"""The Python tasks of the nightly job (databricks.yml), run as Python script tasks on serverless compute.

  job_tasks.py parity                      metric view vs the twins, one run appended to ops.kpi_parity; drift fails the task
  job_tasks.py summary [databricks|none]   the Monday draft for every region, latest closed month, status draft
  --root <path>                            the synced repo root (the bundle passes it; locally the file's own location is used)

Inside the job there is no warehouse connection and no token: SQL runs on the task's own Spark session
(FAIRSHARE_BACKEND=spark) and the model, when asked for, is the workspace's serving endpoint with the job's identity.
Locally the same file runs against DuckDB (FAIRSHARE_BACKEND=duckdb job_tasks.py summary) with the template writer.
"""
import os
import sys
from pathlib import Path

os.environ.setdefault("FAIRSHARE_BACKEND", "spark")
if "--root" in sys.argv:  # serverless runs this file through exec() in a kernel, where __file__ is undefined: the bundle passes the synced repo root
    i = sys.argv.index("--root")
    ROOT = Path(sys.argv[i + 1])
    del sys.argv[i:i + 2]
else:
    ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(1, str(ROOT / "lakehouse"))
from fairshare import db  # noqa: E402


def latest_month() -> str:
    return str(db.query("SELECT MAX(sales_month) AS m FROM aa_demo.gold.fact_agency_sales_monthly")["m"].iloc[0])[:7]


def regions() -> list[str]:
    return db.query("SELECT DISTINCT region FROM aa_demo.gold.dim_agency ORDER BY region")["region"].tolist()


def parity_task():
    import parity
    res = parity.run()
    drift = res[res["status"] == "drift"]
    if len(drift):  # a definition that disagrees with its twin fails the job: no Monday draft, a mail instead
        raise SystemExit(f"parity drift on {sorted(drift['kpi'].unique())}: {len(drift)} rows")


def summary_task(model: str):
    os.environ["FAIRSHARE_MODEL"] = model
    from harness import summary
    writer = summary.make_writer() if model != "none" else None
    month = latest_month()
    for region in regions():
        res = summary.run(region, month, writer)
        summary.save(res, "draft")
        print(f"\n{region} {month}, run {res['run_id']} ({res['model']}): {len(res['badges'])} sentences, {len(res['flagged'])} removed")
        print(res["verified_text"])
        for f in res["flagged"]:
            print("  removed:", f)


if __name__ == "__main__":
    task = sys.argv[1] if len(sys.argv) > 1 else ""
    if task == "parity":
        parity_task()
    elif task == "summary":
        summary_task(sys.argv[2] if len(sys.argv) > 2 else "none")
    else:
        raise SystemExit("usage: job_tasks.py parity | summary [databricks|none]")
