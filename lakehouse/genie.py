"""The Genie Agent (space) over the metric view, created from the API so the setup is code, not clicks.

  FAIRSHARE_BACKEND=databricks python lakehouse/genie.py create     # creates the space, writes GENIE_SPACE_ID into .env
  FAIRSHARE_BACKEND=databricks python lakehouse/genie.py show       # prints the serialized space (to learn the schema, or to review)
  FAIRSHARE_BACKEND=databricks python lakehouse/genie.py benchmarks # adds the 20 benchmark questions with ground-truth SQL to the space
  FAIRSHARE_BACKEND=databricks python lakehouse/genie.py eval       # runs Genie's own evaluation over the benchmarks and prints the results

Scope, deliberately small (accuracy comes from few, well-described sources): the metric view, the agency and market
dimensions, and the pace table. Serialized space format: version 2, checked against the Create Space API reference on Oct 11, 2026.
"""
import json
import os
import re
import sys
import time
import uuid
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from fairshare.dbx import workspace_client  # noqa: E402

TITLE = "fairshare sales metrics"
DESCRIPTION = "Agency sales performance: AA revenue, AA share, fair share (BTS T-100 seat share), share gap, year over year, pace against goal. Synthetic agencies on real seat data."

INSTRUCTIONS = [
    "AA share is revenue based: AA revenue divided by the agency's all-carrier revenue on the same markets and months. Never average pre-computed shares; use the metric view measures.",
    "Fair share is AA's share of scheduled seats on the market (BTS T-100), weighted by the agency's market revenue. Share gap = AA share minus fair share; positive is above fair share.",
    "Use MEASURE() on aa_demo.gold.sales_metrics for every KPI. Year over year (yoy_revenue_pct, aa_revenue_prior_year) is correct at month grain: group by sales_month. For quarters, sum the months of each quarter from the fact grain using the example SQL.",
    "Data covers January 2025 to September 2026. 'Year to date' and '2026' mean sales_month >= '2026-01-01'. The latest month is September 2026.",
    "Pace against goal lives in aa_demo.gold.agency_pace (pace_pct: 100 means on pace to the annual revenue goal, goal spread evenly over twelve months).",
    "Return percentages as percentages with one decimal and money rounded to whole dollars. When the question is ambiguous about the period, ask rather than guess.",
]

SAMPLE_QUESTIONS = [
    "How did Summit Travel Partners do on DFW to ORD in Q3 2026 versus Q3 2025?",
    "Which agencies are below fair share in September 2026, and by how many points?",
    "Who is behind pace against their 2026 goal?",
]


def _lines(s: str):
    return [l for l in s.strip().splitlines()]


def _q(table):
    return {"identifier": table[0], "description": _lines(table[1])}


def example_sqls():
    bench = yaml.safe_load((ROOT / "evals" / "benchmark.yaml").read_text())["questions"]
    picks = {"q04", "q05", "q06", "q09", "q16"}  # the hard patterns: quarter YoY, fair share at a grain, pace, streaks
    out = []
    for q in bench:
        if q["id"] in picks:
            out.append({"id": uuid.uuid4().hex, "question": [q["question"]], "sql": _lines(q["sql"])})
    return out


def serialized(with_benchmarks: bool = False) -> str:
    space = {
        "version": 2,
        "config": {"sample_questions": [{"id": uuid.uuid4().hex, "question": [q]} for q in SAMPLE_QUESTIONS]},
        "data_sources": {
            "metric_views": [{"identifier": "aa_demo.gold.sales_metrics",
                              "description": ["Every KPI defined once: aa_revenue, market_revenue, aa_pax, aa_share, fair_share, share_gap_pts, share_gap_usd, aa_revenue_prior_year, yoy_revenue_pct. Dimensions: agency, agency_type, region, account_manager, market, origin, dest, market_region, sales_month, quarter, year."]}],
            "tables": [
                _q(("aa_demo.gold.dim_agency", "Twelve travel agencies (synthetic): agency_id, agency_name, agency_type (TMC, OTA, Leisure, Consolidator), region (Central, East, West), account_manager.")),
                _q(("aa_demo.gold.dim_market", "Twelve origin-destination markets: market_id, origin, dest, region, aa_hub_origin.")),
                _q(("aa_demo.gold.agency_pace", "Pace against the annual revenue goal by agency and month: ytd_revenue, ytd_goal, pace_pct (100 = on pace).")),
            ],
        },
        "instructions": {
            "text_instructions": [{"id": uuid.uuid4().hex, "content": [t]} for t in INSTRUCTIONS],
            "example_question_sqls": example_sqls(),
        },
    }
    if with_benchmarks:
        bench = yaml.safe_load((ROOT / "evals" / "benchmark.yaml").read_text())["questions"]
        space["benchmarks"] = {"questions": [{"id": uuid.uuid4().hex, "question": [q["question"]],
                                              "answer": [{"format": "SQL", "content": _lines(q["sql"])}]} for q in bench]}
    return json.dumps(space)


def write_env(space_id: str):
    p = ROOT / ".env"
    s = p.read_text()
    host = os.environ["DATABRICKS_HOST"].rstrip("/")
    s = re.sub(r"^GENIE_SPACE_ID=.*$", f"GENIE_SPACE_ID={space_id}", s, flags=re.M)
    s = re.sub(r"^GENIE_SPACE_URL=.*$", f"GENIE_SPACE_URL={host}/genie/rooms/{space_id}", s, flags=re.M)
    p.write_text(s)


def create():
    w = workspace_client()
    wh = os.environ["DATABRICKS_HTTP_PATH"].rsplit("/", 1)[-1]
    sp = w.genie.create_space(warehouse_id=wh, serialized_space=serialized(), title=TITLE, description=DESCRIPTION)
    print("created space", sp.space_id, sp.title)
    write_env(sp.space_id)
    return sp.space_id


def show():
    w = workspace_client()
    sp = w.genie.get_space(os.environ["GENIE_SPACE_ID"], include_serialized_space=True)
    print(json.dumps(json.loads(sp.serialized_space), indent=2)[:6000])


def benchmarks():
    w = workspace_client()
    sid = os.environ["GENIE_SPACE_ID"]
    sp = w.genie.update_space(sid, serialized_space=serialized(with_benchmarks=True))
    print("benchmarks added to", sp.space_id)


def run_eval():
    w = workspace_client()
    sid = os.environ["GENIE_SPACE_ID"]
    r = w.genie.genie_create_eval_run(sid)
    run_id = r.eval_run_id if hasattr(r, "eval_run_id") else getattr(r, "run_id", None)
    print("eval run", run_id, "state", getattr(r, "state", None) or getattr(r, "status", None))
    for _ in range(120):
        time.sleep(10)
        r = w.genie.genie_get_eval_run(sid, run_id)
        state = str(getattr(r, "state", None) or getattr(r, "status", None))
        print("  ", state)
        if any(k in state.upper() for k in ("COMPLETE", "SUCCE", "FAIL", "CANCEL", "ERROR")):
            break
    res = w.genie.genie_list_eval_results(sid, run_id)
    print(res)


if __name__ == "__main__":
    {"create": create, "show": show, "benchmarks": benchmarks, "eval": run_eval}[sys.argv[1]]()
