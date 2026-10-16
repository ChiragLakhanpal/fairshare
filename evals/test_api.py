"""The HTTP API the React app calls, run offline (conftest: DuckDB, no model, no tracing)."""
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from fairshare import db  # noqa: E402


@pytest.fixture
def client():
    from server.main import create_app
    return TestClient(create_app())


def _agency_id(name: str) -> int:
    return int(db.query(f"SELECT agency_id FROM aa_demo.gold.dim_agency WHERE agency_name = '{name}'")["agency_id"].iloc[0])


def test_me_offline(client):
    me = client.get("/api/me").json()
    assert me["email"] is None and me["backend"] == "duckdb" and me["model"] == "none" and me["genie"] is None
    assert me["months"][0] == "2026-09" and me["data_through"] == "2026-09"
    assert me["regions"] == ["All", "Central", "East", "West"]


def test_me_reports_the_viewer(client):
    me = client.get("/api/me", headers={"x-forwarded-email": "dana@example.com", "x-forwarded-user": "dana"}).json()
    assert me["email"] == "dana@example.com" and me["user"] == "dana"


def test_region_and_month_allowlists(client):
    assert client.get("/api/summary", params={"region": "Central' OR '1'='1", "month": "2026-09"}).status_code == 422
    assert client.get("/api/summary", params={"region": "All", "month": "2026-13"}).status_code == 422
    assert client.get("/api/summary", params={"region": "All", "month": "2024-01"}).status_code == 422
    r = client.get("/api/summary", params={"region": "All", "month": "2026-09"})
    assert r.status_code == 200, r.text


def test_summary_all_regions(client):
    s = client.get("/api/summary", params={"region": "All", "month": "2026-09"}).json()
    assert set(s["kpis"]) >= {"aa_revenue", "aa_revenue_prior_year", "yoy_pct", "aa_share_pct", "fair_share_pct", "share_gap_pts", "share_gap_usd", "pace_pct"}
    assert s["kpis"]["aa_revenue"] == 4492373 and s["kpis"]["pace_pct"] == 139.1
    assert len(s["movers"]) == 3 and s["movers"][0]["agency"] == "Harbor Business Travel" and s["movers"][0]["share_chg_pts"] == -10.1
    assert all(b["pace_pct"] < 100 for b in s["behind_pace"]) and {b["agency"] for b in s["behind_pace"]} == {"Harbor Business Travel", "FareHub Online"}
    assert s["headline"] == "September closed ahead of pace and a little under fair share."
    assert s["prior_month"] == "2025-09" and s["calls"] and s["calls"][0]["sql"]


def test_agencies(client):
    rows = client.get("/api/agencies").json()
    assert len(rows) == 12 and set(rows[0]) == {"agency_id", "agency_name", "agency_type", "region", "account_manager"}


def test_explain_unknown_agency_is_422(client):
    assert client.get("/api/explain", params={"agency_id": 999, "month": "2026-08"}).status_code == 422


def test_explain_harbor_august(client):
    e = client.get("/api/explain", params={"agency_id": _agency_id("Harbor Business Travel"), "month": "2026-08"}).json()
    s = e["summary"]
    assert e["agency"]["agency_name"] == "Harbor Business Travel" and e["month"] == "2026-08" and e["prior_month"] == "2025-08"
    assert s["share_effect"] < 0 and abs(s["share_effect"]) > abs(s["volume_effect"]) and "parts_sum" in s
    assert e["markets"] and set(e["markets"][0]) >= {"market", "share_effect", "aa_share_now_pct", "aa_share_prior_pct"}
    assert e["could_not_verify"] and len(e["calls"]) == 2


def test_explain_month_without_prior_year_is_404(client):
    r = client.get("/api/explain", params={"agency_id": _agency_id("Harbor Business Travel"), "month": "2025-08"})
    assert r.status_code == 404 and r.json()["code"] == "no_decomposition"


def test_agreements_summit_page_two(client):
    a = client.get("/api/agreements", params={"agency_id": _agency_id("Summit Travel Partners"), "topic": "share falls below 45% for two consecutive quarters"}).json()
    assert a["hits"][0]["file"] == "summit-travel-partners.md" and a["hits"][0]["page"] == 2 and "45%" in a["hits"][0]["text"]
    assert len(a["hits"]) <= 3


def test_definitions_offline(client):
    d = client.get("/api/definitions").json()
    assert len(d["kpis"]) == 7 and {k["kpi"] for k in d["kpis"]} >= {"aa_share", "fair_share", "pace_pct"}
    assert d["parity"]["source"] == "app/cache/kpi_parity.csv" and d["parity"]["rows"] > 0 and d["runs"]


