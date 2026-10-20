"""The Genie Agent (space) over the metric view, created from the API so the setup is code, not clicks.

  FAIRSHARE_BACKEND=databricks python lakehouse/genie.py create     # creates the space, writes GENIE_SPACE_ID into .env
  FAIRSHARE_BACKEND=databricks python lakehouse/genie.py show       # prints the serialized space (to learn the schema, or to review)
  FAIRSHARE_BACKEND=databricks python lakehouse/genie.py update     # pushes instructions, trusted SQL and the 20 benchmark questions (evals/benchmark.yaml)
  FAIRSHARE_BACKEND=databricks python lakehouse/genie.py eval       # runs Genie's own evaluation over the benchmarks in the space; prints and records the results

Scope, deliberately small (accuracy comes from few, well-described sources): the metric view, the agency and market
dimensions, and the pace table. Serialized space format: version 2, checked against the Create Space API reference on Oct 11, 2026.
The benchmark questions are the same twenty evals/run_benchmark.py uses, so the space's own Benchmarks tab and the repo agree.
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
    "Use MEASURE() on aa_demo.gold.sales_metrics for every KPI. yoy_revenue_pct and aa_revenue_prior_year are ONLY correct when the query groups by sales_month; never select them when grouping by quarter, year or without a month. For a quarter or a year versus the prior one, select aa_revenue for both periods (see the Q3 example) and let the reader compare.",
    "Data covers January 2025 to September 2026. 'Year to date' and '2026' mean sales_month >= '2026-01-01'. The latest month is September 2026.",
    "Pace against goal lives in aa_demo.gold.agency_pace (pace_pct: 100 means on pace to the annual revenue goal, the year-to-date goal is one twelfth of the annual goal for each month the agency reported, so a missing month never counts as zero). pace_pct and attainment_pct are already percentages (68.0 means 68 percent): never multiply them by 100.",
    "sales_month is already the first day of its month: select it as is, keep the name sales_month, and never wrap it in date_trunc.",
    "For a change over time (month over month, year over year) return both the absolute change in dollars and the percent change.",
    "Return percentages as percentages with one decimal and money rounded to whole dollars. When the question is ambiguous about the period, ask rather than guess.",
]

SAMPLE_QUESTIONS = [
    "How did Summit Travel Partners do on DFW to ORD in Q3 2026 versus Q3 2025?",
    "Which agencies are below fair share in September 2026, and by how many points?",
    "Who is behind pace against their 2026 goal?",
]


def _lines(s: str):
    """One element holding the whole text: the API concatenates list elements with no separator (seen Oct 11, 2026)."""
    return [s.strip()]


def _q(table):
    return {"identifier": table[0], "description": _lines(table[1])}


EXAMPLES = [  # trusted SQL for the hard patterns, written against the space's own sources (the metric view and agency_pace)
    ("How did Summit Travel Partners do on DFW to ORD in Q3 2026 versus Q3 2025 (revenue, AA share, fair share, share gap)?",
     """WITH q AS (
  SELECT quarter, MEASURE(aa_revenue) AS aa_revenue, MEASURE(aa_share) AS aa_share, MEASURE(fair_share) AS fair_share,
         MEASURE(share_gap_pts) AS share_gap_pts, MEASURE(aa_pax) AS aa_pax
  FROM aa_demo.gold.sales_metrics
  WHERE agency = 'Summit Travel Partners' AND market = 'DFW-ORD' AND quarter IN ('Q3 2025', 'Q3 2026')
  GROUP BY ALL)
SELECT quarter, ROUND(aa_revenue) AS aa_revenue,
       ROUND((aa_revenue - LAG(aa_revenue) OVER (ORDER BY quarter)) / LAG(aa_revenue) OVER (ORDER BY quarter) * 100, 1) AS revenue_change_pct,
       ROUND(aa_share * 100, 1) AS aa_share_pct, ROUND(fair_share * 100, 1) AS fair_share_pct, ROUND(share_gap_pts, 1) AS share_gap_pts, aa_pax
FROM q ORDER BY quarter
-- the change between the two quarters is computed here so the answer never has to; yoy_revenue_pct is month grain only"""),
    ("In Q3 2026, how far above or below fair share was Summit Travel Partners on DFW to ORD, in points?",
     """SELECT ROUND(MEASURE(aa_share) * 100, 1) AS aa_share_pct, ROUND(MEASURE(fair_share) * 100, 1) AS fair_share_pct, ROUND(MEASURE(share_gap_pts), 1) AS share_gap_pts
FROM aa_demo.gold.sales_metrics
WHERE agency = 'Summit Travel Partners' AND market = 'DFW-ORD' AND quarter = 'Q3 2026'"""),
    ("For August 2026, what was each agency's AA share against its fair share, and the gap in points?",
     """SELECT agency, ROUND(MEASURE(aa_share) * 100, 1) AS aa_share_pct, ROUND(MEASURE(fair_share) * 100, 1) AS fair_share_pct, ROUND(MEASURE(share_gap_pts), 1) AS share_gap_pts
