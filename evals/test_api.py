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
