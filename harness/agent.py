"""The harness: one Microsoft Agent Framework agent, four tools, three rules, a verifier on every answer.

Model backends (FAIRSHARE_MODEL=...):
  azure       a Foundry / Azure OpenAI deployment: AZURE_OPENAI_ENDPOINT, AZURE_OPENAI_API_KEY, AZURE_OPENAI_DEPLOYMENT, AZURE_OPENAI_API_VERSION
  databricks  a Databricks model serving endpoint through the OpenAI-compatible API: DATABRICKS_HOST, DATABRICKS_MODEL (auth as fairshare/dbx.py)
  openai      any OpenAI-compatible endpoint: OPENAI_API_KEY, OPENAI_BASE_URL (optional), OPENAI_MODEL
  none        no model; the app shows cached answers and the template summary

The same code runs on the laptop (python -m harness.agent "question"), inside Foundry Hosted Agents (harness/foundry/host.py)
and inside a Databricks App (app.yaml, lakehouse/app_deploy.py), where the model is a Databricks serving endpoint because Free Edition
apps cannot reach Foundry.
"""
from __future__ import annotations

import re
import os
import sys
import time
from dataclasses import dataclass, field
from functools import lru_cache

from dotenv import load_dotenv

from fairshare.db import ROOT, is_databricks
from harness import aio, facts, tracing
from harness.tools import PHASE_TEXT, SCHEMA_NOTE, ask_metrics, explain_change, run_sql, search_contracts
from harness.verifier import Verification, verify

load_dotenv(ROOT / ".env")

INSTRUCTIONS = """You are the sales analytics agent for an airline's indirect sales team (agencies and corporate accounts).
Account managers and agencies ask you about revenue, AA share, fair share, share gap, year over year, pace against goal,
and what an agency's agreement says. Your audience checks your numbers against Power BI, so:

Three rules, never broken:
1. Every number you state comes from a tool result in this conversation, copied exactly (same rounding; you may add $ and %
   and abbreviate thousands as K and millions as M). Never compute, estimate, or extrapolate. If a derived number is needed,
   get it from a tool as a column (run_sql can compute it).
2. Say which query answered: name the tool and the tables (the app attaches the SQL).
3. Anything the tools did not return goes in a final line starting "Could not verify:" and you say what data would be needed.
   Unknown is an allowed answer. If asked for a prediction (churn, forecast) and there is no model or label in the data,
   say so and offer the nearest thing you can compute, labeled "a proxy, not a prediction".

Which tool:
- Numbers (revenue, share, fair share, gap, YoY, passengers, pace): ask_metrics first. If it says Genie is unavailable or fails, run_sql.
- "Why did X change / why is X down": explain_change (deterministic decomposition). Report volume, mix, share, and the fair-share diagnostic,
  state that the parts sum to the total, and name the markets that moved most.
- Contract terms: search_contracts. Quote the clause with file and page.
Keep answers short: the number, the comparison, the source. No preamble. Plain punctuation (commas, colons, periods); no em dashes, no bullet lists unless asked.
Never paste SQL, column names or raw tool output into the answer: the app attaches the query and the table. Name the source in a few words.
When you offer a proxy, describe its rule in words ("revenue down by more than a tenth year over year and behind pace"), not as a formula with numbers.
Year over year from the metric view is only valid when the query groups by sales_month; for a quarter or a year, compare the two periods' revenue explicitly.
Earlier turns of the conversation are context only: a number from an earlier answer must be queried again before you state it.
""" + "\n" + SCHEMA_NOTE


@dataclass
class Answer:
    question: str
    text: str
    verification: Verification
    calls: list = field(default_factory=list)
    sources: list = field(default_factory=list)
    model: str = ""
    genie_conversation_id: str | None = None
    elapsed_ms: int = 0

    @property
    def flagged(self):
        return self.verification.flagged


def model_backend() -> str:
    return os.environ.get("FAIRSHARE_MODEL", "none").lower()