FROM aa_demo.gold.sales_metrics
WHERE sales_month = DATE '2026-08-01'
GROUP BY ALL ORDER BY share_gap_pts DESC"""),
    ("Year over year AA revenue by agency for August 2026 versus August 2025, with the percent change.",
     """SELECT agency, ROUND(MEASURE(aa_revenue)) AS aug_2026, ROUND(MEASURE(aa_revenue_prior_year)) AS aug_2025, ROUND(MEASURE(yoy_revenue_pct) * 100, 1) AS yoy_pct
FROM aa_demo.gold.sales_metrics
WHERE sales_month = DATE '2026-08-01'
GROUP BY ALL ORDER BY yoy_pct DESC"""),
    ("Which agencies are behind pace against their 2026 goal as of September 2026, and at what percent of pace?",
     """SELECT a.agency_name, p.ytd_revenue, p.revenue_goal_usd, p.pace_pct
FROM aa_demo.gold.agency_pace p JOIN aa_demo.gold.dim_agency a ON a.agency_id = p.agency_id
WHERE p.sales_month = DATE '2026-09-01' AND p.pace_pct < 100
ORDER BY p.pace_pct"""),
    ("What is the three-month rolling average of AA revenue for Sunbelt Vacations in 2026? March and April 2026 have no data.",
     """WITH m AS (
  SELECT EXTRACT(MONTH FROM sales_month) AS month_no, MEASURE(aa_revenue) AS aa_revenue
  FROM aa_demo.gold.sales_metrics WHERE agency = 'Sunbelt Vacations' AND year = 2026 GROUP BY ALL)
SELECT month_no, ROUND(aa_revenue) AS aa_revenue,
       ROUND(AVG(aa_revenue) OVER (ORDER BY month_no RANGE BETWEEN 2 PRECEDING AND CURRENT ROW)) AS rolling_3m_avg
FROM m ORDER BY month_no
-- RANGE on the month number only averages months really inside the window; ROWS BETWEEN 2 PRECEDING would silently span a gap"""),
    ("How many agencies were above fair share in September 2026, and how many below?",
     """WITH m AS (
  SELECT agency, MEASURE(aa_share) AS share, MEASURE(fair_share) AS fair
  FROM aa_demo.gold.sales_metrics WHERE sales_month = DATE '2026-09-01' GROUP BY ALL)
SELECT SUM(CASE WHEN share >= fair THEN 1 ELSE 0 END) AS above_fair_share, SUM(CASE WHEN share < fair THEN 1 ELSE 0 END) AS below_fair_share
FROM m
-- counting agencies needs one row per agency first (a CTE), then the CASE sums; MEASURE() itself never counts entities"""),
    ("Which agencies have been below fair share for three or more consecutive months, ending September 2026?",
     """WITH m AS (
  SELECT agency, sales_month, EXTRACT(YEAR FROM sales_month) * 12 + EXTRACT(MONTH FROM sales_month) AS month_no,
         MEASURE(aa_share) AS share, MEASURE(fair_share) AS fair
  FROM aa_demo.gold.sales_metrics WHERE sales_month <= DATE '2026-09-01' GROUP BY ALL),
