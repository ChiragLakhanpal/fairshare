"""What is worth knowing this month, before anyone asks: the home page's second block.

Fixed queries on the gold and ops tables, one template sentence per finding, the verifier on every sentence against the
rows of its own query, and no model anywhere: the home page never runs one. Each line names the agency it is about (for
the related line under an Ask answer), carries one action (ask a question, open a Delegate agent, open a definition) and
a question for the suggestion chips.

  build(region, month)   the ranked lines, at most LIMIT; every query is recorded as a "signals" call for the route

Ranking: a breached clause first; then the dollars at stake (a tier within reach, a commitment slipping); then severity;
then a fixed order of kinds. ponytail: a model could rank these once the list outgrows one screen; six lines do not need one.
"""
from __future__ import annotations

import sys

import pandas as pd

from fairshare import db
from harness import agents, facts
from harness import mismatch as _mismatch, watch as _watch  # noqa: F401  (the two agents register their names)
from harness.agents import MONTH_NAMES, money, month_label, num
from harness.precall import WORDS, mismatch_block
from harness.summary import _check_scope, _region_pred, streaks_block, weekly_block
from harness.verifier import FactPool, verify

LIMIT = 6
KIND_ORDER = {"clause": 0, "mismatch": 1, "streak": 2, "capacity": 3, "projected": 4, "bookings": 5}
SEVERITY_ORDER = {"risk": 0, "watch": 1, "ok": 2}
NUMBER_WORDS = ["no", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine", "ten", "eleven", "twelve"]


# ---------------------------------------------------------------- the queries
def clauses_block(region: str, mo: str) -> tuple[pd.DataFrame, str, str]:
    """The clauses breached or close to their line this month. The value, line and distance come out in a column named for
    their unit (value_pct, distance_pts, ...), so the verifier matches "96.1%" and "2.2 points" to the right cells."""
    cols = ", ".join(f"CASE WHEN c.unit = '{u}' THEN c.{k} END AS {k}_{u}" for k in ("value", "threshold", "distance") for u in ("pct", "pts", "usd"))
    sql = f"""
        SELECT c.clause_id, c.agency_id, c.agency_name, c.section, c.clause_type, c.status, c.unit, {cols},
               c.quarters_below, c.window_quarters, c.dollars, c.dollars_label, c.file, c.page
        FROM aa_demo.ops.agreement_checks c JOIN aa_demo.gold.dim_agency a ON a.agency_id = c.agency_id
        WHERE c.as_of = DATE '{mo}' AND c.status IN ('breached', 'watch') {_region_pred(region)}
        ORDER BY CASE c.status WHEN 'breached' THEN 0 ELSE 1 END, c.dollars DESC NULLS LAST, c.agency_name, c.section"""
    df = db.query(sql)
    # an agency near two tier lines at once gets one line: the tier within reach (the upsell) over the tier to protect
    if not df.empty:
        tiers = df["clause_type"].str.endswith("_tiers")
        keep = []
        for _k, g in df[tiers].groupby(["agency_id", "clause_type"]):
            up = g[pd.to_numeric(g["distance_pts"], errors="coerce").fillna(pd.to_numeric(g["distance_pct"], errors="coerce")) < 0]
            keep.append((up if not up.empty else g).index[0])
        df = pd.concat([df[~tiers], df.loc[keep]]).sort_index()
    return df, sql.strip(), "ops.agreement_checks"


def mismatches_block(region: str, mo: str) -> tuple[pd.DataFrame, str, str]:
    f = mismatch_block(None, mo)
    df = f.df
    if region != "All" and not df.empty:
        regions = db.query("SELECT agency_id, region FROM aa_demo.gold.dim_agency")
        df = df[df["agency_id"].astype(int).isin(set(regions[regions["region"] == region]["agency_id"].astype(int)))]
    if not df.empty:  # a deal called healthy while share fell is the revenue risk; a stalled deal while share rose is the upside; each by amount
        df = df.assign(_down=(df["share_chg_pts"] < 0)).sort_values(["_down", "amount_usd"], ascending=[False, False]).drop(columns="_down")
    return df, f.sql, f.source


def capacity_block(mo: str, prior: str) -> tuple[pd.DataFrame, str, str]:
    """AA's seats and fair share on every market against the same month a year earlier, the biggest fair-share move first."""
    sql = f"""
        SELECT CONCAT(m.origin, '-', m.dest) AS market, c.aa_seats AS aa_seats_now, p.aa_seats AS aa_seats_prior_year,
               ROUND((c.aa_seats - p.aa_seats) / NULLIF(p.aa_seats, 0) * 100, 1) AS seats_yoy_pct,
               ROUND(c.aa_seat_share * 100, 1) AS fair_share_now_pct, ROUND(p.aa_seat_share * 100, 1) AS fair_share_prior_pct,
               ROUND((c.aa_seat_share - p.aa_seat_share) * 100, 1) AS fair_chg_pts, c.is_projected
        FROM aa_demo.gold.fact_market_capacity c JOIN aa_demo.gold.dim_market m ON m.market_id = c.market_id
        JOIN aa_demo.gold.fact_market_capacity p ON p.market_id = c.market_id AND p.sales_month = DATE '{prior}'
        WHERE c.sales_month = DATE '{mo}'
        ORDER BY ABS(c.aa_seat_share - p.aa_seat_share) DESC, market"""
    return db.query(sql), sql.strip(), "gold.fact_market_capacity"


# ---------------------------------------------------------------- the lines
def _clean(r: dict) -> dict:
    return {k: (None if (isinstance(v, float) and pd.isna(v)) or v is pd.NA else (v.item() if hasattr(v, "item") else v)) for k, v in r.items()}


def _first(r: dict, *keys):
    return next((r[k] for k in keys if r.get(k) is not None), None)


def _poss(name: str) -> str:
    return f"{name}'" if str(name).endswith("s") else f"{name}'s"


def _word(n: int) -> str:
    return NUMBER_WORDS[n] if 0 <= n < len(NUMBER_WORDS) else str(n)  # ponytail: past twelve a digit shows; the verifier skips bare counts


def _clause_line(r: dict) -> tuple[str, str]:
    """The sentence and the severity for one clause check row."""
    a, t, st = r["agency_name"], str(r["clause_type"]), r["status"]
    d, v = _first(r, "distance_pts", "distance_pct", "distance_usd"), _first(r, "value_pct", "value_pts", "value_usd")
    th = _first(r, "threshold_pct", "threshold_pts", "threshold_usd")
    dollars = money(r["dollars"]) if r.get("dollars") else None
    sev = "risk" if st == "breached" else "watch"
    if t.endswith("_tiers") and d is not None and dollars:
        if d < 0:
            return f"{a} is {num(abs(d))} points from an incentive tier worth {dollars} year to date.", sev
        return f"{a} is {num(d)} points above the line for the incentive tier it holds, worth {dollars} year to date.", sev
    if t == "annual_commitment" and v is not None:
        return f"{a} is at {num(v)}% of its revenue commitment{f', with {dollars} of advanced incentive at risk' if dollars else ''}.", sev
    if t == "share_floor_quarters" and d is not None:
        if st == "breached":
            return f"{a} has been below its share floor for {_word(int(r.get('quarters_below') or 0))} quarters in a row.", sev
        return f"{a} is {num(abs(d))} points {'above' if d >= 0 else 'below'} its share floor.", sev
    if t == "revenue_decline_quarters" and v is not None and th is not None:
        return f"{_poss(a)} latest quarter was {num(v)}% of last year's, against a line of {num(th, 0)}%.", sev
    return f"{_poss(a)} {WORDS.get(t, t.replace('_', ' '))} is {'breached' if st == 'breached' else 'close to its line'}.", sev


def _check(text: str, df: pd.DataFrame, source: str) -> dict:
    """The line as the app renders every sentence: verified against the rows of its own query, each number with its source."""
    pool = FactPool()
    pool.add_frame(df, source)
    badges = verify(text, pool).badges()
    return {"text": text, "status": "verified" if all(b["status"] == "verified" for b in badges) else "flagged",
            "numbers": [n for b in badges for n in b["numbers"]]}


def _agent_name(key: str) -> str:
    return agents.AGENTS[key].name if key in agents.AGENTS else key


def build(region: str, month: str) -> list[dict]:
    region, month = _check_scope(region, month)
    mo, prior = f"{month}-01", f"{int(month[:4]) - 1}-{month[5:7]}-01"
    label = month_label(month)
    ctx = facts.current()
    out: list[dict] = []

    def record(block: str, df: pd.DataFrame, sql: str, table: str) -> str:
        ctx.record("signals", {"block": block, "region": region, "month": month, "table": table}, df, sql=sql, source=table)
        return f"signals#{len(ctx.calls)}"

    def add(kind: str, severity: str, text: str, df: pd.DataFrame, source: str, action: dict, chip: str | None, agency: str | None, dollars: float = 0.0):
        sentence = _check(text, df, source)
        if sentence["status"] != "verified":  # the same rule as everywhere: a number no query returned never reaches the page
            print(f"signals: dropped an unverified line: {text!r}", file=sys.stderr)
            return
        out.append({"kind": kind, "severity": severity, "agency": agency, "sentence": sentence, "action": action, "chip": chip,
                    "_rank": (0 if kind == "clause" and severity == "risk" else 1, -float(dollars or 0), SEVERITY_ORDER[severity], KIND_ORDER[kind], len(out))})

    def block(name, fn):
        try:
            return fn()
        except Exception as e:  # one missing table (a fresh clone before lakehouse/run.py) must not take the home page down
            print(f"signals: {name} skipped: {e}", file=sys.stderr)
            return None

    clauses = block("agreement checks", lambda: clauses_block(region, mo))
    if clauses is not None:
        df, sql, table = clauses
        src = record("agreement checks", df, sql, table)
        for r in (_clean(x) for x in df.to_dict("records")):
            text, sev = _clause_line(r)
            topic = WORDS.get(str(r["clause_type"]), str(r["clause_type"]).replace("_", " "))
            add("clause", sev, text, df, src, {"kind": "delegate", "agent": "watch", "label": f"Open {_agent_name('watch')}"},
                f"What does {_poss(r['agency_name'])} agreement say about its {topic}?", r["agency_name"], r.get("dollars") or 0)

    mism = block("CRM versus the data", lambda: mismatches_block(region, mo))
    if mism is not None and not mism[0].empty:
        df, sql, table = mism
        src = record("CRM versus the data", df, sql, table)
        r = _clean(df.iloc[0].to_dict())
        a, chg = str(r["agency_name"]), float(r["share_chg_pts"])
        deal = str(r["opp_name"]).replace(a + " ", "")
        text = (f"{_poss(a)} {money(r['amount_usd'])} {deal} is marked {r['health']} in the CRM stand-in while AA share "
                f"{'fell' if chg < 0 else 'rose'} {num(abs(chg))} points against last year.")
        more = len(df) - 1
        if more:
            text += f" {_word(more).capitalize()} more open {'deal disagrees' if more == 1 else 'deals disagree'} with the data."
        add("mismatch", "risk", text, df, src, {"kind": "delegate", "agent": "mismatch", "label": f"Open {_agent_name('mismatch')}"},
            f"Why is {a} {'down' if chg < 0 else 'up'} in {label}?", a)

    streaks = block("share streaks", lambda: streaks_block(region, mo))
    if streaks is not None:
        df, sql, table = streaks
        src = record("share streaks", df, sql, table)
        for r in (_clean(x) for x in df.to_dict("records")):
            a, n = str(r["agency_name"]), int(r["months_share_down"])
            q = f"Why is {a} down in {label}?"
            add("streak", "watch", f"{_poss(a)} AA share has fallen {n} months in a row.", df, src, {"kind": "ask", "question": q, "label": "Ask why"}, q, a)

    cap = block("capacity moves", lambda: capacity_block(mo, prior))
    if cap is not None and not cap[0].empty:
        df, sql, table = cap
        src = record("capacity moves", df, sql, table)
        r = _clean(df.iloc[0].to_dict())
        seats, fair, market = float(r["seats_yoy_pct"] or 0), float(r["fair_chg_pts"] or 0), str(r["market"])
        if abs(seats) >= 3 or abs(fair) >= 1:
            last = f"last {MONTH_NAMES[int(month[5:7]) - 1]}"
            head = (f"AA {'cut' if seats < 0 else 'added'} seats {num(abs(seats))}% on {market} against {last}" if abs(seats) >= 0.05
                    else f"AA held its seats on {market} against {last}")
            q = f"How did AA's seats on {market} change against last year?"
            add("capacity", "watch" if fair < 0 else "ok", f"{head}, and fair share there {'fell' if fair < 0 else 'rose'} {num(abs(fair))} points, the largest capacity move this month.",
                df, src, {"kind": "ask", "question": q, "label": "Ask about the market"}, q, None)
        if bool(df["is_projected"].fillna(False).any()):
            add("projected", "watch", f"The seat data for {label} is last year's, because this month's seat file is not in yet, so fair share is an estimate until it is.",
                df, src, {"kind": "definitions", "kpi": "fair_share", "label": "See how fair share is defined"}, None, None)

    weekly = block("corporate weekly bookings", lambda: weekly_block(mo))
    if weekly is not None:
        df, sql, table = weekly
        src = record("corporate weekly bookings", df, sql, table)
        w = df.dropna(subset=["wow_pct"])
        if not w.empty:
            r = _clean(w.iloc[-1].to_dict())
            wow = float(r["wow_pct"])
            if abs(wow) >= 5:
                d = pd.Timestamp(r["week_start"])
                scope = " across all regions" if region != "All" else ""
                q = f"Show corporate bookings by week for {label}."
                add("bookings", "ok" if wow >= 0 else "watch",
                    f"Corporate bookings{scope} the week of {MONTH_NAMES[d.month - 1]} {d.day} were {money(r['booked_revenue'])}, {'up' if wow >= 0 else 'down'} {num(abs(wow))}% week over week.",
                    df, src, {"kind": "ask", "question": q, "label": "See the weeks"}, q, None)

    out.sort(key=lambda s: s["_rank"])
    return [{k: v for k, v in s.items() if k != "_rank"} for s in out[:LIMIT]]


if __name__ == "__main__":  # ponytail: the smallest check that fails if the block breaks on the local build
    facts.reset()
    lines = build("All", agents.latest_month())
    for s in lines:
        print(f"[{s['severity']}] {s['sentence']['text']}  ->  {s['action']['label']}")
    assert lines and all(s["sentence"]["status"] == "verified" for s in lines)
    print("signals ok:", len(lines), "lines,", len(facts.current().calls), "queries")