def test_evals_lists_the_golden_set_with_the_newest_result_of_each_kind(client):
    e = client.get("/api/evals").json()
    assert [q["id"] for q in e["questions"]] == [f"q{i:02d}" for i in range(1, 21)]
    assert all(q["genie"] is not None and q["space"] in ("GOOD", "BAD", "NEEDS_REVIEW") and q["judge"] in ("CORRECT", "PARTIAL", "WRONG") for q in e["questions"])
    assert e["space"]["run_at"] >= "2026-10-14" and e["space"]["n"] == 20 and e["harness"]["model"] and 0 <= e["harness"]["backed"] <= 1


def test_brief_template_approve_get(client, monkeypatch, tmp_path):
    monkeypatch.setattr(db, "STATE_FILE", tmp_path / "state.duckdb")
    b = client.post("/api/brief", json={"region": "Central", "month": "2026-09", "writer": "template"}).json()
    assert b["status"] == "draft" and b["sentences"] and b["removed"] == [] and b["model"] == "template"
    assert all(s["status"] == "verified" for s in b["sentences"]) and b["calls"]
    ok = client.post(f"/api/brief/{b['run_id']}/approve").json()
    assert ok["run_id"] == b["run_id"] and ok["status"] == "approved" and ok["verified_text"] == b["verified_text"]
    g = client.get(f"/api/brief/{b['run_id']}").json()
    assert g["status"] == "approved" and g["verified_text"] == b["verified_text"]


def test_brief_rejects_bad_scope(client):
    assert client.post("/api/brief", json={"region": "Mars", "month": "2026-09", "writer": "template"}).status_code == 422


def test_approve_unknown_draft_is_404(client):
    r = client.post("/api/brief/0123456789ab/approve")
    assert r.status_code == 404 and r.json()["code"] == "draft_expired"


def test_spa_fallback(monkeypatch, tmp_path):
    from server import static
    dist = tmp_path / "dist"
    (dist / "assets").mkdir(parents=True)
    (dist / "index.html").write_text("<html>app</html>")
    (dist / "assets" / "app.js").write_text("console.log(1)")
    monkeypatch.setattr(static, "DIST", dist)
    from server.main import create_app
    c = TestClient(create_app())
    assert c.get("/").text == "<html>app</html>" and c.get("/brief/abc").text == "<html>app</html>"
    assert c.get("/assets/app.js").text == "console.log(1)"
    assert c.get("/assets/missing.js").status_code == 404
    r = c.get("/api/nope")
    assert r.status_code == 404 and r.json()["code"] == "not_found"


def test_no_web_build_is_503(monkeypatch, tmp_path):
    from server import static
    monkeypatch.setattr(static, "DIST", tmp_path / "nowhere")
    from server.main import create_app
    c = TestClient(create_app())
    r = c.get("/")
    assert r.status_code == 503 and r.json()["code"] == "no_web_build"


def test_informational_sentences_are_notes_not_verified():
    import pandas as pd
    from harness.verifier import FactPool, verify
    from server.serialize import sentences_json
    pool = FactPool()
    pool.add_frame(pd.DataFrame({"aa_revenue": [330114.0]}), "q")
    v = verify("Revenue was $330K. Could not verify: the cause. Source: ask_metrics.", pool)
    assert [s["status"] for s in sentences_json(v.badges())] == ["verified", "note", "note"]


def test_summary_reports_the_agency_count_for_the_region(client):
    assert client.get("/api/summary", params={"region": "Central", "month": "2026-09"}).json()["agency_count"] == 5
    assert client.get("/api/summary", params={"region": "All", "month": "2026-09"}).json()["agency_count"] == 12


def test_approve_reverifies_edited_text(client, monkeypatch, tmp_path):
    monkeypatch.setattr(db, "STATE_FILE", tmp_path / "state.duckdb")
    b = client.post("/api/brief", json={"region": "Central", "month": "2026-09", "writer": "template"}).json()
    bad = client.post(f"/api/brief/{b['run_id']}/approve", json={"text": "AA revenue was $9.9M and nobody checked it."})
    assert bad.status_code == 422 and bad.json()["code"] == "unverified" and "$9.9M" in bad.json()["removed"][0]["reason"]
    first = b["sentences"][0]["text"]
    ok = client.post(f"/api/brief/{b['run_id']}/approve", json={"text": first})
    assert ok.status_code == 200 and ok.json()["status"] == "approved" and ok.json()["verified_text"] == first
    assert client.get(f"/api/brief/{b['run_id']}").json()["verified_text"] == first


