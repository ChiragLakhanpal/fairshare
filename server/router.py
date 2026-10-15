"""Which path a question takes, decided before any model runs.

  meta      a question about the last answer (what checks, which query, what was removed): answered from the record the
            browser kept of that answer, with no tools and no model, so the harness never re-runs a query to explain itself
  general   a concept question with no term from the data (what is NDC): a tool-less writer answers, and the answer is
            labeled as not from the data
  data      everything else: the sales agent, Genie, the verifier

A function with a test table, not a model: cheap, and its behavior is on record. Terms from the data (agency names,
markets, cities, account managers) are read from the gold tables once per process.
"""
from __future__ import annotations

import re
from functools import lru_cache

from fairshare import db
from harness.verifier import SENTENCE_SPLIT

META = re.compile(
    r"\b(what|which)\b.*\b(checks?|quer(?:y|ies)|sql|tools?|tables?|sources?|steps?)\b.*\b(you|did|ran|run|performed|used|use)\b"
    r"|\bhow (did|was|were) (you|that|this|it|the (answer|number|numbers))\b.*\b(get|got|check|checked|verif(?:y|ied)|comput(?:e|ed)|arrive|arrived|come|came)\b"
    r"|\bwhat did you (remove|take out|drop|leave out|verify|check|run|query)\b"
    r"|\bwhat was (removed|checked|verified)\b"
    r"|\bshow (me )?(the )?(sql|quer(?:y|ies)|checks?)( that| you| it)? ?(ran|used|did|run)?\b"
    r"|\bwhere (did|does) (that|this|the) (number|numbers|answer|data|figure) come from\b"
    r"|\bis (that|this) (number|answer|figure) (verified|checked|right|correct)\b",
    re.I)
CONCEPT = re.compile(r"^\s*(what is|what are|what does\b.*\b(mean|stand for)|what do\b.*\bstand for|explain|define|who is|who are|how does?\b.*\bwork)\b", re.I)
SMALLTALK = re.compile(r"^\s*(hi|hello|hey|thanks|thank you|good (morning|afternoon|evening)|how are you|ok|okay|cool|great|bye|goodbye)\b", re.I)
KPI_WORDS = {
    "revenue", "share", "fair", "gap", "pace", "goal", "goals", "agency", "agencies", "market", "markets", "route", "routes", "agreement", "agreements",
    "contract", "contracts", "clause", "incentive", "incentives", "tier", "tiers", "region", "regions", "central", "east", "west", "quarter", "quarters",
    "month", "months", "year", "yoy", "booking", "bookings", "booked", "corporate", "corporates", "passenger", "passengers", "pax", "seat", "seats",
    "capacity", "decline", "churn", "dollar", "dollars", "sales", "sold", "ytd", "q1", "q2", "q3", "q4", "behind", "ahead", "top", "lost", "won", "gained",
    "january", "february", "march", "april", "may", "june", "july", "august", "september", "october", "november", "december", "aa", "american",
    "manager", "managers", "commitment", "floor", "premium", "volume", "mix", "decomposition", "moved", "down", "up", "versus", "vs",
}
GENERIC_NAME_WORDS = {"travel", "corporate", "online", "group", "services", "partners", "leisure", "business", "gateway", "premier", "the", "of"}


@lru_cache(maxsize=1)
def domain_terms() -> frozenset[str]:
    """Agency name words, market codes and cities, and account manager names from the data, plus the KPI words."""
    terms = set(KPI_WORDS)
    try:
        ag = db.query("SELECT agency_name, account_manager FROM aa_demo.gold.dim_agency")
        for name in list(ag["agency_name"]) + list(ag["account_manager"]):
            terms |= {w for w in re.findall(r"[a-z]+", str(name).lower()) if w not in GENERIC_NAME_WORDS}
        mk = db.query("SELECT origin, dest FROM aa_demo.gold.dim_market")
        terms |= {str(c).lower() for c in list(mk["origin"]) + list(mk["dest"])}
    except Exception:  # no lakehouse yet: the KPI words alone still route the obvious cases
        pass
    terms |= {"dallas", "fort", "worth", "chicago", "charlotte", "york", "laguardia", "miami", "phoenix", "seattle", "washington", "reagan", "francisco",
              "boston", "denver", "austin", "los", "angeles", "jfk", "kennedy"}
    return frozenset(terms)


def classify(question: str) -> str:
    q = (question or "").strip()
    if not q:
        return "data"
    if META.search(q):
        return "meta"
    tokens = re.findall(r"[a-z0-9]+", q.lower())
    if any(t in domain_terms() for t in tokens) or re.search(r"[\d$%]", q):
        return "data"
    if CONCEPT.match(q) or SMALLTALK.match(q):
        return "general"
    return "data"


