"""What the deck says about the data, checked against the local DuckDB build (python lakehouse/run.py first)."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from fairshare import db  # noqa: E402

sys.path.insert(0, str(ROOT / "docs/diagrams/src"))
import json  # noqa: E402
import re  # noqa: E402
import deck_facts  # noqa: E402

FILE = ROOT / "web/src/deck/facts.json"
STORED = json.loads(FILE.read_text(encoding="utf-8")) if FILE.exists() else {}


def test_pace_counts_only_reported_months():
    p = db.query("""SELECT p.sales_month, p.months_reported, p.pace_pct FROM aa_demo.gold.agency_pace p
                    JOIN aa_demo.gold.dim_agency a ON a.agency_id = p.agency_id
                    WHERE a.agency_name = 'Sunbelt Vacations' AND p.sales_month IN (DATE '2026-05-01', DATE '2026-09-01')
                    ORDER BY p.sales_month""")
    assert list(p["months_reported"]) == [3, 7], "Sunbelt has no rows for March and April 2026"
    assert list(p["pace_pct"]) == [123.6, 136.3]


def test_one_font_url_everywhere():
    """The deck loads the fonts first, so a diagram frame's blocking font stylesheet comes from the cache."""
    sys.path.insert(0, str(ROOT / "docs/diagrams/src"))
    import aa
    assert aa.FONT_LINK in (ROOT / "web/index.html").read_text(encoding="utf-8")
    assert aa.FONT_LINK in (ROOT / "docs/diagrams/hairline/src/pages.mjs").read_text(encoding="utf-8")


def test_facts_json_is_fresh():
    fresh = deck_facts.collect()
    assert {k: STORED.get(k) for k in fresh} == fresh, "rerun: FAIRSHARE_BACKEND=duckdb .venv/bin/python docs/diagrams/src/deck_facts.py"


def test_dated_facts_in_the_file_are_the_ones_written_in_deck_facts():
    """The test above skips the dated section, because a local query cannot reproduce it. A hand edit to DATED still has to reach the file."""
    assert STORED.get("dated") == json.loads(json.dumps(deck_facts.DATED)), "rerun: FAIRSHARE_BACKEND=duckdb .venv/bin/python docs/diagrams/src/deck_facts.py"


def test_display_is_the_string_the_file_stores():
    """The figures print display(key) and a slide prints the stored display, so for every fact they must be the same string."""
    assert {k: deck_facts.display(k) for k, *_ in deck_facts.FACTS} == {k: f["display"] for k, f in STORED["facts"].items()}


def test_the_agency_list_is_the_table():
    """The per-agency keys name the twelve agencies in deck_facts.AGENCIES; the list must be dim_agency exactly, in id order."""
    rows = db.query("SELECT agency_name FROM aa_demo.gold.dim_agency ORDER BY agency_id")
    assert [name for _slug, name in deck_facts.AGENCIES] == list(rows["agency_name"])
    assert len({slug for slug, _name in deck_facts.AGENCIES}) == len(deck_facts.AGENCIES), "a short name is used twice"


def test_the_numbers_said_out_loud():
    v = {k: f["value"] for k, f in deck_facts.collect()["facts"].items()}
    assert (v["summit_q3_aa_share"], v["summit_q3_fair_share"], v["summit_q3_gap_usd"], v["summit_q3_pax_share"]) == (53.5, 37.6, 88391, 52.4)
    assert (v["harbor_volume_usd"], v["harbor_mix_usd"], v["harbor_share_usd"], v["harbor_delta_usd"]) == (32836, -140, -97491, -64795)
    assert (v["avg_of_shares_q3"], v["share_of_total_q3"], v["pax_rev_max_gap_pts"]) == (39.7, 38.4, 1.7)
    assert (v["sunbelt_pace_may26_before"], v["sunbelt_pace_may26"], v["duplicate_usd"], v["agency_months_present"]) == (74.2, 123.6, 4920.87, 250)


def test_the_basic_checks_hold():
    bad = [c for c in deck_facts.collect()["checks"] if not c["ok"]]
    assert not bad, bad


def test_every_column_the_deck_shows_exists():
    for table, (_, meanings) in deck_facts.COLUMNS.items():
        schema, name = table.split(".")
        have = set(db.query(f"SELECT column_name FROM information_schema.columns WHERE table_schema = '{schema}' AND table_name = '{name}'")["column_name"])
        assert set(meanings) <= have, (table, set(meanings) - have)


def test_harbor_share_matches_the_metric_view():
    """DuckDB has no metric view; the parity file holds the metric view's own values from Databricks (newest run)."""
    mv = db.query(f"""SELECT sales_month, ROUND(mv_value * 100, 1) AS pct FROM read_csv('{ROOT / "app/cache/kpi_parity.csv"}')
                      WHERE kpi = 'aa_share' AND twin_version = 'v2' AND agency = 'Harbor Business Travel'
                      AND sales_month IN (DATE '2025-09-01', DATE '2026-09-01') QUALIFY ROW_NUMBER() OVER (PARTITION BY sales_month ORDER BY run_at DESC) = 1
                      ORDER BY sales_month""")
    v = deck_facts.collect()["facts"]
    assert list(mv["pct"]) == [v["harbor_share_sep25"]["value"], v["harbor_share_sep26"]["value"]]


def test_keys_are_placeholders_and_the_text_has_no_long_dashes():
    """A slide writes {key}, so a key is snake_case and names one number, in facts or in the dated section but never both.
    The copy rule (no em or en dashes) covers every sentence the deck can print from the file."""
    facts = deck_facts.collect()
    keys = [k for k, *_ in deck_facts.FACTS]
    assert len(keys) == len(set(keys)), "a fact key is listed twice"
    assert not set(keys) & set(deck_facts.DATED), set(keys) & set(deck_facts.DATED)
    assert all(re.fullmatch(r"[a-z][a-z0-9_]*", k) for k in [*keys, *deck_facts.DATED]), "keys are snake_case"
    for k, d in deck_facts.DATED.items():
        assert {"value", "display", "source", "date"} <= set(d), k
        assert re.fullmatch(r"\d{4}-\d{2}-\d{2}", d["date"]), (k, d["date"])
    assert set(facts["facts"]) == set(keys)
    assert not re.search("[\u2013\u2014]", json.dumps({**facts, "dated": deck_facts.DATED}, ensure_ascii=False)), "an em or en dash is in the facts"
