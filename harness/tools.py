"""The four tools. Each one records what it returned (SQL, rows, source) in the run context so the
verifier has a fact pool and the app has a "how I got this" drawer.

ask_metrics      Genie Agent over the metric view (Databricks); the governed path for numbers
run_sql          read-only SQL against aa_demo.gold / aa_demo.ops; the fallback when Genie is unavailable
explain_change   the deterministic year-over-year decomposition (volume, mix, share, fair-share diagnostic)
search_contracts the four agency agreements, by file and page
"""
from __future__ import annotations

import functools
import os
import re
import time
from pathlib import Path
from typing import Annotated

import pandas as pd
from agent_framework import tool

from fairshare import db
from harness import facts, tracing


PHASE_TEXT = {
    "genie": "I am asking Genie for the numbers.",
    "sql": "I am running a query on your data.",
    "explain": "I am working out what moved.",
    "agreement": "I am reading the agreement.",
    "warehouse": "I am waking up the warehouse. The first question after a quiet hour can take about a minute.",
    "start": "I am reading your question and choosing the query.",
    "model": "I am reading the results.",
    "verify": "I am checking every number against the query.",
}


def _instrumented(name, phase):
    """Around every tool body: a cancel checkpoint, a progress event before and after (the browser shows them as steps),
    and an MLflow span when tracing is on. functools.wraps keeps the Annotated signature that @tool reads."""
    def deco(fn):
        body = fn
        if tracing.setup():
            import mlflow
            body = mlflow.trace(name=name, span_type="TOOL")(fn)

        @functools.wraps(fn)
        def wrapper(*args, **kwargs):
            ctx = facts.current()
            ctx.check_cancel()
            if phase != "genie":  # ask_metrics emits its own genie step once the conversation exists, with the question and the link
                ctx.emit("status", phase=phase, tool=name, args=kwargs, text=PHASE_TEXT[phase])
            t0 = time.monotonic()
            try:
                return body(*args, **kwargs)
            finally:
                ctx.emit("status", phase="model", tool=name, text=PHASE_TEXT["model"], ms=int((time.monotonic() - t0) * 1000))
        return wrapper
    return deco

ROOT = Path(__file__).resolve().parents[1]
CONTRACTS = ROOT / "data" / "contracts"
FORBIDDEN = re.compile(r"\b(drop|delete|update|insert|merge|alter|create|truncate|grant|revoke|replace)\b", re.I)


def _table(df: pd.DataFrame, limit: int = 25) -> str:
    if df.empty:
        return "(no rows)"
    shown = df.head(limit).copy()
    for c in shown.columns:
        if pd.api.types.is_float_dtype(shown[c]):
            shown[c] = shown[c].map(lambda x: f"{x:,.4f}".rstrip("0").rstrip(".") if pd.notna(x) else "")
    text = shown.to_string(index=False)
    if len(df) > limit:
        text += f"\n... {len(df) - limit} more rows"
    return text


# ---------------------------------------------------------------- Genie
def _genie_space() -> str | None:
    return os.environ.get("GENIE_SPACE_ID") if db.is_databricks() else None


def _genie_url(space: str, conversation_id: str) -> str:
    from fairshare.dbx import host
    return f"{host()}/genie/rooms/{space}/chats/{conversation_id}"


