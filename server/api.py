"""The routes. Deterministic work runs in the threadpool (contextvars travel with it); model calls await on the loop."""
import os
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from starlette.concurrency import run_in_threadpool

from fairshare import db, dbx
from fairshare.db import ROOT
from harness import agent as harness_agent, facts, summary, tools
from harness.tools import explain_change
from server import drafts, validate
from server.context import Viewer, viewer
from server.serialize import brief_json, calls_json, records

router = APIRouter()
SCOPES = ["sql", "genie", "model-serving"]
LINKS = {"dashboard": "DASHBOARD_URL", "genie": "GENIE_SPACE_URL", "traces": "MLFLOW_TRACES_URL", "repo": "REPO_URL", "app": "DATABRICKS_APP_URL", "job": "JOB_URL"}


def _model_name() -> str:
    b = harness_agent.model_backend()
    if b == "databricks":
        return f"databricks/{os.environ.get('DATABRICKS_MODEL', 'databricks-qwen3-next-80b-a3b-instruct')}"
    if b == "azure":
        return f"azure/{os.environ.get('AZURE_OPENAI_DEPLOYMENT', '')}"
    if b == "openai":
        return f"openai/{os.environ.get('OPENAI_MODEL', 'gpt-4.1-mini')}"
    return "none"


def _prior(month: str) -> str:
    return f"{int(month[:4]) - 1}-{month[5:7]}"


@router.get("/me")
async def me(v: Viewer = Depends(viewer)):
    months = await run_in_threadpool(summary.months)
    sid = os.environ.get("GENIE_SPACE_ID") if db.is_databricks() else None
    return {"email": v.email, "user": v.user, "inside_app": v.inside_app, "scopes": SCOPES, "backend": db.backend(), "model": _model_name(),
            "genie": {"space_id": sid, "url": f"{dbx.host()}/genie/rooms/{sid}"} if sid else None,
            "data_through": months[0], "regions": list(summary.REGIONS), "months": months,
            "links": {k: os.environ[var] for k, var in LINKS.items() if os.environ.get(var)}}


@router.get("/agencies")
async def agencies(v: Viewer = Depends(viewer)):
    return await run_in_threadpool(validate.agencies)


@router.get("/summary")
async def get_summary(region: str, month: str, v: Viewer = Depends(viewer)):
    region, month = validate.scope(region, month)
    ctx = facts.reset()
    f = await run_in_threadpool(summary.build_facts, region, month, ("region", "agencies", "pace", "movers"))
    kpis = {**records(f["region"])[0], **records(f["pace"])[0]}
    behind = [{"agency_id": b["agency_id"], "agency": b["agency_name"], "pace_pct": b["pace_pct"], "aa_revenue": b["aa_revenue"], "yoy_pct": b["yoy_pct"]}
              for b in records(f["behind_pace"], 100)]
    return {"region": region, "month": month, "prior_month": _prior(month), "kpis": kpis, "movers": records(f["movers"]),
            "behind_pace": behind, "headline": summary.headline(f, month), "calls": calls_json(ctx.calls)}


@router.get("/explain")
async def explain(agency_id: int, month: str, v: Viewer = Depends(viewer)):
    a = validate.agency(agency_id)
    _, month = validate.scope("All", month)
    ctx = facts.reset()
    text = await run_in_threadpool(explain_change.func, agency=a["agency_name"], month=month)
    if len(ctx.calls) < 2 or ctx.calls[0].preview is None:
        raise HTTPException(404, {"code": "no_decomposition", "message": text})
    return {"agency": {"agency_id": a["agency_id"], "agency_name": a["agency_name"]}, "month": month, "prior_month": _prior(month),
            "summary": records(ctx.calls[0].preview)[0], "markets": records(ctx.calls[1].preview, 100), "note": text,
            "could_not_verify": "whether the agency changed a preferred-carrier setting or lost a client; that is not in the data",
            "calls": calls_json(ctx.calls)}


