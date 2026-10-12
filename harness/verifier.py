"""The last step on every answer: every number in the draft must exist in a tool result.

Deterministic, no model. A sentence whose numbers all match the fact pool is verified; a sentence
with any unmatched number is moved to `flagged` with the reason "no query supports <number>".
This is the guard against the Monday-morning hallucination (a summary that quotes a figure nobody
queried), and it is why the model is told never to compute: if a derived number is useful, a tool
returns it as a column.

Matching is by displayed precision: "$2.1M" matches 2,087,431.52; "15.5%" matches 0.1551 from a
share column or 15.5 from a pct column; "14 points" matches 14.2 from a pts column.
"""
from __future__ import annotations

import math
import re
from dataclasses import dataclass, field

import pandas as pd

NUMBER = re.compile(
    r"(?P<sign0>[-+])?(?P<cur>\$)?\s?(?P<sign>[-+])?(?P<num>\d{1,3}(?:,\d{3})+|\d+)(?P<dec>\.\d+)?\s?"
    r"(?P<unit>%|percent(?:age points?)?|points?|pts|bn|B|M|K|k|m)?(?![\w-])"
)
DATE_LIKE = re.compile(
    r"\b(?:19|20)\d{2}-\d{2}(?:-\d{2})?\b|\bQ[1-4]\b|\b(?:19|20)\d{2}\b|\b\d{1,2}/\d{1,2}(?:/\d{2,4})?\b"
    r"|\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec)[a-z]*\.?\s+\d{1,2}(?:st|nd|rd|th)?(?:,?\s+(?:19|20)\d{2})?\b"
    r"|\b\d{1,2}(?:st|nd|rd|th)?\s+(?:of\s+)?(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec)[a-z]*\b", re.I)
SENTENCE_SPLIT = re.compile(r"(?<=[.!?])\s+(?=[A-Z\[\(\"$])|\n+")
SCALE = {"K": 1e3, "k": 1e3, "M": 1e6, "m": 1e6, "B": 1e9, "bn": 1e9}
PCT_WORDS = {"%", "percent", "percentage points", "percentage point"}
PTS_WORDS = {"points", "point", "pts"}
RATIO_HINTS = ("share", "pct", "ratio", "rate", "pace")
USD_HINTS = ("revenue", "usd", "goal", "commit", "fare", "effect", "gap_usd", "market_now", "market_prior", "delta_revenue")
PTS_HINTS = ("pts", "points")


@dataclass
class Fact:
    value: float
    unit: str          # usd | pct | pts | count
    source: str        # which tool result it came from
    label: str         # column=value, for the audit page


@dataclass
class FactPool:
    facts: list[Fact] = field(default_factory=list)

    def add(self, value, unit: str, source: str, label: str = ""):
        if value is None or (isinstance(value, float) and math.isnan(value)):
            return
        self.facts.append(Fact(float(value), unit, source, label or f"{value}"))

    def add_frame(self, df: pd.DataFrame, source: str):
        """Every numeric cell becomes a fact; ratio-looking columns are also offered as percentages."""
        for col in df.columns:
            if not pd.api.types.is_numeric_dtype(df[col]) or pd.api.types.is_bool_dtype(df[col]):
                continue
            name = str(col).lower()
            for v in df[col].dropna().tolist():
                v = float(v)
                label = f"{col}={v}"
                if any(h in name for h in PTS_HINTS):
                    self.add(v, "pts", source, label)
                    self.add(v, "pct", source, label)
                elif any(h in name for h in USD_HINTS):
                    self.add(v, "usd", source, label)
                elif "pct" in name or "percent" in name:   # already in percent units whatever the magnitude (yoy_pct = -0.4)
                    self.add(v, "pct", source, label)
                    self.add(v, "pts", source, label)
                elif any(h in name for h in RATIO_HINTS):
                    if -1.5 <= v <= 1.5:
                        self.add(v * 100, "pct", source, label)   # 0.527 shown as 52.7%
                        self.add(v, "count", source, label)
                    else:
                        self.add(v, "pct", source, label)         # already in percent units (delta_pct, pace_pct)
                        self.add(v, "pts", source, label)
                else:
                    self.add(v, "count", source, label)
                    self.add(v, "usd", source, label)  # ids and counts rarely collide with dollar amounts at display precision

    def __len__(self):
        return len(self.facts)


@dataclass
class Number:
    raw: str
    value: float
    unit: str          # usd | pct | pts | count
    tolerance: float
    matched: Fact | None = None


