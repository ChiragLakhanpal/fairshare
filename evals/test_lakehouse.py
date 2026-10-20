"""The checks that fail if the logic breaks. Runs against the local DuckDB build (python lakehouse/run.py first).

  .venv/bin/pytest evals -q
"""
import ast
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
    assert job_tasks.managers() == ["Dana Whitfield", "Marcus Lee", "Priya Raman", "Tom Okafor"]


def test_agents_task_offline_leaves_six_runs_waiting(tmp_path, monkeypatch):
    """The nightly agents task: a pack per manager, the watch, the CRM check; every run saved for the app to show."""
    monkeypatch.setattr(db, "STATE_FILE", tmp_path / "state.duckdb")
    sys.path.insert(0, str(ROOT / "lakehouse"))
    import job_tasks
    from harness import agents
    job_tasks.agents_task("none")
    heads = agents.list_runs(10)
    assert len(heads) == 6 and {h["agent"] for h in heads} == {"precall", "watch", "mismatch"}
    assert all(h["status"] in ("needs_approval", "approved") for h in heads) and sum(h["needs_approval"] for h in heads) >= 12


def test_bundle_runs_every_sql_file_in_the_lakehouse():
    """A new or renamed lakehouse SQL file must appear as a task in databricks.yml, in the same order run.py uses."""
    import yaml
    job = yaml.safe_load((ROOT / "databricks.yml").read_text())["resources"]["jobs"]["fairshare_nightly"]
    in_job = [t["sql_task"]["file"]["path"] for t in job["tasks"] if "sql_task" in t]
    on_disk = sorted(f"lakehouse/{p.name}" for p in (ROOT / "lakehouse").glob("0*.sql"))
    assert in_job == on_disk
    assert {t["spark_python_task"]["parameters"][0] for t in job["tasks"] if "spark_python_task" in t} == {"parity", "summary", "agents"}


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


def test_clause_quotes_are_verbatim():
    """Every extracted clause quotes its agreement word for word on the page it cites, so the citation can be checked."""
    import re
    from harness.tools import _pages
    rows = db.query("SELECT file, page, quote FROM aa_demo.gold.contract_clauses")
    assert len(rows) >= 16
    squash = lambda s: re.sub(r"\s+", " ", s).strip()
    for r in rows.itertuples():
        pages = {p: squash(t) for p, t in _pages(ROOT / "data" / "contracts" / r.file)}
        assert squash(r.quote)[:60] in pages[int(r.page)], (r.file, r.page, r.quote[:60])


def test_agreement_checks_cover_every_clause_and_month():
    n = db.query("SELECT COUNT(DISTINCT clause_id) AS c, COUNT(DISTINCT as_of) AS m, COUNT(*) AS n FROM aa_demo.ops.agreement_checks").iloc[0]
    assert n["m"] == 9 and n["n"] == n["c"] * n["m"]  # January to September 2026, one row per clause per month
    assert set(db.query("SELECT DISTINCT status FROM aa_demo.ops.agreement_checks")["status"]) <= {"ok", "watch", "breached", "not_checkable"}


def test_harbor_commitment_and_summit_share_clauses():
    h = db.query("""SELECT status, value, threshold, dollars FROM aa_demo.ops.agreement_checks
                    WHERE agency_id = 5 AND clause_type = 'annual_commitment' AND as_of = DATE '2026-09-01' ORDER BY dollars DESC""").iloc[0]
    assert h["value"] is not None and h["dollars"] > 0 and h["status"] in ("ok", "watch", "breached")
    s = db.query("""SELECT status, quarters_below FROM aa_demo.ops.agreement_checks
                    WHERE agency_id = 1 AND clause_type = 'share_floor_quarters' AND as_of = DATE '2026-09-01'""").iloc[0]
    assert s["status"] == "ok" and s["quarters_below"] == 0


