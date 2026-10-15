"""Prospect research: for a market, where the headroom is and what the public sources say about the route.

The facts are internal: each agency's AA share against fair share on the market this year (the gap in dollars is the
headroom), the market's totals, the monthly trend, and AA's seats on the route versus last year. The sources are public
pages about the route, quoted with their links (harness/research.py). The writer combines both into a prospecting brief
with a suggested play; a number from a source verifies with the source's URL as its origin, so every number has a home.
This is the piece the data alone cannot do. Nothing is written anywhere: the brief is for reading.
"""
from __future__ import annotations

from fairshare import db
from harness import agents, research
from harness.agents import AgentDef, Fact, money, month_label, num, prior_year, row


def _market(scope: dict) -> tuple[int, str]:
    market = str(scope.get("market") or "").strip().upper()
    rows = db.query("SELECT market_id, CONCAT(origin, '-', dest) AS market FROM aa_demo.gold.dim_market ORDER BY market_id")
    hit = rows[rows["market"] == market]
    if hit.empty:
        raise ValueError(f"No market named {market!r}; the choices are {', '.join(rows['market'])}.")
    return int(hit.iloc[0]["market_id"]), market


def plan(scope: dict) -> list[dict]:
    mid, market = _market(scope)
    month = scope.get("month") or agents.latest_month()
    return [{"market_id": mid, "market": market, "month": month}]


def facts(scope: dict, seed: dict) -> list[Fact]:
    mid, mo, year = seed["market_id"], f"{seed['month']}-01", seed["month"][:4]
    prior = f"{prior_year(seed['month'])}-01"
    hsql = f"""
        SELECT a.agency_name, a.region, a.account_manager, ROUND(SUM(s.aa_revenue), 0) AS aa_revenue, ROUND(SUM(s.market_revenue), 0) AS market_revenue,
               ROUND(SUM(s.aa_revenue) / NULLIF(SUM(s.market_revenue), 0) * 100, 1) AS aa_share_pct,
               ROUND(SUM(s.market_revenue * c.aa_seat_share) / NULLIF(SUM(s.market_revenue), 0) * 100, 1) AS fair_share_pct,
               ROUND((SUM(s.aa_revenue) - SUM(s.market_revenue * c.aa_seat_share)) / NULLIF(SUM(s.market_revenue), 0) * 100, 1) AS share_gap_pts,
               ROUND(SUM(s.aa_revenue) - SUM(s.market_revenue * c.aa_seat_share), 0) AS share_gap_usd
        FROM aa_demo.gold.fact_agency_sales_monthly s JOIN aa_demo.gold.dim_agency a ON a.agency_id = s.agency_id
        JOIN aa_demo.gold.fact_market_capacity c ON c.market_id = s.market_id AND c.sales_month = s.sales_month
        WHERE s.market_id = {mid} AND s.sales_month >= DATE '{year}-01-01' AND s.sales_month <= DATE '{mo}'
        GROUP BY ALL ORDER BY share_gap_usd"""
    tot = f"""
        SELECT ROUND(SUM(s.aa_revenue), 0) AS aa_revenue, ROUND(SUM(s.market_revenue), 0) AS market_revenue,
               ROUND(SUM(s.aa_revenue) / NULLIF(SUM(s.market_revenue), 0) * 100, 1) AS aa_share_pct,
               ROUND(SUM(s.market_revenue * c.aa_seat_share) / NULLIF(SUM(s.market_revenue), 0) * 100, 1) AS fair_share_pct,
               ROUND(SUM(s.aa_revenue) - SUM(s.market_revenue * c.aa_seat_share), 0) AS share_gap_usd,
               COUNT(DISTINCT s.agency_id) AS agencies
        FROM aa_demo.gold.fact_agency_sales_monthly s JOIN aa_demo.gold.fact_market_capacity c ON c.market_id = s.market_id AND c.sales_month = s.sales_month
        WHERE s.market_id = {mid} AND s.sales_month >= DATE '{year}-01-01' AND s.sales_month <= DATE '{mo}'"""
    tsql = f"""
        SELECT s.sales_month, ROUND(SUM(s.aa_revenue), 0) AS aa_revenue, ROUND(SUM(s.aa_revenue) / NULLIF(SUM(s.market_revenue), 0) * 100, 1) AS aa_share_pct,
               ROUND(SUM(s.market_revenue * c.aa_seat_share) / NULLIF(SUM(s.market_revenue), 0) * 100, 1) AS fair_share_pct
        FROM aa_demo.gold.fact_agency_sales_monthly s JOIN aa_demo.gold.fact_market_capacity c ON c.market_id = s.market_id AND c.sales_month = s.sales_month
        WHERE s.market_id = {mid} AND s.sales_month <= DATE '{mo}' AND s.sales_month > DATE '{mo}' - INTERVAL 12 MONTH GROUP BY ALL ORDER BY s.sales_month"""
    csql = f"""
        SELECT c.aa_seats AS aa_seats_now, p.aa_seats AS aa_seats_prior_year, ROUND((c.aa_seats - p.aa_seats) * 100.0 / NULLIF(p.aa_seats, 0), 1) AS seats_change_pct,
               ROUND(c.aa_seat_share * 100, 1) AS aa_seat_share_pct, c.total_seats, c.source
        FROM aa_demo.gold.fact_market_capacity c LEFT JOIN aa_demo.gold.fact_market_capacity p ON p.market_id = c.market_id AND p.sales_month = DATE '{prior}'
        WHERE c.market_id = {mid} AND c.sales_month = DATE '{mo}'"""
    return [Fact("headroom", f"Each agency on {seed['market']} this year: AA share against fair share, and the gap in dollars (the headroom)", db.query(hsql), hsql.strip(), "gold.fact_agency_sales_monthly, gold.fact_market_capacity"),
            Fact("total", f"{seed['market']} this year, all agencies", db.query(tot), tot.strip(), "gold.fact_agency_sales_monthly, gold.fact_market_capacity"),
            Fact("trend", "The market's last twelve months: AA share against fair share", db.query(tsql), tsql.strip(), "gold.fact_agency_sales_monthly"),
            Fact("capacity", "AA seats on the route this month versus the same month last year", db.query(csql), csql.strip(), "gold.fact_market_capacity")]


