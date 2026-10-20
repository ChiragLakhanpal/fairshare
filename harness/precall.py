"""The Monday pre-call pack: one page per agency an account manager owns, for the month.

Blocks (fixed, portable SQL): the month's numbers, why they moved (the decomposition and its markets), the agreement
clauses the watch flagged, the CRM stand-in (open opportunities, the last touch, the contacts), AA seats on the agency's
top markets versus last year, and where the CRM and the data disagree. The writer turns the facts into four short
paragraphs and a draft email; the verifier checks every number; approving records a "Pre-call pack" activity in the
CRM stand-in and opens the email.
"""
from __future__ import annotations

import pandas as pd

from fairshare import db
from harness import agents
from harness.agents import AgentDef, Fact, money, month_label, num, prior_year, row

WORDS = {"share_floor_quarters": "share floor", "annual_commitment": "revenue commitment", "goal": "annual goal",
         "share_premium_tiers": "incentive tier", "share_tiers": "incentive tier", "gap_tiers": "incentive tier",
         "revenue_decline_quarters": "revenue decline clause", "capacity_exclusion": "capacity exclusion", "front_end_incentive": "front-end incentive"}
STATUS_WORDS = {"breached": "breached", "watch": "close to its line", "ok": "fine"}


# ---------------------------------------------------------------- the blocks
def numbers_block(aid: int, mo: str, prior: str) -> Fact:
    sql = f"""
        WITH cur AS (
          SELECT a.agency_id, a.agency_name, a.account_manager, SUM(s.aa_revenue) AS aa_revenue, SUM(s.market_revenue) AS market_revenue,
                 SUM(s.market_revenue * c.aa_seat_share) AS fair_revenue
          FROM aa_demo.gold.fact_agency_sales_monthly s JOIN aa_demo.gold.dim_agency a ON a.agency_id = s.agency_id
          JOIN aa_demo.gold.fact_market_capacity c ON c.market_id = s.market_id AND c.sales_month = s.sales_month
          WHERE s.sales_month = DATE '{mo}' AND a.agency_id = {aid} GROUP BY ALL),
        pri AS (SELECT SUM(aa_revenue) AS aa_revenue_prior FROM aa_demo.gold.fact_agency_sales_monthly WHERE sales_month = DATE '{prior}' AND agency_id = {aid})
        SELECT cur.agency_name, cur.account_manager, ROUND(cur.aa_revenue, 0) AS aa_revenue, ROUND(pri.aa_revenue_prior, 0) AS aa_revenue_prior_year,
               ROUND((cur.aa_revenue - pri.aa_revenue_prior) / NULLIF(pri.aa_revenue_prior, 0) * 100, 1) AS yoy_pct,
               ROUND(cur.aa_revenue / NULLIF(cur.market_revenue, 0) * 100, 1) AS aa_share_pct,
               ROUND(cur.fair_revenue / NULLIF(cur.market_revenue, 0) * 100, 1) AS fair_share_pct,
               ROUND((cur.aa_revenue - cur.fair_revenue) / NULLIF(cur.market_revenue, 0) * 100, 1) AS share_gap_pts,
               ROUND(cur.aa_revenue - cur.fair_revenue, 0) AS share_gap_usd,
               p.pace_pct, ROUND(p.ytd_revenue, 0) AS ytd_revenue, ROUND(p.revenue_goal_usd, 0) AS revenue_goal_usd
        FROM cur CROSS JOIN pri
        LEFT JOIN aa_demo.gold.agency_pace p ON p.agency_id = cur.agency_id AND p.sales_month = DATE '{mo}'"""
    return Fact("numbers", "The month's numbers", db.query(sql), sql.strip(), "gold.fact_agency_sales_monthly, gold.agency_pace")


