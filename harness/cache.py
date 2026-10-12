"""Offline fallback for the demo: record the three scripted answers and the latest parity run, so the app can show them
with no network (phone hotspot down, Wi-Fi blocked, Genie slow).

  FAIRSHARE_BACKEND=databricks FAIRSHARE_MODEL=azure python -m harness.cache      # writes app/cache/answers.json and kpi_parity.csv
"""
import json
from datetime import datetime
from pathlib import Path

from fairshare import db
from harness import agent as harness_agent

ROOT = Path(__file__).resolve().parents[1]
CACHE = ROOT / "app" / "cache"
SCRIPTED = [
    "How did Summit Travel Partners do on DFW to ORD in Q3 2026 versus Q3 2025, and are they ahead of fair share?",
    "What does Summit Travel Partners' agreement say happens if their share drops under 45% for two quarters, and has that happened?",
    "Which agencies are about to churn?",
]


def main():
    CACHE.mkdir(exist_ok=True)
    ag = harness_agent.make_agent()
    answers = {}
    if ag is not None:
        for q in SCRIPTED:
            a = harness_agent.ask(q, ag)
            answers[q] = {"text": a.text, "flagged": a.flagged, "sql": [c.sql for c in a.calls if c.sql], "sources": a.sources,
                          "model": a.model, "recorded": datetime.now().isoformat(timespec="minutes")}
            print(f"cached: {q[:60]}... ({'clean' if a.verification.ok else 'flagged'})")
        (CACHE / "answers.json").write_text(json.dumps(answers, indent=2))
    if db.is_databricks():
        try:
            par = db.query("SELECT * FROM aa_demo.ops.kpi_parity")
            par.to_csv(CACHE / "kpi_parity.csv", index=False)
            print(f"cached parity: {len(par)} rows")
        except Exception as e:
            print(f"no parity to cache: {e}")


if __name__ == "__main__":
    main()
