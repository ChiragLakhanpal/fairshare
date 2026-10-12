"""Runs the twenty benchmark questions.

  python evals/run_benchmark.py --check            # ground-truth SQL only: every query runs and returns rows (works offline; the pre-commit hook uses this)
  python evals/run_benchmark.py --genie            # Genie alone (Databricks + GENIE_SPACE_ID): result set vs ground truth
  python evals/run_benchmark.py --harness          # the full harness: verifier (deterministic) + LLM judge vs ground truth
  python evals/run_benchmark.py --genie --harness --label "after prompt change"

Writes evals/results/<timestamp>.json, updates evals/results/latest.json and evals/results/README.md (one row per run).
A result set "matches" when every ground-truth row is represented by a returned row sharing at least half of its numbers (see matches()).
"""
from __future__ import annotations

import argparse
import asyncio
import json
import sys
import time
from datetime import datetime
from pathlib import Path

import pandas as pd
import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from fairshare import db  # noqa: E402

HERE = Path(__file__).parent
RESULTS = HERE / "results"


def load():
    return yaml.safe_load((HERE / "benchmark.yaml").read_text())["questions"]


def row_keys(df: pd.DataFrame) -> list[tuple]:
    """Each row as a sorted tuple of its rounded numeric values (names and order do not matter)."""
    keys = []
    for _, r in df.iterrows():
        nums = []
        for v in r.values:
            try:
                f = float(v)
            except (TypeError, ValueError):
                continue
            if pd.notna(f):
                nums.append(round(f, 1))
        keys.append(tuple(sorted(nums)))
    return keys


def matches(gt: pd.DataFrame, got: pd.DataFrame | None) -> bool:
    """Every ground-truth row is represented by some returned row that shares at least half of its numbers (within rounding),
    and the returned set is not smaller than the ground truth. Extra or missing columns are fine; wrong numbers are not."""
    if got is None or got.empty:
        return False
    gk, ok = row_keys(gt), row_keys(got)
    if len(ok) < len(gk):
        return False
    def overlap(g, o):
        hits = sum(any(abs(x - y) <= max(0.6, abs(x) * 0.005) for y in o) for x in g)
        return hits >= max(1, (len(g) + 1) // 2)
    return all(any(overlap(g, o) for o in ok) for g in gk)


def check(questions):
    bad = 0
    for q in questions:
        try:
            df = db.query(q["sql"])
            print(f"{q['id']} ok  {len(df):3d} rows  {q['question'][:70]}")
        except Exception as e:
            bad += 1
            print(f"{q['id']} FAIL {e}")
    return bad


def genie_run(questions):
    from harness.tools import _genie_ask
    out = []
    for q in questions:
        gt = db.query(q["sql"])
        t0 = time.time()
        try:
            text, df, sql = _genie_ask(q["question"])
            ok = matches(gt, df)
            err = None
        except Exception as e:
            df, sql, ok, err = None, None, False, str(e)
        out.append({"id": q["id"], "pass": ok, "seconds": round(time.time() - t0, 1), "genie_sql": sql, "error": err, "hard": q.get("hard", False)})
        print(f"{q['id']} {'PASS' if ok else 'FAIL'} {out[-1]['seconds']}s")
        time.sleep(2)
    return out


JUDGE = """You are grading an analytics answer. GROUND TRUTH is a table computed from the warehouse; ANSWER is what an agent said.
Grade CORRECT if every number the ANSWER states agrees with GROUND TRUTH within rounding and the answer addresses the question;
PARTIAL if the main figure agrees but something is missing or extra; WRONG if a stated number contradicts GROUND TRUTH or the answer dodges.
Reply with one word: CORRECT, PARTIAL or WRONG."""


def harness_run(questions):
    from harness import agent as harness_agent
    ag = harness_agent.make_agent()
    if ag is None:
        raise SystemExit("no model configured (FAIRSHARE_MODEL)")
    from agent_framework import Agent
    judge = Agent(harness_agent.make_client(), instructions=JUDGE, name="judge")
    out = []
    for q in questions:
        gt = db.query(q["sql"])
        t0 = time.time()
        try:
            a = harness_agent.ask(q["question"], ag)
            verdict = asyncio.run(judge.run(f"QUESTION: {q['question']}\n\nGROUND TRUTH:\n{gt.to_string(index=False)}\n\nANSWER:\n{a.text}")).text.strip().upper()
            rec = {"id": q["id"], "supported": a.verification.ok, "flagged": a.flagged, "judge": verdict[:8], "tools": [c.tool for c in a.calls],
                   "seconds": round(time.time() - t0, 1), "answer": a.text, "hard": q.get("hard", False)}
        except Exception as e:
            rec = {"id": q["id"], "supported": False, "flagged": [], "judge": "ERROR", "tools": [], "seconds": round(time.time() - t0, 1), "answer": str(e), "hard": q.get("hard", False)}
        out.append(rec)
        print(f"{q['id']} supported={rec['supported']} judge={rec['judge']} tools={rec['tools']} {rec['seconds']}s")
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--genie", action="store_true")
    ap.add_argument("--harness", action="store_true")
    ap.add_argument("--label", default="")
    args = ap.parse_args()
    questions = load()
    if args.check or not (args.genie or args.harness):
        bad = check(questions)
        print(f"ground truth: {len(questions) - bad}/{len(questions)} run")
        sys.exit(1 if bad else 0)
    RESULTS.mkdir(exist_ok=True)
    result = {"run_at": datetime.now().isoformat(timespec="seconds"), "label": args.label, "backend": db.backend(), "n": len(questions)}
    if args.genie:
        g = genie_run(questions)
        result["genie"] = g
        result["genie_pass_rate"] = sum(x["pass"] for x in g) / len(g)
    if args.harness:
        h = harness_run(questions)
        result["harness"] = h
        result["harness_supported_rate"] = sum(x["supported"] for x in h) / len(h)
        result["harness_correct_rate"] = sum(x["judge"] == "CORRECT" for x in h) / len(h)
    stamp = result["run_at"].replace(":", "")
    (RESULTS / f"{stamp}.json").write_text(json.dumps(result, indent=2, default=str))
    (RESULTS / "latest.json").write_text(json.dumps(result, indent=2, default=str))
    readme = RESULTS / "README.md"
    if not readme.exists():
        readme.write_text("# Benchmark runs\n\n| run | label | backend | Genie pass | harness supported | harness correct |\n|---|---|---|---|---|---|\n")
    with readme.open("a") as f:
        f.write(f"| {result['run_at']} | {args.label} | {db.backend()} | {result.get('genie_pass_rate', '')} | {result.get('harness_supported_rate', '')} | {result.get('harness_correct_rate', '')} |\n")
    print(json.dumps({k: v for k, v in result.items() if not isinstance(v, list)}, indent=2))


if __name__ == "__main__":
    main()