def why_block(aid: int, mo: str) -> tuple[Fact, Fact]:
    sql = f"""
        SELECT ROUND(d.revenue_now, 0) AS revenue_now, ROUND(d.revenue_prior, 0) AS revenue_prior, ROUND(d.delta_revenue, 0) AS delta_revenue, d.delta_pct,
               d.market_delta_pct, ROUND(d.aa_share_now * 100, 1) AS aa_share_now_pct, ROUND(d.aa_share_prior * 100, 1) AS aa_share_prior_pct,
               ROUND((d.aa_share_now - d.aa_share_prior) * 100, 1) AS share_chg_pts,
               ROUND(d.fair_share_now * 100, 1) AS fair_share_now_pct, ROUND(d.fair_share_prior * 100, 1) AS fair_share_prior_pct,
               ROUND((d.fair_share_now - d.fair_share_prior) * 100, 1) AS fair_share_chg_pts,
               ROUND(d.volume_effect, 0) AS volume_effect, ROUND(d.mix_effect, 0) AS mix_effect, ROUND(d.share_effect, 0) AS share_effect,
               ROUND(d.fair_share_effect, 0) AS fair_share_effect
        FROM aa_demo.ops.decomposition d WHERE d.agency_id = {aid} AND d.sales_month = DATE '{mo}'"""
    why = db.query(sql)
    msql = f"""
        SELECT CONCAT(m.origin, '-', m.dest) AS market, ROUND(k.share_effect, 0) AS share_effect, ROUND(k.mix_effect, 0) AS mix_effect,
               ROUND(k.aa_share_now * 100, 1) AS aa_share_now_pct, ROUND(k.aa_share_prior * 100, 1) AS aa_share_prior_pct, ROUND(k.market_revenue_now, 0) AS market_revenue_now
        FROM aa_demo.ops.decomposition_markets k JOIN aa_demo.gold.dim_market m ON m.market_id = k.market_id
        WHERE k.agency_id = {aid} AND k.sales_month = DATE '{mo}' ORDER BY ABS(k.share_effect) DESC LIMIT 3"""
    note = "" if not why.empty else "No same month last year to compare with, so there is no volume, mix and share split."
    return (Fact("why", "Why it moved versus the same month last year (volume, mix and share add up to the change)", why, sql.strip(), "ops.decomposition", note),
            Fact("markets", "The three markets that moved most on share", db.query(msql) if not why.empty else pd.DataFrame(), msql.strip(), "ops.decomposition_markets"))


def clauses_block(aid: int, mo: str) -> Fact:
    sql = f"""
        SELECT section, TRY_CAST(section AS DOUBLE) AS section_number, clause_type, status, value, threshold, distance, unit, quarters_below, window_quarters,
               dollars, dollars_label, consequence, file, page
        FROM aa_demo.ops.agreement_checks WHERE agency_id = {aid} AND as_of = DATE '{mo}' AND status <> 'not_checkable'
        ORDER BY CASE status WHEN 'breached' THEN 0 WHEN 'watch' THEN 1 ELSE 2 END, dollars DESC, threshold DESC"""
    df = db.query(sql)
    has = int(db.query(f"SELECT COUNT(*) AS n FROM aa_demo.gold.contract_clauses WHERE agency_id = {aid}")["n"].iloc[0]) > 0
    note = "" if not df.empty else ("The agreement has no check for this month." if has else "No agreement on file for this agency.")
    return Fact("clauses", "Agreement clauses this month, as checked against the data", df, sql.strip(), "ops.agreement_checks", note)


def crm_block(aid: int, mo: str) -> tuple[Fact, Fact, Fact]:
    osql = f"""SELECT opp_name, stage, health, ROUND(amount_usd, 0) AS amount_usd, close_date, updated_at, owner
               FROM aa_demo.gold.crm_opportunities WHERE agency_id = {aid} AND stage <> 'Closed Won' ORDER BY amount_usd DESC"""
    opps = db.query(osql)
    csql = f"SELECT contact_name, title, email FROM aa_demo.gold.crm_contacts WHERE agency_id = {aid} ORDER BY contact_id"
    contacts = db.query(csql)
    tsql = f"""SELECT a.happened_at, a.activity_type, a.subject, c.contact_name FROM aa_demo.gold.crm_activities a
               LEFT JOIN aa_demo.gold.crm_contacts c ON c.contact_id = a.contact_id WHERE a.agency_id = {aid} ORDER BY a.happened_at DESC LIMIT 1"""
    touch = db.query(tsql)
    touch["source"] = "crm"
    try:  # what the app itself recorded (an approved pack, a CRM update), newest first
        app = db.state_query(f"SELECT happened_at, activity_type, subject, owner AS contact_name FROM {db.CRM_ACTIVITIES} WHERE agency_id = {aid} ORDER BY happened_at DESC LIMIT 1")
        if not app.empty:
            app["source"] = "app"
            touch = pd.concat([touch, app], ignore_index=True)
    except Exception:
        pass
    if not touch.empty:
        touch["happened_at"] = pd.to_datetime(touch["happened_at"]).dt.date
        touch = touch.sort_values("happened_at", ascending=False).head(1).reset_index(drop=True)
        # "days ago" counts from the later of the real today and the month after the as-of month, so a touch the app recorded
        # today never reads as negative against the data's own clock (the data stops in September 2026)
        ref = max(pd.Timestamp(mo) + pd.DateOffset(months=1), pd.Timestamp.today().normalize())
        touch["days_since_touch"] = (ref - pd.to_datetime(touch["happened_at"])).dt.days
        touch = touch.rename(columns={"happened_at": "last_touch"})
    return (Fact("opportunities", "Open opportunities in the CRM stand-in", opps, osql.strip(), "gold.crm_opportunities (the CRM stand-in)"),
            Fact("last_touch", "The last touch in the CRM stand-in", touch, tsql.strip(), "gold.crm_activities and ops.crm_activities (the CRM stand-in)"),
            Fact("contacts", "Contacts at the agency (the CRM stand-in)", contacts, csql.strip(), "gold.crm_contacts (the CRM stand-in)"))


