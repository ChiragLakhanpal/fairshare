"""The checks that fail if the logic breaks. Runs against the local DuckDB build (python lakehouse/run.py first).

  .venv/bin/pytest evals -q
"""
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from fairshare import db  # noqa: E402
from harness import facts, summary  # noqa: E402
from harness.tools import explain_change, run_sql, search_contracts  # noqa: E402
from harness.verifier import FactPool, verify  # noqa: E402


def test_silver_fixes_the_two_traps():
    bronze = db.query("SELECT COUNT(*) n FROM aa_demo.bronze.fact_corporate_bookings")["n"].iloc[0]
    silver = db.query("SELECT COUNT(*) n, COUNT(DISTINCT ticket_number) t FROM aa_demo.silver.fact_corporate_bookings").iloc[0]
    assert bronze - silver["n"] == 6, "six duplicate tickets are planted; silver must drop exactly them"
    assert silver["n"] == silver["t"]
    channels = set(db.query("SELECT DISTINCT channel FROM aa_demo.silver.fact_corporate_bookings")["channel"])
    assert channels == {"NDC", "GDS", "OTA", "Direct"}, channels


def test_decomposition_parts_sum_to_the_total():
    d = db.query("SELECT residual, volume_effect, mix_effect, share_effect, delta_revenue FROM aa_demo.ops.decomposition")
    assert len(d) == 106  # 12 agencies x 9 months of 2026, minus Sunbelt's two missing months
    assert d["residual"].abs().max() < 0.05
    assert ((d["volume_effect"] + d["mix_effect"] + d["share_effect"] - d["delta_revenue"]).abs() < 0.05).all()


def test_harbor_august_is_a_share_story():
    facts.reset()
    text = explain_change.func(agency="Harbor", month="2026-08")
    s = facts.current().calls[0].preview.iloc[0]
    assert s["delta_pct"] < -10 and s["share_effect"] < 0 and abs(s["share_effect"]) > abs(s["volume_effect"])
    assert abs(s["fair_share_now_pct"] - s["fair_share_prior_pct"]) < 2, "AA capacity barely moved; the story is the agency"
    assert "parts_sum" in text


def test_run_sql_is_read_only():
    facts.reset()
    assert run_sql.func(sql="DROP TABLE aa_demo.gold.dim_agency").startswith("Rejected")
    assert run_sql.func(sql="DELETE FROM aa_demo.gold.dim_agency").startswith("Rejected")
    assert "rows" in run_sql.func(sql="SELECT COUNT(*) AS n FROM aa_demo.gold.dim_agency")


def test_contract_clause_with_page():
    facts.reset()
    out = search_contracts.func(agency="Summit", topic="share falls below 45% for two consecutive quarters")
    assert "summit-travel-partners.md, page 2" in out and "45%" in out


def test_verifier_flags_unsupported_numbers():
    pool = FactPool()
    pool.add_frame(pd.DataFrame({"aa_revenue": [2087431.52], "aa_share": [0.5271], "share_gap_pts": [14.25], "delta_pct": [-15.5]}), "q")
    v = verify("Revenue $2.1M, share 52.7%, 14 points ahead, down 15.5%. Engagement rose 12%.", pool)
    assert [s.verified for s in v.sentences] == [True, False]
    assert "12%" in v.flagged[0]["reason"]


def test_template_summary_verifies_clean():
    res = summary.run("Central", "2026-09")
    assert res["badges"] and not res["flagged"]
    res = summary.run("East", "2026-08")
    assert res["badges"] and not res["flagged"], res["flagged"]


def test_viewer_token_wins_inside_the_apps_runtime(monkeypatch):
    """The Apps runtime exports the app's own client id and secret next to the viewer's forwarded token; the SDK must be
    told which to use, or every page dies with RequestError (Oct 13, 2026)."""
    from fairshare import dbx
    monkeypatch.setenv("DATABRICKS_CLIENT_ID", "the-app")
    monkeypatch.setenv("DATABRICKS_CLIENT_SECRET", "not-a-real-secret")
    monkeypatch.setenv("DATABRICKS_HOST", "https://example.cloud.databricks.com")
    monkeypatch.delenv("DATABRICKS_TOKEN", raising=False)
    monkeypatch.setattr("databricks.sdk.config.Config._resolve_host_metadata", lambda self: None)  # offline: skip the SDK's host probe
    dbx.set_user_token("viewer-token")
    try:
        assert dbx.workspace_client().config.auth_type == "pat"
        assert dbx.header_factory()() == {"Authorization": "Bearer viewer-token"}
        assert dbx.bearer_token() == "viewer-token"
    finally:
        dbx.set_user_token(None)


