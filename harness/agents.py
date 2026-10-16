"""The Delegate runtime: what the four agents share.

An agent is fixed SQL blocks (facts), a tool-less writer for the prose (the thinking model when FAIRSHARE_THINKER names
one, else the loop model, else a template), the verifier on every sentence, and a person's decision with the side
effect (a mail draft the browser opens, an activity row in the CRM stand-in). Runs persist in aa_demo.ops.agent_runs
through the state-table path, so the nightly job and the app write the same shape and the app shows both.

  AGENTS                          the registry; precall, watch, prospect and mismatch register at import
  run(key, scope, by, mode)       facts -> prose -> check for every item the agent plans; sync, for the job and tests
  run_async(...)                  the same on the caller's loop (the server), appending items as they finish
  approve / reject                a decision on one item: re-verify an edit, write the CRM row once, save
  supersede                       a run that wrote a page again retires its older waiting version (a fresh approval every time)
  pages                           the unit a person decides on: one per agent and title, newest version first, with its history
  save / load / load_runs         ops.agent_runs
"""
from __future__ import annotations

import asyncio
import json
import os
import re
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Callable

import pandas as pd

from fairshare import db
from harness import aio
from harness.facts import records
from harness.summary import _clean, prettify
from harness.verifier import INFORMATIONAL, SENTENCE_SPLIT, FactPool, extract_numbers, verify


@dataclass
class Fact:
    """One block of returned rows the writer may quote: a label the prose can refer to, the frame, the SQL, the source."""
    name: str
    label: str
    df: pd.DataFrame
    sql: str = ""
    source: str = ""
    note: str = ""

    def to_json(self) -> dict:
        return {"name": self.name, "label": self.label, "sql": self.sql or None, "source": self.source or None, "note": self.note, "rows": records(self.df, 50)}

    @classmethod
    def from_json(cls, d: dict) -> "Fact":
        return cls(name=d["name"], label=d["label"], df=pd.DataFrame(d.get("rows") or []), sql=d.get("sql") or "", source=d.get("source") or "", note=d.get("note") or "")


