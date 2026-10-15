"""Public sources for prospect research: what the open web says about a route.

  sources(market)                      the provider's results for a market: [{title, url, published, snippet}]
  python -m harness.research fetch CLT-LGA [query]   search now and write the cache file

Providers (FAIRSHARE_SEARCH): `cached` (the default) reads data/research/<market>.json, written once with the sources'
URLs and a quoted snippet each, so the demo runs without a search key and every citation can be opened; `brave` calls
the Brave Search API with SEARCH_API_KEY. At an airline the live provider is Bing grounding through Foundry; the
interface is the same list. Research is about a real route, never a real company with fictional numbers attached
(CLAUDE.md rule 8).
"""
from __future__ import annotations

import json
import os
import re
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DIR = ROOT / "data" / "research"
MARKET = re.compile(r"^[A-Z]{3}-[A-Z]{3}$")


def provider() -> str:
    return os.environ.get("FAIRSHARE_SEARCH", "cached").lower()


def _file(market: str) -> Path:
    return DIR / f"{market}.json"


def cached(market: str) -> list[dict]:
    p = _file(market)
    if not MARKET.match(market or "") or not p.exists():
        return []
    return list(json.loads(p.read_text()).get("sources", []))


def brave(query: str, count: int = 8) -> list[dict]:
    """Brave Search's web endpoint: the free plan takes a key in a header; results carry a title, a URL, an age and a description."""
    import urllib.parse
    import urllib.request
    key = os.environ.get("SEARCH_API_KEY", "").strip()
    if not key:
        raise RuntimeError("SEARCH_API_KEY is not set; FAIRSHARE_SEARCH=brave needs it")
    url = "https://api.search.brave.com/res/v1/web/search?" + urllib.parse.urlencode({"q": query, "count": count})
    req = urllib.request.Request(url, headers={"X-Subscription-Token": key, "Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=20) as r:
        data = json.load(r)
    return [{"title": x.get("title", ""), "url": x.get("url", ""), "published": x.get("age") or x.get("page_age"), "snippet": re.sub(r"<[^>]+>", "", x.get("description", ""))}
            for x in (data.get("web") or {}).get("results", [])]


def default_query(market: str) -> str:
    o, d = market.split("-")
    return f"{o} {d} route airline capacity schedule news"


def sources(market: str, query: str | None = None) -> list[dict]:
    if provider() == "brave":
        return brave(query or default_query(market))
    return cached(market)


def fetch(market: str, query: str | None = None) -> Path:
    if not MARKET.match(market or ""):
        raise SystemExit("market looks like CLT-LGA")
    q = query or default_query(market)
    found = brave(q)
    DIR.mkdir(exist_ok=True)
    _file(market).write_text(json.dumps({"market": market, "query": q, "fetched_at": datetime.now().isoformat(timespec="minutes"), "provider": "brave", "sources": found}, indent=2))
    print(f"{_file(market).name}: {len(found)} sources")
    return _file(market)


if __name__ == "__main__":
    if len(sys.argv) >= 3 and sys.argv[1] == "fetch":
        fetch(sys.argv[2], " ".join(sys.argv[3:]) or None)
    else:
        raise SystemExit(__doc__)