def fact(fs: list[Fact], name: str) -> Fact:
    return next(f for f in fs if f.name == name)


INSTRUCTIONS = """You write a prospecting brief for an airline sales team about one market from the FACTS and the SOURCES only.
Three short paragraphs: where the headroom is (the agencies selling AA below fair share on this market and the dollars, largest
first, and the market's totals); what the public sources say about the route (quote them word for word, each with its number in
brackets like [1], and never add a fact that is not in a source); a suggested play in two sentences (which agency to start with and
why, and what to offer, in words). Every number comes from the FACTS exactly as shown or is quoted verbatim from a source. Never
compute. Write shares as 38.8%, gaps as "$1.82M below fair share", never with a minus sign. No column names, no codes, no NA, no ISO
dates, no em dashes, no bullet points. End with one line starting "Could not verify:" naming what neither the facts nor the sources
cover, without numbers."""


def template(seed: dict, fs: list[Fact]) -> str:
    head, t = fact(fs, "headroom").df, row(fact(fs, "total").df)
    cap = row(fact(fs, "capacity").df)
    below = head[head["share_gap_usd"] < 0]
    market, month = seed["market"], seed["month"]
    gap = t.get("share_gap_usd") or 0
    p1 = (f"On {market}, agencies sold {money(t.get('aa_revenue'))} of AA travel in {month[:4]} through {month_label(month)}, an AA share of {num(t.get('aa_share_pct'))}% "
          f"against a fair share of {num(t.get('fair_share_pct'))}%, which is {money(abs(gap))} {'below' if gap < 0 else 'above'} fair share. ")
    if below.empty:
        p1 += "No agency sells AA below fair share on this market, so the headroom is in growing the market, not in share."
    else:
        p1 += "The headroom sits with " + ", ".join(f"{r.agency_name} ({money(abs(r.share_gap_usd))} below fair share at {num(r.aa_share_pct)}% against {num(r.fair_share_pct)}%)" for r in below.head(3).itertuples()) + "."
    if cap.get("seats_change_pct") is not None:
        p1 += f" AA's seat share on the route is {num(cap.get('aa_seat_share_pct'))}% this month, with seats {num(cap['seats_change_pct'])}% against last year."
    srcs = research.sources(market)
    if srcs:
        p2 = "What the public sources say about the route: " + " ".join(f"[{i}] \"{s.get('snippet', '').strip()}\"" for i, s in enumerate(srcs[:3], 1))
    else:
        p2 = "No public sources are on file for this route yet; run the research fetch with a search key to add them."
    first = below.iloc[0]["agency_name"] if not below.empty else (head.iloc[0]["agency_name"] if not head.empty else "the largest agency")
    p3 = (f"A suggested play: start with {first}, where the gap to fair share is the largest on this route, and bring the route's own story from the sources to the call. "
          f"Offer a route-specific target with the account manager, and review it against fair share each month.")
    return "\n\n".join([p1, p2, p3, "Could not verify: the agencies' own view of the route or any change in their booking tools; neither the facts nor the sources cover that."])


agents.register(AgentDef(
    key="prospect", name="Prospect research",
    summary="For a market: where the headroom is (the agencies selling AA below fair share there, in dollars), what public sources say about the route, quoted with their links, and a suggested play. The piece the data alone cannot do.",
    reads=["gold.fact_agency_sales_monthly", "gold.fact_market_capacity", "public sources (data/research, or a live search with a key)"],
    writes=["nothing; a brief to read"], approver="the account manager", scope_kind="market", kind="prospect", noun="brief",
    plan=plan, facts=facts, instructions=INSTRUCTIONS, template=template,
    action=lambda seed, fs, text: {"type": "none", "subject": f"Prospect research: {seed['market']}", "body": text, "crm": None},
    severity=lambda seed, fs: "watch" if (row(fact(fs, "total").df).get("share_gap_usd") or 0) < 0 else "ok",
    title=lambda seed, fs: seed["market"],
    subtitle=lambda seed, fs: f"{month_label(seed['month'])}, {money(abs(row(fact(fs, 'total').df).get('share_gap_usd') or 0))} {'below' if (row(fact(fs, 'total').df).get('share_gap_usd') or 0) < 0 else 'above'} fair share this year",
    sources=lambda seed, fs: research.sources(seed["market"]),
    empty_text="No market was named."))
