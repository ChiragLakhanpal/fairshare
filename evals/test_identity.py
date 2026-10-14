"""Per-request identity and run context: two viewers in flight at once must never see each other's token,
fact pool or tool calls (the Streamlit app kept both as process globals)."""
import asyncio
import contextvars
import sys
import threading
from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from fairshare import db, dbx  # noqa: E402
from harness import facts  # noqa: E402


def test_user_token_is_per_context():
    seen = {}

    def worker(name):
        with dbx.bind(f"token-{name}"):
            seen[name] = dbx.user_token()

    threads = [threading.Thread(target=worker, args=(n,)) for n in ("a", "b")]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert seen == {"a": "token-a", "b": "token-b"}
    assert dbx.user_token() is None, "binding in another context must not leak into this one"


def test_user_token_survives_to_thread():
    async def main():
        with dbx.bind("viewer-x"):
            return await asyncio.to_thread(dbx.user_token)
    assert asyncio.run(main()) == "viewer-x"


def test_workspace_client_cached_per_token(monkeypatch):
    monkeypatch.setenv("DATABRICKS_HOST", "https://example.cloud.databricks.com")
    monkeypatch.setattr("databricks.sdk.config.Config._resolve_host_metadata", lambda self: None)
    with dbx.bind("tok-1"):
        c1 = dbx.workspace_client()
        c1_again = dbx.workspace_client()
    with dbx.bind("tok-2"):
        c2 = dbx.workspace_client()
    assert c1 is c1_again, "one client per token: the SDK probes the host on every construction"
    assert c1 is not c2
    assert c1.config.auth_type == "pat" and c2.config.token == "tok-2"


def test_run_context_is_per_context():
    ctx_main = facts.reset()
    results = {}

    def worker(name):
        ctx = facts.reset()
        ctx.record("run_sql", {"sql": "x"}, pd.DataFrame({"n": [1]}))
        results[name] = ctx

    t = threading.Thread(target=worker, args=("t",))
    t.start()
    t.join()
    assert results["t"] is not ctx_main
    assert facts.current() is ctx_main and ctx_main.calls == []


def test_run_context_created_lazily_per_context():
    ctx = contextvars.copy_context()
    ctx.run(facts._var.set, None)  # a context with no run yet (a copy inherits the parent's run on purpose)
    inner = ctx.run(facts.current)
    assert inner is ctx.run(facts.current), "created once per context"
    assert inner is not facts.current(), "and never leaks into the parent"


def test_record_emits_a_tool_event():
    events = []
    ctx = facts.reset(on_event=events.append)
    ctx.record("run_sql", {"sql": "SELECT 1"}, pd.DataFrame({"n": [1, 2]}), sql="SELECT 1", source="SQL: t")
    assert len(events) == 1
    ev = events[0]
    assert ev["type"] == "tool" and ev["tool"] == "run_sql" and ev["rows"] == 2 and ev["sql"] == "SELECT 1"
    assert ev["preview"] == [{"n": 1}, {"n": 2}] and "t_ms" in ev


def test_emit_without_listener_is_a_noop():
    ctx = facts.reset()
    ctx.emit("status", phase="genie")  # must not raise


def test_check_cancel_raises_once_cancelled():
    ctx = facts.reset()
    ctx.check_cancel()
    ctx.cancel.set()
    with pytest.raises(facts.Cancelled):
        ctx.check_cancel()


def test_clear_keeps_listener_and_conversation():
    events = []
    ctx = facts.reset(on_event=events.append, genie_conversation_id="conv-1")
    ctx.record("run_sql", {"sql": "x"}, pd.DataFrame({"n": [1]}))
    ctx.clear()
    assert ctx.calls == [] and ctx.sources == [] and ctx.pool.facts == []
    assert ctx.genie_conversation_id == "conv-1"
    ctx.emit("status", phase="model")
    assert events[-1]["type"] == "status"


def test_sql_connection_per_token(monkeypatch):
    class FakeConn:
        def __init__(self, **kw):
            self.kw = kw

    monkeypatch.setenv("FAIRSHARE_BACKEND", "databricks")
    monkeypatch.setenv("DATABRICKS_HOST", "https://example.cloud.databricks.com")
    monkeypatch.setenv("DATABRICKS_HTTP_PATH", "/sql/1.0/warehouses/abc")
    monkeypatch.setattr("databricks.sql.connect", lambda **kw: FakeConn(**kw))
    db._conns.clear()
    with dbx.bind("tok-a"):
        a1, _ = db._databricks()
        a2, _ = db._databricks()
    with dbx.bind("tok-b"):
        b, _ = db._databricks()
    assert a1 is a2 and a1 is not b
    assert a1.kw["access_token"] == "tok-a" and b.kw["access_token"] == "tok-b"
    db._conns.clear()