@dataclass
class Item:
    item_id: str
    kind: str
    title: str
    subtitle: str = ""
    severity: str | None = None
    status: str = "draft"
    facts: list[Fact] = field(default_factory=list)
    sources: list[dict] = field(default_factory=list)
    draft: str = ""
    verified_text: str = ""
    flagged: list = field(default_factory=list)
    badges: list = field(default_factory=list)
    action: dict = field(default_factory=lambda: {"type": "none", "subject": "", "body": "", "crm": None})
    decided_at: str | None = None
    decided_by: str | None = None
    seed: dict = field(default_factory=dict)
    summary: str = ""                                  # one plain sentence for a list row
    titles: list[str] = field(default_factory=list)   # the section titles the page body is read under, in order

    def _grouped(self) -> list[list[dict]]:
        """The verified sentences regrouped into the draft's paragraphs: the verifier split the same text in the same order."""
        sents = self.sentences()
        paras = [p for p in re.split(r"\n\s*\n", self.draft or "") if p.strip()]
        out, i = [], 0
        for p in paras:
            n = len([s for s in SENTENCE_SPLIT.split(p) if s and s.strip()])
            out.append(sents[i:i + n])
            i += n
        if i < len(sents):  # a draft without blank lines, or a count mismatch: the rest is one paragraph
            out.append(sents[i:])
        return [g for g in out if g]

    def _parts(self) -> tuple[list[list[dict]], list[list[dict]], str | None]:
        """Body paragraphs, the email as paragraphs (from the sentence that starts with Subject:), and the could-not-verify note."""
        body, email, note, in_email = [], [], None, False
        for g in self._grouped():
            para = []
            for s in g:
                t = s["text"].strip()
                if t.lower().startswith("could not verify"):
                    note = re.sub(r"^could not verify:?\s*", "", t, flags=re.I).strip() or None
                    continue
                if t.lower().startswith("subject:"):
                    in_email = True
                para.append(s)
            if para:
                (email if in_email else body).append(para)
        return body, email, note

    def sections(self) -> list[dict]:
        body, _, _ = self._parts()
        return [{"title": self.titles[i] if i < len(self.titles) else "", "sentences": para} for i, para in enumerate(body)]

    def email(self) -> dict | None:
        """The subject, then the paragraphs as written (a greeting, the body, a sign-off); older pages wrote one paragraph."""
        _, mail, _ = self._parts()
        if not mail:
            return None
        subject = re.sub(r"^subject:\s*", "", mail[0][0]["text"].strip(), flags=re.I).rstrip(".").strip()
        paras = [p for p in [mail[0][1:], *mail[1:]] if p]
        return {"to": (self.action or {}).get("to") or "", "to_name": (self.action or {}).get("to_name") or "", "subject": subject,
                "sentences": [s for p in paras for s in p], "paragraphs": paras}

    def note(self) -> str | None:
        return self._parts()[2]

    def numbers_checked(self) -> int:
        return sum(len(s.get("numbers", [])) for s in self.sentences() if s["status"] == "verified")

    def pool(self) -> FactPool:
        """Every number the prose may carry: the facts' cells, and the numbers quoted in a cited source (with its URL)."""
        pool = FactPool()
        for f in self.facts:
            pool.add_frame(f.df, f.name)
            if "unit" in f.df.columns:  # a clause row says what its value, line and distance are measured in (pts, pct, usd)
                for r in f.df.to_dict("records"):
                    units = {"pts": ("pts", "pct"), "pct": ("pct", "pts"), "usd": ("usd",)}.get(str(r.get("unit")), ())
                    for col in ("value", "threshold", "distance"):
                        v = r.get(col)
                        if v is not None and not (isinstance(v, float) and pd.isna(v)):
                            for u in units:
                                pool.add(float(v), u, f.name, f"{col}={v}")
        for i, s in enumerate(self.sources, 1):
            src = f"web: {s.get('url', '')}"
            for n in extract_numbers(s.get("snippet", "") or ""):
                pool.add(n.value, n.unit, src, f"source [{i}]: {n.raw}")
                if n.unit == "count":
                    pool.add(n.value, "pct", src, f"source [{i}]: {n.raw}")
        return pool

    def sentences(self) -> list[dict]:
        return [{"text": b["sentence"], "status": "note" if INFORMATIONAL.match(b["sentence"]) else b["status"], "numbers": b.get("numbers", [])} for b in self.badges]

    def to_json(self) -> dict:
        return {"item_id": self.item_id, "kind": self.kind, "title": self.title, "subtitle": self.subtitle, "severity": self.severity, "status": self.status,
                "summary": self.summary, "sentences": self.sentences(), "sections": self.sections(), "email": self.email(), "note": self.note(),
                "numbers_checked": self.numbers_checked(), "removed": self.flagged, "verified_text": self.verified_text, "draft": self.draft,
                "facts": [f.to_json() for f in self.facts], "sources": self.sources, "action": self.action,
                "decided_at": self.decided_at, "decided_by": self.decided_by, "badges": self.badges, "seed": self.seed, "titles": self.titles}

    def head(self) -> dict:
        """What a list row needs."""
        return {"item_id": self.item_id, "kind": self.kind, "title": self.title, "subtitle": self.subtitle, "severity": self.severity, "summary": self.summary, "status": self.status,
                "decided_at": self.decided_at, "decided_by": self.decided_by}

    @classmethod
    def from_json(cls, d: dict) -> "Item":
        return cls(item_id=d["item_id"], kind=d["kind"], title=d["title"], subtitle=d.get("subtitle", ""), severity=d.get("severity"), status=d.get("status", "draft"),
                   facts=[Fact.from_json(f) for f in d.get("facts", [])], sources=d.get("sources", []), draft=d.get("draft", ""), verified_text=d.get("verified_text", ""),
                   flagged=d.get("removed", []), badges=d.get("badges", []), action=d.get("action") or {"type": "none", "subject": "", "body": "", "crm": None},
                   decided_at=d.get("decided_at"), decided_by=d.get("decided_by"), seed=d.get("seed", {}), summary=d.get("summary", ""), titles=d.get("titles", []))


