"""The Delegate routes: the catalog of agents with their pages, runs started in the background and polled, the decisions
on their items, and the CRM stand-in's activities. A run executes in a task created inside the request, so it carries the
viewer's token: SQL runs as the person who pressed Run now. Finished runs live in ops.agent_runs and are read from there
(the nightly job retires pages this process never saw); a run in progress lives only here until it finishes, so a poll
sees its items appear."""
from __future__ import annotations

import asyncio
from typing import Literal

import pandas as pd
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from starlette.concurrency import run_in_threadpool

from fairshare import db
from harness import agents
from harness import mismatch, precall, prospect, watch  # noqa: F401  (each registers its agent on import)
from harness.agents import AGENTS, Run
from server import validate
from server.context import Viewer, viewer

router = APIRouter()
ORDER = ["precall", "watch", "prospect", "mismatch"]
CRM_LABEL = "the CRM stand-in (Dynamics 365 Sales at an airline)"
RUNS: dict[str, Run] = {}   # the runs this process started or touched, newest last; ponytail: fifty at most. The table wins once a run has finished.
MAX = 50


def _remember(run: Run) -> Run:
    RUNS[run.run_id] = run
    while len(RUNS) > MAX:
        RUNS.pop(next(iter(RUNS)))
    return run


def _managers() -> list[str]:
    return db.query("SELECT DISTINCT account_manager FROM aa_demo.gold.dim_agency ORDER BY account_manager")["account_manager"].tolist()


def _markets() -> list[dict]:
    df = db.query("SELECT market_id, CONCAT(origin, '-', dest) AS market FROM aa_demo.gold.dim_market ORDER BY market_id")
    return [{"market_id": int(r.market_id), "market": r.market} for r in df.itertuples()]


def _runs(limit: int) -> list[Run]:
    """The table, plus the runs still in progress here (a run is saved when it finishes) and any finished one the table
    has not caught up with yet. Newest first."""
    out = {r.run_id: r for r in agents.load_runs(max(limit, 50))}
    for r in RUNS.values():
        if r.status == "running" or r.run_id not in out:
            out[r.run_id] = r
    return sorted(out.values(), key=lambda r: r.created_at, reverse=True)[:limit]


def _headers(limit: int) -> list[dict]:
    return [r.header() for r in _runs(limit)]


def _catalog() -> dict:
    runs = _runs(200)
    pages = agents.pages(runs)
    last, running = {}, {}
    for r in runs:
        last.setdefault(r.agent, {"run_id": r.run_id, "status": r.status, "created_at": r.created_at})
        if r.status == "running":
            running.setdefault(r.agent, {"run_id": r.run_id, "progress": r.progress})
    keys = [k for k in ORDER if k in AGENTS] + [k for k in AGENTS if k not in ORDER]
    return {"agents": [{"key": a.key, "name": a.name, "summary": a.summary, "one_liner": a.one_liner, "cadence": a.cadence,
                        "steps": [{"key": f"s{i}", "title": t, "sub": s} for i, (t, s) in enumerate(a.steps, 1)],
                        "reads": a.reads, "writes": a.writes, "approver": a.approver, "scope_kind": a.scope_kind,
                        "last_run": last.get(a.key), "running": running.get(a.key), "pages": pages.get(a.key, []),
                        "waiting": sum(1 for p in pages.get(a.key, []) if p["status"] == "draft")} for a in (AGENTS[k] for k in keys)],
            "managers": _managers(), "markets": _markets(), "crm_label": CRM_LABEL}


@router.get("/agents")
async def catalog(v: Viewer = Depends(viewer)):
    return await run_in_threadpool(_catalog)


class ScopeIn(BaseModel):
    manager: str | None = Field(default=None, max_length=80)
    region: str | None = Field(default=None, max_length=20)
    month: str | None = Field(default=None, max_length=10)
    market: str | None = Field(default=None, max_length=10)


class RunIn(BaseModel):
    scope: ScopeIn = Field(default_factory=ScopeIn)
    writer: Literal["guarded", "template"] = "guarded"


def _check_scope(key: str, scope: dict) -> dict:
    """The trust boundary for a run: a month in the data, an allowlisted region, a manager or market that exists."""
    a = AGENTS[key]
    if scope.get("month"):
        _, scope["month"] = validate.scope("All", scope["month"])
    if a.scope_kind == "region":
        validate.scope(scope.get("region") or "All", scope.get("month") or agents.latest_month())
    if a.scope_kind == "manager":
        if scope.get("manager") not in _managers():
            raise HTTPException(422, {"code": "unknown_manager", "message": "Pick an account manager from the list."})
    if a.scope_kind == "market":
        if str(scope.get("market") or "").upper() not in {m["market"] for m in _markets()}:
            raise HTTPException(422, {"code": "unknown_market", "message": "Pick a market from the list."})
        scope["market"] = str(scope["market"]).upper()
    return scope