@dataclass
class Sentence:
    text: str
    numbers: list[Number]

    @property
    def verified(self) -> bool:
        return all(n.matched is not None for n in self.numbers)

    @property
    def unmatched(self) -> list[Number]:
        return [n for n in self.numbers if n.matched is None]


@dataclass
class Verification:
    sentences: list[Sentence]

    @property
    def verified_text(self) -> str:
        return " ".join(s.text for s in self.sentences if s.verified)

    @property
    def flagged(self) -> list[dict]:
        return [{"sentence": s.text, "reason": "no query supports " + ", ".join(n.raw for n in s.unmatched)}
                for s in self.sentences if not s.verified]

    @property
    def ok(self) -> bool:
        return not self.flagged

    def badges(self) -> list[dict]:
        out = []
        for s in self.sentences:
            out.append({"sentence": s.text, "status": "verified" if s.verified else "flagged",
                        "numbers": [{"raw": n.raw, "source": n.matched.source if n.matched else None,
                                     "fact": n.matched.label if n.matched else None} for n in s.numbers]})
        return out


def extract_numbers(text: str) -> list[Number]:
    """Numbers with units; years, dates and quarter labels are skipped."""
    masked = DATE_LIKE.sub(lambda m: " " * len(m.group(0)), text)
    out = []
    for m in NUMBER.finditer(masked):
        raw = text[m.start():m.end()].strip()
        num = (m.group("num") or "").replace(",", "")
        if not num:
            continue
        value = float(num + (m.group("dec") or ""))
        decimals = len((m.group("dec") or ".")[1:])
        unit_tok = (m.group("unit") or "").strip()
        scale = SCALE.get(unit_tok, 1.0)
        if m.group("cur"):
            unit = "usd"
        elif unit_tok in PCT_WORDS:
            unit = "pct"
        elif unit_tok in PTS_WORDS:
            unit = "pts"
        else:
            unit = "count"
        if "-" in (m.group("sign") or "", m.group("sign0") or ""):
            value = -value
        tol = 0.5 * 10 ** (-decimals) * scale
        out.append(Number(raw=raw, value=value * scale, unit=unit, tolerance=tol))
    return out


def _match(n: Number, pool: FactPool) -> Fact | None:
    units = {"usd": ("usd",), "pct": ("pct", "pts"), "pts": ("pts", "pct"), "count": ("count", "usd", "pct", "pts")}[n.unit]
    best = None
    for f in pool.facts:
        if f.unit not in units:
            continue
        for v in (f.value, -f.value):  # "down 15.5%" is written positive for a negative delta
            if abs(v - n.value) <= max(n.tolerance, abs(v) * 0.0005):
                if best is None or abs(f.value - n.value) < abs(best.value - n.value):
                    best = f
    return best


INFORMATIONAL = re.compile(r"^(could not verify|source|sources|not in the data)\b", re.I)


def verify(draft: str, pool: FactPool) -> Verification:
    """Sentences that declare their own uncertainty ("Could not verify: ...") or name sources carry no claims and are not checked.
    Bare small integers with no unit ("3+ months", "two of the four agencies" written as 2) are thresholds and counts of
    things, not metrics, and cannot be matched meaningfully; they are skipped."""
    sentences = []
    for text in (s.strip() for s in SENTENCE_SPLIT.split(draft) if s and s.strip()):
        numbers = [] if INFORMATIONAL.match(text) else [n for n in extract_numbers(text)
                                                       if not (n.unit == "count" and float(n.value).is_integer() and abs(n.value) < 13 and "." not in n.raw and "," not in n.raw)]
        for n in numbers:
            n.matched = _match(n, pool)
        sentences.append(Sentence(text=text, numbers=numbers))
    return Verification(sentences)


if __name__ == "__main__":  # ponytail: the smallest check that fails if the matcher breaks
    pool = FactPool()
    pool.add_frame(pd.DataFrame({"aa_revenue": [2087431.52], "aa_share": [0.5271], "fair_share": [0.3846],
                                 "share_gap_pts": [14.25], "aa_pax": [6100], "delta_pct": [-15.5]}), "q1")
    v = verify("Summit Travel Partners, Q3 2026: AA revenue $2.1M. Share 52.7% against a fair share of 38.5%, 14 points ahead. "
               "Passengers 6,100. Revenue down 15.5%. WoW engagement rose 12% in the week of 2026-09-28.", pool)
    assert [s.verified for s in v.sentences] == [True, True, True, True, False], v.badges()
    assert "12%" in v.flagged[0]["reason"]
    print("verifier ok:", len(v.sentences), "sentences,", len(v.flagged), "flagged")