def test_agencies_are_read_per_call_not_cached_across_viewers(monkeypatch):
    from server import validate
    calls = []
    real = validate.db.query
    monkeypatch.setattr(validate.db, "query", lambda sql: (calls.append(sql), real(sql))[1])
    validate.agencies()
    validate.agencies()
    assert len(calls) == 2


# ---------------------------------------------------------------- Delegate: the agents routes
def _state(monkeypatch, tmp_path):
    from server import agents_api
    monkeypatch.setattr(db, "STATE_FILE", tmp_path / "state.duckdb")
    monkeypatch.setattr(agents_api, "RUNS", {})  # runs from other tests stay out of this one's catalog and inbox


def test_agents_catalog(client):
    c = client.get("/api/agents").json()
    assert [a["key"] for a in c["agents"]] == ["precall", "watch", "prospect", "mismatch"]
    assert len(c["managers"]) == 4 and len(c["markets"]) == 12 and c["markets"][0]["market"] == "DFW-LAX" and "stand-in" in c["crm_label"]
    assert all({"key", "name", "summary", "reads", "writes", "approver", "scope_kind", "last_run"} <= set(a) for a in c["agents"])
    assert {a["scope_kind"] for a in c["agents"]} == {"manager", "region", "market"}


def test_run_pack_wait_and_poll(client, monkeypatch, tmp_path):
    _state(monkeypatch, tmp_path)
    r = client.post("/api/agents/precall/run?wait=true", json={"scope": {"manager": "Marcus Lee", "month": "2026-09"}, "writer": "template"})
    assert r.status_code == 200, r.text
    run = r.json()
    assert run["status"] == "needs_approval" and len(run["items"]) == 4 and run["agent_name"] == "Monday pre-call pack" and run["model"] == "template"
    assert run["progress"] == {"done": 4, "total": 4, "text": "4 of 4 waiting for a decision.", "phase": "done", "item": None} and run["error"] is None and run["finished_at"]
    item = run["items"][0]
    assert item["facts"] and item["facts"][0]["rows"] and item["facts"][0]["sql"] and item["sentences"] and item["action"]["type"] == "email" and item["status"] == "draft"
    g = client.get(f"/api/agents/runs/{run['run_id']}").json()
    assert g["status"] == "needs_approval" and [i["title"] for i in g["items"]] == [i["title"] for i in run["items"]]
    heads = client.get("/api/agents/runs").json()
    assert heads[0]["run_id"] == run["run_id"] and heads[0]["needs_approval"] == 4 and heads[0]["items"] == 4 and heads[0]["agent_name"] == "Monday pre-call pack"
    pre = next(a for a in client.get("/api/agents").json()["agents"] if a["key"] == "precall")
    assert pre["last_run"]["run_id"] == run["run_id"] and pre["last_run"]["status"] == "needs_approval"


def test_approve_and_reject_items(client, monkeypatch, tmp_path):
    _state(monkeypatch, tmp_path)
    H = {"x-forwarded-email": "dana@example.com", "x-forwarded-user": "dana"}
    run = client.post("/api/agents/precall/run?wait=true", json={"scope": {"manager": "Dana Whitfield", "month": "2026-09"}, "writer": "template"}, headers=H).json()
    rid, items = run["run_id"], run["items"]
    assert len(items) == 3
    a = client.post(f"/api/agents/runs/{rid}/items/{items[0]['item_id']}/approve", json={}, headers=H)
    assert a.status_code == 200 and a.json()["status"] == "approved" and a.json()["decided_by"] == "dana@example.com" and a.json()["decided_at"]
    bad = client.post(f"/api/agents/runs/{rid}/items/{items[1]['item_id']}/approve", json={"text": "AA revenue was $9.9M and nobody checked it."}, headers=H)
    assert bad.status_code == 422 and bad.json()["code"] == "unverified" and "$9.9M" in bad.json()["removed"][0]["reason"]
    rj = client.post(f"/api/agents/runs/{rid}/items/{items[1]['item_id']}/reject", json={}, headers=H).json()
    assert rj["status"] == "rejected" and rj["decided_by"] == "dana@example.com"
    g = client.get(f"/api/agents/runs/{rid}", headers=H).json()
    assert g["status"] == "needs_approval" and [i["status"] for i in g["items"]] == ["approved", "rejected", "draft"]
    acts = client.get("/api/crm/activities", params={"agency_id": items[0]["seed"]["agency_id"]}, headers=H).json()
    assert acts[0]["source"] == "app" and acts[0]["activity_type"] == "Pre-call pack" and acts[0]["owner"] == "dana@example.com" and any(x["source"] == "crm" for x in acts)
    assert client.post(f"/api/agents/runs/{rid}/items/nope/approve", json={}, headers=H).status_code == 404
    assert client.get("/api/agents/runs/000000000000", headers=H).status_code == 404


