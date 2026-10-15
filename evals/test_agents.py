"""The Delegate runtime (harness/agents.py) with a fake agent, then the four real agents, offline (DuckDB, template writer)."""
import sys
from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from fairshare import db  # noqa: E402
from harness import agents  # noqa: E402
from harness.agents import AgentDef, Fact  # noqa: E402

SCOPE = {"region": "All", "month": "2026-09"}


@pytest.fixture
def state(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "STATE_FILE", tmp_path / "state.duckdb")
    return tmp_path


def fake_agent(fail_on: str | None = None) -> AgentDef:
    def plan(scope):
        return [{"key": "a", "n": 1}, {"key": "b", "n": 2}]

    def facts_fn(scope, seed):
        if fail_on == seed["key"]:
            raise RuntimeError("boom")
        df = pd.DataFrame({"aa_revenue": [330114.0 * seed["n"]], "yoy_pct": [-16.4]})
        return [Fact(name="numbers", label="The month's numbers", df=df, sql="SELECT 1", source="test")]

    def template(seed, fs):
        return f"Revenue was ${fs[0].df['aa_revenue'].iloc[0] / 1000:.0f}K, down 16.4%. Engagement rose 12%."

    def action(seed, fs, text):
        return {"type": "crm", "subject": "s", "body": text, "crm": {"agency_id": 5, "activity_type": "Test", "subject": "Test approved"}}

    return AgentDef(key="fake", name="Fake agent", summary="A test.", reads=["x"], writes=["y"], approver="you", scope_kind="region", kind="page",
                    plan=plan, facts=facts_fn, instructions="", template=template, action=action,
                    severity=lambda seed, fs: "watch", title=lambda seed, fs: f"Item {seed['key']}", subtitle=lambda seed, fs: "sub")


def test_run_offline_two_items_one_flagged_sentence(state):
    agents.register(fake_agent())
    run = agents.run("fake", SCOPE, "tester", mode="template")
    assert run.status == "needs_approval" and len(run.items) == 2 and run.finished_at and run.error is None
    a = run.items[0]
    assert a.title == "Item a" and a.severity == "watch" and a.status == "draft"
    assert a.verified_text.startswith("Revenue was $330K") and a.flagged and "12%" in a.flagged[0]["reason"]
    assert a.action["crm"]["agency_id"] == 5 and run.progress == {"done": 2, "total": 2, "text": agents.progress_text(run)}


def test_save_and_load_round_trip(state):
    agents.register(fake_agent())
    run = agents.run("fake", SCOPE, "tester", mode="template")
    loaded = agents.load(run.run_id)
    assert loaded is not None and loaded.status == "needs_approval" and [i.title for i in loaded.items] == ["Item a", "Item b"]
    assert loaded.items[1].facts[0].df["aa_revenue"].iloc[0] == 660228.0 and loaded.items[0].flagged
    heads = agents.list_runs()
    assert heads[0]["run_id"] == run.run_id and heads[0]["items"] == 2 and heads[0]["needs_approval"] == 2 and heads[0]["agent_name"] == "Fake agent"


def test_approve_is_idempotent_and_writes_one_crm_activity(state):
    agents.register(fake_agent())
    run = agents.run("fake", SCOPE, "tester", mode="template")
    item = agents.approve(run, run.items[0].item_id, None, "dana@example.com")
    assert item.status == "approved" and item.decided_by == "dana@example.com" and item.decided_at
    agents.approve(run, run.items[0].item_id, None, "dana@example.com")
    acts = db.state_query("SELECT * FROM aa_demo.ops.crm_activities")
    assert len(acts) == 1 and acts.iloc[0]["agency_id"] == 5 and acts.iloc[0]["activity_type"] == "Test"
    assert run.status == "needs_approval"  # one draft left
    assert agents.load(run.run_id).items[0].status == "approved"


def test_approve_rejects_an_edit_with_an_unsupported_number(state):
    agents.register(fake_agent())
    run = agents.run("fake", SCOPE, "tester", mode="template")
    with pytest.raises(agents.Unverified) as e:
        agents.approve(run, run.items[0].item_id, "Revenue was $9.9M and nobody checked it.", "dana")
    assert "$9.9M" in e.value.flagged[0]["reason"]
    assert run.items[0].status == "draft"
    item = agents.approve(run, run.items[0].item_id, "Revenue was $330K.", "dana")  # a supported edit goes through
    assert item.status == "approved" and item.verified_text == "Revenue was $330K."


def test_reject_and_the_run_status_follows_the_items(state):
    agents.register(fake_agent())
    run = agents.run("fake", SCOPE, "tester", mode="template")
    agents.reject(run, run.items[0].item_id, "dana")
    assert run.items[0].status == "rejected" and run.status == "needs_approval"
    agents.reject(run, run.items[1].item_id, "dana")
    assert run.status == "rejected"
    run2 = agents.run("fake", SCOPE, "tester", mode="template")
    agents.approve(run2, run2.items[0].item_id, None, "dana")
    agents.reject(run2, run2.items[1].item_id, "dana")
    assert run2.status == "approved"


def test_run_records_a_failed_block(state):
    agents.register(fake_agent(fail_on="b"))
    run = agents.run("fake", SCOPE, "tester", mode="template")
    assert run.status == "failed" and "boom" in run.error and len(run.items) == 1 and run.finished_at
    assert agents.load(run.run_id).status == "failed"


def test_a_run_is_running_until_it_finishes():
    run = agents.new_run("fake", SCOPE, "tester", "template")
    assert run.status == "running" and run.to_json()["status"] == "running" and run.progress["total"] == 0
