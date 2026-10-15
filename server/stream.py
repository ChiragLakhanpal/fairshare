"""POST /api/ask as Server-Sent Events: progress while the agent works, then the answer, then done. One request, ordered
events; the browser's AbortController (the Stop button) shows up here as a disconnect, which cancels the run."""
import asyncio
import json
import os
import re
import time

from pydantic import BaseModel, Field

from fairshare import dbx
from harness import agent as harness_agent, facts
from harness.agent import Answer
from harness.tools import PHASE_TEXT
from server import cached
from server.context import Viewer
from server.serialize import calls_json, sentences_json

ASK_TIMEOUT_S = int(os.environ.get("ASK_TIMEOUT_S", "300"))
ASK_CONCURRENCY = int(os.environ.get("ASK_CONCURRENCY", "4"))
_slots = asyncio.Semaphore(ASK_CONCURRENCY)
COULD_NOT = re.compile(r"(?:^|(?<=[.!?]\s))(Could not verify[^.]*\.?)", re.I)


class Turn(BaseModel):
    role: str = Field(pattern="^(user|assistant)$")
    text: str = Field(max_length=4000)


class Scope(BaseModel):
    region: str = Field(max_length=20)
    month: str = Field(max_length=10)


class AskIn(BaseModel):
    question: str = Field(min_length=1, max_length=2000)
    history: list[Turn] = Field(default_factory=list, max_length=6)
    genie_conversation_id: str | None = Field(default=None, max_length=120)
    scope: Scope | None = None


def _kind(a: Answer) -> str:
    tools = {c.tool for c in a.calls}
    low = a.text.lower()
    if "proxy, not a prediction" in low or low.startswith("could not verify"):
        return "refusal"
    if "explain_change" in tools:
        return "why"
    if "search_contracts" in tools:
        return "agreement"
    return "numbers"


def answer_json(a: Answer) -> dict:
    v = a.verification
    kind = _kind(a)
    return {"question": a.question, "text": a.text, "model": a.model, "kind": kind, "sentences": sentences_json(v.badges()),
            "removed": v.flagged, "could_not_verify": [m.strip() for m in COULD_NOT.findall(a.text)], "verified_text": v.verified_text,
            "calls": calls_json(a.calls), "sources": a.sources, "follow_ups": cached.FOLLOW_UPS[kind],
            "genie_conversation_id": a.genie_conversation_id, "timing": {"total_ms": a.elapsed_ms, "tools_ms": sum(c.ms for c in a.calls)},
            "cached": None, "trace_url": os.environ.get("MLFLOW_TRACES_URL") or None}


async def ask_events(viewer: Viewer, body: AskIn):
    seq = 0
    t0 = time.monotonic()

    def sse(event: str, data: dict) -> dict:
        nonlocal seq
        seq += 1
        return {"id": str(seq), "event": event, "data": json.dumps(data, default=str)}

    def done():
        return sse("done", {"t_ms": int((time.monotonic() - t0) * 1000)})

    dbx.set_user_token(viewer.token)
    loop = asyncio.get_running_loop()
    queue: asyncio.Queue = asyncio.Queue()
    ctx = facts.reset(on_event=lambda ev: loop.call_soon_threadsafe(queue.put_nowait, ev), genie_conversation_id=body.genie_conversation_id)
    question = body.question.strip()
    if body.scope:
        question = f"Current scope: {body.scope.region}, {body.scope.month}\n\n{question}"

    if harness_agent.model_backend() == "none":
        yield sse("status", {"phase": "model", "text": PHASE_TEXT["start"], "t_ms": 0})
        hit = cached.lookup(body.question)
        if hit is None:
            yield sse("error", {"code": "no_model", "message": "No model is configured here, and this question has no recorded answer."})
        else:
            yield sse("answer", hit)
        yield done()
        return

    try:
        await asyncio.wait_for(_slots.acquire(), timeout=0.05)
    except asyncio.TimeoutError:
        yield sse("error", {"code": "busy", "message": "Too many questions are running right now. Try again in a moment."})
        yield done()
        return

    task = asyncio.create_task(asyncio.wait_for(harness_agent.ask_async(question, history=[t.model_dump() for t in body.history]), ASK_TIMEOUT_S))
    try:
        yield sse("status", {"phase": "model", "text": PHASE_TEXT["start"], "t_ms": 0})
        while not task.done():
            try:
                ev = await asyncio.wait_for(queue.get(), 0.5)
            except asyncio.TimeoutError:
                continue
            yield sse(ev.pop("type"), ev)
        await asyncio.sleep(0)  # let the last call_soon_threadsafe callbacks land
        while not queue.empty():
            ev = queue.get_nowait()
            yield sse(ev.pop("type"), ev)
        try:
            yield sse("answer", answer_json(task.result()))
        except asyncio.TimeoutError:
            yield sse("error", {"code": "timeout", "message": "That took longer than five minutes, so I stopped. Try a narrower question."})
        except facts.Cancelled:
            yield sse("error", {"code": "cancelled", "message": "Stopped."})
        except Exception as e:  # the model or a tool failed in a way the harness did not catch
            yield sse("error", {"code": "agent_failed", "message": f"{type(e).__name__}: {str(e)[:300]}"})
    finally:
        ctx.cancel.set()
        if not task.done():
            task.cancel()
        _slots.release()
    yield done()
