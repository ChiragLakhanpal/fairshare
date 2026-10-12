"""Foundry Hosted Agents entry point: the same agent, served over the Responses protocol.

Local check:   .venv/bin/python -m harness.foundry.host   (serves on :8088; POST /responses)
Deploy:        see harness/foundry/README.md (azd ai agent init / provision / deploy)

Foundry Hosted Agents is GA; the Python hosting package is prerelease (pip install --pre agent-framework-foundry-hosting),
and in agent-framework 1.21 ResponsesHostServer already ships in agent_framework.foundry.
"""
import os

from agent_framework.foundry import ResponsesHostServer

from harness.agent import make_agent


def build():
    agent = make_agent()
    if agent is None:
        raise SystemExit("set FAIRSHARE_MODEL (azure) and the AZURE_OPENAI_* variables before hosting")
    return agent


if __name__ == "__main__":
    ResponsesHostServer(build).run(port=int(os.environ.get("PORT", "8088")))
