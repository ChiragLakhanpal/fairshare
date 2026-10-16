"""The Delegate writers as agents the Foundry project owns (Build > Agents in the portal).

One Foundry prompt agent per Delegate agent: the same instructions, the gpt-5-mini deployment, and the account's content
filter policy as its guardrail. The App calls it through the project's Responses API with an agent reference and the
project key: the FACTS block goes in, the page comes back, and the verifier checks every number exactly as before. The
instructions stay in the harness (one place) and `lakehouse/foundry.py sync` pushes them as a new version when they change.
"""
import asyncio
import hashlib
import json
import os
import urllib.error
import urllib.request
from types import SimpleNamespace

API = "2025-11-15-preview"
NAMES = {"precall": "fairshare-precall-pack", "watch": "fairshare-agreement-watch", "prospect": "fairshare-prospect-research", "mismatch": "fairshare-crm-vs-reality"}


def endpoint() -> str:
    return os.environ["FOUNDRY_PROJECT_ENDPOINT"].rstrip("/")


def call(method: str, path: str, body: dict | None = None, token: str | None = None, timeout: int = 180) -> dict:
    """One request to the project. The key travels in the api-key header; a signed-in person's token as a bearer (the
    evaluation API wants an identity, which a key is not). Errors carry the status and the service's message."""
    url = f"{endpoint()}{path}{'&' if '?' in path else '?'}api-version={API}"
    headers = {"Content-Type": "application/json"}
    headers.update({"Authorization": f"Bearer {token}"} if token else {"api-key": os.environ["AZURE_OPENAI_API_KEY"]})
    req = urllib.request.Request(url, data=json.dumps(body).encode() if body is not None else None, method=method, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read() or b"{}")
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"{method} {path}: {e.code} {e.read().decode(errors='replace')[:2000]}") from None  # long enough for a content filter verdict


def definition(a) -> dict:
    """The prompt agent a Delegate agent becomes: its instructions, the deployment, the guardrail policy when one is named
    (FOUNDRY_RAI_POLICY, the content filter policy's full resource id; the service refuses a bare name)."""
    from harness.agents import writer_instructions
    d = {"kind": "prompt", "model": os.environ.get("AZURE_OPENAI_DEPLOYMENT", "gpt-5-mini"), "instructions": writer_instructions(a)}
    policy = os.environ.get("FOUNDRY_RAI_POLICY", "").strip()
    if policy:
        d["rai_config"] = {"rai_policy_name": policy}
    return d


def same(current: dict | None, wanted: dict) -> bool:
    """Whether the version Foundry has already says what we want (the service adds fields of its own; only ours count)."""
    if not current:
        return False
    policy = lambda d: (d.get("rai_config") or {}).get("rai_policy_name")
    return all(current.get(k) == wanted[k] for k in ("kind", "model", "instructions")) and policy(current) == policy(wanted)


def latest(name: str) -> dict | None:
    """The newest version of a named agent, None when the agent does not exist yet."""
    try:
        data = call("GET", f"/agents/{name}/versions").get("data", [])
    except RuntimeError as e:
        if ": 404 " in str(e):
            return None
        raise
    return max(data, key=lambda v: int(v["version"])) if data else None


def sync(registry: dict) -> list[str]:
    """A new version for every agent whose instructions or guardrail changed, nothing for the rest; one line per agent."""
    out = []
    for key, a in registry.items():
        name, wanted = NAMES[key], definition(a)
        have = latest(name)
        if have and same(have.get("definition"), wanted):
            out.append(f"unchanged {name}:{have['version']}")
            continue
        v = call("POST", f"/agents/{name}/versions", {"definition": wanted, "description": a.one_liner or a.summary,
                                                      "metadata": {"source": "fairshare harness", "instructions_sha": hashlib.sha256(wanted["instructions"].encode()).hexdigest()[:12]}})
        out.append(f"{'updated' if have else 'created'} {name}:{v['version']}")
    return out


def respond(name: str, text: str) -> SimpleNamespace:
    """One call to the named agent: the text it wrote, and which version answered."""
    r = call("POST", "/openai/responses", {"agent": {"name": name, "type": "agent_reference"}, "input": text})
    out = "".join(c.get("text", "") for o in r.get("output", []) if o.get("type") == "message" for c in o.get("content", []) if c.get("type") == "output_text")
    return SimpleNamespace(text=out, version=str((r.get("agent") or {}).get("version") or ""), id=r.get("id"))


class FoundryWriter:
    """What run_async awaits in place of the local writer agent: the same .run(text) with a .text on what comes back.
    The label names the agent and, once it has answered, the version, so a run records exactly who wrote it."""

    def __init__(self, key: str):
        self.name = NAMES[key]
        self.label = f"foundry/{self.name}"

    async def run(self, text: str) -> SimpleNamespace:
        try:
            r = await asyncio.to_thread(respond, self.name, text)
        except RuntimeError as e:
            if '"code":"content_filter"' not in str(e):
                raise
            # the guardrail refused the input before the model ran: the run writes this page from the template instead (no model
            # reads the facts, so nothing planted in them can act) and says so in the page's note; the other pages go on
            return SimpleNamespace(text="", version="", id=None, blocked=blocked_by(str(e)))
        if r.version:
            self.label = f"foundry/{self.name}:{r.version}"
        return r


def blocked_by(message: str) -> str:
    """The filters that fired, from the service's error text: 'jailbreak, indirect attack'."""
    import re
    names = re.findall(r'"(\w+)":\s*\{[^{}]*"filtered":\s*true', message)   # the verdict lists detected before filtered for some filters
    return ", ".join(dict.fromkeys(n.replace("_", " ") for n in names)) or "content filter"