below AS (SELECT agency, month_no FROM m WHERE share < fair),
isl AS (SELECT agency, month_no, month_no - ROW_NUMBER() OVER (PARTITION BY agency ORDER BY month_no) AS grp FROM below),
runs AS (SELECT agency, MAX(month_no) AS last_no, COUNT(*) AS months_below FROM isl GROUP BY agency, grp)
SELECT agency, months_below FROM runs WHERE last_no = 2026 * 12 + 9 AND months_below >= 3 ORDER BY months_below DESC"""),
]


def example_sqls():
    return [{"id": uuid.uuid4().hex, "question": [q], "sql": [sql]} for q, sql in EXAMPLES]


def benchmark_id(qid: str) -> str:
    """Stable per question (q01..q20), so an update keeps the questions and their past evaluations."""
    return uuid.uuid5(uuid.NAMESPACE_URL, f"fairshare/benchmark/{qid}").hex


def benchmark_questions():
    return yaml.safe_load((ROOT / "evals" / "benchmark.yaml").read_text())["questions"]


def serialized() -> str:
    space = {
        "version": 2,
        "config": {"sample_questions": [{"id": uuid.uuid4().hex, "question": [q]} for q in SAMPLE_QUESTIONS]},
        "data_sources": {
            "metric_views": [{"identifier": "aa_demo.gold.sales_metrics",
                              "description": ["Every KPI defined once: aa_revenue, market_revenue, aa_pax, aa_share, fair_share, share_gap_pts, share_gap_usd, aa_revenue_prior_year, yoy_revenue_pct. Dimensions: agency, agency_type, region, account_manager, market, origin, dest, market_region, sales_month, quarter, year."]}],
            "tables": sorted([  # the API requires tables sorted by identifier
                _q(("aa_demo.gold.dim_agency", "Twelve travel agencies (synthetic): agency_id, agency_name, agency_type (TMC, OTA, Leisure, Consolidator), region (Central, East, West), account_manager.")),
                _q(("aa_demo.gold.dim_market", "Twelve origin-destination markets: market_id, origin, dest, region, aa_hub_origin.")),
                _q(("aa_demo.gold.agency_pace", "Pace against the annual revenue goal by agency and month: ytd_revenue, months_reported, ytd_goal (one twelfth of the goal per month reported), pace_pct (100 = on pace to the full-year goal), attainment_pct (ytd_revenue as a percent of the full-year goal). Both _pct columns are already percentages, 68.0 means 68 percent.")),
            ], key=lambda t: t["identifier"]),
        },
        "instructions": {
            "text_instructions": [{"id": uuid.uuid4().hex, "content": ["\n".join(INSTRUCTIONS)]}],  # the API allows exactly one item
            "example_question_sqls": example_sqls(),
        },
        "benchmarks": {"questions": [{"id": benchmark_id(q["id"]), "question": [q["question"]],
                                      "answer": [{"format": "SQL", "content": _lines(q["sql"])}]} for q in benchmark_questions()]},
    }
    return json.dumps(_sorted(space))


def _sorted(node):
    """The API requires every list sorted by id (or identifier). Applied to the whole tree."""
    if isinstance(node, dict):
        return {k: _sorted(v) for k, v in node.items()}
    if isinstance(node, list):
        items = [_sorted(x) for x in node]
        if items and all(isinstance(x, dict) for x in items):
            key = "id" if all("id" in x for x in items) else ("identifier" if all("identifier" in x for x in items) else None)
            if key:
                items.sort(key=lambda x: x[key])
        return items
    return node


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
    raw = sp.serialized_space or getattr(sp, "serialized_space_export", None)
    print(sp.as_dict() if raw is None else json.dumps(json.loads(raw), indent=2)[:8000])


def update():
    w = workspace_client()
    sid = os.environ["GENIE_SPACE_ID"]
    sp = w.genie.update_space(sid, serialized_space=serialized(), title=TITLE, description=DESCRIPTION)
    print("updated", sp.space_id)


def run_eval():
    """Genie's own evaluation (the space's Benchmarks tab): for each question it generates SQL, runs it and the benchmark SQL,
    compares the result sets and has a judge name the difference. One line per question, then a row in evals/results/README.md
    so the in-space score sits next to the repo runner's."""
    from datetime import datetime
    from fairshare.dbx import warm_warehouse
    w = workspace_client()
    sid = os.environ["GENIE_SPACE_ID"]
    warm_warehouse()
    run = w.genie.genie_create_eval_run(sid)
    print("eval run", run.eval_run_id)
    while (run.eval_run_status.value if run.eval_run_status else "RUNNING") in ("NOT_STARTED", "RUNNING"):
        time.sleep(15)
        run = w.genie.genie_get_eval_run(sid, run.eval_run_id)
        print(f"  {run.eval_run_status.value if run.eval_run_status else '?'}: {run.num_done or 0}/{run.num_questions or 0} done,"
              f" {run.num_correct or 0} correct, {run.num_needs_review or 0} to review")
    by_id = {benchmark_id(q["id"]): q["id"] for q in benchmark_questions()}
    rows, token = [], None
    while True:
        page = w.genie.genie_list_eval_results(sid, run.eval_run_id, page_size=50, page_token=token)
        for r in page.eval_results or []:
            d = w.genie.genie_get_eval_result_details(sid, run.eval_run_id, r.result_id)
            rows.append({"id": by_id.get(r.benchmark_question_id, r.benchmark_question_id), "question": r.question,
                         "assessment": d.assessment.value if d.assessment else None, "reasons": [x.value for x in d.assessment_reasons or []],
                         "genie_sql": next((x.response for x in d.actual_response or [] if x.response_type and x.response_type.value == "SQL"), None)})
        token = page.next_page_token
        if not token:
            break
    rows.sort(key=lambda x: x["id"])
    for x in rows:
        print(f"{x['id']}  {x['assessment'] or '?':13} {x['question'][:80]}" + (f"  [{', '.join(x['reasons'])}]" if x["reasons"] else ""))
    n, good = run.num_questions or len(rows), run.num_correct or sum(x["assessment"] == "GOOD" for x in rows)
    print(f"{good}/{n} correct, {run.num_needs_review or 0} need review")
    results = ROOT / "evals" / "results"
    stamp = datetime.now().isoformat(timespec="seconds")
    (results / f"{stamp.replace(':', '')}-genie-eval.json").write_text(json.dumps({"run_at": stamp, "eval_run_id": run.eval_run_id, "n": n, "correct": good,
                                                                                   "needs_review": run.num_needs_review or 0, "results": rows}, indent=2))
    with (results / "README.md").open("a") as f:
        f.write(f"| {stamp} | Genie's in-space evaluation of the same twenty benchmarks (run {run.eval_run_id}, {run.num_needs_review or 0} need review)"
                f" | databricks | {good / n:.2f} |  |  | (Genie only, Databricks judge) |\n")


if __name__ == "__main__":
    {"create": create, "show": show, "update": update, "benchmarks": update, "eval": run_eval}[sys.argv[1]]()
