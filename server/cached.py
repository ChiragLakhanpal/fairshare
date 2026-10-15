"""FAIRSHARE_MODEL=none: the three scripted answers recorded by `python -m harness.cache`, served in the Answer shape so
the app works on a laptop with no model (the page says the answer is cached)."""
import json
import re

from fairshare.db import ROOT
from harness.verifier import SENTENCE_SPLIT

FILE = ROOT / "app" / "cache" / "answers.json"


def _norm(q: str) -> str:
    return re.sub(r"\s+", " ", q.strip().lower())


def lookup(question: str) -> dict | None:
    if not FILE.exists():
        return None
    data = json.loads(FILE.read_text())
    hit = next((v for k, v in data.items() if _norm(k) == _norm(question)), None)
    if hit is None:
        return None
    flagged = {f["sentence"] for f in hit.get("flagged", [])}
    sentences = [{"text": s, "status": "flagged" if s in flagged else "verified", "numbers": []}
                 for s in SENTENCE_SPLIT.split(hit["text"].strip()) if s.strip()]
    calls = [{"i": i + 1, "tool": "ask_metrics", "args": {"question": question}, "sql": sql, "rows": None, "note": "", "preview": [], "genie": None, "ms": 0}
             for i, sql in enumerate(hit.get("sql", []))]
    return {"question": question, "text": hit["text"], "model": hit.get("model", ""), "kind": "numbers", "sentences": sentences,
            "removed": hit.get("flagged", []), "could_not_verify": [s["text"] for s in sentences if s["text"].lower().startswith("could not verify")],
            "verified_text": " ".join(s["text"] for s in sentences if s["status"] == "verified"), "calls": calls, "sources": hit.get("sources", []),
            "follow_ups": FOLLOW_UPS["numbers"], "genie_conversation_id": None, "timing": {"total_ms": 0, "tools_ms": 0},
            "cached": {"recorded": hit.get("recorded"), "model": hit.get("model")}, "trace_url": None}


FOLLOW_UPS = {
    "numbers": ["Why did this change?", "How does that compare with fair share?", "Show me the last twelve months."],
    "why": ["What does the agreement say?", "How does this compare with last month?", "Draft a note to the account manager about this."],
    "agreement": ["Has this happened?", "What are the incentive tiers?", "Show me this agency's numbers for the quarter."],
    "refusal": ["Which agencies are behind pace?", "Who lost the most share this month?", "Show me the proxy rule."],
    "meta": ["Why did this change?", "Show me the same for last month.", "What does the agreement say?"],
    "general": ["Which agencies are behind pace?", "Why is Harbor down this month?", "What does Summit's agreement say about a share floor?"],
}
