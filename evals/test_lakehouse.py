"""The checks that fail if the logic breaks. Runs against the local DuckDB build (python lakehouse/run.py first).

  .venv/bin/pytest evals -q
"""
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