def test_run_unknown_agent_is_404_and_bad_scopes_are_422(client):
    assert client.post("/api/agents/nope/run", json={"scope": {}}).status_code == 404
    assert client.post("/api/agents/precall/run", json={"scope": {"manager": "Nobody", "month": "2026-09"}}).status_code == 422
    assert client.post("/api/agents/watch/run", json={"scope": {"region": "Mars", "month": "2026-09"}}).status_code == 422
    assert client.post("/api/agents/prospect/run", json={"scope": {"market": "XXX-YYY"}}).status_code == 422
    assert client.post("/api/agents/precall/run", json={"scope": {"manager": "Marcus Lee", "month": "2026-13"}}).status_code == 422


def test_run_in_the_background_is_running_then_waits_for_approval(monkeypatch, tmp_path):
    import time
    _state(monkeypatch, tmp_path)
    from server.main import create_app
    with TestClient(create_app()) as c:  # one event loop for every request, so the background task survives between polls
        run = c.post("/api/agents/mismatch/run", json={"scope": {"region": "All", "month": "2026-09"}, "writer": "template"}).json()
        assert run["status"] == "running" and run["items"] == [] and run["progress"]["total"] == 0
        for _ in range(100):
            g = c.get(f"/api/agents/runs/{run['run_id']}").json()
            if g["status"] != "running":
                break
            time.sleep(0.1)
        assert g["status"] == "needs_approval" and g["items"] and g["progress"]["done"] == g["progress"]["total"] == len(g["items"])


def test_catalog_words_steps_waiting_and_running(client, monkeypatch, tmp_path):
    _state(monkeypatch, tmp_path)
    for a in client.get("/api/agents").json()["agents"]:
        assert a["one_liner"].endswith(".") and a["cadence"].endswith(".") and 5 <= len(a["steps"]) <= 7
        assert a["steps"][-2]["title"] == "Check" and a["steps"][-1]["title"] == "Approve" and all(s["sub"] for s in a["steps"])
        assert a["waiting"] == 0 and a["running"] is None
    client.post("/api/agents/mismatch/run?wait=true", json={"scope": {"region": "All", "month": "2026-09"}, "writer": "template"})
    m = next(a for a in client.get("/api/agents").json()["agents"] if a["key"] == "mismatch")
    assert m["waiting"] >= 1 and m["last_run"]["status"] == "needs_approval"


def test_catalog_carries_the_pages_and_a_rerun_refreshes_them(client, monkeypatch, tmp_path):
    _state(monkeypatch, tmp_path)
    assert all(a["pages"] == [] for a in client.get("/api/agents").json()["agents"])
    run = client.post("/api/agents/precall/run?wait=true", json={"scope": {"manager": "Marcus Lee", "month": "2026-09"}, "writer": "template"}).json()
    item = run["items"][0]
    assert item["summary"] and item["sections"] and item["email"]["subject"] and item["note"] and item["numbers_checked"] > 0 and run["progress"]["phase"] == "done"
    client.post(f"/api/agents/runs/{run['run_id']}/items/{item['item_id']}/approve", json={})
    pre = next(a for a in client.get("/api/agents").json()["agents"] if a["key"] == "precall")
    assert pre["waiting"] == 3 and [p["status"] for p in pre["pages"]] == ["draft", "draft", "draft", "approved"]
    page = pre["pages"][0]
    assert {"item_id", "kind", "title", "subtitle", "severity", "summary", "status", "run_id", "created_at", "scope", "decided_at", "decided_by", "versions"} <= set(page) and page["summary"]
    again = client.post("/api/agents/precall/run?wait=true", json={"scope": {"manager": "Marcus Lee", "month": "2026-09"}, "writer": "template"}).json()
    pre = next(a for a in client.get("/api/agents").json()["agents"] if a["key"] == "precall")
    assert pre["waiting"] == 4 and len(pre["pages"]) == 4 and all(p["run_id"] == again["run_id"] for p in pre["pages"])
    assert [v["status"] for v in next(p for p in pre["pages"] if p["title"] == item["title"])["versions"]] == ["draft", "approved"]
    assert [v["status"] for v in next(p for p in pre["pages"] if p["title"] != item["title"])["versions"]] == ["draft", "superseded"]
    assert client.get("/api/agents/inbox").status_code == 404
