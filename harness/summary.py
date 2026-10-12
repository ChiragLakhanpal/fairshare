"""The Monday summary: fixed metric calls, a model writes the prose, the verifier quarantines any number
no query returned, a human approves before anything is sent.

build_facts(region, month)  runs the fixed queries (MEASURE() on Databricks, the twin SQL locally) and records them
draft(...)                  asks the model for the prose (or a plain template when no model is configured)
save(...)                   writes the run to aa_demo.ops.summaries with status draft | approved | rejected
"""
from __future__ import annotations

import json
import re
import uuid
from datetime import datetime

import pandas as pd

from fairshare import db
from harness import aio, facts
from harness.verifier import verify


def _mv(sql_mv: str, sql_twin: str) -> pd.DataFrame:
    return db.query(sql_mv if db.is_databricks() else sql_twin)


def build_facts(region: str, month: str) -> dict:
    """All the numbers the summary may use. Everything is a returned column; nothing is left to arithmetic."""
    mo = f"{month[:7]}-01"
    y, m = int(mo[:4]), int(mo[5:7])
    prior = f"{y - 1:04d}-{m:02d}-01"
    ctx = facts.current()
    out = {}

    region_sql_twin = f"""
        WITH cur AS (
          SELECT SUM(s.aa_revenue) AS aa_revenue, SUM(s.market_revenue) AS market_revenue, SUM(s.market_revenue * c.aa_seat_share) AS fair_revenue
          FROM aa_demo.gold.fact_agency_sales_monthly s JOIN aa_demo.gold.dim_agency a ON a.agency_id = s.agency_id
          JOIN aa_demo.gold.fact_market_capacity c ON c.market_id = s.market_id AND c.sales_month = s.sales_month
          WHERE a.region = '{region}' AND s.sales_month = DATE '{mo}'),
        pri AS (
          SELECT SUM(s.aa_revenue) AS aa_revenue_prior_year FROM aa_demo.gold.fact_agency_sales_monthly s JOIN aa_demo.gold.dim_agency a ON a.agency_id = s.agency_id
          WHERE a.region = '{region}' AND s.sales_month = DATE '{prior}')
        SELECT ROUND(cur.aa_revenue, 0) AS aa_revenue, ROUND(pri.aa_revenue_prior_year, 0) AS aa_revenue_prior_year,
               ROUND((cur.aa_revenue - pri.aa_revenue_prior_year) / NULLIF(pri.aa_revenue_prior_year, 0) * 100, 1) AS yoy_pct,
               ROUND(cur.aa_revenue / NULLIF(cur.market_revenue, 0) * 100, 1) AS aa_share_pct,
               ROUND(cur.fair_revenue / NULLIF(cur.market_revenue, 0) * 100, 1) AS fair_share_pct,
               ROUND((cur.aa_revenue - cur.fair_revenue) / NULLIF(cur.market_revenue, 0) * 100, 1) AS share_gap_pts,
               ROUND(cur.aa_revenue - cur.fair_revenue, 0) AS share_gap_usd
        FROM cur, pri"""
    region_sql_mv = f"""
        SELECT ROUND(MEASURE(aa_revenue), 0) AS aa_revenue, ROUND(MEASURE(aa_revenue_prior_year), 0) AS aa_revenue_prior_year,
               ROUND(MEASURE(yoy_revenue_pct) * 100, 1) AS yoy_pct, ROUND(MEASURE(aa_share) * 100, 1) AS aa_share_pct,
               ROUND(MEASURE(fair_share) * 100, 1) AS fair_share_pct, ROUND(MEASURE(share_gap_pts), 1) AS share_gap_pts,
               ROUND(MEASURE(share_gap_usd), 0) AS share_gap_usd
        FROM aa_demo.gold.sales_metrics WHERE region = '{region}' AND sales_month = DATE '{mo}' GROUP BY ALL"""
    out["region"] = _mv(region_sql_mv, region_sql_twin)
    ctx.record("build_summary", {"region": region, "month": month, "block": "region"}, out["region"], sql=(region_sql_mv if db.is_databricks() else region_sql_twin).strip(),
               source="sales_metrics" if db.is_databricks() else "gold.fact_agency_sales_monthly")

    agencies_sql = f"""
        WITH cur AS (
          SELECT a.agency_id, a.agency_name, SUM(s.aa_revenue) AS aa_revenue, SUM(s.market_revenue) AS market_revenue, SUM(s.market_revenue * c.aa_seat_share) AS fair_revenue
          FROM aa_demo.gold.fact_agency_sales_monthly s JOIN aa_demo.gold.dim_agency a ON a.agency_id = s.agency_id
          JOIN aa_demo.gold.fact_market_capacity c ON c.market_id = s.market_id AND c.sales_month = s.sales_month
          WHERE a.region = '{region}' AND s.sales_month = DATE '{mo}' GROUP BY ALL),
        pri AS (
          SELECT agency_id, SUM(aa_revenue) AS aa_revenue_prior FROM aa_demo.gold.fact_agency_sales_monthly WHERE sales_month = DATE '{prior}' GROUP BY ALL)
        SELECT cur.agency_name, ROUND(cur.aa_revenue, 0) AS aa_revenue,
               ROUND((cur.aa_revenue - pri.aa_revenue_prior) / NULLIF(pri.aa_revenue_prior, 0) * 100, 1) AS yoy_pct,
               ROUND(cur.aa_revenue / NULLIF(cur.market_revenue, 0) * 100, 1) AS aa_share_pct,
               ROUND((cur.aa_revenue - cur.fair_revenue) / NULLIF(cur.market_revenue, 0) * 100, 1) AS share_gap_pts,
               ROUND(cur.aa_revenue - cur.fair_revenue, 0) AS share_gap_usd,
               p.pace_pct
        FROM cur LEFT JOIN pri ON pri.agency_id = cur.agency_id
        LEFT JOIN aa_demo.gold.agency_pace p ON p.agency_id = cur.agency_id AND p.sales_month = DATE '{mo}'
        ORDER BY cur.aa_revenue DESC"""
    out["agencies"] = db.query(agencies_sql)
    ctx.record("build_summary", {"region": region, "month": month, "block": "agencies"}, out["agencies"], sql=agencies_sql.strip(), source="gold.agency_pace")

    streak_sql = f"""
        WITH m AS (
          SELECT a.agency_name, s.sales_month, SUM(s.aa_revenue) / NULLIF(SUM(s.market_revenue), 0) AS share
          FROM aa_demo.gold.fact_agency_sales_monthly s JOIN aa_demo.gold.dim_agency a ON a.agency_id = s.agency_id
          WHERE a.region = '{region}' AND s.sales_month <= DATE '{mo}' GROUP BY ALL),
        d AS (
          SELECT agency_name, sales_month, share, LAG(share) OVER (PARTITION BY agency_name ORDER BY sales_month) AS prev_share,
                 ROW_NUMBER() OVER (PARTITION BY agency_name ORDER BY sales_month DESC) AS rn
          FROM m),
        f AS (
          SELECT agency_name, rn, CASE WHEN share < prev_share THEN 1 ELSE 0 END AS down FROM d),
        g AS (
          SELECT agency_name, MIN(rn) - 1 AS streak FROM f WHERE down = 0 GROUP BY agency_name)
        SELECT f.agency_name, COALESCE(g.streak, MAX(f.rn)) AS months_share_down
        FROM f LEFT JOIN g ON g.agency_name = f.agency_name GROUP BY f.agency_name, g.streak
        HAVING COALESCE(g.streak, MAX(f.rn)) >= 3 ORDER BY months_share_down DESC"""
    out["streaks"] = db.query(streak_sql)
    ctx.record("build_summary", {"region": region, "month": month, "block": "share streaks"}, out["streaks"], sql=streak_sql.strip(), source="gold.fact_agency_sales_monthly")

    weekly_sql = f"""
        SELECT week_start, ROUND(SUM(booked_revenue), 0) AS booked_revenue, SUM(tickets) AS tickets,
               ROUND((SUM(booked_revenue) - LAG(SUM(booked_revenue)) OVER (ORDER BY week_start)) / NULLIF(LAG(SUM(booked_revenue)) OVER (ORDER BY week_start), 0) * 100, 1) AS wow_pct
        FROM aa_demo.gold.fact_corporate_bookings_weekly
        WHERE week_start >= DATE '{mo}' - INTERVAL 35 DAY AND week_start + INTERVAL 6 DAY < DATE '{mo}' + INTERVAL 1 MONTH
        GROUP BY week_start ORDER BY week_start"""
    out["weekly"] = db.query(weekly_sql)
    ctx.record("build_summary", {"region": region, "month": month, "block": "corporate weekly bookings"}, out["weekly"], sql=weekly_sql.strip(), source="gold.fact_corporate_bookings_weekly")
    return out


