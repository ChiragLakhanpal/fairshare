"""The harness as the server needs it: tools that report progress and honour Stop, Genie conversations that continue,
one model client for every viewer, an async ask with history, and the summary blocks behind the first screen."""
import asyncio
import sys
from pathlib import Path
from types import SimpleNamespace

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from fairshare import db, dbx  # noqa: E402
from harness import agent as harness_agent, facts, summary, tools  # noqa: E402


def test_instrumented_tool_emits_status_then_tool_then_model():
    events = []
    facts.reset(on_event=events.append)
    out = tools.run_sql.func(sql="SELECT COUNT(*) AS n FROM aa_demo.gold.dim_agency")
    assert "rows" in out
    kinds = [(e["type"], e.get("phase")) for e in events]
    assert kinds == [("status", "sql"), ("tool", None), ("status", "model")]
    assert events[0]["tool"] == "run_sql" and "sql" in events[0]["args"]
    assert events[-1]["ms"] >= 0


def test_instrumented_tool_stops_when_cancelled():
    ctx = facts.reset()
    ctx.cancel.set()
    with pytest.raises(facts.Cancelled):
        tools.run_sql.func(sql="SELECT 1 AS n")


def test_search_returns_scored_hits_with_file_and_page():
    hits = tools._search("Summit", "share falls below 45% for two consecutive quarters")
    assert hits and hits[0][1] == "summit-travel-partners.md" and hits[0][2] == 2 and "45%" in hits[0][3]


class FakeWait:
    def __init__(self, conversation_id, message_id, msg):
        self.conversation_id, self.message_id, self.msg = conversation_id, message_id, msg

    def result(self, timeout=None, callback=None):
        if callback:
            callback(self.msg)
        return self.msg


def _fake_workspace(calls):
    def msg(cid, mid):
        return SimpleNamespace(conversation_id=cid, message_id=mid, attachments=[
            SimpleNamespace(text=SimpleNamespace(content="Genie says"), query=SimpleNamespace(query="SELECT 1 AS n"), attachment_id="a1")])

    class Genie:
        def start_conversation(self, space_id, content):
            calls.append(("start", content))
            return FakeWait("c-new", "m1", msg("c-new", "m1"))

        def create_message(self, space_id, conversation_id, content):
            calls.append(("continue", conversation_id, content))
            if conversation_id == "expired":
                raise RuntimeError("404 Not Found: conversation")
            return FakeWait(conversation_id, "m2", msg(conversation_id, "m2"))

        def get_message_attachment_query_result(self, space_id, conversation_id, message_id, attachment_id):
            sr = SimpleNamespace(manifest=SimpleNamespace(schema=SimpleNamespace(columns=[SimpleNamespace(name="n")]), total_chunk_count=1),
                                 result=SimpleNamespace(data_array=[["1"]]), statement_id="s1")
            return SimpleNamespace(statement_response=sr)

    return SimpleNamespace(genie=Genie(), config=SimpleNamespace(host="https://example.cloud.databricks.com"))


@pytest.fixture
def genie(monkeypatch):
    calls = []
    monkeypatch.setenv("FAIRSHARE_BACKEND", "databricks")
    monkeypatch.setenv("GENIE_SPACE_ID", "space-1")
    monkeypatch.setenv("DATABRICKS_HOST", "https://example.cloud.databricks.com")
    monkeypatch.setattr("fairshare.dbx.workspace_client", lambda: _fake_workspace(calls))
    monkeypatch.setattr("fairshare.dbx.warm_warehouse", lambda *a, **k: "RUNNING")
    return calls


def test_genie_ask_starts_then_continues_a_conversation(genie):
    facts.reset()
    text, df, sql, cid, mid = tools._genie_ask("q1")
    assert (text, sql, cid, mid) == ("Genie says", "SELECT 1 AS n", "c-new", "m1") and df["n"].iloc[0] == 1
    _, _, _, cid2, mid2 = tools._genie_ask("q2", conversation_id="c-new")
    assert (cid2, mid2) == ("c-new", "m2")
    assert [c[0] for c in genie] == ["start", "continue"] and genie[1][1] == "c-new"


def test_genie_ask_falls_back_when_the_conversation_is_gone(genie):
    facts.reset()
    _, _, _, cid, _ = tools._genie_ask("q", conversation_id="expired")
    assert cid == "c-new" and [c[0] for c in genie] == ["continue", "start"]


def test_ask_metrics_records_genie_ids_and_progress(genie):
    events = []
    ctx = facts.reset(on_event=events.append)
    tools.ask_metrics.func(question="How did Summit do?")
    assert ctx.genie_conversation_id == "c-new"
    call = ctx.calls[-1]
    assert call.genie["conversation_id"] == "c-new" and call.genie["message_id"] == "m1" and call.genie["url"].endswith("/genie/rooms/space-1/chats/c-new")
    phases = [e.get("phase") for e in events if e["type"] == "status"]
    assert phases == ["warehouse", "genie", "model"]  # one Genie step, emitted once the conversation exists, carrying the question and the link
    g = [e for e in events if e["type"] == "status" and e.get("genie")][0]
    assert g["genie"]["conversation_id"] == "c-new" and g["tool"] == "ask_metrics" and g["args"] == {"question": "How did Summit do?"}
    tools.ask_metrics.func(question="And FareHub?")
    assert genie[-1][0] == "continue" and genie[-1][1] == "c-new"


def test_genie_wait_honours_cancel(genie):
    ctx = facts.reset()
    ctx.cancel.set()
    with pytest.raises(facts.Cancelled):
        tools._genie_ask("q")


