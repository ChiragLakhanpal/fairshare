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
    yield tmp_path
    agents.AGENTS.pop("fake", None)  # the fake agent must not reach the catalog of other tests


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
    assert a.action["crm"]["agency_id"] == 5 and run.progress == {"done": 2, "total": 2, "text": agents.progress_text(run), "phase": "done", "item": None}


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


# ---------------------------------------------------------------- the Monday pre-call pack
def fact(item, name):
    return next(f for f in item.facts if f.name == name)


def test_pack_marcus_lee_offline(state):
    from harness import precall  # noqa: F401  (registers the agent)
    run = agents.run("precall", {"manager": "Marcus Lee", "month": "2026-09"}, "tester", mode="template")
    assert run.status == "needs_approval" and run.error is None
    assert {i.title for i in run.items} == {"BlueSky Corporate Travel", "Harbor Business Travel", "Capitol Corporate Travel", "Atlantic Premier Travel"}
    harbor = next(i for i in run.items if i.title.startswith("Harbor"))
    assert harbor.severity == "risk" and harbor.kind == "page" and "Marcus Lee" in harbor.subtitle
    assert {f.name for f in harbor.facts} >= {"numbers", "why", "markets", "clauses", "opportunities", "last_touch", "contacts", "schedule", "mismatch"}
    assert not fact(harbor, "mismatch").df.empty and not fact(harbor, "clauses").df.empty and fact(harbor, "numbers").df.iloc[0]["aa_revenue"] == 330114
    assert harbor.action["type"] == "email" and harbor.action["subject"].startswith("Pre-call pack") and harbor.action["crm"]["activity_type"] == "Pre-call pack"
    assert harbor.action["crm"]["agency_id"] == 5 and "Subject:" not in harbor.action["body"] and harbor.action["body"]
    for item in run.items:
        assert not item.flagged, (item.title, item.flagged)
        assert "Could not verify" in item.draft
    assert "crm stand-in" in harbor.verified_text.lower() and "share" in harbor.verified_text.lower()


def test_pack_agency_without_agreement(state):
    from harness import precall  # noqa: F401
    run = agents.run("precall", {"manager": "Dana Whitfield", "month": "2026-09"}, "tester", mode="template")
    north = next(i for i in run.items if i.title.startswith("Northstar"))
    assert fact(north, "clauses").df.empty and "no agreement on file" in north.verified_text.lower() and not north.flagged


def test_pack_month_without_prior_year(state):
    from harness import precall  # noqa: F401
    run = agents.run("precall", {"manager": "Marcus Lee", "month": "2025-09"}, "tester", mode="template")
    assert run.status == "needs_approval", run.error
    harbor = next(i for i in run.items if i.title.startswith("Harbor"))
    assert fact(harbor, "why").df.empty and "no comparison" in harbor.verified_text.lower() and not harbor.flagged


def test_pack_rejects_an_unknown_manager(state):
    from harness import precall  # noqa: F401
    run = agents.run("precall", {"manager": "Nobody", "month": "2026-09"}, "tester", mode="template")
    assert run.status == "failed" and "manager" in run.error.lower()


# ---------------------------------------------------------------- agreement watch
def test_watch_september(state):
    from harness import watch  # noqa: F401
    run = agents.run("watch", {"region": "All", "month": "2026-09"}, "tester", mode="template")
    assert run.status == "needs_approval", run.error
    titles = [i.title for i in run.items]
    assert any("Harbor" in t for t in titles) and any("BlueSky" in t for t in titles) and any("Summit" in t for t in titles)
    harbor = next(i for i in run.items if "Harbor" in i.title)
    assert harbor.kind == "clause" and harbor.severity in ("watch", "risk") and {f.name for f in harbor.facts} >= {"check", "trend", "contacts"}
    assert harbor.action["type"] == "email" and harbor.action["subject"].startswith("Agreement watch") and harbor.action["crm"]["agency_id"] == 5
    summit = next(i for i in run.items if "Summit" in i.title)
    assert not fact(summit, "tiers").df.empty and "tier" in summit.verified_text.lower()
    for item in run.items:
        assert not item.flagged, (item.title, item.flagged)
        assert "Could not verify" in item.draft and "Hello " in item.draft


def test_watch_region_with_nothing_to_flag_has_no_items(state):
    from harness import watch  # noqa: F401
    run = agents.run("watch", {"region": "West", "month": "2026-09"}, "tester", mode="template")
    assert run.error is None and run.items == [] and run.status == "approved" and "clause" in run.progress["text"].lower()


# ---------------------------------------------------------------- CRM versus reality
def test_mismatch_finds_harbor_renewal(state):
    from harness import mismatch  # noqa: F401
    run = agents.run("mismatch", {"region": "All", "month": "2026-09"}, "tester", mode="template")
    assert run.status == "needs_approval", run.error
    harbor = next(i for i in run.items if "Harbor" in i.title)
    assert harbor.kind == "mismatch" and harbor.severity == "risk" and not harbor.flagged
    assert harbor.action["type"] == "crm" and harbor.action["crm"]["activity_type"] == "CRM update" and harbor.action["crm"]["agency_id"] == 5
    agents.approve(run, harbor.item_id, None, "dana")
    acts = db.state_query("SELECT * FROM aa_demo.ops.crm_activities")
    assert len(acts) == 1 and acts.iloc[0]["activity_type"] == "CRM update" and acts.iloc[0]["agency_id"] == 5


