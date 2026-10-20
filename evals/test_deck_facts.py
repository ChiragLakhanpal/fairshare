"""What the deck says about the data, checked against the local DuckDB build (python lakehouse/run.py first)."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from fairshare import db  # noqa: E402


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