@router.get("/agreements")
async def agreements(topic: str = Query(..., min_length=1, max_length=200), agency_id: int | None = None, v: Viewer = Depends(viewer)):
    name = validate.agency(agency_id)["agency_name"] if agency_id is not None else ""
    hits = await run_in_threadpool(tools._search, name, topic)
    return {"agency": name or None, "topic": topic, "hits": [{"file": f, "page": p, "text": t, "score": s} for s, f, p, t in hits[:3]]}


def _parity() -> dict:
    import pandas as pd
    df, source = None, None
    if db.is_databricks():
        try:
            df, source = db.query("SELECT * FROM aa_demo.ops.kpi_parity"), "ops.kpi_parity"
        except Exception:
            df = None
    if df is None or df.empty:
        csv = ROOT / "app" / "cache" / "kpi_parity.csv"
        if not csv.exists():
            return {"parity": None, "runs": []}
        df, source = pd.read_csv(csv), "app/cache/kpi_parity.csv"
    df = df.copy()
    df["ok"] = df["status"].astype(str).str.lower() == "ok"
    runs = (df.groupby("run_id").agg(run_at=("run_at", "min"), kpis=("kpi", "nunique"), rows=("kpi", "size"), drift=("ok", lambda s: int((~s).sum())))
            .reset_index().sort_values("run_at", ascending=False))
    latest = runs.iloc[0]
    cur = df[df["run_id"] == latest["run_id"]].copy()
    cur["month"] = cur["sales_month"].astype(str).str[:7]
    grid = {k: {m: ("ok" if g["ok"].all() else "drift") for m, g in kg.groupby("month")} for k, kg in cur.groupby("kpi")}
    return {"parity": {"run_id": str(latest["run_id"]), "run_at": str(latest["run_at"]), "kpis": int(latest["kpis"]), "rows": int(latest["rows"]),
                       "drift": int(latest["drift"]), "grid": grid, "drifting": records(cur[~cur["ok"]].drop(columns=["ok", "month"]), 20), "source": source},
            "runs": records(runs, 50)}


@router.get("/definitions")
async def definitions(v: Viewer = Depends(viewer)):
    kpis = await run_in_threadpool(lambda: records(db.query("SELECT * FROM aa_demo.ops.kpi_definitions"), 100))
    return {"kpis": kpis, **await run_in_threadpool(_parity)}


class BriefIn(BaseModel):
    region: str = Field(max_length=20)
    month: str = Field(max_length=10)
    writer: Literal["guarded", "unguarded", "template"] = "guarded"


@router.post("/brief")
async def post_brief(body: BriefIn, v: Viewer = Depends(viewer)):
    region, month = validate.scope(body.region, body.month)
    facts.reset()
    w = None if body.writer == "template" else summary.make_writer(None if body.writer == "guarded" else summary.UNGUARDED_INSTRUCTIONS)
    res = await summary.run_async(region, month, w)
    drafts.put(res, body.writer)
    return brief_json(res, "draft", body.writer)


@router.post("/brief/{run_id}/approve")
async def approve_brief(run_id: str, v: Viewer = Depends(viewer)):
    item = drafts.get(run_id)
    if item is None:
        raise HTTPException(404, {"code": "draft_expired", "message": "That draft is gone. Write the brief again."})
    await run_in_threadpool(summary.save, item["res"], "approved")
    drafts.approve(run_id)
    return {"run_id": run_id, "status": "approved", "table": db.SUMMARIES}


@router.get("/brief/{run_id}")
async def get_brief(run_id: str, v: Viewer = Depends(viewer)):
    item = drafts.get(run_id)
    if item is not None:
        return brief_json(item["res"], item["status"], item["writer"])
    row = await run_in_threadpool(summary.load, run_id)
    if row is None:
        raise HTTPException(404, {"code": "not_found", "message": "No brief with that id."})
    return brief_json(row, row["status"])