def _clean(df: pd.DataFrame) -> pd.DataFrame:
    """Dates as YYYY-MM-DD strings so neither the model nor the verifier sees 00:00:00."""
    out = df.copy()
    for c in out.columns:
        if pd.api.types.is_datetime64_any_dtype(out[c]):
            out[c] = out[c].dt.strftime("%Y-%m-%d")
        elif out[c].dtype == object and len(out) and hasattr(out[c].iloc[0], "isoformat"):
            out[c] = out[c].map(lambda d: d.isoformat() if hasattr(d, "isoformat") else d)
    return out


def facts_text(f: dict, region: str, month: str) -> str:
    def t(df):
        return _clean(df).to_string(index=False) if not df.empty else "(none)"
    return (f"FACTS for the {region} region, month {month[:7]} (all numbers from queries; quote them exactly as shown, same rounding)\n\n"
            f"Region totals:\n{t(f['region'])}\n\nAgencies (pace_pct: 100 = on pace to the annual goal):\n{t(f['agencies'])}\n\n"
            f"Agencies whose AA share fell for 3+ consecutive months ending this month:\n{t(f['streaks'])}\n\n"
            f"Corporate account bookings by week (all regions; wow_pct = week over week change in booked revenue):\n{t(f['weekly'])}\n")


DRAFT_INSTRUCTIONS = """You write the Monday performance summary for the Sales VP from the FACTS block only.
Rules: every number you write must appear in the FACTS exactly as shown (same rounding; you may add $ and % signs and
abbreviate thousands as K and millions as M, e.g. 1653532 as $1.65M, 416407 as $416K). Never compute, estimate, or infer
a number. Do not explain causes that the facts do not state. Write for a VP: no column names, no table jargon, no dates
in ISO form (say "the week of September 21"). Six to nine sentences in this order: headline (revenue, year over year,
share vs fair share), pace (who is behind, or that nobody is), biggest share gap, watch list (share streaks, or none),
corporate bookings (last week vs prior week). Plain prose, plain punctuation (no em dashes), no bullet points, no headings, no preamble,
no "Source" line (the app attaches the queries). End with one line starting "Could not verify:" naming what the facts
do not cover, without numbers."""


