"""The home page's "Worth knowing this month" block: fixed queries, template prose, the verifier, no model. Offline
(conftest: DuckDB, no model); the data is deterministic (seed 88201), so the September lines are pinned here."""
import re
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from fairshare import db  # noqa: E402
from harness import facts, signals  # noqa: E402


@pytest.fixture
def client():
    from server.main import create_app
    return TestClient(create_app())


def _texts(out):
    return [s["sentence"]["text"] for s in out]


def test_september_lines_rank_dollars_at_stake_first_then_the_rest_in_a_fixed_order():
    facts.reset()
    out = signals.build("All", "2026-09")
    assert [s["kind"] for s in out] == ["clause", "clause", "mismatch", "clause", "capacity", "bookings"]
    t = _texts(out)
    assert t[0] == "Summit Travel Partners is 2.2 points from an incentive tier worth $188K year to date."
    assert t[1] == "Harbor Business Travel is at 96.1% of its revenue commitment, with $46K of advanced incentive at risk."
    assert re.fullmatch(r"Harbor Business Travel's \$5\.2[67]M 2027 renewal is marked On track in the CRM stand-in while AA share fell 10\.1 points against last year\. "
                        r"Four more open deals disagree with the data\.", t[2])
    assert t[3] == "BlueSky Corporate Travel is 0.1 points above its share floor."
    assert t[4] == "AA cut seats 4.4% on ORD-SFO against last September, and fair share there fell 1.3 points, the largest capacity move this month."
    assert t[5] == "Corporate bookings the week of September 21 were $416K, up 12.4% week over week."
    assert [s["severity"] for s in out] == ["watch", "watch", "risk", "watch", "watch", "ok"]
    assert [s["agency"] for s in out] == ["Summit Travel Partners", "Harbor Business Travel", "Harbor Business Travel", "BlueSky Corporate Travel", None, None]


def test_every_line_is_checked_against_the_query_that_produced_it():
    for region in ("All", "Central", "East", "West"):
        facts.reset()
        out = signals.build(region, "2026-09")
        assert out, region
        for s in out:
            sent = s["sentence"]
            assert sent["status"] == "verified", (region, sent)
            assert all(n["source"] for n in sent["numbers"]), (region, sent)
        # the numbers point at the calls the route returns, by tool and position
        names = {f"signals#{i + 1}" for i in range(len(facts.current().calls))}
        assert {n["source"] for s in out for n in s["sentence"]["numbers"]} <= names


def test_a_region_only_names_its_own_agencies_and_keeps_the_network_lines():
    regions = db.query("SELECT agency_name, region FROM aa_demo.gold.dim_agency")
    west = set(regions[regions["region"] == "West"]["agency_name"])
    facts.reset()
    out = signals.build("West", "2026-09")
    named = [s["agency"] for s in out if s["agency"]]
    assert named and set(named) <= west
    assert [s["kind"] for s in out] == ["mismatch", "capacity", "bookings"]
    assert _texts(out)[0] == "FareHub Online's $1.68M NDC adoption is marked On track in the CRM stand-in while AA share fell 8.1 points against last year."
    facts.reset()
    central = _texts(signals.build("Central", "2026-09"))
    assert central[1].endswith("Two more open deals disagree with the data.")
    assert "rose 3.4 points" in central[1]


def test_each_line_carries_one_action_and_a_question_for_the_chips():
    facts.reset()
    out = signals.build("All", "2026-09")
    assert out[0]["action"] == {"kind": "delegate", "agent": "watch", "label": "Open Agreement watch"}
    assert out[0]["chip"] == "What does Summit Travel Partners' agreement say about its incentive tier?"
    assert out[2]["action"] == {"kind": "delegate", "agent": "mismatch", "label": "Open CRM versus reality"}
    assert out[2]["chip"] == "Why is Harbor Business Travel down in September 2026?"
    assert out[4]["action"]["kind"] == "ask" and out[4]["action"]["question"] == out[4]["chip"] == "How did AA's seats on ORD-SFO change against last year?"
    assert out[5]["action"]["kind"] == "ask" and out[5]["chip"] == "Show corporate bookings by week for September 2026."


def test_the_route_returns_the_lines_with_their_calls(client):
    r = client.get("/api/signals", params={"region": "All", "month": "2026-09"})
    assert r.status_code == 200, r.text
    j = r.json()
    assert j["region"] == "All" and j["month"] == "2026-09" and len(j["signals"]) == 6
    assert j["calls"] and all(c["sql"] for c in j["calls"]) and j["calls"][0]["tool"] == "signals"
    assert {c["args"]["block"] for c in j["calls"]} >= {"agreement checks", "CRM versus the data", "share streaks", "capacity moves", "corporate weekly bookings"}
    assert client.get("/api/signals", params={"region": "All", "month": "2026-13"}).status_code == 422
    assert client.get("/api/signals", params={"region": "Nowhere", "month": "2026-09"}).status_code == 422