@dataclass
class Run:
    run_id: str
    agent: str
    scope: dict
    requested_by: str
    model: str
    created_at: str
    finished_at: str | None = None
    items: list[Item] = field(default_factory=list)
    progress: dict = field(default_factory=lambda: {"done": 0, "total": 0, "text": ""})
    error: str | None = None

    @property
    def status(self) -> str:
        """Derived from the items, never set by hand."""
        if self.error:
            return "failed"
        if self.finished_at is None:
            return "running"
        if any(i.status == "draft" for i in self.items):
            return "needs_approval"
        if any(i.status == "approved" for i in self.items):
            return "approved"
        if any(i.status == "rejected" for i in self.items):
            return "rejected"
        return "superseded" if self.items else "approved"   # every page was written again by a later run, or there was nothing to decide

    def item(self, item_id: str) -> Item:
        for i in self.items:
            if i.item_id == item_id:
                return i
        raise KeyError(item_id)

    def agent_name(self) -> str:
        return AGENTS[self.agent].name if self.agent in AGENTS else self.agent

    def header(self) -> dict:
        return {"run_id": self.run_id, "agent": self.agent, "agent_name": self.agent_name(), "scope": self.scope, "status": self.status,
                "created_at": self.created_at, "finished_at": self.finished_at, "items": len(self.items),
                "needs_approval": sum(1 for i in self.items if i.status == "draft")}

    def to_json(self) -> dict:
        return {**self.header(), "requested_by": self.requested_by, "model": self.model, "progress": self.progress,
                "items": [i.to_json() for i in self.items], "error": self.error}


@dataclass
class AgentDef:
    key: str
    name: str
    summary: str
    reads: list[str]
    writes: list[str]
    approver: str
    scope_kind: str                                   # manager | region | market
    kind: str                                         # the items' kind: page | clause | prospect | mismatch
    plan: Callable[[dict], list[dict]]                # scope -> the items to write, as seeds
    facts: Callable[[dict, dict], list[Fact]]         # (scope, seed) -> the facts, every number the prose may use
    instructions: str                                 # the writer's instructions; the FACTS block follows
    template: Callable[[dict, list[Fact]], str]       # (seed, facts) -> the same section with no model
    action: Callable[[dict, list[Fact], str], dict]   # (seed, facts, verified_text) -> what approving does
    severity: Callable[[dict, list[Fact]], str | None]
    title: Callable[[dict, list[Fact]], str]
    subtitle: Callable[[dict, list[Fact]], str] = lambda seed, fs: ""
    sources: Callable[[dict, list[Fact]], list[dict]] | None = None
    empty_text: str = "Nothing needed attention."
    noun: str = "item"                                # for the progress line: page, alert, brief, note
    one_liner: str = ""                               # what it does, one plain sentence
    cadence: str = ""                                 # when it runs, one plain sentence
    steps: list[tuple[str, str]] = field(default_factory=list)      # (one-word title, a short line) in order; the last two are Check and Approve
    section_titles: list[str] = field(default_factory=list)         # the page body's paragraphs are read under these
    summarize: Callable[[dict, list[Fact]], str] = lambda seed, fs: ""  # (seed, facts) -> one plain sentence for a list row


AGENTS: dict[str, AgentDef] = {}


def register(a: AgentDef) -> AgentDef:
    AGENTS[a.key] = a
    return a


class Unverified(Exception):
    """An edit carried a number no fact supports; the item stays a draft."""

    def __init__(self, flagged: list[dict]):
        super().__init__("unverified")
        self.flagged = flagged


def _now() -> str:
    """Milliseconds: two runs inside one second (the job, the tests) must still order, since the newest version of a page wins."""
    return datetime.now().isoformat(timespec="milliseconds")


def _q(s) -> str:
    """A SQL string literal. Spark SQL literals process backslash escapes (a JSON "\\n" would land as a newline and "\\"" as a
    quote, which broke every saved run on Oct 15, 2026); DuckDB's do not, so the doubling is Databricks-only."""
    s = str(s).replace("'", "''")
    if db.is_databricks():
        s = s.replace("\\", "\\\\")
    return "'" + s + "'"


# ---------------------------------------------------------------- words the templates share
MONTH_NAMES = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"]


def money(x) -> str:
    """$4.29M, $330K, $412: the same display rounding the verifier matches at."""
    if x is None or (isinstance(x, float) and pd.isna(x)):
        return "n/a"
    v = abs(float(x))
    s = "-" if float(x) < 0 else ""
    if v >= 1e6:
        return f"{s}${v / 1e6:.2f}M"
    if v >= 1e3:
        return f"{s}${v / 1e3:.0f}K"
    return f"{s}${v:,.0f}"


def num(x, digits: int = 1) -> str:
    return "n/a" if x is None or pd.isna(x) else f"{float(x):.{digits}f}"