def schedule_block(aid: int, mo: str, prior: str) -> Fact:
    sql = f"""
        SELECT CONCAT(m.origin, '-', m.dest) AS market, ROUND(s.aa_revenue, 0) AS aa_revenue, c.aa_seats AS aa_seats_now, p.aa_seats AS aa_seats_prior_year,
               ROUND((c.aa_seats - p.aa_seats) * 100.0 / NULLIF(p.aa_seats, 0), 1) AS seats_change_pct, ROUND(c.aa_seat_share * 100, 1) AS aa_seat_share_pct
        FROM aa_demo.gold.fact_agency_sales_monthly s JOIN aa_demo.gold.dim_market m ON m.market_id = s.market_id
        JOIN aa_demo.gold.fact_market_capacity c ON c.market_id = s.market_id AND c.sales_month = s.sales_month
        LEFT JOIN aa_demo.gold.fact_market_capacity p ON p.market_id = s.market_id AND p.sales_month = DATE '{prior}'
        WHERE s.agency_id = {aid} AND s.sales_month = DATE '{mo}' ORDER BY s.market_revenue DESC LIMIT 5"""
    return Fact("schedule", "AA seats on the agency's top five markets, this month versus the same month last year", db.query(sql), sql.strip(), "gold.fact_market_capacity")


def mismatch_block(aid: int | None, mo: str) -> Fact:
    """Open opportunities whose CRM health disagrees with the data: on track while share fell three points or more, at risk
    or stalled while share rose three points or more. Shared with the CRM versus reality agent (aid None: every agency)."""
    where = f"o.agency_id = {aid}" if aid is not None else "1 = 1"
    sql = f"""
        SELECT * FROM (
          SELECT o.agency_id, a.agency_name, o.opp_id, o.opp_name, o.stage, o.health, ROUND(o.amount_usd, 0) AS amount_usd, o.close_date, o.updated_at, o.owner,
                 ROUND((d.aa_share_now - d.aa_share_prior) * 100, 1) AS share_chg_pts, ROUND(d.delta_pct, 1) AS revenue_yoy_pct,
                 CASE WHEN o.health = 'On track' AND (d.aa_share_now - d.aa_share_prior) * 100 <= -3 THEN 'The CRM says on track; the data says AA share is down.'
                      WHEN o.health IN ('At risk', 'Stalled') AND (d.aa_share_now - d.aa_share_prior) * 100 >= 3 THEN 'The CRM says at risk; the data says AA share is up.'
                      END AS mismatch
          FROM aa_demo.gold.crm_opportunities o JOIN aa_demo.gold.dim_agency a ON a.agency_id = o.agency_id
          JOIN aa_demo.ops.decomposition d ON d.agency_id = o.agency_id AND d.sales_month = DATE '{mo}'
          WHERE {where} AND o.stage <> 'Closed Won') x
        WHERE mismatch IS NOT NULL ORDER BY amount_usd DESC"""
    return Fact("mismatch", "Where the CRM stand-in and the data disagree", db.query(sql), sql.strip(), "gold.crm_opportunities, ops.decomposition")


