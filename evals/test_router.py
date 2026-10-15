"""The chat router (server/router.py): questions about the last answer come from its record, concept questions with no
domain term go to a tool-less writer with a label, everything else goes to the sales agent. A function, not a model."""
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from server import router  # noqa: E402

CASES = [
    # about the last answer
    ("What are the checks you performed?", "meta"),
    ("Which query did you run?", "meta"),
    ("what queries did you use for that", "meta"),
    ("How did you verify that number?", "meta"),
    ("How was this answer checked?", "meta"),
    ("What did you remove?", "meta"),
    ("Show me the SQL you ran.", "meta"),
    ("Where did that number come from?", "meta"),
    ("Which tables did you use?", "meta"),
    ("Is that number verified?", "meta"),
    # general knowledge, no domain term
    ("What is NDC?", "general"),
    ("What does TMC stand for?", "general"),
    ("Explain what a GDS is.", "general"),
    ("Who is the CEO of Delta?", "general"),
    ("What is a travel management company?", "general"),
    ("How does an airline loyalty program usually work?", "general"),
    ("How does an airline incentive program usually work?", "data"),  # "incentive" is a term from the agreements: a domain term wins over concept phrasing
    ("Define fare basis.", "general"),
    ("hello", "general"),
    ("thanks!", "general"),
    ("What are the main global distribution systems?", "general"),
    # the data
    ("Why is Harbor down this month?", "data"),
    ("Which agencies are behind pace?", "data"),
    ("What does Summit's agreement say about a share floor?", "data"),
    ("Explain fair share.", "data"),
    ("What is AA share for FareHub in Q3 2026?", "data"),
    ("Show me revenue by region for 2026.", "data"),
    ("How did BlueSky do on DFW to ORD last quarter versus last year?", "data"),
    ("What is the share gap in dollars for the East region?", "data"),
    ("Which markets did Marcus Lee's agencies lose share on?", "data"),
    ("Top 5 agencies by revenue in September.", "data"),
]


@pytest.mark.parametrize("question,expected", CASES)
def test_classify(question, expected):
    assert router.classify(question) == expected, question


def test_meta_answer_from_the_record():
    last = {"calls": [{"tool": "ask_metrics", "args": {"question": "Harbor revenue in August 2026"}, "sql": "SELECT 1", "rows": 1, "note": ""},
                      {"tool": "explain_change", "args": {"agency": "Harbor", "month": "2026-08"}, "sql": "aa_demo.ops.decomposition", "rows": 1, "note": ""}],
            "removed": [{"sentence": "Engagement rose 12%.", "reason": "no query supports 12%"}], "verified_numbers": 5, "sources": ["Genie: sales_metrics", "ops.decomposition"]}
    a = router.meta_answer("What are the checks you performed?", last)
    assert a["kind"] == "meta" and "2 queries" in a["text"] and "Genie" in a["text"] and "12%" in a["text"] and "5 numbers" in a["text"]
    assert a["calls"] and a["calls"][0]["sql"] == "SELECT 1" and all(s["status"] == "note" for s in a["sentences"]) and a["removed"] == []
    assert a["verified_text"] == a["text"] and a["follow_ups"]


def test_meta_answer_without_a_previous_answer():
    a = router.meta_answer("Which query did you run?", None)
    assert a["kind"] == "meta" and "no previous answer" in a["text"].lower() and a["calls"] == []


def test_general_answer_shape_marks_every_sentence_as_a_note():
    a = router.general_answer("What is NDC?", "NDC is a data standard for airline retailing. It replaces older messaging formats.")
    assert a["kind"] == "general" and [s["status"] for s in a["sentences"]] == ["note", "note"] and a["removed"] == [] and a["calls"] == []
