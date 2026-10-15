"""Agreement watch: every measurable promise in the agreements, checked against the data for the month.

One item per clause the checker (lakehouse/07_agreement_watch.sql) marked breached or close to its line, including the
tier an agency is one step from. The facts are the check row, the clause as extracted, the agency's recent months, the
tier table where one applies, the closed quarters where a quarter rule applies, and the contacts. The writer drafts the
alert and a notice (a breach) or an upsell note (a tier within reach); approving opens the email and records the note in
the CRM stand-in.
"""
from __future__ import annotations

import re

import pandas as pd

from fairshare import db
from harness import agents
from harness.agents import AgentDef, Fact, money, month_label, num, row
from harness.precall import STATUS_WORDS, WORDS
from harness.summary import REGIONS


def _scope(scope: dict) -> tuple[str, str]:
    region = scope.get("region") or "All"
    month = scope.get("month") or agents.latest_month()
    if region not in REGIONS:
        raise ValueError(f"region must be one of {', '.join(REGIONS)}")
    return region, month


def plan(scope: dict) -> list[dict]:
    region, month = _scope(scope)
    pred = "" if region == "All" else f"AND a.region = '{region}'"
    sql = f"""
        SELECT c.clause_id, c.agency_id, c.agency_name, c.section, c.clause_type, c.status, c.dollars, c.distance
        FROM aa_demo.ops.agreement_checks c JOIN aa_demo.gold.dim_agency a ON a.agency_id = c.agency_id
        WHERE c.as_of = DATE '{month}-01' AND c.status IN ('breached', 'watch') {pred}
        ORDER BY CASE c.status WHEN 'breached' THEN 0 ELSE 1 END, c.dollars DESC NULLS LAST, c.agency_name, c.section"""
    df = db.query(sql)
    # an agency near two tier lines at once gets one alert: the tier within reach (the upsell) over the tier to protect
    tiers = df["clause_type"].str.endswith("_tiers") if not df.empty else df
    if not df.empty and tiers.any():
        keep = []
        for (_aid, _t), g in df[tiers].groupby(["agency_id", "clause_type"]):
            up = g[g["distance"] < 0]
            keep.append((up if not up.empty else g).index[0])
        df = pd.concat([df[~tiers], df.loc[keep]]).sort_index()
    return [{"clause_id": r.clause_id, "agency_id": int(r.agency_id), "agency_name": r.agency_name, "section": str(r.section),
             "clause_type": r.clause_type, "status": r.status, "month": month} for r in df.itertuples()]


def facts(scope: dict, seed: dict) -> list[Fact]:
    aid, mo, cid = seed["agency_id"], f"{seed['month']}-01", seed["clause_id"].replace("'", "''")
    csql = f"""SELECT clause_id, agency_name, section, TRY_CAST(section AS DOUBLE) AS section_number, clause_type, status, value, threshold, distance, unit,
                      quarters_below, window_quarters, dollars, dollars_label, consequence, file, page
               FROM aa_demo.ops.agreement_checks WHERE clause_id = '{cid}' AND as_of = DATE '{mo}'"""
    xsql = f"SELECT section, clause_type, metric, operator, threshold, threshold_2, window_quarters, consequence, quote, file, page FROM aa_demo.gold.contract_clauses WHERE clause_id = '{cid}'"
    tsql = f"""SELECT s.sales_month, ROUND(SUM(s.aa_revenue), 0) AS aa_revenue, ROUND(SUM(s.aa_revenue) / NULLIF(SUM(s.market_revenue), 0) * 100, 1) AS aa_share_pct,
                      ROUND(SUM(s.market_revenue * c.aa_seat_share) / NULLIF(SUM(s.market_revenue), 0) * 100, 1) AS fair_share_pct
               FROM aa_demo.gold.fact_agency_sales_monthly s JOIN aa_demo.gold.fact_market_capacity c ON c.market_id = s.market_id AND c.sales_month = s.sales_month
               WHERE s.agency_id = {aid} AND s.sales_month <= DATE '{mo}' AND s.sales_month > DATE '{mo}' - INTERVAL 6 MONTH GROUP BY ALL ORDER BY s.sales_month"""
    out = [Fact("check", "The check for this clause and month", db.query(csql), csql.strip(), "ops.agreement_checks"),
           Fact("clause", "The clause as extracted from the agreement, with its page", db.query(xsql), xsql.strip(), "gold.contract_clauses"),
           Fact("trend", "The agency's last six months", db.query(tsql), tsql.strip(), "gold.fact_agency_sales_monthly")]
    if seed["clause_type"].endswith("_tiers"):
        tiers_sql = f"""SELECT threshold, value, distance, unit, dollars, status FROM aa_demo.ops.agreement_checks
                        WHERE agency_id = {aid} AND as_of = DATE '{mo}' AND clause_type = '{seed['clause_type']}' ORDER BY threshold NULLS FIRST"""
        out.append(Fact("tiers", "Every tier line for this agency, with the incentive each pays at this year's revenue", db.query(tiers_sql), tiers_sql.strip(), "ops.agreement_checks"))
    else:
        out.append(Fact("tiers", "Tier lines (none for this clause)", pd.DataFrame(), "", ""))
    if seed["clause_type"] in ("share_floor_quarters", "revenue_decline_quarters"):
        qsql = f"""
            WITH q AS (
              SELECT CAST(EXTRACT(YEAR FROM sales_month) AS INT) AS yr, CAST(EXTRACT(QUARTER FROM sales_month) AS INT) AS qtr,
                     ROUND(SUM(aa_revenue) / NULLIF(SUM(market_revenue), 0) * 100, 1) AS aa_share_pct, ROUND(SUM(aa_revenue), 0) AS aa_revenue,
                     COUNT(DISTINCT sales_month) AS months_in, MAX(sales_month) AS last_month
              FROM aa_demo.gold.fact_agency_sales_monthly WHERE agency_id = {aid} GROUP BY ALL)
            SELECT CONCAT('Q', CAST(c.qtr AS STRING), ' ', CAST(c.yr AS STRING)) AS quarter, c.aa_share_pct, c.aa_revenue,
                   ROUND(c.aa_revenue / NULLIF(p.aa_revenue, 0) * 100, 1) AS revenue_vs_prior_year_pct
            FROM q c LEFT JOIN q p ON p.yr = c.yr - 1 AND p.qtr = c.qtr
            WHERE c.months_in = 3 AND c.last_month <= DATE '{mo}' ORDER BY c.yr DESC, c.qtr DESC LIMIT 4"""
        out.append(Fact("quarters", "The last four closed quarters", db.query(qsql), qsql.strip(), "gold.fact_agency_sales_monthly"))
    csql2 = f"SELECT contact_name, title, email FROM aa_demo.gold.crm_contacts WHERE agency_id = {aid} ORDER BY contact_id"
    out.append(Fact("contacts", "Contacts at the agency (the CRM stand-in)", db.query(csql2), csql2.strip(), "gold.crm_contacts (the CRM stand-in)"))
    return out