def template_draft(f: dict, region: str, month: str) -> str:
    """No model configured: a plain template from the same facts, so the page still works offline."""
    r = f["region"].iloc[0]
    def money(x):
        sign = "-" if x < 0 else ""
        x = abs(x)
        return f"{sign}${x / 1e6:.1f}M" if x >= 1e6 else f"{sign}${x / 1e3:.0f}K"
    lines = [f"{region} region, {month[:7]}: AA revenue {money(r['aa_revenue'])}, {r['yoy_pct']:+.1f}% year over year. "
             f"AA share {r['aa_share_pct']}% against a fair share of {r['fair_share_pct']}%, a gap of {r['share_gap_pts']} points worth {money(r['share_gap_usd'])}."]
    behind = f["agencies"][f["agencies"]["pace_pct"] < 100]
    if not behind.empty:
        lines.append("Behind pace: " + "; ".join(f"{a.agency_name} at {a.pace_pct}% of pace" for a in behind.itertuples()) + ".")
    worst = f["agencies"].sort_values("share_gap_pts").iloc[0]
    lines.append(f"Biggest share gap: {worst['agency_name']}, {worst['share_gap_pts']} points vs fair share ({money(worst['share_gap_usd'])}).")
    if not f["streaks"].empty:
        s = f["streaks"].iloc[0]
        lines.append(f"Watch: {s['agency_name']} share down {int(s['months_share_down'])} months running.")
    w = _clean(f["weekly"]).dropna(subset=["wow_pct"])
    if not w.empty:
        last = w.iloc[-1]
        lines.append(f"Corporate bookings week of {last['week_start']}: {money(last['booked_revenue'])}, {last['wow_pct']:+.1f}% week over week.")
    return " ".join(lines)


_writer = None


