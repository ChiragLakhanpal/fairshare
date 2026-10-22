"""The home page's "Worth knowing this month" block: fixed queries, template prose, the verifier, no model. Offline
(conftest: DuckDB, no model); the sales are deterministic (seed 88201) and the seats are the committed T-100 file
(data/t100/aa_seat_share.csv), so the September lines are pinned here. September 2026's seats repeat September 2025's until the
DOT publishes them, so no route moved that month and the line that says so takes the capacity line's place; July 2026, the newest
month the DOT has published, still has a capacity line."""
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
    # With the T-100 seats Summit's share premium is -0.7 points year to date, 5.7 from its next tier, so its tier is no longer within reach
    # and has no line; Harbor's commitment, with dollars at stake, leads.
    facts.reset()
    out = signals.build("All", "2026-09")
    assert [s["kind"] for s in out] == ["clause", "mismatch", "clause", "projected", "bookings"]
    t = _texts(out)
    assert t[0] == "Harbor Business Travel is at 96.1% of its revenue commitment, with $46K of advanced incentive at risk."
    assert re.fullmatch(r"Harbor Business Travel's \$5\.2[67]M 2027 renewal is marked On track in the CRM stand-in while AA share fell 10\.1 points against last year\. "
                        r"Four more open deals disagree with the data\.", t[1])
    assert t[2] == "BlueSky Corporate Travel is 0.1 points above its share floor."
    assert t[3] == "The seat data for September 2026 is last year's, because this month's seat file is not in yet, so fair share is an estimate until it is."
    assert t[4] == "Corporate bookings the week of September 21 were $416K, up 12.4% week over week."
    assert [s["severity"] for s in out] == ["watch", "risk", "watch", "watch", "ok"]
    assert [s["agency"] for s in out] == ["Harbor Business Travel", "Harbor Business Travel", "BlueSky Corporate Travel", None, None]


def test_a_month_with_published_seats_names_the_largest_capacity_move():
    # July 2026 is the newest month the DOT has published. The West's lines leave room for the network's capacity line, which the All view
    # ranks past its six.
    facts.reset()
    out = signals.build("West", "2026-07")
    assert [s["kind"] for s in out] == ["mismatch", "streak", "bookings", "capacity"]
    cap = out[3]
    assert cap["sentence"]["text"] == "AA cut seats 9.3% on CLT-LGA against last July, and fair share there rose 7.0 points, the largest capacity move this month."
    assert cap["severity"] == "ok" and cap["agency"] is None
    assert cap["action"] == {"kind": "ask", "question": "How did AA's seats on CLT-LGA change against last year?", "label": "Ask about the market"}
    assert cap["chip"] == cap["action"]["question"]


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
    assert [s["kind"] for s in out] == ["mismatch", "projected", "bookings"]
    assert _texts(out)[0] == "FareHub Online's $1.68M NDC adoption is marked On track in the CRM stand-in while AA share fell 8.1 points against last year."
    facts.reset()
    central = _texts(signals.build("Central", "2026-09"))
    assert central[0].endswith("Two more open deals disagree with the data.")
    assert "rose 3.4 points" in central[0]


def test_each_line_carries_one_action_and_a_question_for_the_chips_except_the_note_on_last_years_seats():
    facts.reset()
    out = signals.build("All", "2026-09")
    assert out[0]["action"] == {"kind": "delegate", "agent": "watch", "label": "Open Agreement watch"}
    assert out[0]["chip"] == "What does Harbor Business Travel's agreement say about its revenue commitment?"
    assert out[1]["action"] == {"kind": "delegate", "agent": "mismatch", "label": "Open CRM versus reality"}
    assert out[1]["chip"] == "Why is Harbor Business Travel down in September 2026?"
    assert out[3]["action"] == {"kind": "definitions", "kpi": "fair_share", "label": "See how fair share is defined"} and out[3]["chip"] is None
    assert out[4]["action"]["kind"] == "ask" and out[4]["chip"] == "Show corporate bookings by week for September 2026."


def test_the_route_returns_the_lines_with_their_calls(client):
    r = client.get("/api/signals", params={"region": "All", "month": "2026-09"})
    assert r.status_code == 200, r.text
    j = r.json()
    assert j["region"] == "All" and j["month"] == "2026-09" and len(j["signals"]) == 5
    assert j["calls"] and all(c["sql"] for c in j["calls"]) and j["calls"][0]["tool"] == "signals"
    assert {c["args"]["block"] for c in j["calls"]} >= {"agreement checks", "CRM versus the data", "share streaks", "capacity moves", "corporate weekly bookings"}
    assert client.get("/api/signals", params={"region": "All", "month": "2026-13"}).status_code == 422
    assert client.get("/api/signals", params={"region": "Nowhere", "month": "2026-09"}).status_code == 422
