"""What the deck says about the data, checked against the local DuckDB build (python lakehouse/run.py first)."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from fairshare import db  # noqa: E402

sys.path.insert(0, str(ROOT / "docs/diagrams/src"))
import datetime  # noqa: E402
import json  # noqa: E402
import math  # noqa: E402
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


# ---- units on the examples, a reason on every check, and Genie's earlier runs (the deck redesign, task 2)

MONTH_ABBR = "Jan Feb Mar Apr May Jun Jul Aug Sep Oct Nov Dec".split()
SHOWN_AS = {  # the kinds of unit, and the way a slide writes each
    "usd": r"-?\$\d{1,3}(,\d{3})*",                    # $1,310,400: dollars that are always whole
    "cents": r"-?\$\d{1,3}(,\d{3})*\.\d{2}",           # $80,582.47, -$64,794.93: dollars and cents
    "percent": r"-?\d+(\.\d+)?%",                      # 123.6%: the column holds percent points already
    "share": r"-?\d+(\.\d+)?%",                        # 38.05%: the column holds a fraction of one, 0.3805
    "count": r"\d{1,3}(,\d{3})*",                      # 275 and 57,075: a separator from four digits
    "month": rf"({'|'.join(MONTH_ABBR)}) \d{{4}}",     # Sep 2026
}
UNIT_OF = {  # the columns that carry a unit, by hand from their meanings; ids, years, days, names and flags show what is stored
    "gold.fact_agency_sales_monthly": {"sales_month": "month", "aa_revenue": "cents", "aa_pax": "count", "market_revenue": "cents", "market_pax": "count"},
    "gold.fact_market_capacity": {"sales_month": "month", "aa_seats": "count", "total_seats": "count", "aa_seat_share": "share"},
    "gold.agency_goals": {"revenue_goal_usd": "usd", "share_goal": "share"},
    "gold.agency_pace": {"sales_month": "month", "aa_revenue": "cents", "ytd_revenue": "cents", "revenue_goal_usd": "usd", "ytd_goal": "usd",
                         "pace_pct": "percent", "attainment_pct": "percent", "months_reported": "count"},
    "gold.contract_clauses": {"window_quarters": "count"},
    "gold.crm_opportunities": {"amount_usd": "usd"},
    "gold.fact_corporate_bookings": {"fare_usd": "cents", "ticket_count": "count"},
    "gold.dim_corporate": {"annual_commitment_usd": "usd"},
    "ops.decomposition": {"sales_month": "month", "revenue_now": "cents", "revenue_prior": "cents", "delta_revenue": "cents", "delta_pct": "percent",
                          "market_now": "cents", "market_prior": "cents", "market_delta_pct": "percent", "aa_share_now": "share", "aa_share_prior": "share",
                          "fair_share_now": "share", "fair_share_prior": "share", "volume_effect": "cents", "mix_effect": "cents",
                          "share_effect": "cents", "fair_share_effect": "cents", "residual": "cents"},
}


def _says(example, kind):
    """The value an example with a unit says, back in the scale the table stores it in: a fraction for a share, the first of the month."""
    if kind == "month":
        name, year = example.split()
        return datetime.date(int(year), MONTH_ABBR.index(name) + 1, 1)
    number = float(example.replace("$", "").replace(",", "").replace("%", ""))
    return number / 100 if kind == "share" else number


def test_the_row_slide_examples_carry_their_units():
    """The row slide printed 80582.47, 0.3805 and 2026-09-01. Now money has a dollar sign, a share a percent sign, a count a separator from four digits, a month its name."""
    sales = {c["name"]: c["example"] for c in STORED["columns"]["gold.fact_agency_sales_monthly"]}
    seats = {c["name"]: c["example"] for c in STORED["columns"]["gold.fact_market_capacity"]}
    assert (sales["aa_revenue"], sales["market_revenue"]) == ("$80,582.47", "$145,829.00")
    assert (sales["aa_pax"], sales["market_pax"], sales["sales_month"]) == ("275", "500", "Sep 2026")
    assert (seats["aa_seats"], seats["total_seats"], seats["aa_seat_share"], seats["sales_month"]) == ("57,075", "150,000", "38.05%", "Sep 2026")


def test_every_example_carries_its_unit():
    """Every money, share, count and month column of every table the deck shows writes its unit and still says the stored value (a share is
    the fraction times a hundred). An id, a year, a day, a name, a flag or a missing value shows what is stored, so no id gets a separator."""
    for table, (where, meanings) in deck_facts.COLUMNS.items():
        raw = deck_facts.query(f"SELECT * FROM aa_demo.{table} WHERE {where}")[0]
        shown = {c["name"]: c["example"] for c in STORED["columns"][table]}
        assert set(shown) == set(meanings), table
        for column, example in shown.items():
            kind, stored, at = UNIT_OF.get(table, {}).get(column), raw[column], f"{table}.{column}: {example!r}"
            if kind is None or stored is None:
                assert example == deck_facts._example(stored), at
                continue
            assert re.fullmatch(SHOWN_AS[kind], example), at
            said = _says(example, kind)
            assert said == stored if kind == "month" else math.isclose(said, stored, rel_tol=0, abs_tol=1e-9), (at, said, stored)
    assert set(UNIT_OF) <= set(deck_facts.COLUMNS) and all(set(c) <= set(deck_facts.COLUMNS[t][1]) for t, c in UNIT_OF.items()), "UNIT_OF names a column the deck does not show"


BANNED_IN_COPY = ("additionally", "crucial", "delve", "enduring", "enhance", "fostering", "garner", "interplay", "intricate", "landscape", "pivotal",
                  "showcase", "tapestry", "testament", "underscore", "vibrant")


def test_every_check_has_a_key_and_a_plain_reason():
    """The checks slide names each check by its key and prints its why, a sentence a sales director and a data lead both read. The copy rules
    that a test can see: no digits, no em or en dash, no colon, semicolon or bracket, one whole sentence, none of the stock words or phrases,
    no -ing tail, and the data is never called real."""
    checks = STORED["checks"]
    assert len(checks) == len(deck_facts.CHECKS)
    assert all(set(c) == {"key", "name", "why", "expected", "actual", "ok"} for c in checks)
    keys = [c["key"] for c in checks]
    assert len(keys) == len(set(keys)), "a check key is used twice"
    assert all(re.fullmatch(r"[a-z][a-z0-9]*(_[a-z0-9]+)*", k) for k in keys), f"check keys are snake_case: {keys}"
    for c in checks:
        why = c["why"]
        assert isinstance(why, str) and re.fullmatch(r"[A-Z][^.]*\.", why), f"{c['key']}: one sentence that starts with a capital and ends with a period"
        assert not re.search(r"\d", why), f"{c['key']}: a digit"
        assert not re.search("[\u2013\u2014]", why), f"{c['key']}: an em or en dash"
        assert not re.search(r"[:;()]", why), f"{c['key']}: a colon, semicolon or bracket"
        assert not re.search(r"\b(?:" + "|".join(BANNED_IN_COPY) + ")", why, re.IGNORECASE), f"{c['key']}: a stock word"
        assert not re.search(r"serves as|stands as|not just|not only", why, re.IGNORECASE), f"{c['key']}: a stock phrase"
        assert not re.search(r",\s+\w+ing\b", why), f"{c['key']}: an -ing tail"
        assert not re.search(r"\breal\b", why, re.IGNORECASE), f"{c['key']}: the data is made up, never call it real"


def test_genie_earlier_runs_are_dated_from_their_result_files():
    """The two Oct 19 runs that scored 17 of 20 before five benchmark questions named their columns. The value is checked against the files it cites."""
    d = deck_facts.DATED["genie_benchmark_earlier"]
    assert (d["value"], d["display"], d["date"]) == (17, "17 of 20", "2026-10-19")
    for name in ("2026-10-19T211129-genie-eval.json", "2026-10-19T212948-genie-eval.json"):
        assert f"evals/results/{name}" in d["source"], name
        run = json.loads((ROOT / "evals/results" / name).read_text(encoding="utf-8"))
        assert (run["correct"], run["n"]) == (d["value"], 20), name
    assert STORED["dated"]["genie_benchmark_earlier"] == json.loads(json.dumps(d)), "rerun deck_facts.py"
