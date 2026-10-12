"""The harness: one Microsoft Agent Framework agent, four tools, three rules, a verifier on every answer.

Model backends (FAIRSHARE_MODEL=...):
  azure       a Foundry / Azure OpenAI deployment: AZURE_OPENAI_ENDPOINT, AZURE_OPENAI_API_KEY, AZURE_OPENAI_DEPLOYMENT, AZURE_OPENAI_API_VERSION
  databricks  a Databricks model serving endpoint through the OpenAI-compatible API: DATABRICKS_HOST, DATABRICKS_TOKEN, DATABRICKS_MODEL
  openai      any OpenAI-compatible endpoint: OPENAI_API_KEY, OPENAI_BASE_URL (optional), OPENAI_MODEL
  none        no model; the app shows cached answers and the template summary

The same code runs on the laptop (python -m harness.agent "question") and inside Foundry Hosted Agents (harness/foundry/host.py).
"""
from __future__ import annotations

import asyncio
import os
import sys
from dataclasses import dataclass, field

from dotenv import load_dotenv

from fairshare.db import ROOT, is_databricks
from harness import facts, tracing
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
Keep answers short: the number, the comparison, the source. No preamble.
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
        return OpenAIChatClient(model=os.environ["AZURE_OPENAI_DEPLOYMENT"], azure_endpoint=os.environ["AZURE_OPENAI_ENDPOINT"],
                                api_key=os.environ["AZURE_OPENAI_API_KEY"], api_version=os.environ.get("AZURE_OPENAI_API_VERSION", "2025-04-01-preview"))
    if b == "databricks":
        host = os.environ["DATABRICKS_HOST"].rstrip("/")
        return OpenAIChatClient(model=os.environ.get("DATABRICKS_MODEL", "databricks-gpt-5-mini"), base_url=f"{host}/serving-endpoints",
                                api_key=os.environ["DATABRICKS_TOKEN"])
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
    agent = agent or make_agent()
    if agent is None:
        raise RuntimeError("no model configured (FAIRSHARE_MODEL=none); use cached answers")
    facts.reset()
    resp = asyncio.run(agent.run(question))
    text = (resp.text or "").strip()
    ctx = facts.current()
    return Answer(question=question, text=text, verification=verify(text, ctx.pool), calls=ctx.calls, sources=ctx.sources,
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