def month_label(ym: str) -> str:
    return f"{MONTH_NAMES[int(ym[5:7]) - 1]} {ym[:4]}"


def prior_year(ym: str) -> str:
    return f"{int(ym[:4]) - 1}-{ym[5:7]}"


def latest_month() -> str:
    from harness.summary import months
    return months()[0]


def row(df: pd.DataFrame) -> dict:
    """The first row as plain Python values (NaN as None); {} when the frame is empty."""
    if df is None or df.empty:
        return {}
    return {k: (None if (isinstance(v, float) and pd.isna(v)) else (v.item() if hasattr(v, "item") else v)) for k, v in df.iloc[0].to_dict().items()}


# ---------------------------------------------------------------- the writer
_writers: dict[str, object] = {}


def thinker_backend() -> str:
    from harness.agent import model_backend
    return (os.environ.get("FAIRSHARE_THINKER") or model_backend()).lower()


def writer_name() -> str:
    b = thinker_backend()
    if b == "foundry":
        return "foundry"   # the agent and its version once it has answered (harness/foundry.py)
    if b == "azure":
        return f"azure/{os.environ.get('AZURE_OPENAI_DEPLOYMENT', '')}"
    if b == "databricks":
        return f"databricks/{os.environ.get('DATABRICKS_MODEL', 'databricks-qwen3-next-80b-a3b-instruct')}"
    if b == "openai":
        return f"openai/{os.environ.get('OPENAI_MODEL', 'gpt-4.1-mini')}"
    return "template"


def make_writer(a: "AgentDef"):
    """A tool-less agent on the thinking backend: it sees the FACTS block and nothing else. None when no model is configured.
    On the foundry backend it is the Foundry agent of the same name, whose instructions a sync pushed from this registry."""
    if thinker_backend() == "none":
        return None
    if thinker_backend() == "foundry":
        from harness.foundry import FoundryWriter
        return FoundryWriter(a.key)
    instructions = writer_instructions(a)
    if instructions not in _writers:
        from agent_framework import Agent
        from harness.agent import make_client
        client = make_client(thinker_backend())
        if client is None:
            return None
        _writers[instructions] = Agent(client, instructions=instructions, name="fairshare-delegate-writer")
    return _writers[instructions]


USD_COLS = ("revenue", "usd", "dollars", "amount", "effect", "goal", "commitment", "delta_revenue", "market_now", "market_prior", "ytd")


def _display(df: pd.DataFrame) -> pd.DataFrame:
    """Money columns as $1,234 (the model copies what it sees), other floats trimmed, empty cells blank."""
    out = _clean(df.copy())
    for c in out.columns:
        name = str(c).lower()
        if pd.api.types.is_numeric_dtype(out[c]) and not pd.api.types.is_bool_dtype(out[c]):
            if any(h in name for h in USD_COLS) and "pct" not in name and "pts" not in name:
                out[c] = out[c].map(lambda v: "" if pd.isna(v) else (f"-${abs(v):,.0f}" if v < 0 else f"${v:,.0f}"))
            else:
                out[c] = out[c].map(lambda v: "" if pd.isna(v) else (f"{v:g}" if isinstance(v, float) else str(v)))
        else:
            out[c] = out[c].map(lambda v: "" if (v is None or (isinstance(v, float) and pd.isna(v))) else str(v))
    return out


FACTS_RULES = ("The user message is a FACTS block and nothing else: every frame as a table, every public source numbered. Quote numbers exactly as "
               "shown, same rounding. Columns ending in _pct are percentages (write them with %), columns ending in _pts are points (write 'points'), "
               "dollar amounts carry a $ (you may shorten $330,114 to $330K and $4,290,000 to $4.29M). A blank cell is a fact that is not available: "
               "do not mention it and never write NA or NaN. Sources are public pages: quote them word for word and cite the number in brackets.")


def writer_instructions(a: "AgentDef") -> str:
    """What the writer is told, in the system turn: the agent's own instructions and the rules for reading the FACTS block. The
    message itself carries data only; rule sentences inside it read as a jailbreak to Foundry's prompt shield (two legitimate
    pages were refused on Oct 15, 2026)."""
    return f"{a.instructions}\n\n{FACTS_RULES}"