def _genie_ask(question: str, conversation_id: str | None = None) -> tuple[str, pd.DataFrame | None, str | None, str, str]:
    """Chat-mode Genie through the SDK, called as the user (PAT), never as a service principal. Continues the thread's
    conversation when one is given (a gone or foreign conversation falls back to a fresh one). Returns
    (text, rows, sql, conversation_id, message_id)."""
    from datetime import timedelta
    from fairshare.dbx import warm_warehouse, workspace_client
    ctx = facts.current()
    w = workspace_client()
    space = _genie_space()
    ctx.emit("status", phase="warehouse", text=PHASE_TEXT["warehouse"])
    warm_warehouse()  # Free Edition stops the warehouse after 10 idle minutes; Genie then waits in PENDING_WAREHOUSE far longer than a direct start (8 s)
    timeout = timedelta(seconds=int(os.environ.get("GENIE_TIMEOUT_S", "150")))

    def start():
        delay = 2.0
        for attempt in range(4):
            try:
                return w.genie.start_conversation(space_id=space, content=question)
            except Exception as e:  # 429 RATE_LIMIT_EXCEEDED or a transient error: back off and retry
                if attempt == 3 or "429" not in str(e) and "RATE_LIMIT" not in str(e):
                    raise
                time.sleep(delay)
                delay *= 2

    wait = None
    if conversation_id:
        try:
            wait = w.genie.create_message(space_id=space, conversation_id=conversation_id, content=question)
        except Exception as e:
            if not any(code in str(e) for code in ("400", "403", "404", "NOT_FOUND", "PERMISSION", "INVALID")):
                raise
    if wait is None:
        wait = start()
    cid, mid = wait.conversation_id, wait.message_id
    ctx.emit("status", phase="genie", tool="ask_metrics", args={"question": question}, text=PHASE_TEXT["genie"],
             genie={"conversation_id": cid, "message_id": mid, "url": _genie_url(space, cid)})
    ctx.check_cancel()
    msg = wait.result(timeout=timeout, callback=lambda _m: ctx.check_cancel())
    text, df, sql = "", None, None
    for att in msg.attachments or []:
        if att.text and att.text.content:
            text += att.text.content + "\n"
        if att.query:
            sql = att.query.query
            res = w.genie.get_message_attachment_query_result(space_id=space, conversation_id=cid, message_id=mid, attachment_id=att.attachment_id)
            sr = res.statement_response
            cols = [c.name for c in sr.manifest.schema.columns] if sr and sr.manifest and sr.manifest.schema else []
            rows = list(sr.result.data_array) if sr and sr.result and sr.result.data_array else []
            # results beyond the first chunk are fetched by chunk index
            if sr and sr.manifest and sr.manifest.total_chunk_count and sr.manifest.total_chunk_count > 1:
                for i in range(1, sr.manifest.total_chunk_count):
                    chunk = w.statement_execution.get_statement_result_chunk_n(sr.statement_id, i)
                    rows.extend(chunk.data_array or [])
            df = pd.DataFrame(rows, columns=cols)
            for c in df.columns:  # Genie returns strings; make numbers numeric so they enter the fact pool
                try:
                    df[c] = pd.to_numeric(df[c])
                except (ValueError, TypeError):
                    pass
    return text.strip(), df, sql, cid, mid


@tool(name="ask_metrics",
      description="Ask the governed sales metrics agent (Genie over the sales_metrics metric view) a question about AA revenue, "
                  "share, fair share, share gap, year over year, passengers, by agency, market, region, month, quarter or year. "
                  "Returns the SQL it ran and the result table. Use this first for any number.")
@_instrumented("ask_metrics", "genie")
def ask_metrics(question: Annotated[str, "The business question, in plain English, with the agency, market and period spelled out."]) -> str:
    ctx = facts.current()
    if not _genie_space():
        ctx.record("ask_metrics", {"question": question}, None, note="Genie not configured in this environment; use run_sql")
        return ("Genie is not available in this environment. Write the query yourself with run_sql against the documented tables "
                "(use MEASURE() on aa_demo.gold.sales_metrics when on Databricks).")
    t0 = time.monotonic()
    try:
        text, df, sql, cid, mid = _genie_ask(question, conversation_id=ctx.genie_conversation_id)
    except facts.Cancelled:
        raise
    except Exception as e:
        ctx.record("ask_metrics", {"question": question}, None, note=f"Genie failed: {e}")
        return f"Genie failed ({type(e).__name__}). Fall back to run_sql with your own query."
    ctx.genie_conversation_id = cid
    ctx.record("ask_metrics", {"question": question}, df, sql=sql, note=text, source="Genie: sales_metrics",
               genie={"conversation_id": cid, "message_id": mid, "url": _genie_url(_genie_space(), cid)}, ms=int((time.monotonic() - t0) * 1000))
    body = f"Genie said: {text}\n" if text else ""
    if sql:
        body += f"SQL:\n{sql}\n"
    if df is not None:
        body += f"Result ({len(df)} rows):\n{_table(df)}"
    return body or "Genie returned no answer."