def test_job_tasks_pick_the_latest_closed_month_and_every_region():
    """lakehouse/job_tasks.py drafts one summary per region for the newest month in gold (the job sets the spark backend;
    conftest already set duckdb, so setdefault leaves it)."""
    sys.path.insert(0, str(ROOT / "lakehouse"))
    import job_tasks
    assert job_tasks.latest_month() == "2026-09"
    assert job_tasks.regions() == ["Central", "East", "West"]


def test_bundle_runs_every_sql_file_in_the_lakehouse():
    """A new or renamed lakehouse SQL file must appear as a task in databricks.yml, in the same order run.py uses."""
    import yaml
    job = yaml.safe_load((ROOT / "databricks.yml").read_text())["resources"]["jobs"]["fairshare_nightly"]
    in_job = [t["sql_task"]["file"]["path"] for t in job["tasks"] if "sql_task" in t]
    on_disk = sorted(f"lakehouse/{p.name}" for p in (ROOT / "lakehouse").glob("0*.sql"))
    assert in_job == on_disk
    assert {t["spark_python_task"]["parameters"][0] for t in job["tasks"] if "spark_python_task" in t} == {"parity", "summary"}


def test_aio_run_works_inside_a_running_loop():
    """A serverless job task runs inside a kernel whose event loop is already running (Oct 14, 2026)."""
    import asyncio
    from harness import aio

    async def answer():
        await asyncio.sleep(0)
        return 42

    assert aio.run(answer()) == 42  # the laptop and Streamlit case: no loop on this thread

    async def kernel():
        return aio.run(answer())  # called from inside a running loop

    assert asyncio.run(kernel()) == 42


def test_app_deploy_ships_the_server_not_streamlit():
    """The Databricks App runs the FastAPI server over the React build; the Streamlit pages never go up again."""
    import yaml
    sys.path.insert(0, str(ROOT / "lakehouse"))
    import app_deploy
    assert "server" in app_deploy.INCLUDE and "web/dist" in app_deploy.INCLUDE and "app/cache" in app_deploy.INCLUDE
    assert "app" not in app_deploy.INCLUDE and ".streamlit" not in app_deploy.INCLUDE and "docs" not in app_deploy.INCLUDE
    reqs = app_deploy.APP_REQUIREMENTS
    assert "fastapi" in reqs and "uvicorn" in reqs and "sse-starlette" in reqs and "streamlit" not in reqs
    manifest = yaml.safe_load((ROOT / "app.yaml").read_text())
    assert manifest["command"] == ["python", "-m", "server.main"]
    assert not any(e["name"].startswith("STREAMLIT") for e in manifest["env"])


def test_crm_stand_in_tables_load():
    """Synthetic Dynamics-shaped tables: a contact for every agency, the planted Harbor trap, a last touch for everyone."""
    c = db.query("SELECT COUNT(*) AS n, COUNT(DISTINCT agency_id) AS a FROM aa_demo.gold.crm_contacts").iloc[0]
    assert c["a"] == 12 and c["n"] >= 12
    o = db.query("SELECT agency_id, opp_name, stage, health FROM aa_demo.gold.crm_opportunities WHERE agency_id = 5 AND opp_name LIKE '%renewal%'").iloc[0]
    assert o["stage"] == "Negotiate" and o["health"] == "On track"  # the CRM says fine while share collapsed
    last = db.query("SELECT agency_id, MAX(happened_at) AS last_touch FROM aa_demo.gold.crm_activities GROUP BY ALL")
    assert len(last) == 12 and str(last["last_touch"].min()) >= "2026-07-01"


def test_state_tables_map_every_ops_name(tmp_path, monkeypatch):
    """The local state file stands in for every aa_demo.ops table the app writes, not only summaries."""
    monkeypatch.setattr(db, "STATE_FILE", tmp_path / "s.duckdb")
    db.state_execute(["CREATE TABLE IF NOT EXISTS aa_demo.ops.crm_activities (activity_id STRING, agency_id INT)",
                      "INSERT INTO aa_demo.ops.crm_activities VALUES ('a', 5)"])
    assert db.state_query("SELECT COUNT(*) AS n FROM aa_demo.ops.crm_activities")["n"].iloc[0] == 1