def facts_text(item: Item) -> str:
    """The FACTS block for one item: every frame as a table, every source numbered, nothing else (the rules are in writer_instructions)."""
    def table(df: pd.DataFrame) -> str:
        return _display(df).to_string(index=False) if not df.empty else "(none)"
    parts = [f"FACTS for {item.title}" + (f" ({item.subtitle})" if item.subtitle else "") + ".\n"]
    for f in item.facts:
        parts.append(f"{f.label}:\n{table(f.df)}" + (f"\nNote: {f.note}" if f.note else ""))
    if item.sources:
        parts.append("SOURCES:\n" + "\n".join(
            f"[{i}] {s.get('title', '')}" + (f" ({s['published']})" if s.get("published") else "") + f" {s.get('url', '')}\n    \"{s.get('snippet', '')}\""
            for i, s in enumerate(item.sources, 1)))
    return "\n\n".join(parts)


def verify_item(item: Item, text: str) -> None:
    from harness.agent import _clean as clean_text
    text = prettify(clean_text(text))
    v = verify(text, item.pool())
    item.draft, item.verified_text, item.flagged, item.badges = text, v.verified_text, v.flagged, v.badges()


# ---------------------------------------------------------------- runs
def new_run(key: str, scope: dict, requested_by: str, mode: str = "guarded") -> Run:
    return Run(run_id=uuid.uuid4().hex[:12], agent=key, scope=dict(scope), requested_by=requested_by,
               model="template" if mode == "template" else writer_name(), created_at=_now())


def progress_text(run: Run) -> str:
    a = AGENTS.get(run.agent)
    noun = a.noun if a else "item"
    done, total = run.progress.get("done", 0), run.progress.get("total", 0)
    if run.status == "running":
        return f"Writing {noun} {min(done + 1, total)} of {total}." if total else "Starting."
    if run.status == "failed":
        return "The run failed."
    if not run.items:
        return a.empty_text if a else "Nothing needed attention."
    drafts = sum(1 for i in run.items if i.status == "draft")
    return f"{drafts} of {len(run.items)} waiting for a decision." if drafts else "Every item has a decision."


async def run_async(key: str, scope: dict, requested_by: str, mode: str = "guarded", run: Run | None = None) -> Run:
    """Facts, prose and the check for every item the agent plans, on the caller's loop and in the caller's context (the
    viewer's token inside the App). Items are appended as they finish, so a poller sees the run grow. A block that raises
    ends the run as failed with the error text and keeps the items already written."""
    a = AGENTS[key]
    run = run or new_run(key, scope, requested_by, mode)
    writer = None if mode == "template" else make_writer(a)
    run.model = writer_name() if writer else "template"
    def provisional_title(seed: dict) -> str:
        try:
            return a.title(seed, [])
        except Exception:
            return str(seed.get("agency_name") or seed.get("market") or seed.get("opp_name") or "")

    try:
        seeds = await asyncio.to_thread(a.plan, scope)
        run.progress = {"done": 0, "total": len(seeds), "text": "", "phase": "facts", "item": None}
        run.progress["text"] = progress_text(run)
        for i, seed in enumerate(seeds, 1):
            run.progress.update(phase="facts", item=provisional_title(seed))
            fs = await asyncio.to_thread(a.facts, scope, seed)
            item = Item(item_id=uuid.uuid4().hex[:8], kind=a.kind, title=a.title(seed, fs), subtitle=a.subtitle(seed, fs), severity=a.severity(seed, fs),
                        facts=fs, sources=a.sources(seed, fs) if a.sources else [], seed=seed, summary=a.summarize(seed, fs), titles=list(a.section_titles))
            run.progress.update(phase="draft", item=item.title)
            if writer is None:
                text = a.template(seed, fs)
            else:
                resp = await writer.run(facts_text(item))
                text = resp.text or ""
                run.model = getattr(writer, "label", run.model)
                if getattr(resp, "blocked", None):
                    text = a.template(seed, fs) + f"\n\nCould not verify: Foundry's guardrail refused these facts ({resp.blocked}), so the template wrote this page without a model."
            run.progress["phase"] = "check"
            verify_item(item, text)
            item.action = a.action(seed, fs, item.verified_text)
            run.items.append(item)
            run.progress["done"] = i
            run.progress["text"] = progress_text(run)
    except Exception as e:  # one bad block ends the run honestly; what was written stays
        run.error = f"{type(e).__name__}: {str(e)[:300]}"
    run.progress.update(phase="done", item=None)
    try:
        await asyncio.to_thread(supersede, run)   # before the run reads as finished, so a poller that sees it done sees the pages right
    except Exception as e:  # the new pages stand; the older versions keep waiting and the log says why
        print(f"supersede after run {run.run_id}: {type(e).__name__}: {str(e)[:200]}")
    run.finished_at = _now()
    run.progress["text"] = progress_text(run)
    await asyncio.to_thread(save, run)
    return run


