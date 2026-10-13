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
from dataclasses import dataclass, field

from dotenv import load_dotenv

from fairshare.db import ROOT, is_databricks
from harness import aio, facts, tracing
from harness.tools import SCHEMA_NOTE, ask_metrics, explain_change, run_sql, search_contracts
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
""" + "\n" + SCHEMA_NOTE


@dataclass
class Answer:
    question: str
    text: str
    verification: Verification
    calls: list = field(default_factory=list)
    sources: list = field(default_factory=list)
    model: str = ""

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
        # answers "passthrough is not supported" for gpt-oss, Oct 13, 2026). Llama 4 Maverick because the reasoning models (gpt-oss,
        # qwen3.5) return content as reasoning+text parts the framework drops. The token is the user's, inside the App the viewer's.
        return OpenAIChatCompletionClient(model=os.environ.get("DATABRICKS_MODEL", "databricks-llama-4-maverick"), base_url=f"{host()}/serving-endpoints",
                                          api_key=bearer_token())
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


def ask(question: str, agent=None) -> Answer:
    """One question through the harness: reset the run context, run the agent, verify the answer."""
    if tracing.setup():
        import mlflow
        with mlflow.start_span(name="fairshare.ask") as sp:
            sp.set_inputs({"question": question})
            a = _ask(question, agent)
            sp.set_outputs({"answer": a.text, "verified": a.verification.ok, "tools": [c.tool for c in a.calls]})
            return a
    return _ask(question, agent)


def _ask(question: str, agent=None) -> Answer:
    agent = agent or make_agent()
    if agent is None:
        raise RuntimeError("no model configured (FAIRSHARE_MODEL=none); use cached answers")
    facts.reset()
    resp = aio.run(agent.run(question))
    text = (resp.text or "").strip().replace(" \u2014 ", ", ").replace("\u2014", ", ").replace(" \u2013 ", ", ")
    ctx = facts.current()
    return Answer(question=question, text=text, verification=verify(text, ctx.pool, question), calls=ctx.calls, sources=ctx.sources,
                  model=model_backend() + ("/databricks" if is_databricks() else "/duckdb"))


def main(argv):
    q = " ".join(argv) or "How did Summit Travel Partners do on DFW to ORD in 2026 so far versus 2025, and are they ahead of fair share?"
    a = ask(q)
    print(a.text)
    print("\n-- verification:", "clean" if a.verification.ok else a.flagged)
    print("-- tools:", [(c.tool, c.rows) for c in a.calls])
    print("-- sources:", a.sources)


if __name__ == "__main__":
    main(sys.argv[1:])