def _notes(text: str) -> list[dict]:
    return [{"text": s.strip(), "status": "note", "numbers": []} for s in SENTENCE_SPLIT.split(text) if s and s.strip()]


def _describe(call: dict) -> str:
    tool, args = call.get("tool"), call.get("args") or {}
    rows = call.get("rows")
    rows_words = f" ({rows} {'row' if rows == 1 else 'rows'})" if isinstance(rows, int) else ""
    if tool == "ask_metrics":
        return f"Genie, asked \"{args.get('question', '')}\"{rows_words}"
    if tool == "run_sql":
        tables = sorted(set(re.findall(r"aa_demo\.\w+\.\w+", str(call.get("sql") or ""))))
        return f"a SQL query on {', '.join(tables) if tables else 'the gold tables'}{rows_words}"
    if tool == "explain_change":
        return f"the decomposition for {args.get('agency', 'the agency')} in {args.get('month', 'the month')}{rows_words}"
    if tool == "search_contracts":
        return f"the agreement search for {args.get('agency', 'the agency')} about {args.get('topic', 'the topic')}"
    if tool == "build_summary":
        return f"the summary's {args.get('block', 'facts')} block{rows_words}"
    return f"{tool}{rows_words}"


def meta_answer(question: str, last: dict | None) -> dict:
    """The checks on the last answer, from the browser's record of it. No model, no tools, nothing re-run."""
    from server.cached import FOLLOW_UPS
    if not last or not isinstance(last, dict) or not (last.get("calls") or last.get("verified_numbers") or last.get("removed")):
        text = "There is no previous answer in this conversation to check. Ask a question about the data first, and I will show the queries behind the answer."
        calls = []
    else:
        calls = [c for c in (last.get("calls") or []) if isinstance(c, dict)]
        n = len(calls)
        removed = [r for r in (last.get("removed") or []) if isinstance(r, dict)]
        k = int(last.get("verified_numbers") or 0)
        parts = []
        if n:
            parts.append(f"I ran {n} {'query' if n == 1 else 'queries'} for the last answer: " + "; ".join(_describe(c) for c in calls) + ".")
        else:
            parts.append("The last answer ran no query.")
        parts.append(f"The checker matched {'the 1 number' if k == 1 else f'all {k} numbers'} in the sentences you saw against the query results, at the same rounding."
                     if k else "The sentences you saw carried no numbers to check.")
        if removed:
            parts.append(f"It removed {len(removed)} {'sentence' if len(removed) == 1 else 'sentences'} before you saw the answer: " +
                         " ".join(f"\"{r.get('sentence', '')}\" ({r.get('reason', '')})." for r in removed))
        else:
            parts.append("Nothing was removed.")
        parts.append("The queries and the result tables are under Show the query on that answer, and the Genie conversation opens from Open in Genie.")
        text = " ".join(parts)
    calls_json = [{"i": i + 1, "tool": c.get("tool", ""), "args": c.get("args") or {}, "sql": c.get("sql"), "rows": c.get("rows"), "note": c.get("note", ""),
                   "preview": [], "genie": c.get("genie"), "ms": 0} for i, c in enumerate(calls)]
    return {"question": question, "text": text, "model": "none", "kind": "meta", "sentences": _notes(text), "removed": [], "could_not_verify": [],
            "verified_text": text, "calls": calls_json, "sources": list(last.get("sources") or []) if last else [], "follow_ups": FOLLOW_UPS["meta"],
            "genie_conversation_id": None, "timing": {"total_ms": 0, "tools_ms": 0}, "cached": None, "trace_url": None}


GENERAL_INSTRUCTIONS = """You answer a general question for an airline sales team in two or three plain sentences. You have no access to
the team's data; if the question needs their numbers, say that and suggest asking it as a data question. Plain punctuation, no em
dashes, no bullet points, no preamble."""


def general_answer(question: str, text: str, model: str = "") -> dict:
    """A concept answer from the writer, labeled as not from the data. Every sentence is a note: nothing here claims a number from a query."""
    from server.cached import FOLLOW_UPS
    text = (text or "").strip().replace(" — ", ", ").replace("—", ", ")
    return {"question": question, "text": text, "model": model, "kind": "general", "sentences": _notes(text), "removed": [], "could_not_verify": [],
            "verified_text": text, "calls": [], "sources": [], "follow_ups": FOLLOW_UPS["general"], "genie_conversation_id": None,
            "timing": {"total_ms": 0, "tools_ms": 0}, "cached": None, "trace_url": None}
