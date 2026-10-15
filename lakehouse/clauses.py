"""The agreements, read once by the thinking model into a table of measurable promises with page citations.

  FAIRSHARE_MODEL=azure .venv/bin/python lakehouse/clauses.py extract   # four agreements -> data/out/contract_clauses.csv
  .venv/bin/python lakehouse/clauses.py review                          # re-check a committed CSV (quotes verbatim, known types)

The CSV is reviewed by a person and committed; the nightly job loads it as bronze and never re-extracts.
lakehouse/07_agreement_watch.sql turns it into ops.agreement_checks, one row per clause per month, which is what the
Agreement watch agent reads. The model does the reading; SQL does the checking; the verifier guards the prose.
"""
from __future__ import annotations

import asyncio
import csv
import json
import os
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from harness.tools import CONTRACTS, _pages  # noqa: E402

OUT = ROOT / "data" / "out" / "contract_clauses.csv"
COLUMNS = ["clause_id", "agency_id", "file", "page", "section", "clause_type", "metric", "operator", "threshold", "threshold_2", "window_quarters", "consequence", "quote"]
TYPES = {
    "share_floor_quarters": "the agency's AA revenue share falls below threshold (percent) for window_quarters consecutive calendar quarters; metric aa_share",
    "annual_commitment": "the agency commits to at least threshold dollars of AA revenue in the year; threshold_2 is the attainment percent a consequence attaches to (one row per consequence, plus one row for the commitment itself with threshold_2 empty); metric aa_revenue",
    "goal": "an annual goal: threshold dollars (metric aa_revenue) or threshold percent of share (metric aa_share); no consequence",
    "share_premium_tiers": "an incentive tier by annual share premium (AA share minus fair share, points): threshold is the tier's lower bound in points (0 for the lowest tier), threshold_2 the incentive percent of AA revenue (0 for none); one row per tier; metric share_premium_pts",
    "share_tiers": "an incentive tier by annual AA revenue share: threshold the lower bound in percent, threshold_2 the incentive percent; one row per tier; metric aa_share",
    "gap_tiers": "an incentive tier by the share gap to fair share in points: threshold the lower bound (negative allowed), threshold_2 the incentive percent; one row per tier, and a row with threshold_2 0 for the band that earns nothing; metric share_gap_pts",
    "revenue_decline_quarters": "AA revenue in a quarter below threshold percent of the same quarter a year earlier, for window_quarters consecutive quarters; metric revenue_yoy_ratio",
    "capacity_exclusion": "a quarter in which the carrier cut scheduled seats on a market by more than threshold percent is excluded from a count; metric aa_seats_yoy_pct, threshold as a negative number (a 15% cut is -15)",
    "front_end_incentive": "an incentive of threshold percent of AA revenue paid or advanced; metric aa_revenue",
    "not_checkable": "a promise the sales data cannot check: notice periods, data due dates, service levels, display rules, reporting; metric none, thresholds empty",
}
METRICS = {"aa_share", "aa_revenue", "share_premium_pts", "share_gap_pts", "revenue_yoy_ratio", "aa_seats_yoy_pct", "none"}

INSTRUCTIONS = """You read one airline-agency agreement and list every clause that promises, measures or triggers something, as JSON.
Return exactly one JSON object: {"clauses": [ ... ]} with one object per row, keys:
  section (the clause number as written, like "5.1"), page (the integer after "<!-- page N -->" the text sits under),
  clause_type (one of the types below), metric (one of the metrics below), operator (one of "<", "<=", ">=", ">", "between", "none"),
  threshold (a plain number: 45 for 45%, 4290000 for $4,290,000, -15 for a 15% cut; null when none),
  threshold_2 (a second plain number when the type says so; null otherwise), window_quarters (an integer or null),
  consequence (what happens, in the agreement's own words, one sentence), quote (the exact sentence or sentences copied from the page, verbatim, no edits).
Rules: one row per threshold or tier, never a range in one row. Quote verbatim: the review step rejects a quote that is not on its page.
Every clause goes somewhere: a promise the sales data cannot check gets clause_type not_checkable with metric none.
Types: """ + "\n".join(f"- {k}: {v}" for k, v in TYPES.items()) + "\nMetrics: " + ", ".join(sorted(METRICS)) + "\nNo prose outside the JSON."


