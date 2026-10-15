"""CRM versus reality: every open opportunity whose health in the CRM stand-in disagrees with the data.

On track while AA share fell three points or more against last year, or at risk or stalled while it rose three points or
more. One item per opportunity: what the CRM says, what the data says, and a drafted CRM note; approving records the
note in the CRM stand-in (at an airline, a Dynamics activity through Dataverse).
"""
from __future__ import annotations

from fairshare import db
from harness import agents
from harness.agents import AgentDef, Fact, money, month_label, num, row
from harness.precall import crm_block, mismatch_block, why_block
from harness.summary import REGIONS


def plan(scope: dict) -> list[dict]:
    region = scope.get("region") or "All"
    month = scope.get("month") or agents.latest_month()
    if region not in REGIONS:
        raise ValueError(f"region must be one of {', '.join(REGIONS)}")
    df = mismatch_block(None, f"{month}-01").df
    if region != "All" and not df.empty:
        regions = db.query("SELECT agency_id, region FROM aa_demo.gold.dim_agency")
        keep = set(regions[regions["region"] == region]["agency_id"].astype(int))
        df = df[df["agency_id"].astype(int).isin(keep)]
    return [{"agency_id": int(r.agency_id), "agency_name": r.agency_name, "opp_id": int(r.opp_id), "opp_name": r.opp_name, "month": month} for r in df.itertuples()]


def facts(scope: dict, seed: dict) -> list[Fact]:
    aid, mo = seed["agency_id"], f"{seed['month']}-01"
    mis = mismatch_block(aid, mo)
    mis.df = mis.df[mis.df["opp_id"].astype(int) == seed["opp_id"]].reset_index(drop=True)
    mis.name, mis.label = "opportunity", "The opportunity in the CRM stand-in, and what the data says"
    why, _markets = why_block(aid, mo)
    _opps, touch, contacts = crm_block(aid, mo)
    return [mis, why, touch, contacts]


def fact(fs: list[Fact], name: str) -> Fact:
    return next(f for f in fs if f.name == name)


INSTRUCTIONS = """You write a CRM correction for an account manager from the FACTS block only. Three sentences: what the CRM stand-in
says about the opportunity (its name, stage, amount and health), what the data says (the share move in points and the revenue
change against the same month last year), and what to change. Then a blank line and a line starting "CRM note:" with two sentences
the account manager can paste into the record. Every number exactly as in the facts; never compute; no column names, no ISO dates,
no em dashes. End with one line starting "Could not verify:" naming what the facts do not cover, without numbers."""


def template(seed: dict, fs: list[Fact]) -> str:
    o, w = row(fact(fs, "opportunity").df), row(fact(fs, "why").df)
    chg, yoy = o.get("share_chg_pts"), o.get("revenue_yoy_pct")
    new_health = "At risk" if str(o.get("health")) == "On track" else "On track"
    p1 = (f"The CRM stand-in says the {o['opp_name']}, worth {money(o.get('amount_usd'))} in the {o['stage']} stage, is {o['health']}. "
          f"The data says AA share moved {num(chg)} points against the same month last year and revenue moved {num(yoy)}%. "
          f"The record should say {new_health}, with a note on the share move.")
    note = (f"CRM note: AA share moved {num(chg)} points year over year in {month_label(seed['month'])}, and revenue was {money(w.get('revenue_now'))}, "
            f"{num(yoy)}% against last year. Health changed to {new_health} after review.")
    return "\n\n".join([p1, note, f"Could not verify: why the opportunity was marked {o['health']}; the CRM stand-in holds no note on it."])


def action(seed: dict, fs: list[Fact], verified_text: str) -> dict:
    i = verified_text.find("CRM note:")
    body = (verified_text[i + len("CRM note:"):] if i >= 0 else verified_text).split("Could not verify")[0].strip()
    return {"type": "crm", "subject": f"CRM update: {seed['opp_name']}", "body": body,
            "crm": {"agency_id": seed["agency_id"], "activity_type": "CRM update", "subject": "Health changed after review"}}


agents.register(AgentDef(
    key="mismatch", name="CRM versus reality",
    summary="Every open opportunity whose health in the CRM stand-in disagrees with the data: on track while share collapses, at risk while share grows. For each one, a drafted CRM note, for approval.",
    reads=["the CRM stand-in", "ops.decomposition"], writes=["a note in the CRM stand-in"], approver="the account manager",
    scope_kind="region", kind="mismatch", noun="note",
    plan=plan, facts=facts, instructions=INSTRUCTIONS, template=template, action=action,
    severity=lambda seed, fs: "risk",
    title=lambda seed, fs: f"{seed['agency_name']}: {seed['opp_name']}",
    subtitle=lambda seed, fs: f"{month_label(seed['month'])}, {str(row(fact(fs, 'opportunity').df).get('mismatch') or '').rstrip('.')}",
    empty_text="The CRM stand-in and the data agree on every open opportunity."))