def run(key: str, scope: dict, requested_by: str, mode: str = "guarded") -> Run:
    """The sync path for the job and the tests."""
    return aio.run(run_async(key, scope, requested_by, mode))


# ---------------------------------------------------------------- decisions
def _approve(run: Run, item: Item, text: str | None, by: str) -> None:
    """The decision itself, not yet saved: an edit goes through the same checker against the same facts; the CRM row is written once."""
    text = (text or "").strip()
    if text and text not in (item.draft, item.verified_text):
        v = verify(text, item.pool())
        if v.flagged:
            raise Unverified(v.flagged)
        item.draft, item.verified_text, item.flagged, item.badges = text, v.verified_text, v.flagged, v.badges()
        if run.agent in AGENTS:
            item.action = AGENTS[run.agent].action(item.seed, item.facts, item.verified_text)
    crm = (item.action or {}).get("crm")
    if crm:
        crm_write(int(crm["agency_id"]), crm["activity_type"], crm["subject"], item.verified_text, by, run.run_id, item.item_id)
    item.status, item.decided_at, item.decided_by = "approved", _now(), by


def _reject(item: Item, by: str) -> None:
    item.status, item.decided_at, item.decided_by = "rejected", _now(), by


def approve(run: Run, item_id: str, text: str | None, by: str) -> Item:
    """One decision, saved; a page already decided keeps its decision."""
    item = run.item(item_id)
    if item.status == "draft":
        _approve(run, item, text, by)
        save(run)
    return item


def reject(run: Run, item_id: str, by: str) -> Item:
    item = run.item(item_id)
    if item.status == "draft":
        _reject(item, by)
        save(run)
    return item


def decide(run: Run, item_ids: list[str], by: str, approve: bool) -> list[Item]:
    """Several decisions on one run, saved once. Pages already decided keep their decision; an unknown id raises KeyError
    before anything is written. No edits here: an edit is a decision on one page."""
    items = [run.item(i) for i in item_ids]
    for item in items:
        if item.status == "draft":
            _approve(run, item, None, by) if approve else _reject(item, by)
    save(run)
    return items


def supersede(run: Run) -> int:
    """A page is one agent and one title (an agency, a clause, a market, a deal). Once a run has written it again, the older
    version still waiting is retired: the numbers may have moved, so every refresh needs a fresh approval. Decided versions
    stay as history. Returns how many drafts were retired."""
    titles = {i.title for i in run.items}
    n = 0
    if not titles:
        return 0
    for h in _rows(f"SELECT run_id FROM {db.AGENT_RUNS} WHERE agent = {_q(run.agent)} AND status = 'needs_approval' AND run_id <> {_q(run.run_id)}"):
        old = load(h["run_id"])
        hits = [i for i in old.items if i.status == "draft" and i.title in titles] if old else []
        for i in hits:
            i.status = "superseded"
        if hits:
            n += len(hits)
            save(old)
    return n


def pages(runs: list[Run]) -> dict[str, list[dict]]:
    """Every page the agents have written, by agent: one entry per title with its newest version on top and every earlier
    version as history. The pages still waiting for a decision come first, then the rest, newest first."""
    by: dict[tuple[str, str], list[tuple[Run, Item]]] = {}
    for r in sorted(runs, key=lambda r: r.created_at, reverse=True):
        for i in r.items:
            by.setdefault((r.agent, i.title), []).append((r, i))
    out: dict[str, list[dict]] = {}
    for (agent, _), versions in by.items():
        r, i = versions[0]
        out.setdefault(agent, []).append({**i.head(), "run_id": r.run_id, "created_at": r.created_at, "scope": r.scope,
                                          "versions": [{"run_id": vr.run_id, "item_id": vi.item_id, "created_at": vr.created_at, "scope": vr.scope,
                                                        "status": "superseded" if k and vi.status == "draft" else vi.status,   # an older draft is replaced, whatever the row says
                                                        "decided_at": vi.decided_at, "decided_by": vi.decided_by} for k, (vr, vi) in enumerate(versions)]})
    for lst in out.values():
        lst.sort(key=lambda p: p["status"] != "draft")   # already newest first; the sort is stable
    return out