# ---------------------------------------------------------------- the agent
def plan(scope: dict) -> list[dict]:
    manager = str(scope.get("manager") or "").strip()
    month = scope.get("month") or agents.latest_month()
    managers = db.query("SELECT DISTINCT account_manager FROM aa_demo.gold.dim_agency")["account_manager"].tolist()
    if manager not in managers:
        raise ValueError(f"No account manager named {manager!r}; the choices are {', '.join(sorted(managers))}.")
    rows = db.query(f"SELECT agency_id, agency_name, account_manager FROM aa_demo.gold.dim_agency WHERE account_manager = {db.literal(manager)} ORDER BY agency_id")
    return [{"agency_id": int(r.agency_id), "agency_name": r.agency_name, "manager": r.account_manager, "month": month} for r in rows.itertuples()]


def facts(scope: dict, seed: dict) -> list[Fact]:
    aid, mo = seed["agency_id"], f"{seed['month']}-01"
    prior = f"{prior_year(seed['month'])}-01"
    why, markets = why_block(aid, mo)
    opps, touch, contacts = crm_block(aid, mo)
    fs = [numbers_block(aid, mo, prior), why, markets, clauses_block(aid, mo), opps, touch, contacts, schedule_block(aid, mo, prior), mismatch_block(aid, mo)]
    # the same wording the template uses, as a one-row frame the model can copy: "down 16.4%", "a gap of 5.9 points worth $57K below
    # fair share", "took $97K". Text cells add nothing to the fact pool; the numbers in them match the numeric columns above.
    fs.append(Fact("phrases", "Ready-made phrases, already worded the right way: copy them", pd.DataFrame([phrases(seed, fs)]), "", "derived from the facts above"))
    return fs


def fact(fs: list[Fact], name: str) -> Fact:
    return next(f for f in fs if f.name == name)


def severity(seed: dict, fs: list[Fact]) -> str:
    n, cl = row(fact(fs, "numbers").df), fact(fs, "clauses").df
    if not fact(fs, "mismatch").df.empty or (not cl.empty and (cl["status"] == "breached").any()) or (n.get("yoy_pct") is not None and n["yoy_pct"] <= -10):
        return "risk"
    if (not cl.empty and (cl["status"] == "watch").any()) or (n.get("pace_pct") is not None and n["pace_pct"] < 100) or (n.get("yoy_pct") is not None and n["yoy_pct"] < 0):
        return "watch"
    return "ok"


INSTRUCTIONS = """You write a one-page pre-call pack for an airline account manager from the FACTS block only.
Six short paragraphs, each separated by a blank line, in this order: where the agency stands (AA revenue, the change from the same
month last year, AA share against fair share with the gap in dollars, pace to goal); what moved and why (volume, mix and share, which
add up to the change, and the markets that moved most; or that there is no comparison when the facts say so); what the agreement puts
at stake (the clause, its status, the distance to its line and the dollars; or that there is no agreement on file); what the CRM
stand-in shows (open opportunities, the last touch, and any disagreement between the CRM and the data); AA seats on the agency's top
markets versus last year; and what to do on the call (three talking points, each tied to a number). Then a blank line and an email to
the first contact named in the facts, laid out as a real email: a line "Subject: ...", a blank line, "Hello <first name>," on its
own line, a blank line, two short paragraphs separated by a blank line (the numbers, then the ask), a blank line, and one closing
line "Best regards, <the account manager's name>". The "Ready-made phrases" row is already worded the right way: copy those phrases where they fit.
Every number you write must appear in the FACTS exactly as shown (same rounding; you may add $ and % and write thousands as K and
millions as M). Never compute, estimate or infer a number. Write a decline as "down $65K" or "a loss of $65K", never with a minus
sign; write shares as 34.2%, changes in share as 10.1 points, money with a $. Never write a column name, a code such as
annual_commitment, or NA: say "the revenue commitment", "the share floor", "the incentive tier" in words. No table jargon, no dates
in ISO form, no numbered lists. Plain prose with plain punctuation: no em dashes, no bullet points, no headings. End with one line
starting "Could not verify:" naming what the facts do not cover, without numbers."""


def _yoy_words(n: dict, month: str) -> str:
    y = n.get("yoy_pct")
    if y is None:
        return "with no comparison to the same month last year"
    return f"{'down' if y < 0 else 'up'} {num(abs(y))}% from {month_label(prior_year(month))}"


