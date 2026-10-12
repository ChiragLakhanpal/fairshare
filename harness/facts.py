"""Per-run record of what the tools returned: the fact pool the verifier checks against, and the
SQL and sources the app shows in the "how I got this" drawer.

ponytail: one module-level run context, reset by the agent before each question. Fine for one user
on one laptop; a contextvar per request if this ever serves concurrent users.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import pandas as pd

from harness.verifier import FactPool


@dataclass
class ToolCall:
    tool: str
    arguments: dict
    sql: str | None
    rows: int
    note: str = ""
    preview: pd.DataFrame | None = None


@dataclass
class RunContext:
    pool: FactPool = field(default_factory=FactPool)
    calls: list[ToolCall] = field(default_factory=list)
    sources: list[str] = field(default_factory=list)

    def record(self, tool: str, arguments: dict, df: pd.DataFrame | None, sql: str | None = None, note: str = "", source: str | None = None):
        if df is not None:
            self.pool.add_frame(df, f"{tool}#{len(self.calls) + 1}")
        self.calls.append(ToolCall(tool=tool, arguments=arguments, sql=sql, rows=0 if df is None else len(df), note=note,
                                   preview=None if df is None else df.head(50)))
        if source and source not in self.sources:
            self.sources.append(source)


_current = RunContext()


def current() -> RunContext:
    return _current


def reset() -> RunContext:
    global _current
    _current = RunContext()
    return _current