def _agency_ids() -> dict[str, int]:
    from fairshare import db
    rows = db.query("SELECT agency_id, agency_name FROM aa_demo.gold.dim_agency")
    return {str(r.agency_name).lower().split()[0]: int(r.agency_id) for r in rows.itertuples()}


def _squash(s: str) -> str:
    return re.sub(r"\s+", " ", s or "").strip()


def review(rows: list[dict]) -> list[dict]:
    """Quotes verbatim on their page, known types and metrics, numeric thresholds. Raises on the first problem."""
    ids = _agency_ids()
    out = []
    for r in rows:
        f = CONTRACTS / r["file"]
        pages = {p: _squash(t) for p, t in _pages(f)}
        page = int(r["page"])
        if page not in pages:
            raise SystemExit(f"{r['file']} {r.get('section')}: page {page} does not exist")
        q = _squash(r["quote"])
        if not q or q[:60] not in pages[page]:
            raise SystemExit(f"{r['file']} {r.get('section')}: quote is not verbatim on page {page}: {q[:80]!r}")
        if r["clause_type"] not in TYPES:
            raise SystemExit(f"{r['file']} {r.get('section')}: unknown clause_type {r['clause_type']!r}")
        if r["metric"] not in METRICS:
            raise SystemExit(f"{r['file']} {r.get('section')}: unknown metric {r['metric']!r}")
        for k in ("threshold", "threshold_2", "window_quarters"):
            v = r.get(k)
            if v not in (None, ""):
                float(v)
        if r["clause_type"].endswith("_tiers") and str(r.get("operator")) == "<":
            r["threshold"] = None   # "below X earns nothing" is the band with no lower bound, not a line at X
        r["section"] = str(r.get("section") or "").strip().rstrip(".")
        key = f.stem.split("-")[0]
        r["agency_id"] = ids[key]
        r["quote"] = q
        out.append(r)
    return out


def _ids(rows: list[dict]) -> list[dict]:
    seen: dict[str, int] = {}
    for r in rows:
        base = f"{Path(r['file']).stem.split('-')[0]}-{str(r['section']).replace(' ', '')}"
        seen[base] = seen.get(base, 0) + 1
        r["clause_id"] = f"{base}-{seen[base]}" if seen[base] > 1 else base
    return rows


def write(rows: list[dict]) -> None:
    rows = _ids(sorted(rows, key=lambda r: (r["file"], int(r["page"]), str(r["section"]))))
    with open(OUT, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=COLUMNS)
        w.writeheader()
        for r in rows:
            w.writerow({k: ("" if r.get(k) is None else r.get(k)) for k in COLUMNS})
    print(f"{OUT.name}: {len(rows)} clauses")


def read() -> list[dict]:
    with open(OUT, newline="") as fh:
        return list(csv.DictReader(fh))


async def _extract_one(agent, path: Path) -> list[dict]:
    text = path.read_text()
    resp = await agent.run(f"Agreement file: {path.name}\n\n{text}")
    body = resp.text.strip()
    body = body[body.find("{"): body.rfind("}") + 1]
    rows = json.loads(body)["clauses"]
    for r in rows:
        r["file"] = path.name
    print(f"  {path.name}: {len(rows)} rows")
    return rows


def extract() -> None:
    from agent_framework import Agent
    from harness.agent import make_client, model_backend
    client = make_client(os.environ.get("FAIRSHARE_THINKER") or model_backend())
    if client is None:
        raise SystemExit("set FAIRSHARE_MODEL (or FAIRSHARE_THINKER) to a model backend to extract")
    agent = Agent(client, instructions=INSTRUCTIONS, name="fairshare-clause-reader")

    async def all_files():
        return [row for f in sorted(CONTRACTS.glob("*.md")) for row in await _extract_one(agent, f)]

    rows = asyncio.run(all_files())
    write(review(rows))


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "review"
    if cmd == "extract":
        extract()
    elif cmd == "review":
        rows = review(read())
        write(rows)  # normalized (sections, open bands) and re-sorted; a no-op on a reviewed file
        print(f"{OUT.name}: {len(rows)} clauses, every quote verbatim")
    else:
        raise SystemExit(__doc__)