def phrases(seed: dict, fs: list[Fact]) -> dict:
    """Every number the page needs, already in words: the template assembles these, and the model is told to copy them."""
    agency, month = seed["agency_name"], seed["month"]
    n = row(fact(fs, "numbers").df)
    w = row(fact(fs, "why").df)
    mk = fact(fs, "markets").df
    cl = fact(fs, "clauses")
    opps, touch, contacts = fact(fs, "opportunities").df, row(fact(fs, "last_touch").df), fact(fs, "contacts").df
    sched, mis = fact(fs, "schedule").df, fact(fs, "mismatch").df
    gap = n.get("share_gap_pts") or 0
    ph = {"revenue": f"{money(n.get('aa_revenue'))} of AA travel in {month_label(month)}", "yoy": _yoy_words(n, month),
          "share": f"AA share was {num(n.get('aa_share_pct'))}% against a fair share of {num(n.get('fair_share_pct'))}%",
          "gap": f"a gap of {num(abs(gap))} points worth {money(abs(n.get('share_gap_usd') or 0))} {'below' if gap < 0 else 'above'} fair share",
          "pace": f"year to date the agency is at {num(n['pace_pct'])}% of pace to its goal" if n.get("pace_pct") is not None else "pace to goal is not available for this month"}
    if not w:
        ph["change"] = "there is no comparison with the same month last year, so the change cannot be split into volume, mix and share"
    else:
        gave = lambda v: f"{'added' if v >= 0 else 'took'} {money(abs(v))}"
        ph["change"] = f"against the same month last year, revenue {'fell' if w['delta_revenue'] < 0 else 'rose'} {money(abs(w['delta_revenue']))} ({num(abs(w['delta_pct']))}%)"
        ph["volume"], ph["mix"], ph["share_effect"] = f"volume {gave(w['volume_effect'])}", f"mix {gave(w['mix_effect'])}", f"share {gave(w['share_effect'])}"
        ph["share_move"] = f"AA share went from {num(w['aa_share_prior_pct'])}% to {num(w['aa_share_now_pct'])}%, {'down' if w['share_chg_pts'] < 0 else 'up'} {num(abs(w['share_chg_pts']))} points"
        ph["fair_move"] = f"fair share went from {num(w['fair_share_prior_pct'])}% to {num(w['fair_share_now_pct'])}%"
        if not mk.empty:
            ph["top_markets"] = "the markets that moved most on share were " + ", ".join(f"{r.market} ({'lost' if r.share_effect < 0 else 'gained'} {money(abs(r.share_effect))})" for r in mk.itertuples())
    if cl.df.empty:
        ph["agreement"] = f"There is no agreement on file for {agency}." if "No agreement" in cl.note else "The agreement has no check for this month."
    else:
        lines = []
        flagged = cl.df[cl.df["status"].isin(["breached", "watch"])]
        for r in (flagged if not flagged.empty else cl.df.head(1)).head(2).itertuples():
            kind = WORDS.get(r.clause_type, r.clause_type.replace("_", " "))
            if r.clause_type == "annual_commitment":
                lines.append(f"The agreement's {kind} (clause {r.section}) puts the agency at {num(r.value)}% of its commitment at this pace, against a line of "
                             f"{num(r.threshold, 0)}%, with {money(r.dollars)} of advanced incentive at stake; that is {STATUS_WORDS.get(r.status, r.status)}.")
            elif r.unit == "usd":
                lines.append(f"The agreement's {kind} (clause {r.section}) is {STATUS_WORDS.get(r.status, r.status)}: {money(r.dollars)} to date.")
            else:
                unit = "%" if r.unit == "pct" else " points"
                dollars = f", with {money(r.dollars)} of incentive at this tier" if r.dollars is not None and not pd.isna(r.dollars) and r.dollars > 0 else ""
                lines.append(f"The agreement's {kind} (clause {r.section}) is {STATUS_WORDS.get(r.status, r.status)}: {num(r.value)}{unit} against a line of {num(r.threshold)}{unit}{dollars}.")
        ph["agreement"] = " ".join(lines)
    if opps.empty:
        crm = "The CRM stand-in shows no open opportunity."
    else:
        o = opps.iloc[0]
        crm = (f"The CRM stand-in shows {len(opps)} open {'opportunity' if len(opps) == 1 else 'opportunities'}, the largest being the {o['opp_name']} at "
               f"{money(o['amount_usd'])} in the {o['stage']} stage, marked {o['health']}.")
    if touch:
        when = pd.Timestamp(touch["last_touch"]).strftime("%B %d").replace(" 0", " ")
        crm += f" The last touch was a {str(touch['activity_type']).lower()} on {when} ({touch['subject']}), {int(touch['days_since_touch'])} days ago."
    for r in mis.itertuples():
        crm += f" The CRM says the {r.opp_name} is {r.health}, but AA share is {'down' if r.share_chg_pts < 0 else 'up'} {num(abs(r.share_chg_pts))} points against last year, so the record needs a correction."
    ph["crm"] = crm
    moved = sched.dropna(subset=["seats_change_pct"]) if not sched.empty else sched
    ph["seats"] = ("There is no seat comparison with last year for the agency's top markets this month." if moved.empty else
                   "On the agency's top markets, AA seats versus last year: " + ", ".join(f"{r.market} {'up' if r.seats_change_pct >= 0 else 'down'} {num(abs(r.seats_change_pct))}%" for r in moved.head(3).itertuples()) + ".")
    points = [f"the share gap is worth {money(abs(n.get('share_gap_usd') or 0))} {'below' if gap < 0 else 'above'} fair share"]
    if not mk.empty:
        points.append(f"{mk.iloc[0]['market']} {'lost' if mk.iloc[0]['share_effect'] < 0 else 'gained'} {money(abs(mk.iloc[0]['share_effect']))} of share")
    elif not sched.empty:
        points.append(f"{sched.iloc[0]['market']} is their biggest market at {money(sched.iloc[0]['aa_revenue'])} of AA revenue")
    points.append(f"pace is {num(n['pace_pct'])}% of goal" if n.get("pace_pct") is not None else "the annual goal needs a check")
    ph["talking_points"] = "; ".join(points)
    ph["contact"] = f"{contacts.iloc[0]['contact_name']} ({contacts.iloc[0]['email']})" if not contacts.empty else "no contact on file"
    ph["manager"] = str(n.get("account_manager") or seed["manager"])
    return ph