def test_make_client_reads_the_viewer_token_per_request(monkeypatch):
    monkeypatch.setenv("FAIRSHARE_MODEL", "databricks")
    monkeypatch.setenv("DATABRICKS_HOST", "https://example.cloud.databricks.com")
    monkeypatch.setenv("DATABRICKS_MODEL", "databricks-qwen3-next-80b-a3b-instruct")
    monkeypatch.setenv("DATABRICKS_TOKEN", "dapi-test")  # never the browser OAuth flow in a test
    monkeypatch.setattr("databricks.sdk.config.Config._resolve_host_metadata", lambda self: None)
    dbx._cached_client.cache_clear()
    client = harness_agent.make_client()
    inner = next(getattr(client, a) for a in ("client", "_client", "async_client") if getattr(client, a, None) is not None)
    assert callable(inner._api_key_provider)

    async def refresh():  # the async OpenAI client awaits the provider on every request (openai 3.29, _client.py:1024)
        return await inner._refresh_api_key()

    with dbx.bind("tok-1"):
        assert asyncio.run(refresh()) == "tok-1"
    with dbx.bind("tok-2"):
        assert asyncio.run(refresh()) == "tok-2"


class StubAgent:
    def __init__(self, text):
        self.text, self.seen = text, []

    async def run(self, messages):
        self.seen.append(messages)
        await asyncio.sleep(0)
        return SimpleNamespace(text=self.text)


def test_ask_async_passes_history_and_verifies():
    stub = StubAgent("Harbor sold $330K in September.")
    facts.reset()

    async def go():
        facts.current().record("run_sql", {"sql": "x"}, pd.DataFrame({"aa_revenue": [330114.0]}))
        return await harness_agent.ask_async("Why?", stub, history=[{"role": "user", "text": "Hi"}, {"role": "assistant", "text": "Hello"}])

    a = asyncio.run(go())
    msgs = stub.seen[0]
    assert [m.role.value if hasattr(m.role, "value") else m.role for m in msgs] == ["user", "assistant", "user"]
    assert msgs[-1].text == "Why?"
    assert a.verification.ok and a.text.startswith("Harbor sold")
    assert a.elapsed_ms >= 0


def test_sync_ask_still_works_for_the_cli():
    stub = StubAgent("No numbers here.")
    a = harness_agent.ask("hello", stub)
    assert a.text == "No numbers here." and a.verification.ok


def test_check_scope_rejects_injection_and_bad_months():
    with pytest.raises(ValueError):
        summary._check_scope("Central' OR '1'='1", "2026-09")
    with pytest.raises(ValueError):
        summary._check_scope("All", "2026-13")
    with pytest.raises(ValueError):
        summary._check_scope("All", "2024-01")
    assert summary._check_scope("All", "2026-09") == ("All", "2026-09")
    assert summary._check_scope("East", "2026-08-01") == ("East", "2026-08")


def test_build_facts_all_regions_has_the_first_screen_blocks():
    facts.reset()
    f = summary.build_facts("All", "2026-09")
    r = f["region"].iloc[0]
    assert r["aa_revenue"] == 4492373 and r["aa_share_pct"] == 37.8 and r["fair_share_pct"] == 39.0
    assert f["pace"].iloc[0]["pace_pct"] == 139.1
    assert list(f["movers"]["agency"])[:2] == ["Harbor Business Travel", "FareHub Online"] and len(f["movers"]) == 3
    assert f["movers"].iloc[0]["share_chg_pts"] == -10.1
    assert set(f["behind_pace"]["agency_name"]) == {"Harbor Business Travel", "FareHub Online"}
    assert "agency_id" in f["agencies"].columns


def test_headline_is_deterministic_prose():
    facts.reset()
    f = summary.build_facts("All", "2026-09")
    assert summary.headline(f, "2026-09") == "September closed ahead of pace and a little under fair share."
    f2 = summary.build_facts("West", "2026-09")
    assert summary.headline(f2, "2026-09") == "September closed ahead of pace and under fair share by 12.8 points."


def test_template_brief_still_verifies_for_a_region_and_for_all():
    for region in ("Central", "All"):
        res = asyncio.run(summary.run_async(region, "2026-09"))
        assert res["badges"] and not res["flagged"], (region, res["flagged"])


def test_save_then_load_a_brief(monkeypatch, tmp_path):
    monkeypatch.setattr(db, "STATE_FILE", tmp_path / "state.duckdb")
    res = summary.run("East", "2026-08")
    summary.save(res, status="approved")
    row = summary.load(res["run_id"])
    assert row["status"] == "approved" and row["region"] == "East" and row["verified_text"] == res["verified_text"]
    assert summary.load("000000000000") is None


def test_benchmark_genie_run_unpacks_the_genie_tuple(monkeypatch):
    import importlib.util
    spec = importlib.util.spec_from_file_location("run_benchmark", ROOT / "evals" / "run_benchmark.py")
    rb = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(rb)
    df = pd.DataFrame({"n": [12]})
    monkeypatch.setattr("harness.tools._genie_ask", lambda q, conversation_id=None: ("Genie says", df, "SELECT 12 AS n", "c1", "m1"))
    monkeypatch.setattr(rb.time, "sleep", lambda s: None)
    out = rb.genie_run([{"id": "q0", "question": "How many agencies?", "sql": "SELECT COUNT(*) AS n FROM aa_demo.gold.dim_agency"}])
    assert out[0]["error"] is None and out[0]["pass"] is True and out[0]["genie_sql"] == "SELECT 12 AS n"