def crm_write(agency_id: int, activity_type: str, subject: str, notes: str, by: str, run_id: str, item_id: str) -> str:
    """One activity in the CRM stand-in per approved item: a second approval of the same item replaces, never duplicates."""
    t = db.CRM_ACTIVITIES
    activity_id = uuid.uuid4().hex[:12]
    db.state_execute([
        f"""CREATE TABLE IF NOT EXISTS {t} (activity_id STRING, agency_id INT, activity_type STRING, subject STRING, happened_at STRING,
            owner STRING, notes STRING, run_id STRING, item_id STRING)""",
        f"DELETE FROM {t} WHERE run_id = {_q(run_id)} AND item_id = {_q(item_id)}",
        f"INSERT INTO {t} VALUES ({_q(activity_id)}, {int(agency_id)}, {_q(activity_type)}, {_q(subject)}, {_q(_now())}, {_q(by)}, {_q(notes)}, {_q(run_id)}, {_q(item_id)})"])
    return activity_id


# ---------------------------------------------------------------- persistence
def save(run: Run) -> None:
    t = db.AGENT_RUNS
    payload = json.dumps({"progress": run.progress, "items": [i.to_json() for i in run.items]}, default=str)
    db.state_execute([
        f"""CREATE TABLE IF NOT EXISTS {t} (run_id STRING, agent STRING, scope_json STRING, status STRING, requested_by STRING, model STRING,
            created_at STRING, finished_at STRING, error STRING, payload_json STRING)""",
        f"DELETE FROM {t} WHERE run_id = {_q(run.run_id)}",
        f"INSERT INTO {t} VALUES (" + ", ".join([_q(run.run_id), _q(run.agent), _q(json.dumps(run.scope)), _q(run.status), _q(run.requested_by), _q(run.model),
                                                _q(run.created_at), "NULL" if run.finished_at is None else _q(run.finished_at),
                                                "NULL" if run.error is None else _q(run.error), _q(payload)]) + ")"])


def _from_row(row: dict) -> Run:
    try:
        payload = json.loads(row.get("payload_json") or "{}")
    except ValueError:  # a row saved before the literal escaping fix: unreadable, shown as failed rather than breaking the list
        payload = {"items": [], "progress": {"done": 0, "total": 0, "text": "The saved run could not be read."}}
        row = {**row, "error": row.get("error") or "ValueError: the saved run could not be read"}
    run = Run(run_id=row["run_id"], agent=row["agent"], scope=json.loads(row.get("scope_json") or "{}"), requested_by=row.get("requested_by") or "",
              model=row.get("model") or "", created_at=row.get("created_at") or "", finished_at=row.get("finished_at") or None,
              items=[Item.from_json(i) for i in payload.get("items", [])], progress=payload.get("progress") or {"done": 0, "total": 0, "text": ""},
              error=row.get("error") or None)
    a = AGENTS.get(run.agent)
    if a:  # runs saved by an earlier version get today's titles and summaries from their stored facts
        for item in run.items:
            if not item.titles:
                item.titles = list(a.section_titles)
            try:
                if item.seed:
                    item.title = a.title(item.seed, item.facts)
                if not item.summary:
                    item.summary = a.summarize(item.seed, item.facts)
            except Exception:
                pass
    return run


def _rows(sql: str) -> list[dict]:
    try:
        df = db.state_query(sql)
    except Exception:
        return []
    return [{k: (None if pd.isna(v) else v) for k, v in r.items()} for r in df.to_dict("records")] if not df.empty else []


def load(run_id: str) -> Run | None:
    if not re.fullmatch(r"[0-9a-f]{12}", str(run_id)):
        return None
    rows = _rows(f"SELECT * FROM {db.AGENT_RUNS} WHERE run_id = '{run_id}'")
    return _from_row(rows[0]) if rows else None


def load_runs(limit: int = 20) -> list[Run]:
    """The newest runs, whole: the catalog groups their items into pages."""
    return [_from_row(r) for r in _rows(f"SELECT * FROM {db.AGENT_RUNS} ORDER BY created_at DESC LIMIT {int(limit)}")]


def list_runs(limit: int = 20) -> list[dict]:
    return [r.header() for r in load_runs(limit)]