def make_client():
    """Returns an Agent Framework chat client for the configured backend, or None."""
    from agent_framework.openai import OpenAIChatClient
    b = model_backend()
    if b == "azure":
        endpoint = os.environ["AZURE_OPENAI_ENDPOINT"].rstrip("/")
        if endpoint.endswith("/openai/v1"):
            # Foundry's v1 surface is OpenAI-compatible and takes the key as a bearer token; no api-version (the dated
            # api-version path answered "API version not supported" on Oct 11, 2026).
            return OpenAIChatClient(model=os.environ["AZURE_OPENAI_DEPLOYMENT"], base_url=endpoint, api_key=os.environ["AZURE_OPENAI_API_KEY"])
        return OpenAIChatClient(model=os.environ["AZURE_OPENAI_DEPLOYMENT"], azure_endpoint=re.sub(r"/openai/?$", "", endpoint),
                                api_key=os.environ["AZURE_OPENAI_API_KEY"], api_version=os.environ.get("AZURE_OPENAI_API_VERSION", "2025-04-01-preview"))
    if b == "databricks":
        from agent_framework.openai import OpenAIChatCompletionClient
        from fairshare.dbx import bearer_token, host
        # pay-per-token Foundation Model API through chat completions (OpenAIChatClient speaks the Responses API, which Databricks
        # answers "passthrough is not supported" for every Free Edition model, Oct 13, 2026). Qwen3-Next instruct: plain content and
        # real tool calls; the reasoning models (gpt-oss, qwen3.5) return content as reasoning+text parts the framework drops, and
        # Llama 4 Maverick pasted a run_sql call as text instead of calling it. The token is the user's, inside the App the viewer's.
        # api_key is the function, not its value: the OpenAI client calls it on every request, so one client serves every
        # viewer and each call carries the token bound to the current request (fairshare/dbx.py).
        return OpenAIChatCompletionClient(model=os.environ.get("DATABRICKS_MODEL", "databricks-qwen3-next-80b-a3b-instruct"), base_url=f"{host()}/serving-endpoints",
                                          api_key=bearer_token)
    if b == "openai":
        return OpenAIChatClient(model=os.environ.get("OPENAI_MODEL", "gpt-4.1-mini"), api_key=os.environ["OPENAI_API_KEY"],
                                base_url=os.environ.get("OPENAI_BASE_URL"))
    return None


def make_agent():
    from agent_framework import Agent
    client = make_client()
    if client is None:
        return None
    tracing.setup()
    tools = [ask_metrics, run_sql, explain_change, search_contracts]
    return Agent(client, instructions=INSTRUCTIONS, name="fairshare-sales-agent", tools=tools,
                 description="Answers agency and corporate sales performance questions with the number, the SQL, and the source.")


@lru_cache(maxsize=1)
def get_agent():
    """The one agent for the process: the client reads the viewer's token per request, so nothing in it is per viewer."""
    return make_agent()


def ask(question: str, agent=None) -> Answer:
    """One question from the command line, the benchmark or the cache: a fresh run context, then the async path on the
    process loop. The server calls ask_async itself on its own loop with the request's context already set up."""
    facts.reset()
    if tracing.setup():
        import mlflow
        with mlflow.start_span(name="fairshare.ask") as sp:
            sp.set_inputs({"question": question})
            a = aio.run(ask_async(question, agent))
            sp.set_outputs({"answer": a.text, "verified": a.verification.ok, "tools": [c.tool for c in a.calls]})
            return a
    return aio.run(ask_async(question, agent))


PASTED_CALL = re.compile(r'(\{\s*"name"\s*:\s*"(ask_metrics|run_sql|explain_change|search_contracts)"|\b(ask_metrics|run_sql|explain_change|search_contracts)\s*\()')


def _clean(text: str) -> str:
    return (text or "").strip().replace(" \u2014 ", ", ").replace("\u2014", ", ").replace(" \u2013 ", ", ")


async def ask_async(question: str, agent=None, *, history=()) -> Answer:
    """One question on the caller's event loop, in the caller's run context (the server sets one up per request with the
    viewer's token, the progress listener and the thread's Genie conversation). history is the browser's earlier turns,
    [{"role": "user"|"assistant", "text": ...}], passed as prior messages."""
    from agent_framework import Message
    agent = agent or get_agent()
    if agent is None:
        raise RuntimeError("no model configured (FAIRSHARE_MODEL=none); use cached answers")
    ctx = facts.current()
    t0 = time.monotonic()
    prior = [Message(h["role"], [h["text"]]) for h in history if h.get("text")]

    async def run(q: str) -> str:
        resp = await agent.run(prior + [Message("user", [q])])
        return _clean(resp.text)

    text = await run(question)
    if PASTED_CALL.search(text):
        # open models (Llama 4 Maverick, Qwen3-Next; Oct 13, 2026) sometimes write the tool call as text instead of making it:
        # one retry with the instruction made explicit, then an honest refusal rather than a pasted query on screen
        ctx.clear()
        text = await run(question + "\n\nCall the tool; do not write the call out as text.")
        if PASTED_CALL.search(text):
            text = "Could not verify: the model wrote a query instead of running it. Ask again, or use the laptop model."
    if not text:
        text = "Could not verify: the model returned no answer text."
    ctx.emit("status", phase="verify", text=PHASE_TEXT["verify"])
    return Answer(question=question, text=text, verification=verify(text, ctx.pool, question), calls=ctx.calls, sources=ctx.sources,
                  model=model_backend() + ("/databricks" if is_databricks() else "/duckdb"),
                  genie_conversation_id=ctx.genie_conversation_id, elapsed_ms=int((time.monotonic() - t0) * 1000))


def main(argv):
    q = " ".join(argv) or "How did Summit Travel Partners do on DFW to ORD in 2026 so far versus 2025, and are they ahead of fair share?"
    a = ask(q)
    print(a.text)
    print("\n-- verification:", "clean" if a.verification.ok else a.flagged)
    print("-- tools:", [(c.tool, c.rows) for c in a.calls])
    print("-- sources:", a.sources)


if __name__ == "__main__":
    main(sys.argv[1:])