def make_writer(instructions: str | None = None):
    """The writer has no tools: it sees the FACTS block and nothing else, so every number it can write is already in the pool."""
    global _writer
    if instructions is None and _writer is not None:
        return _writer
    from agent_framework import Agent
    from harness.agent import make_client
    client = make_client()
    if client is None:
        return None
    w = Agent(client, instructions=instructions or DRAFT_INSTRUCTIONS, name="fairshare-monday-writer")
    if instructions is None:
        _writer = w
    return w


def prettify(text: str) -> str:
    """Display formatting only, applied before verification so the badges match what is shown: raw floats become money
    ($1653532.0 -> $1.65M, $416407.0 -> $416K), trailing .0 goes, 'down -0.4%' becomes 'down 0.4%', em dashes become commas."""
    def money(m):
        v = float(m.group(1).replace(",", ""))
        if v >= 1e6:
            return f"${v / 1e6:.2f}M"
        if v >= 1e4:
            return f"${v / 1e3:.0f}K"
        return m.group(0)
    text = re.sub(r"\$(\d[\d,]*(?:\.\d+)?)(?![\d.,]*[KMBkmb])", money, text)
    text = re.sub(r"(?<=\d)\.0\b(?!\d)", "", text)
    text = re.sub(r"\b(up|down|rose|fell|increased|decreased)\s+-", r"\1 ", text, flags=re.I)
    text = text.replace(" \u2014 ", ", ").replace("\u2014", ", ").replace(" \u2013 ", ", ")
    return text


def draft(f: dict, region: str, month: str, writer=None) -> str:
    text = facts_text(f, region, month)
    if writer is None:
        return template_draft(f, region, month)
    resp = aio.run(writer.run(text))
    return prettify(resp.text.strip())


def run(region: str, month: str, writer=None) -> dict:
    """Facts, draft, verification. Returns everything the Monday page and ops.summaries need."""
    from harness import tracing
    if tracing.setup():
        import mlflow
        with mlflow.start_span(name="fairshare.monday_summary") as sp:
            sp.set_inputs({"region": region, "month": month, "writer": "template" if writer is None else "agent"})
            res = _run(region, month, writer)
            sp.set_outputs({"sentences": len(res["badges"]), "flagged": len(res["flagged"])})
            return res
    return _run(region, month, writer)


def _run(region: str, month: str, writer=None) -> dict:
    facts.reset()
    f = build_facts(region, month)
    d = draft(f, region, month, writer)
    v = verify(d, facts.current().pool)
    return {"run_id": uuid.uuid4().hex[:12], "region": region, "month": month[:7], "created_at": datetime.now().isoformat(timespec="seconds"),
            "draft": d, "verified_text": v.verified_text, "flagged": v.flagged, "badges": v.badges(), "facts": f,
            "calls": facts.current().calls, "model": "template" if writer is None else "agent"}


def _q(s: str) -> str:
    return "'" + str(s).replace("'", "''") + "'"


def save(result: dict, status: str = "draft") -> None:
    t = db.SUMMARIES
    db.state_execute([
        f"""CREATE TABLE IF NOT EXISTS {t} (
            run_id STRING, region STRING, month STRING, created_at STRING, status STRING, model STRING,
            draft STRING, verified_text STRING, flagged_json STRING, badges_json STRING)""",
        f"DELETE FROM {t} WHERE run_id = {_q(result['run_id'])}",
        f"INSERT INTO {t} VALUES (" + ", ".join(_q(x) for x in [
            result["run_id"], result["region"], result["month"], result["created_at"], status, result["model"],
            result["draft"], result["verified_text"], json.dumps(result["flagged"]), json.dumps(result["badges"], default=str)]) + ")"])


def history(limit: int = 20) -> pd.DataFrame:
    try:
        return db.state_query(f"SELECT run_id, region, month, created_at, status, model, flagged_json FROM {db.SUMMARIES} ORDER BY created_at DESC LIMIT {limit}")
    except Exception:
        return pd.DataFrame()


if __name__ == "__main__":
    res = run("Central", "2026-09")
    print(res["draft"])
    print("flagged:", res["flagged"])
    assert res["badges"], "no sentences"
    assert not res["flagged"], "the template draft must verify clean; the matcher or the template drifted"
    print("summary ok:", len(res["badges"]), "sentences verified")