def test_app_deploy_thinker_switch_puts_the_key_in_a_secret_resource(monkeypatch):
    """FAIRSHARE_APP_THINKER=azure names the thinking model in the App's env and reads the key from a secret scope resource;
    the key itself never appears in the manifest."""
    sys.path.insert(0, str(ROOT / "lakehouse"))
    import app_deploy
    monkeypatch.delenv("FAIRSHARE_APP_THINKER", raising=False)
    assert "FAIRSHARE_THINKER" not in app_deploy.manifest().decode() and not any(r.name == "azure_key" for r in app_deploy.resources())
    monkeypatch.setenv("FAIRSHARE_APP_THINKER", "azure")
    monkeypatch.setenv("AZURE_OPENAI_ENDPOINT", "https://example.openai.azure.com/openai/v1")
    monkeypatch.setenv("AZURE_OPENAI_DEPLOYMENT", "gpt-5-mini")
    monkeypatch.setenv("AZURE_OPENAI_API_KEY", "not-a-real-key")
    m = app_deploy.manifest().decode()
    assert "FAIRSHARE_THINKER" in m and "valueFrom: azure_key" in m and "gpt-5-mini" in m and "not-a-real-key" not in m
    assert any(r.name == "azure_key" and r.secret.scope == "fairshare" and r.secret.key == "azure-openai-key" for r in app_deploy.resources())


def test_decimal_columns_from_the_warehouse_become_numbers():
    """The SQL connector hands DECIMAL columns over as decimal.Decimal objects; the verifier only reads numeric columns (Oct 15, 2026:
    every live pre-call page lost its seats sentence to "no query supports 2%, 1.7%, 0.8%")."""
    import decimal
    df = pd.DataFrame({"seats_change_pct": [decimal.Decimal("2.0"), decimal.Decimal("1.7"), None], "market": ["DCA-BOS", "CLT-LGA", "DFW-DCA"], "n": [1, 2, 3]})
    out = db.numeric(df)
    assert pd.api.types.is_float_dtype(out["seats_change_pct"]) and out["seats_change_pct"].iloc[0] == 2.0 and pd.isna(out["seats_change_pct"].iloc[2])
    assert not pd.api.types.is_numeric_dtype(out["market"]) and pd.api.types.is_integer_dtype(out["n"])
    pool = FactPool()
    pool.add_frame(out, "schedule")
    assert verify("DCA-BOS up 2%, CLT-LGA up 1.7%.", pool).ok


def test_literal_keeps_apostrophes_and_backslashes(monkeypatch):
    """Databricks SQL joins adjacent string literals, so 'AA''s' is stored as "AAs" (Oct 19, 2026: "On the agencys top markets" on the
    stored pre-call pages). Text built into a statement by hand goes through db.literal, which escapes for the backend it will run on."""
    tricky = 'On the agency\'s "top" markets, a\\b'
    # DuckDB: the literal round-trips through a real query
    assert db.query(f"SELECT {db.literal(tricky)} AS v")["v"].iloc[0] == tricky
    # Databricks: Spark joins adjacent literals ('AA''s' becomes "AAs"), so a quote is escaped with a backslash
    monkeypatch.setattr(db, "is_databricks", lambda: True)
    assert db.literal("agency's") == "'agency\\'s'"
    assert db.literal("a\\b") == "'a\\\\b'"


# Oct 19, 2026: text built into a statement by hand doubled its quotes, and Databricks stored "AAs" for 'AA''s' on 37 of 44 saved runs. The fix is that
# fairshare.db.literal is the only place that escapes a quote or a backslash. This reads the Python under the four folders that write SQL and fails on
# any other: a replace that works on a single quote or a backslash, a replace that writes two quotes or a backslash and a quote, or chr(39).
def hand_escapes(source):
    """The lines of Python source that build a SQL string literal by hand. Read as syntax, so a comment or a string that only mentions
    an escape is left alone."""
    quote, slash = "'", "\\"

    def text(node):
        return node.value if isinstance(node, ast.Constant) and isinstance(node.value, str) else None

    lines = set()
    for node in ast.walk(ast.parse(source)):
        if not isinstance(node, ast.Call):
            continue
        if isinstance(node.func, ast.Name) and node.func.id == "chr" and [getattr(a, "value", None) for a in node.args] == [39]:
            lines.add(node.lineno)  # chr(39) is a single quote, written to dodge the quote in the source
        elif isinstance(node.func, ast.Attribute) and node.func.attr == "replace" and len(node.args) >= 2:
            old, new = text(node.args[0]), text(node.args[1])
            if old in (quote, slash) or new in (quote * 2, slash + quote):
                lines.add(node.lineno)
    return sorted(lines)


