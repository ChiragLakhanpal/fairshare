"""The repo never calls the made-up seat data real, never says Power BI itself was checked, fair share has no wrong synonym, portable SQL never escapes a quote, no $$ body holds a semicolon, and the nightly job cuts every SQL file where run.py does."""
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from fairshare import db  # noqa: E402

REAL = re.compile(r"T-100 \(real\)|seat data is real|seats are BTS|real, public|public\s+airline\s+(seat\s+)?data|real seat data"
                  r"|BTS T-100 seats|BTS T-100 ·|BTS T-100 \+|seat share from BTS|\(BTS T-100|capacity \(T-100\)"
                  r"|BTS has not published|published BTS data|^Real: BTS", re.M)
POWER_BI = re.compile(r"Power BI uses the same definition|the Power BI check|kept equal by|checked vs Power BI"
                      r"|check vs Power BI|Power BI twin, checked|Power BI twin of each one")
# what happens when real files exist, how to get them, and this file
ALLOWED = {"data/t100.py", "data/make_data.py", "docs/day0.md", "evals/test_labels.py"}
TEXT = (".py", ".sql", ".md", ".svg", ".html", ".mjs", ".ts", ".tsx", ".yaml", ".json")


def hits(rx):
    files = subprocess.run(["git", "ls-files", "-co", "--exclude-standard"], cwd=ROOT, capture_output=True, text=True, check=True).stdout.splitlines()
    out = []
    for f in files:
        if f.endswith(TEXT) and f not in ALLOWED and not f.startswith(("docs/superpowers/", "web/dist/")):
            text = (ROOT / f).read_text(encoding="utf-8", errors="ignore")
            out += [f"{f}:{text.count(chr(10), 0, m.start()) + 1}: {m.group(0)}" for m in rx.finditer(text)]
    return out


def test_nothing_calls_the_seat_data_real():
    assert not hits(REAL), "\n".join(hits(REAL))


def test_nothing_says_power_bi_itself_was_checked():
    assert not hits(POWER_BI), "\n".join(hits(POWER_BI))


def test_fair_share_has_no_qsi_synonym():
    assert "QSI" not in (ROOT / "lakehouse/03_metric_view.sql").read_text(encoding="utf-8")


# the figures that print data values (05 prints none); every one says so in its logo band, and so does each animated twin
DATA_FIGURES = ["04-journey-sales-director", "04-journey-sales-director-animated", "06-data-pipeline", "06-data-pipeline-animated",
                "07-fair-share", "08-why-it-moved", "08-why-it-moved-animated", "09-definitions", "09a-numbers-share", "09a-numbers-share-animated",
                "09b-numbers-gaps", "09b-numbers-gaps-animated", "10-coverage", "11-revenue-by-month", "11-revenue-by-month-animated",
                "12-share-vs-fair", "14-what-was-planted"]


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
