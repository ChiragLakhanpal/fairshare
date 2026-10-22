"""The seats are the DOT's T-100 with the months it has not published flagged, the made-up agency data is never called real, Power BI itself is
never said to be checked, fair share has no wrong synonym, portable SQL never escapes a quote, no $$ body holds a semicolon, and the nightly job cuts
every SQL file where run.py does."""
import csv
import re
import subprocess
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from fairshare import db  # noqa: E402

# Words that would call the made-up data real: the agencies and their sales, the goals, the bookings and the corporates, the agreements and the CRM.
# The seats are the DOT's T-100 and may be called real; nothing else may.
MADE_UP = r"(?:agenc(?:y|ies)|agency sales|sales(?: data)?|goals?|bookings?|corporates?|companies|contracts?|agreements?|CRM(?: data)?)"
# "Not a real contract", as each agreement says of itself, is the opposite claim, so a "real" after "not a" or "never a" passes.
AGENCY_REAL = re.compile(rf"\b{MADE_UP} (?:is|are) real\b|(?<!not a )(?<!never a )\breal {MADE_UP}\b|\b{MADE_UP} (?:is|are) not made up\b", re.I)
POWER_BI = re.compile(r"Power BI uses the same definition|the Power BI check|kept equal by|checked vs Power BI"
                      r"|check vs Power BI|Power BI twin, checked|Power BI twin of each one")
# this file, which spells the patterns out
ALLOWED = {"evals/test_labels.py"}
TEXT = (".py", ".sql", ".md", ".svg", ".html", ".mjs", ".ts", ".tsx", ".yaml", ".json")
# history: the design notes and the recorded results stay as they were written
HISTORY = ("docs/superpowers/", "evals/results/", "web/dist/")


def hits(rx):
    files = subprocess.run(["git", "ls-files", "-co", "--exclude-standard"], cwd=ROOT, capture_output=True, text=True, check=True).stdout.splitlines()
    out = []
    for f in files:
        if f.endswith(TEXT) and f not in ALLOWED and not f.startswith(HISTORY):
            text = (ROOT / f).read_text(encoding="utf-8", errors="ignore")
            out += [f"{f}:{text.count(chr(10), 0, m.start()) + 1}: {m.group(0)}" for m in rx.finditer(text)]
    return out