def hand_built_literals(root):
    """Every such line under harness/, server/, lakehouse/ and fairshare/ of `root`, except inside db.literal, where the escape belongs."""
    found = []
    for folder in ("harness", "server", "lakehouse", "fairshare"):
        for path in sorted((root / folder).rglob("*.py")):
            source = path.read_text(encoding="utf-8")
            allowed = range(0)
            if path == root / "fairshare" / "db.py":
                literal = next(n for n in ast.walk(ast.parse(source)) if isinstance(n, ast.FunctionDef) and n.name == "literal")
                allowed = range(literal.lineno, literal.end_lineno + 1)
            found += [f"{path.relative_to(root).as_posix()}:{n}" for n in hand_escapes(source) if n not in allowed]
    return found


BY_HAND = r"""
x = s.replace("'", "''")
x = s.replace('\'', "\\'")
x = s.replace(chr(39), chr(39) * 2)
q = chr(39)
x = s.replace("\\", "\\\\")
x = s.replace(quote, "''")
x = s.replace(quote, "\\'")
"""
NOT_BY_HAND = r"""
x = db.literal(s)
x = s.replace("_", " ")
x = s.replace("-", " ")
x = f"{a} 'quoted' {b}"
x = "it's"
# s.replace("'", "''")
"""


def test_the_scan_sees_every_way_to_escape_a_quote_by_hand():
    for line in BY_HAND.strip().splitlines():
        assert hand_escapes(line + "\n") == [1], f"the scan should flag: {line}"
    for line in NOT_BY_HAND.strip().splitlines():
        assert hand_escapes(line + "\n") == [], f"the scan should leave alone: {line}"


def test_the_scan_walks_the_four_folders_and_spares_only_db_literal(tmp_path):
    escape = 'def f(s):\n    return s.replace("\'", "\'\'")\n'
    for folder in ("harness", "server", "lakehouse", "fairshare", "data"):
        (tmp_path / folder).mkdir()
        (tmp_path / folder / "m.py").write_text(escape, encoding="utf-8")
    assert hand_built_literals(tmp_path) == [f"{folder}/m.py:2" for folder in ("harness", "server", "lakehouse", "fairshare")]  # data/ is not one of the four
    (tmp_path / "fairshare" / "db.py").write_text(escape.replace("def f", "def literal") + "\n\n" + escape.replace("def f", "def other"), encoding="utf-8")
    found = hand_built_literals(tmp_path)
    assert "fairshare/db.py:2" not in found and "fairshare/db.py:6" in found, found  # the escape inside literal() is the one allowed


def test_nothing_builds_a_sql_literal_by_hand_outside_db_literal():
    found = hand_built_literals(ROOT)
    assert not found, "build the literal with fairshare.db.literal, which escapes for the backend: " + ", ".join(found)


def test_the_jobs_foundry_env_comes_from_the_secret_scope(monkeypatch):
    import importlib.util
    spec = importlib.util.spec_from_file_location("job_tasks", ROOT / "lakehouse" / "job_tasks.py")
    jt = importlib.util.module_from_spec(spec)
    monkeypatch.setenv("FAIRSHARE_BACKEND", "duckdb")
    spec.loader.exec_module(jt)
    for var in ("FAIRSHARE_THINKER", "AZURE_OPENAI_API_KEY", "FOUNDRY_PROJECT_ENDPOINT"):
        monkeypatch.delenv(var, raising=False)
    jt.foundry_env(get={"azure-openai-key": "k", "foundry-endpoint": "https://p.services.ai.azure.com/api/projects/x"}.__getitem__)
    import os
    assert os.environ["FAIRSHARE_THINKER"] == "foundry" and os.environ["AZURE_OPENAI_API_KEY"] == "k"
    assert os.environ["FOUNDRY_PROJECT_ENDPOINT"].endswith("/projects/x")