def template(seed: dict, fs: list[Fact]) -> str:
    agency, month = seed["agency_name"], seed["month"]
    ph = row(fact(fs, "phrases").df) if any(f.name == "phrases" for f in fs) else phrases(seed, fs)
    p1 = f"{agency} sold {ph['revenue']}, {ph['yoy']}. {ph['share'][0].upper() + ph['share'][1:]}, {ph['gap']}. {ph['pace'][0].upper() + ph['pace'][1:]}."
    if "volume" not in ph or not ph.get("volume"):
        p2 = ph["change"][0].upper() + ph["change"][1:] + "."
    else:
        p2 = f"{ph['change'][0].upper() + ph['change'][1:]}: {ph['volume']}, {ph['mix']} and {ph['share_effect']}; the three add up to the change. {ph['share_move']}, while {ph['fair_move']}."
        if ph.get("top_markets"):
            p2 += f" {ph['top_markets'][0].upper() + ph['top_markets'][1:]}."
    p3, p4, p5 = ph["agreement"], ph["crm"], ph["seats"]
    p6 = f"Three points for the call: {ph['talking_points']}."
    first = str(ph["contact"]).split()[0] if ph.get("contact") and ph["contact"] != "no contact on file" else "there"
    email = (f"Subject: {agency}, {month_label(month)}: performance and next steps.\n\n"
             f"Hello {first},\n\n"
             f"Thank you for the time this month. AA revenue with you was {ph['revenue']}, {ph['yoy']}. "
             f"Your {ph['share']}.\n\n"
             f"I would like to walk through what moved and what we can do together on your largest markets. "
             f"Could we find thirty minutes next week?\n\n"
             f"Best regards, {ph['manager']}")
    return "\n\n".join([p1, p2, p3, p4, p5, p6, email, "Could not verify: whether the agency changed a preferred-carrier setting or lost a client."])


def action(seed: dict, fs: list[Fact], verified_text: str) -> dict:
    i = verified_text.find("Hello ")
    body = verified_text[i:] if i >= 0 else verified_text
    body = body.split("Could not verify")[0].strip()
    contacts = fact(fs, "contacts").df
    return {"type": "email", "subject": f"Pre-call pack: {seed['agency_name']}, {month_label(seed['month'])}", "body": body,
            "to": str(contacts.iloc[0]["email"]) if not contacts.empty else "", "to_name": str(contacts.iloc[0]["contact_name"]) if not contacts.empty else "",
            "crm": {"agency_id": seed["agency_id"], "activity_type": "Pre-call pack", "subject": f"Pre-call pack approved for {month_label(seed['month'])}"}}


