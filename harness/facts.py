"""Per-run record of what the tools returned: the fact pool the verifier checks against, and the
SQL and sources the app shows under "show the query".

One RunContext per request, held in a ContextVar so concurrent viewers never share a pool. It also carries the
listener that turns tool activity into progress events for the browser, the cancel flag the Stop button sets,
and the Genie conversation a thread continues.
"""
from __future__ import annotations

import math
import threading
import time
from contextvars import ContextVar
from dataclasses import dataclass, field
from typing import Callable

import pandas as pd

from harness.verifier import FactPool


class Cancelled(Exception):
    """The viewer pressed Stop (or closed the tab); the run gives up at the next checkpoint."""


def records(df: pd.DataFrame | None, limit: int = 50) -> list[dict]:
    """A DataFrame as JSON-safe rows: NaN becomes null, dates become ISO strings, numpy scalars become Python ones."""
    if df is None:
        return []
    out = df.head(limit).copy()
    for c in out.columns:
        if pd.api.types.is_datetime64_any_dtype(out[c]):
            out[c] = out[c].dt.strftime("%Y-%m-%d")
    rows = []
    for r in out.to_dict("records"):
        row = {}
        for k, v in r.items():
            if hasattr(v, "item"):
                v = v.item()
            if isinstance(v, float) and math.isnan(v):
                v = None
            elif hasattr(v, "isoformat"):
                v = v.isoformat()
            row[str(k)] = v
        rows.append(row)
    return rows


@dataclass
class ToolCall:
    tool: str
    arguments: dict
    sql: str | None
    rows: int
    note: str = ""
    preview: pd.DataFrame | None = None
    genie: dict | None = None
    ms: int = 0

    def to_json(self, i: int) -> dict:
        return {"i": i, "tool": self.tool, "args": self.arguments, "sql": self.sql, "rows": self.rows, "note": self.note,
                "preview": records(self.preview), "genie": self.genie, "ms": self.ms}


@dataclass
class RunContext:
    pool: FactPool = field(default_factory=FactPool)
    calls: list[ToolCall] = field(default_factory=list)
    sources: list[str] = field(default_factory=list)
    on_event: Callable[[dict], None] | None = None
    cancel: threading.Event = field(default_factory=threading.Event)
    genie_conversation_id: str | None = None
    t0: float = field(default_factory=time.monotonic)

    def record(self, tool: str, arguments: dict, df: pd.DataFrame | None, sql: str | None = None, note: str = "",
               source: str | None = None, genie: dict | None = None, ms: int = 0):
        if df is not None:
            self.pool.add_frame(df, f"{tool}#{len(self.calls) + 1}")
        call = ToolCall(tool=tool, arguments=arguments, sql=sql, rows=0 if df is None else len(df), note=note,
                        preview=None if df is None else df.head(50), genie=genie, ms=ms)
        self.calls.append(call)
        if source and source not in self.sources:
            self.sources.append(source)
        self.emit("tool", **call.to_json(len(self.calls)))

    def emit(self, type: str, **data) -> None:
        """A progress event for the browser; a no-op when nobody listens (the CLI, the benchmark, a job task)."""
        if self.on_event is None:
            return
        data["type"] = type
        data.setdefault("t_ms", int((time.monotonic() - self.t0) * 1000))
        self.on_event(data)

    def check_cancel(self) -> None:
        if self.cancel.is_set():
            raise Cancelled()

    def clear(self) -> None:
        """A fresh pool and call list for a retry, keeping the listener, the cancel flag and the conversation."""
        self.pool = FactPool()
        self.calls = []
        self.sources = []


_var: ContextVar = ContextVar("fairshare_run", default=None)


def current() -> RunContext:
    ctx = _var.get()
    if ctx is None:
        ctx = RunContext()
        _var.set(ctx)
    return ctx


def reset(**kw) -> RunContext:
    ctx = RunContext(**kw)
    _var.set(ctx)
    return ctx


def use(ctx: RunContext) -> RunContext:
    _var.set(ctx)
    return ctx