def _csv(path):
    with open(ROOT / path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


# The months the DOT had not published when the T-100 files were downloaded (Oct 21, 2026; July 2026 was the newest month). data/t100.py gives
# each the same month of 2025, and the deck says so ("August and September 2026 repeat 2025"), so a fresh download that publishes them fails
# here first, before the copy is out of date.
PROJECTED = {date(2026, 8, 1), date(2026, 9, 1)}


def test_the_seats_are_the_dots_t100_in_the_files_and_in_gold():
    """Every seat row is a T-100 row: the generator's CSV copies data/t100/aa_seat_share.csv (data/t100.py's output) and says source t100, and
    gold.fact_market_capacity holds the same rows."""
    t100 = {(r["market_id"], r["sales_month"]): r for r in _csv("data/t100/aa_seat_share.csv")}
    out = _csv("data/out/fact_market_capacity.csv")
    routes, months = len(_csv("data/out/dim_market.csv")), len({r["sales_month"] for r in _csv("data/out/fact_agency_sales_monthly.csv")})
    assert len(out) == len(t100) == routes * months, "one seat row per route and month, in both files"
    assert {r["source"] for r in out} == {"t100"}, "every seat row says it came from T-100"
    for r in out:
        t = t100[(r["market_id"], r["sales_month"])]
        assert (int(r["aa_seats"]), int(r["total_seats"]), float(r["aa_seat_share"])) == (int(t["aa_seats"]), int(t["total_seats"]), float(t["aa_seat_share"])), r
    gold = db.query("SELECT source, COUNT(*) AS n FROM aa_demo.gold.fact_market_capacity GROUP BY source")
    assert list(gold["source"]) == ["t100"] and int(gold["n"].iloc[0]) == routes * months, "gold holds the same T-100 rows"


def test_the_months_the_dot_has_not_published_are_flagged_and_repeat_2025():
    """is_projected marks exactly the months the DOT has not published, on every route, in the T-100 file, the generator's CSV and gold; each of
    those rows is the same month of 2025; and the metric view gives the flag to Genie and the dashboard as capacity_is_projected."""
    for path in ("data/t100/aa_seat_share.csv", "data/out/fact_market_capacity.csv"):
        rows = _csv(path)
        flagged = {date.fromisoformat(r["sales_month"]) for r in rows if r["is_projected"].lower() == "true"}
        assert flagged == PROJECTED, (path, sorted(flagged))
        by = {(r["market_id"], date.fromisoformat(r["sales_month"])): r for r in rows}
        for (market, month), r in by.items():
            if month in PROJECTED:
                last = by[(market, date(month.year - 1, month.month, 1))]
                assert (r["aa_seats"], r["total_seats"], r["aa_seat_share"]) == (last["aa_seats"], last["total_seats"], last["aa_seat_share"]), (path, market, month)
    gold = db.query("""SELECT c.sales_month, COUNT(*) AS n, COUNT(*) FILTER (WHERE c.aa_seats = p.aa_seats AND c.total_seats = p.total_seats) AS repeats
                       FROM aa_demo.gold.fact_market_capacity c
                       JOIN aa_demo.gold.fact_market_capacity p ON p.market_id = c.market_id
                        AND EXTRACT(YEAR FROM p.sales_month) = EXTRACT(YEAR FROM c.sales_month) - 1 AND EXTRACT(MONTH FROM p.sales_month) = EXTRACT(MONTH FROM c.sales_month)
                       WHERE c.is_projected GROUP BY c.sales_month ORDER BY c.sales_month""")
    routes = int(db.query("SELECT COUNT(*) AS n FROM aa_demo.gold.dim_market")["n"].iloc[0])
    assert [(d.date() if hasattr(d, "date") else d, int(n), int(k)) for d, n, k in zip(gold["sales_month"], gold["n"], gold["repeats"])] == \
        [(m, routes, routes) for m in sorted(PROJECTED)], "gold flags the same months on every route, each with last year's seats"
    view = (ROOT / "lakehouse/03_metric_view.sql").read_text(encoding="utf-8")
    assert re.search(r"- name: capacity_is_projected\s+expr: cap\.is_projected", view), "the metric view lets a question filter or show the flag"


def test_nothing_calls_the_made_up_agency_data_real():
    assert not hits(AGENCY_REAL), "\n".join(hits(AGENCY_REAL))


def test_nothing_says_power_bi_itself_was_checked():
    assert not hits(POWER_BI), "\n".join(hits(POWER_BI))


def test_fair_share_has_no_qsi_synonym():
    assert "QSI" not in (ROOT / "lakehouse/03_metric_view.sql").read_text(encoding="utf-8")


# the figures that print data values (05 prints none); every one says so in its logo band, and so does each animated twin
DATA_FIGURES = ["04-journey-sales-director", "04-journey-sales-director-animated", "06-data-pipeline", "06-data-pipeline-animated",
                "07-fair-share", "08-why-it-moved", "08-why-it-moved-animated", "09-definitions", "09a-numbers-share", "09a-numbers-share-animated",
                "09b-numbers-gaps", "09b-numbers-gaps-animated", "10-coverage", "11-revenue-by-month", "11-revenue-by-month-animated",
                "12-share-vs-fair", "12-share-vs-fair-animated", "14-what-was-planted"]


def test_every_data_figure_says_synthetic_data_in_its_logo_band():
    for slug in DATA_FIGURES:
        html = (ROOT / "docs" / "diagrams" / f"{slug}.html").read_text(encoding="utf-8")
        assert "FAIRSHARE · SYNTHETIC DATA" in html, f"{slug} prints data values, so its logo band must say synthetic data"


# The files that run on both DuckDB and Databricks SQL (CLAUDE.md rule 5). 00_bronze.sql and 03_metric_view.sql are Databricks only.
PORTABLE_SQL = ["01_silver.sql", "02_gold.sql", "04_definitions.sql", "06_decomposition.sql", "07_agreement_watch.sql"]


def test_portable_sql_has_no_doubled_quotes():
    # Databricks reads 'AA''s' as two adjacent literals and joins them, so the apostrophe disappears ("AAs"); DuckDB keeps it. Write the text without one.
    found = [f"lakehouse/{name}:{n}" for name in PORTABLE_SQL
             for n, line in enumerate((ROOT / "lakehouse" / name).read_text(encoding="utf-8").splitlines(), 1) if "''" in line]
    assert not found, "doubled quote in " + ", ".join(found)


def test_metric_view_body_has_no_semicolon():
    # The nightly job's SQL task cuts a file at every semicolon outside single quotes and comments, and it does not know $$ (Oct 20, 2026: it cut the YAML in two).
    found = []
    for path in sorted((ROOT / "lakehouse").glob("*.sql")):
        text = path.read_text(encoding="utf-8")
        for body in re.finditer(r"\$\$(.*?)\$\$", text, re.S):
            found += [f"lakehouse/{path.name}:{text.count(chr(10), 0, i) + 1}" for i in range(*body.span(1)) if text[i] == ";"]
    assert not found, "semicolon inside a $$ body at " + ", ".join(found)


# How the nightly job's SQL task cuts a file, read off the warehouse's query history (Oct 19 and 20, 2026); run.py cuts differently, in db.statements.
# An apostrophe flips "inside quotes" wherever it sits in code, a line that starts with -- is left alone, a semicolon outside quotes cuts, and $$ means
# nothing to it. Comment lines stay in the piece they sit in, and the warehouse rejects a piece made only of comments. This predicted all 48 statements
# of the Oct 20 run exactly. Not seen yet: a backslash before an apostrophe, and a -- after code on the same line; both count as plain code here.
def job_pieces(text):
    """Every piece the job would send for one file, with the line of the semicolon that ended it (None for the last piece)."""
    pieces, cur, quoted = [], "", False
    for n, line in enumerate(text.splitlines(keepends=True), 1):
        if not quoted and line.lstrip().startswith("--"):
            cur += line
            continue
        for ch in line:
            if ch == "'":
                quoted = not quoted
            if ch == ";" and not quoted:
                pieces.append((n, cur))
                cur = ""
            else:
                cur += ch
    return pieces + [(None, cur)]


def without_comments(piece):
    return "\n".join(l for l in piece.splitlines() if not l.lstrip().startswith("--")).strip()


def test_nightly_job_cuts_each_sql_file_where_run_py_does():
    # Oct 20, 2026: the job cut 03_metric_view.sql at a semicolon in its YAML and run.py did not, so only the job failed. The two must cut every file the same way.
    problems = []
    for path in sorted((ROOT / "lakehouse").glob("0*.sql")):
        pieces = job_pieces(path.read_text(encoding="utf-8"))
        real = [(n, p) for n, p in pieces if p.strip()]  # what follows the last semicolon is usually just a newline
        sent = [without_comments(p).rstrip(";").strip() for _, p in real if without_comments(p)]
        problems += [f"lakehouse/{path.name}: the piece that ends {'at line ' + str(n) if n else 'the file'} holds only comments" for n, p in real if not without_comments(p)]
        if sent != db.statements(path):
            problems.append(f"lakehouse/{path.name}: the job sends {len(sent)} statements, run.py runs {len(db.statements(path))} (the job cuts after lines {[n for n, _ in pieces if n]})")
    assert not problems, "\n".join(problems)