def fact(fs: list[Fact], name: str) -> Fact:
    return next(f for f in fs if f.name == name)


INSTRUCTIONS = """You write an agreement alert for the Sales Operations lead from the FACTS block only.
Three sentences first: what the clause says (quote its line from the facts), where the agency stands (the value and the distance
to the line, and the consecutive quarters where the facts give them), and what is at stake in dollars. Then a blank line and the
draft to the agency: a line "Subject: ..." then a blank line, then "Hello <first name>," and five sentences. For a breached or
threatened clause the draft is a notice that states the clause, the numbers and the next step; for a tier within reach it is an
upsell note that says what a higher tier would pay. Every number you write must appear in the FACTS exactly as shown (same rounding;
$ and % and K or M are fine). Never compute. No column names, no ISO dates, no em dashes, no bullet points. End with one line
starting "Could not verify:" naming what the facts do not cover, without numbers."""


def _consequence(text) -> str:
    text = str(text or "").strip()
    if not text or re.search(r"\d", text):
        return "the consequence in the agreement applies"
    return text[0].lower() + text[1:].rstrip(".")


def template(seed: dict, fs: list[Fact]) -> str:
    c, x = row(fact(fs, "check").df), row(fact(fs, "clause").df)
    agency, kind, status = seed["agency_name"], WORDS.get(seed["clause_type"], seed["clause_type"].replace("_", " ")), STATUS_WORDS.get(seed["status"], seed["status"])
    t = seed["clause_type"]
    side = "below" if (c.get("distance") or 0) < 0 else "above"
    dist = num(abs(c.get("distance") or 0))
    if t == "share_floor_quarters":
        p1 = (f"{agency}'s agreement (clause {c['section']}) says that if AA share falls below {num(c['threshold'])}% for {int(c['window_quarters'] or 0)} consecutive quarters, "
              f"{_consequence(c.get('consequence'))}. The latest closed quarter came in at {num(c['value'])}%, {dist} points {side} the line, "
              f"with {int(c['quarters_below'] or 0)} consecutive quarters below it so far; that is {status}.")
        ask = f"the share floor of {num(c['threshold'])}% in clause {c['section']}"
    elif t == "revenue_decline_quarters":
        p1 = (f"{agency}'s agreement (clause {c['section']}) says that if quarterly AA revenue falls below {num(c['threshold'], 0)}% of the same quarter a year earlier for "
              f"{int(c['window_quarters'] or 0)} consecutive quarters, {_consequence(c.get('consequence'))}. The latest closed quarter was {num(c['value'])}% of last year's; that is {status}.")
        ask = f"the revenue line of {num(c['threshold'], 0)}% in clause {c['section']}"
    elif t == "annual_commitment":
        p1 = (f"{agency} committed to at least {money(x.get('threshold'))} of AA revenue this year (clause {c['section']}). At this pace the year ends at {num(c['value'])}% "
              f"of the commitment, against the {num(c['threshold'], 0)}% line, with {money(c.get('dollars'))} of advanced incentive at stake; that is {status}.")
        ask = f"the commitment of {money(x.get('threshold'))} in clause {c['section']}"
    elif t.endswith("_tiers"):
        unit = "%" if c.get("unit") == "pct" else " points"
        p1 = (f"{agency}'s incentive runs in tiers (clause {c['section']}). Year to date the agency is at {num(c['value'])}{unit}, {dist}{unit} {side} the "
              f"{num(c['threshold'])}{unit} line; the tier at that line pays {money(c.get('dollars'))} at this year's revenue, so this is {'an upsell within reach' if side == 'below' else 'a tier worth protecting'}.")
        ask = f"the {num(c['threshold'])}{unit} tier line in clause {c['section']}"
    elif t == "goal":
        unit = "%" if c.get("unit") == "pct" else " points"
        p1 = f"The agreement sets a goal (clause {c['section']}); the agency stands at {num(c['value'])}{unit} against {num(c['threshold'])}{unit}, which is {status}."
        ask = f"the goal in clause {c['section']}"
    else:
        p1 = f"The agreement's {kind} (clause {c['section']}) is {status}: {num(c['value'])} against a line of {num(c['threshold'])}."
        ask = f"clause {c['section']}"
    if seed["status"] == "breached":
        p2 = "The condition in the clause holds, so the next step is a formal notice to the agency and a review with the account manager."
    elif side == "below" and t.endswith("_tiers"):
        p2 = f"The next step is an upsell conversation: {dist}{unit} more would move the agency up a tier."
    else:
        p2 = "The next step is a note to the account manager before the quarter closes, so the agency hears it from us first."
    contacts = fact(fs, "contacts").df
    first = str(contacts.iloc[0]["contact_name"]).split()[0] if not contacts.empty else "there"
    notice = seed["status"] == "breached" or not (side == "below" and t.endswith("_tiers"))
    email = (f"Subject: {agency}: {'a note on ' if not notice else ''}{ask}.\n\n"
             f"Hello {first}, I am writing about {ask}. " +
             (f"The latest check puts you at {num(c['value'])}{'%' if c.get('unit') == 'pct' else (' points' if c.get('unit') == 'pts' else '')} against that line. " if c.get("value") is not None else "") +
             (f"We would like to walk through the numbers with you and agree the next step together. " if notice else
              f"A higher tier would pay {money(c.get('dollars'))} at this year's revenue, and you are {dist}{unit} from it. ") +
             "Could we find thirty minutes next week? I will send the monthly report ahead of the call. Best regards, Sales Operations")
    return "\n\n".join([p1, p2, email, "Could not verify: anything outside the sales data, such as a change the agency made in its booking tool."])