def clause_summary(r) -> str:
    """One plain sentence about a clause check row (a Series or a dict)."""
    get = r.get
    t, d, v, th = get("clause_type"), get("distance"), get("value"), get("threshold")
    d = None if d is None or pd.isna(d) else float(d)
    dollars = money(get("dollars")) if get("dollars") is not None and not pd.isna(get("dollars")) and float(get("dollars")) > 0 else None
    if t == "share_floor_quarters" and d is not None:
        return f"{num(abs(d))} points {'above' if d >= 0 else 'below'} its share floor."
    if str(t).endswith("_tiers") and d is not None:
        return f"{num(abs(d))} points from a higher tier worth {dollars} this year." if d < 0 else f"{num(d)} points above the line for its tier, worth {dollars} this year."
    if t == "annual_commitment":
        return f"At {num(v)}% of its revenue commitment at this pace, with {dollars} of advanced incentive at stake."
    if t == "revenue_decline_quarters":
        return f"The latest quarter was {num(v)}% of last year's, against a line of {num(th, 0)}%."
    if t == "goal":
        return f"At {num(v)}{'%' if get('unit') == 'pct' else ' points'} against a goal of {num(th)}."
    return f"The {WORDS.get(t, str(t).replace('_', ' '))} is {STATUS_WORDS.get(get('status'), get('status'))}."


def summary(seed: dict, fs: list[Fact]) -> str:
    n, cl, mis = row(fact(fs, "numbers").df), fact(fs, "clauses"), fact(fs, "mismatch").df
    tail = " No agreement on file." if "No agreement" in cl.note else ""
    if not mis.empty:
        r = mis.iloc[0]
        chg = float(r["share_chg_pts"])
        deal = str(r["opp_name"]).replace(seed["agency_name"] + " ", "")
        return f"Share is {'down' if chg < 0 else 'up'} {num(abs(chg))} points, and the CRM still says the {deal} is {str(r['health']).lower()}."
    if not cl.df.empty and cl.df.iloc[0]["status"] in ("breached", "watch"):
        return clause_summary(cl.df.iloc[0])
    yoy, gap = n.get("yoy_pct"), n.get("share_gap_pts") or 0
    if yoy is None:
        return f"{num(abs(gap))} points {'above' if gap >= 0 else 'below'} fair share; no comparison with last year.{tail}"
    return f"{'Up' if yoy >= 0 else 'Down'} {num(abs(yoy))}%, {num(abs(gap))} points {'above' if gap >= 0 else 'below'} fair share.{tail}"


agents.register(AgentDef(
    key="precall", name="Monday pre-call pack",
    summary="For every agency an account manager owns, one page: the month's numbers, why they moved, the agreement clauses at stake, the CRM stand-in's last touch and open opportunities, the schedule on their routes, talking points, and a drafted email.",
    reads=["gold.fact_agency_sales_monthly", "ops.decomposition", "ops.agreement_checks", "the CRM stand-in", "gold.fact_market_capacity"],
    writes=["an activity in the CRM stand-in", "an email draft"], approver="the account manager", scope_kind="manager", kind="page", noun="page",
    plan=plan, facts=facts, instructions=INSTRUCTIONS, template=template, action=action, severity=severity,
    title=lambda seed, fs: seed["agency_name"], subtitle=lambda seed, fs: f"{month_label(seed['month'])}, {seed['manager']}",
    empty_text="This manager owns no agencies.",
    one_liner="Writes one page for each of your agencies before Monday's calls, with an email ready to send.",
    cadence="Runs every night. You can also run it now.",
    steps=[("Numbers", "Revenue, share, pace"), ("Why", "Volume, mix, share since last year"), ("Agreement", "Clauses near their line"), ("CRM", "Last touch, open deals"),
           ("Draft", "The page and the email"), ("Check", "Every number against its query"), ("Approve", "Waits for you")],
    section_titles=["Where they stand", "What moved", "The agreement", "The CRM stand-in", "The schedule", "For the call"],
    summarize=summary))