# ---------------------------------------------------------------- prospect research
def test_research_cached_provider_reads_the_file():
    from harness import research
    src = research.sources("CLT-LGA")
    assert src and all({"title", "url", "snippet"} <= set(s) for s in src) and all(s["url"].startswith("http") for s in src)
    assert research.sources("ZZZ-ZZZ") == []


def test_prospect_clt_lga_offline(state):
    from harness import prospect  # noqa: F401
    run = agents.run("prospect", {"market": "CLT-LGA", "month": "2026-09"}, "tester", mode="template")
    assert run.status == "needs_approval", run.error
    assert len(run.items) == 1
    item = run.items[0]
    assert item.kind == "prospect" and item.title == "CLT-LGA" and {f.name for f in item.facts} >= {"headroom", "total", "trend", "capacity"}
    assert len(item.sources) >= 2 and not item.flagged, item.flagged
    assert item.action["type"] == "none"
    web = [n for s in item.badges for n in s["numbers"] if str(n.get("source") or "").startswith("web: ")]
    assert web, "the brief quotes at least one number from a cited source, and it verifies with the source as its origin"
    assert "headroom" in item.verified_text.lower() and "[1]" in item.verified_text


def test_prospect_unknown_market_fails_honestly(state):
    from harness import prospect  # noqa: F401
    run = agents.run("prospect", {"market": "XXX-YYY", "month": "2026-09"}, "tester", mode="template")
    assert run.status == "failed" and "market" in run.error.lower()


# ---------------------------------------------------------------- the document view: sections, the email, the note, a summary
def test_item_sections_email_note_and_summary(state):
    from harness import precall  # noqa: F401
    run = agents.run("precall", {"manager": "Marcus Lee", "month": "2026-09"}, "tester", mode="template")
    harbor = next(i for i in run.items if i.title.startswith("Harbor"))
    j = harbor.to_json()
    assert [s["title"] for s in j["sections"]] == ["Where they stand", "What moved", "The agreement", "The CRM stand-in", "The schedule", "For the call"]
    assert all(s["sentences"] for s in j["sections"]) and j["sections"][0]["sentences"][0]["text"].startswith("Harbor Business Travel sold")
    assert j["email"] and j["email"]["subject"].startswith("Harbor Business Travel, September 2026") and j["email"]["to"].endswith("@harborbusinesstravel.example")
    assert j["email"]["to_name"] and j["email"]["sentences"][0]["text"].startswith("Hello ") and "Best regards" in j["email"]["sentences"][-1]["text"]
    assert j["note"].startswith("whether the agency changed") and "Could not verify" not in j["note"]
    assert "10.1 points" in j["summary"] and "renewal" in j["summary"] and j["numbers_checked"] > 10
    assert run.progress["phase"] == "done" and run.progress["item"] is None
    north = next(i for i in agents.run("precall", {"manager": "Dana Whitfield", "month": "2026-09"}, "tester", mode="template").items if i.title.startswith("Northstar"))
    assert "no agreement on file" in north.to_json()["summary"].lower()


def test_watch_and_mismatch_items_have_summaries_and_sections(state):
    from harness import mismatch, watch  # noqa: F401
    w = agents.run("watch", {"region": "All", "month": "2026-09"}, "tester", mode="template")
    summit = next(i for i in w.items if "Summit" in i.title).to_json()
    assert "tier" in summit["summary"].lower() and "$188K" in summit["summary"] and [s["title"] for s in summit["sections"]] == ["The alert", "What to do"] and summit["email"]
    m = agents.run("mismatch", {"region": "All", "month": "2026-09"}, "tester", mode="template")
    harbor = next(i for i in m.items if "Harbor" in i.title).to_json()
    assert "On track" in harbor["summary"] and len(harbor["sections"]) == 2 and harbor["email"] is None and harbor["note"]


def test_registry_carries_the_words_the_catalog_needs():
    from harness import mismatch, precall, prospect, watch  # noqa: F401
    for key in ("precall", "watch", "prospect", "mismatch"):
        a = agents.AGENTS[key]
        assert a.one_liner.endswith(".") and a.cadence.endswith(".") and 5 <= len(a.steps) <= 7
        assert [t for t, _ in a.steps][-2:] == ["Check", "Approve"] and a.section_titles


def test_ready_made_phrases_travel_with_the_facts(state):
    from harness import precall, watch  # noqa: F401
    run = agents.run("precall", {"manager": "Marcus Lee", "month": "2026-09"}, "tester", mode="template")
    harbor = next(i for i in run.items if i.title.startswith("Harbor"))
    ph = fact(harbor, "phrases").df.iloc[0]
    assert ph["gap"] == "a gap of 5.9 points worth $57K below fair share" and ph["share_move"].endswith("down 10.1 points") and ph["volume"] == "volume added $33K"
    assert ph["gap"] in harbor.draft and ph["crm"] in harbor.draft and not harbor.flagged
    w = agents.run("watch", {"region": "All", "month": "2026-09"}, "tester", mode="template")
    summit = next(i for i in w.items if "Summit" in i.title)
    ph = fact(summit, "phrases").df.iloc[0]
    assert ph["distance"] == "2.2 points below the line" and ph["dollars"].startswith("$188K") and not summit.flagged