@router.post("/agents/{key}/run")
async def start_run(key: str, body: RunIn, wait: bool = False, v: Viewer = Depends(viewer)):
    if key not in AGENTS:
        raise HTTPException(404, {"code": "unknown_agent", "message": "No agent with that name."})
    scope = await run_in_threadpool(_check_scope, key, {k: val for k, val in body.scope.model_dump().items() if val})
    mode = "template" if body.writer == "template" or agents.thinker_backend() == "none" else "guarded"
    run = _remember(agents.new_run(key, scope, v.email or "laptop", mode))
    task = asyncio.create_task(agents.run_async(key, scope, run.requested_by, mode, run=run))   # the request's context travels with it
    if wait:
        await task
    return run.to_json()


@router.get("/agents/runs")
async def runs(limit: int = 20, v: Viewer = Depends(viewer)):
    return await run_in_threadpool(_headers, max(1, min(int(limit), 100)))


def _run(run_id: str) -> Run:
    """A run in progress is read from memory, a finished one from the table, where a later run may have retired its pages."""
    run = RUNS.get(run_id)
    if run is None or run.status != "running":
        run = agents.load(run_id) or run
    if run is None:
        raise HTTPException(404, {"code": "not_found", "message": "No run with that id."})
    return _remember(run)


@router.get("/agents/runs/{run_id}")
async def get_run(run_id: str, v: Viewer = Depends(viewer)):
    return (await run_in_threadpool(_run, run_id)).to_json()


class ApproveIn(BaseModel):
    text: str | None = Field(default=None, max_length=8000)


def _decide(run_id: str, item_id: str, text: str | None, by: str, approve: bool) -> dict:
    run = _run(run_id)
    try:
        item = agents.approve(run, item_id, text, by) if approve else agents.reject(run, item_id, by)
    except KeyError:
        raise HTTPException(404, {"code": "no_item", "message": "No item with that id in this run."})
    except agents.Unverified as e:
        raise HTTPException(422, {"code": "unverified", "message": "Your edit has a number no fact supports, so it cannot be approved.", "removed": e.flagged})
    return item.to_json()


@router.post("/agents/runs/{run_id}/items/{item_id}/approve")
async def approve_item(run_id: str, item_id: str, body: ApproveIn | None = None, v: Viewer = Depends(viewer)):
    return await run_in_threadpool(_decide, run_id, item_id, body.text if body else None, v.email or "laptop", True)


class DecideIn(BaseModel):
    approve: bool
    item_ids: list[str] = Field(min_length=1, max_length=50)


@router.post("/agents/runs/{run_id}/decide")
async def decide_items(run_id: str, body: DecideIn, v: Viewer = Depends(viewer)):
    """Several pages of one run at once; an edit stays a decision on one page."""
    def go():
        run = _run(run_id)
        try:
            return [i.to_json() for i in agents.decide(run, body.item_ids, v.email or "laptop", body.approve)]
        except KeyError:
            raise HTTPException(404, {"code": "no_item", "message": "No item with that id in this run."})
    return await run_in_threadpool(go)


@router.post("/agents/runs/{run_id}/items/{item_id}/reject")
async def reject_item(run_id: str, item_id: str, v: Viewer = Depends(viewer)):
    return await run_in_threadpool(_decide, run_id, item_id, None, v.email or "laptop", False)


def _activities(agency_id: int, limit: int = 20) -> list[dict]:
    crm = db.query(f"""SELECT CAST(a.activity_id AS STRING) AS activity_id, a.agency_id, a.activity_type, a.subject, CAST(a.happened_at AS STRING) AS happened_at,
                              a.owner, a.notes, c.contact_name
                       FROM aa_demo.gold.crm_activities a LEFT JOIN aa_demo.gold.crm_contacts c ON c.contact_id = a.contact_id
                       WHERE a.agency_id = {int(agency_id)} ORDER BY a.happened_at DESC LIMIT {int(limit)}""")
    crm["source"] = "crm"
    try:
        app = db.state_query(f"SELECT activity_id, agency_id, activity_type, subject, happened_at, owner, notes FROM {db.CRM_ACTIVITIES} WHERE agency_id = {int(agency_id)} ORDER BY happened_at DESC LIMIT {int(limit)}")
    except Exception:
        app = pd.DataFrame()
    if not app.empty:
        app["contact_name"] = None
        app["source"] = "app"
        crm = pd.concat([app, crm], ignore_index=True)
    if crm.empty:
        return []
    crm["happened_at"] = crm["happened_at"].astype(str)
    crm = crm.sort_values("happened_at", ascending=False).head(limit)
    return [{k: (None if (isinstance(val, float) and pd.isna(val)) else (val.item() if hasattr(val, "item") else val)) for k, val in r.items()} for r in crm.to_dict("records")]


@router.get("/crm/activities")
async def crm_activities(agency_id: int, v: Viewer = Depends(viewer)):
    validate.agency(agency_id)
    return await run_in_threadpool(_activities, agency_id)