# ---------------------------------------------------------------- direct SQL
SCHEMA_NOTE = """Tables (catalog aa_demo):
gold.fact_agency_sales_monthly(agency_id, market_id, sales_month DATE first of month, aa_revenue, aa_pax, market_revenue, market_pax)
gold.dim_agency(agency_id, agency_name, agency_type, region, account_manager)
gold.dim_market(market_id, origin, dest, region, aa_hub_origin)
gold.fact_market_capacity(market_id, sales_month, aa_seats, total_seats, aa_seat_share, is_projected, source)  -- aa_seat_share is fair share
gold.agency_goals(agency_id, goal_year, revenue_goal_usd, share_goal)
gold.agency_pace(agency_id, goal_year, sales_month, aa_revenue, ytd_revenue, revenue_goal_usd, ytd_goal, pace_pct, attainment_pct, months_reported)  -- ytd_goal = goal * months_reported / 12
gold.fact_corporate_bookings(booking_id, ticket_number, corp_id, booking_date, travel_date, origin, dest, channel, fare_usd, ticket_count, cabin, agency_id)
gold.fact_corporate_bookings_weekly(week_start, corp_id, booked_revenue, tickets, prior_week_revenue, wow_pct)
gold.dim_corporate(corp_id, corp_name, industry, hq_city, contract_start, contract_end, annual_commitment_usd)
ops.decomposition(agency_id, sales_month, revenue_now, revenue_prior, delta_revenue, delta_pct, market_now, market_prior, market_delta_pct, aa_share_now, aa_share_prior, fair_share_now, fair_share_prior, volume_effect, mix_effect, share_effect, fair_share_effect, residual)
Definitions: AA share = SUM(aa_revenue)/SUM(market_revenue). Fair share = SUM(market_revenue*aa_seat_share)/SUM(market_revenue). Share gap pts = (share - fair share)*100.
On Databricks prefer the metric view: SELECT agency, MEASURE(aa_share) FROM aa_demo.gold.sales_metrics WHERE year = 2026 GROUP BY ALL.
Data covers Jan 2025 to Sep 2026. Return percentages and deltas as columns; never leave arithmetic to the reader."""


@tool(name="run_sql",
      description="Run one read-only SQL SELECT against the aa_demo catalog (gold and ops schemas) and return up to 200 rows. "
                  "Use when ask_metrics is unavailable or for a join it cannot do. Compute every percentage, difference "
                  "and ratio inside the SQL so the answer only quotes returned columns.")
@_instrumented("run_sql", "sql")
def run_sql(sql: Annotated[str, "A single SELECT or WITH statement. No DDL or DML."]) -> str:
    ctx = facts.current()
    s = "\n".join(l for l in (sql or "").strip().splitlines() if not l.strip().startswith("--")).strip().rstrip(";").strip()
    if not re.match(r"^(select|with)\b", s, re.I) or FORBIDDEN.search(s):
        ctx.record("run_sql", {"sql": sql}, None, note="rejected: not a read-only SELECT")
        return "Rejected: only a single read-only SELECT/WITH statement is allowed."
    if not re.search(r"\blimit\s+\d+\s*$", s, re.I):
        s += "\nLIMIT 200"
    try:
        df = db.query(s)
        ctx.record("run_sql", {"sql": sql}, df, sql=s, source="SQL: " + ", ".join(sorted(set(re.findall(r"aa_demo\.\w+\.\w+", s, re.I)))))
        return f"Result ({len(df)} rows):\n{_table(df)}"
    except Exception as e:
        import traceback
        traceback.print_exc()
        ctx.record("run_sql", {"sql": sql}, None, note=f"error: {e}")
        return f"SQL error: {e}"


# ---------------------------------------------------------------- decomposition
def _month(month: str) -> str:
    m = re.match(r"^(\d{4})-(\d{1,2})", month.strip())
    if not m:
        raise ValueError("month must look like 2026-08")
    return f"{int(m.group(1)):04d}-{int(m.group(2)):02d}-01"