def action(seed: dict, fs: list[Fact], verified_text: str) -> dict:
    i = verified_text.find("Hello ")
    body = (verified_text[i:] if i >= 0 else verified_text).split("Could not verify")[0].strip()
    contacts = fact(fs, "contacts").df
    kind = WORDS.get(seed["clause_type"], seed["clause_type"].replace("_", " "))
    return {"type": "email", "subject": f"Agreement watch: {seed['agency_name']}, {kind}", "body": body,
            "to": str(contacts.iloc[0]["email"]) if not contacts.empty else "",
            "crm": {"agency_id": seed["agency_id"], "activity_type": "Agreement notice" if seed["status"] == "breached" else "Agreement note",
                    "subject": f"Agreement watch: clause {seed['section']} {seed['status']}"}}


agents.register(AgentDef(
    key="watch", name="Agreement watch",
    summary="Every measurable promise in the agreements, checked against the metric view for the month: breached, close to its line, or fine, with the distance and the dollars. For each alert, a drafted notice or a drafted upsell note, for approval.",
    reads=["gold.contract_clauses", "ops.agreement_checks", "gold.fact_agency_sales_monthly", "the CRM stand-in"],
    writes=["an email draft", "a note in the CRM stand-in"], approver="the Sales Operations lead", scope_kind="region", kind="clause", noun="alert",
    plan=plan, facts=facts, instructions=INSTRUCTIONS, template=template, action=action,
    severity=lambda seed, fs: "risk" if seed["status"] == "breached" else "watch",
    title=lambda seed, fs: f"{seed['agency_name']}: {WORDS.get(seed['clause_type'], seed['clause_type'].replace('_', ' '))} (clause {seed['section']})",
    subtitle=lambda seed, fs: f"{month_label(seed['month'])}, {STATUS_WORDS.get(seed['status'], seed['status'])}",
    empty_text="No clause needs attention this month."))
