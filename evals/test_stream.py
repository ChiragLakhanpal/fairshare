"""POST /api/ask as a stream: ordered events, the offline cached fallback, two viewers at once, and Stop."""
import asyncio
import json
import sys
import threading
from pathlib import Path
from types import SimpleNamespace

import pandas as pd
import pytest
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from fairshare import dbx  # noqa: E402
from harness import facts, summary  # noqa: E402

CACHED_Q = "How did Summit Travel Partners do on DFW to ORD in Q3 2026 versus Q3 2025, and are they ahead of fair share?"


@pytest.fixture
def client():
    from server.main import create_app
    return TestClient(create_app())


def events_of(client, body, headers=None):
    out, cur = [], {}
    with client.stream("POST", "/api/ask", json=body, headers=headers or {}) as r:
        assert r.status_code == 200 and r.headers["content-type"].startswith("text/event-stream")
        for line in r.iter_lines():
            line = line.rstrip("\r")
            if not line:
                if cur.get("event"):
                    out.append({"id": cur.get("id"), "event": cur["event"], "data": json.loads(cur.get("data", "{}"))})
                cur = {}
            elif ":" in line and not line.startswith(":"):
                k, v = line.split(":", 1)
                cur[k.strip()] = (cur.get(k.strip(), "") + v.strip()) if k.strip() == "data" else v.strip()
    return out


def test_ask_cached_sse_order(client):
    ev = events_of(client, {"question": CACHED_Q})
    assert [e["event"] for e in ev] == ["status", "answer", "done"]
    assert [int(e["id"]) for e in ev] == [1, 2, 3]
    a = ev[1]["data"]
    assert a["cached"]["recorded"] and a["sentences"] and a["calls"][0]["sql"].lstrip().upper().startswith("WITH")
    assert a["kind"] == "numbers" and len(a["follow_ups"]) == 3


def test_ask_unknown_question_offline_is_no_model(client):
    ev = events_of(client, {"question": "Something nobody recorded"})
    assert [e["event"] for e in ev] == ["status", "error", "done"] and ev[1]["data"]["code"] == "no_model"


def test_ask_rejects_an_empty_or_huge_question(client):
    assert client.post("/api/ask", json={"question": ""}).status_code == 422
    assert client.post("/api/ask", json={"question": "x" * 2001}).status_code == 422


class StubAgent:
    """Runs run_sql the way the framework does (off the loop) and quotes a returned number."""
    def __init__(self, sleep=0.0):
        self.sleep, self.seen = sleep, []

    async def run(self, messages):
        from harness.tools import run_sql
        self.seen.append(messages)

        def body():
            for _ in range(int(self.sleep / 0.05)):
                facts.current().check_cancel()
                import time
                time.sleep(0.05)
            return run_sql.func(sql="SELECT COUNT(*) AS n FROM aa_demo.gold.dim_agency")
        out = await asyncio.to_thread(body)
        n = out.split("\n")[-1].strip()
        return SimpleNamespace(text=f"There are {n} agencies in the data.")


def test_ask_sse_with_stub_agent(client, monkeypatch):
    monkeypatch.setenv("FAIRSHARE_MODEL", "databricks")
    stub = StubAgent()
    monkeypatch.setattr("harness.agent.get_agent", lambda: stub)
    ev = events_of(client, {"question": "How many agencies are there?", "history": [{"role": "user", "text": "hi"}, {"role": "assistant", "text": "hello"}],
                            "scope": {"region": "East", "month": "2026-09"}})
    kinds = [(e["event"], e["data"].get("phase")) for e in ev]
    assert kinds == [("status", "model"), ("status", "sql"), ("tool", None), ("status", "model"), ("status", "verify"), ("answer", None), ("done", None)], kinds
    a = ev[-2]["data"]
    assert a["sentences"][0]["status"] == "verified" and a["calls"][0]["tool"] == "run_sql" and a["kind"] == "numbers"
    assert a["timing"]["total_ms"] >= 0 and a["genie_conversation_id"] is None
    assert len(stub.seen[0]) == 3 and stub.seen[0][-1].text.startswith("Current scope: East, 2026-09")


def test_identity_isolation_across_concurrent_requests(client, monkeypatch):
    seen, real = {}, summary.build_facts
    barrier = threading.Barrier(2, timeout=10)

    def spy(region, month, blocks=summary.ALL_BLOCKS):
        barrier.wait()  # both requests are inside build_facts at the same time
        seen[dbx.user_token()] = threading.current_thread().name
        return real(region, month, blocks)

    monkeypatch.setattr(summary, "build_facts", spy)
    results = {}

    def call(tok):
        results[tok] = client.get("/api/summary", params={"region": "All", "month": "2026-09"}, headers={"x-forwarded-access-token": tok}).status_code

    threads = [threading.Thread(target=call, args=(t,)) for t in ("tok-a", "tok-b")]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert results == {"tok-a": 200, "tok-b": 200} and set(seen) == {"tok-a", "tok-b"}
    assert dbx.user_token() is None


def test_stop_cancels_the_run(monkeypatch):
    monkeypatch.setenv("FAIRSHARE_MODEL", "databricks")
    stub = StubAgent(sleep=5.0)
    monkeypatch.setattr("harness.agent.get_agent", lambda: stub)
    from server import stream
    from server.context import Viewer
    from server.stream import AskIn

    async def go():
        gen = stream.ask_events(Viewer(None, None, None, False), AskIn(question="slow one"))
        first = await gen.__anext__()
        assert first["event"] == "status"
        ctx = facts.current()
        await gen.aclose()  # the browser pressed Stop (or closed the tab)
        return ctx

    ctx = asyncio.run(go())
    assert ctx.cancel.is_set()


def test_server_never_calls_aio():
    bad = [p for p in (ROOT / "server").glob("*.py") if "aio." in p.read_text()]
    assert bad == []