@tool(name="explain_change",
      description="Explain WHY an agency's AA revenue changed versus the same month last year: a deterministic decomposition into "
                  "volume (the agency sold more or less travel overall), mix (it shifted which markets it sells), and share "
                  "(AA won or lost share within markets), plus a fair-share diagnostic (how much AA's own capacity change explains). "
                  "The three parts sum to the total change exactly. Also lists the markets that moved most.")
@_instrumented("explain_change", "explain")
def explain_change(agency: Annotated[str, "Agency name, or a distinctive part of it, e.g. 'Harbor'"],
                   month: Annotated[str, "The month to explain, e.g. '2026-08' (compared with 2025-08)"]) -> str:
    ctx = facts.current()
    try:
        mo = _month(month)
    except ValueError as e:
        return str(e)
    like = agency.replace("'", "''").lower()
    head = db.query(f"""
        SELECT a.agency_name, d.* FROM aa_demo.ops.decomposition d JOIN aa_demo.gold.dim_agency a ON a.agency_id = d.agency_id
        WHERE LOWER(a.agency_name) LIKE '%{like}%' AND d.sales_month = DATE '{mo}'""")
    if head.empty:
        ctx.record("explain_change", {"agency": agency, "month": month}, None, note="no decomposition row")
        return (f"No decomposition for '{agency}' in {mo[:7]}: either the agency name did not match, or there is no same month "
                f"last year to compare with (data covers Jan 2025 to Sep 2026; comparisons start Jan 2026).")
    r = head.iloc[0]
    markets = db.query(f"""
        SELECT CONCAT(m.origin, '-', m.dest) AS market, ROUND(k.share_effect, 0) AS share_effect, ROUND(k.mix_effect, 0) AS mix_effect,
               ROUND(k.aa_share_now * 100, 1) AS aa_share_now_pct, ROUND(k.aa_share_prior * 100, 1) AS aa_share_prior_pct,
               ROUND(k.market_revenue_now, 0) AS market_revenue_now
        FROM aa_demo.ops.decomposition_markets k JOIN aa_demo.gold.dim_market m ON m.market_id = k.market_id
        WHERE k.agency_id = {int(r['agency_id'])} AND k.sales_month = DATE '{mo}' ORDER BY k.share_effect""")
    summary = pd.DataFrame([{
        "revenue_now": r["revenue_now"], "revenue_prior": r["revenue_prior"], "delta_revenue": r["delta_revenue"], "delta_pct": r["delta_pct"],
        "market_delta_pct": r["market_delta_pct"], "aa_share_now_pct": round(r["aa_share_now"] * 100, 1), "aa_share_prior_pct": round(r["aa_share_prior"] * 100, 1),
        "fair_share_now_pct": round(r["fair_share_now"] * 100, 1), "fair_share_prior_pct": round(r["fair_share_prior"] * 100, 1),
        "volume_effect": r["volume_effect"], "mix_effect": r["mix_effect"], "share_effect": r["share_effect"], "fair_share_effect": r["fair_share_effect"],
        "parts_sum": round(r["volume_effect"] + r["mix_effect"] + r["share_effect"], 2),
        "share_gap_now_pts": round((r["aa_share_now"] - r["fair_share_now"]) * 100, 1),
    }])
    ctx.record("explain_change", {"agency": agency, "month": month}, summary, sql="aa_demo.ops.decomposition (lakehouse/06_decomposition.sql)",
               source="ops.decomposition")
    ctx.record("explain_change", {"agency": agency, "month": month, "detail": "markets"}, markets, sql="aa_demo.ops.decomposition_markets",
               source="ops.decomposition_markets")
    prior = mo[:4]
    return (f"{r['agency_name']}, {mo[:7]} vs {int(prior) - 1}-{mo[5:7]}\n"
            f"AA revenue {r['revenue_now']:,.0f} vs {r['revenue_prior']:,.0f}: delta {r['delta_revenue']:,.0f} ({r['delta_pct']:+.1f}%).\n"
            f"Agency total market revenue changed {r['market_delta_pct']:+.1f}%.\n"
            f"AA share {r['aa_share_now'] * 100:.1f}% vs {r['aa_share_prior'] * 100:.1f}%; fair share {r['fair_share_now'] * 100:.1f}% vs {r['fair_share_prior'] * 100:.1f}%.\n"
            f"Effects (sum to the delta): volume {r['volume_effect']:,.0f}; mix {r['mix_effect']:,.0f}; share {r['share_effect']:,.0f}; "
            f"parts_sum {summary['parts_sum'].iloc[0]:,.0f}. Fair-share diagnostic {r['fair_share_effect']:,.0f} (not part of the sum).\n"
            f"Markets by share effect:\n{_table(markets, 12)}\n"
            f"Quote only these numbers. If asked about causes not in the data (contract changes, staff turnover), say they are not in the data.")


