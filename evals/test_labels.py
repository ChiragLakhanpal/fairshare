"""The repo never calls the made-up seat data real, never says Power BI itself was checked, fair share has no wrong synonym, and portable SQL never escapes a quote."""
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
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


# the figures that print data values (05 prints none); every one says so in its logo band
DATA_FIGURES = ["04-journey-sales-director", "06-data-pipeline", "07-fair-share", "08-why-it-moved", "09-definitions"]


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