# ---------------------------------------------------------------- contracts
def _pages(path: Path):
    text = path.read_text()
    parts = re.split(r"<!-- page (\d+) -->", text)
    pages = []
    # parts: [preamble, '1', page1, '2', page2, ...]
    for i in range(1, len(parts), 2):
        pages.append((int(parts[i]), parts[i + 1]))
    return pages


def _paragraphs(page_text: str):
    return [p.strip() for p in re.split(r"\n\s*\n", page_text) if p.strip() and not p.strip().startswith("#")]


def _files(agency: str) -> list[Path]:
    key = agency.lower().split()[0] if agency.strip() else ""
    return [p for p in sorted(CONTRACTS.glob("*.md")) if key and key in p.stem.lower()] or sorted(CONTRACTS.glob("*.md"))


def _search(agency: str, topic: str) -> list[tuple[int, str, int, str]]:
    """Keyword overlap over the agreement paragraphs: (score, file, page, paragraph), best first."""
    words = {w for w in re.findall(r"[a-z0-9%]+", topic.lower()) if len(w) > 2}
    hits = []
    for f in _files(agency):
        for page, text in _pages(f):
            for para in _paragraphs(text):
                pw = set(re.findall(r"[a-z0-9%]+", para.lower()))
                score = len(words & pw) + (2 if re.search(r"\d+%", para) and any(w.endswith("%") for w in words) else 0)
                if score:
                    hits.append((score, f.name, page, para))
    hits.sort(key=lambda h: (-h[0], h[1], h[2]))
    return hits


@tool(name="search_contracts",
      description="Find what an agency's agreement says about a topic (share maintenance, incentive tiers, goals, termination, "
                  "data sharing, volume commitment, reporting). Returns the clause text with file name and page. Quote it; do not paraphrase numbers.")
@_instrumented("search_contracts", "agreement")
def search_contracts(agency: Annotated[str, "Agency name or part of it, e.g. 'Summit'"],
                     topic: Annotated[str, "What to look for, e.g. 'share falls below 45% for two quarters'"]) -> str:
    ctx = facts.current()
    files = _files(agency)
    hits = _search(agency, topic)
    if not hits:
        ctx.record("search_contracts", {"agency": agency, "topic": topic}, None, note="no clause matched")
        return f"No clause about '{topic}' in {', '.join(f.name for f in files)}. Say the agreement does not cover it."
    top = hits[:3]
    nums = pd.DataFrame([{"file": h[1], "page": h[2], "clause_numbers": " ".join(re.findall(r"\$?\d[\d,]*\.?\d*%?", h[3]))} for h in top])
    pool_df = pd.DataFrame({"clause_value": [float(x.replace("$", "").replace(",", "").rstrip("%")) for h in top for x in re.findall(r"\$?\d[\d,]*\.?\d*%?", h[3]) if re.search(r"\d", x)]})
    pool_df_pct = pd.DataFrame({"clause_pct": [float(x.replace(",", "").rstrip("%")) for h in top for x in re.findall(r"\d[\d,]*\.?\d*%", h[3])]})
    for h in top:
        ctx.record("search_contracts", {"agency": agency, "topic": topic}, None, note=f"{h[1]} page {h[2]}", source=f"{h[1]} p.{h[2]}")
    ctx.pool.add_frame(pool_df, "search_contracts")
    ctx.pool.add_frame(pool_df_pct, "search_contracts")
    return "\n\n".join(f"[{h[1]}, page {h[2]}]\n{h[3]}" for h in top)
