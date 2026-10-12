"""Shared bits for the Streamlit pages: paths, the cached agent, formatting, the 'how I got this' drawer."""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from fairshare import db  # noqa: E402
from harness import agent as harness_agent  # noqa: E402

CACHE = ROOT / "app" / "cache"
MONTHS = [f"2026-{m:02d}" for m in range(1, 10)]


def setup(title: str):
    st.set_page_config(page_title=f"fairshare | {title}", page_icon="✈", layout="wide")
    st.markdown("""<style>
        .badge{display:inline-block;padding:2px 8px;border-radius:10px;font-size:0.8rem;margin-right:6px}
        .ok{background:#e4f3e8;color:#1e6b36}.bad{background:#fdecec;color:#a12626}.muted{color:#6b7280}
        .sent{line-height:1.7}.flag{border-left:3px solid #c0392b;background:#fff5f5;padding:8px 12px;margin:6px 0}
        .verified{border-left:3px solid #1e6b36;background:#f3faf5;padding:8px 12px;margin:6px 0}
        </style>""", unsafe_allow_html=True)
    with st.sidebar:
        st.markdown(f"**Data:** `{db.backend()}`  \n**Model:** `{harness_agent.model_backend()}`")
        if db.backend() == "duckdb":
            st.caption("Offline mode: local DuckDB copy of the gold tables. Switch with FAIRSHARE_BACKEND=databricks.")


@st.cache_resource(show_spinner=False)
def get_agent():
    try:
        return harness_agent.make_agent()
    except Exception as e:  # missing env var and the like: the pages fall back to cached answers
        st.sidebar.warning(f"agent not available: {e}")
        return None


def esc(text: str) -> str:
    """Streamlit markdown treats $...$ as LaTeX; dollar signs in prose must be escaped."""
    return str(text).replace("$", "\\$")


def money(x, decimals=1) -> str:
    if x is None or pd.isna(x):
        return ""
    sign = "-" if x < 0 else ""
    x = abs(float(x))
    if x >= 1e6:
        return f"{sign}${x / 1e6:.{decimals}f}M"
    if x >= 1e3:
        return f"{sign}${x / 1e3:.0f}K"
    return f"{sign}${x:,.0f}"


def pct(x, decimals=1) -> str:
    return "" if x is None or pd.isna(x) else f"{float(x):.{decimals}f}%"


def badges_html(badges: list[dict]) -> str:
    parts = []
    for b in badges:
        cls = "ok" if b["status"] == "verified" else "bad"
        label = "verified" if b["status"] == "verified" else "flagged"
        parts.append(f'<div class="{ "verified" if cls == "ok" else "flag"}"><span class="badge {cls}">{label}</span>{b["sentence"]}</div>')
    return "".join(parts)


def drawer(calls, sources, title="How I got this"):
    with st.expander(title, expanded=False):
        if sources:
            st.markdown("**Sources:** " + ", ".join(f"`{s}`" for s in sources))
        for i, c in enumerate(calls, 1):
            st.markdown(f"**{i}. {c.tool}** `{json.dumps(c.arguments, default=str)[:160]}` {c.rows} rows" + (f"  \n{c.note}" if c.note else ""))
            if c.sql:
                st.code(c.sql, language="sql")
            if c.preview is not None and len(c.preview):
                st.dataframe(c.preview, hide_index=True, use_container_width=True)
        url = os.environ.get("MLFLOW_TRACES_URL")
        if url:
            st.markdown(f"[Open the trace in MLflow]({url})")


def load_cache(name: str):
    p = CACHE / name
    if p.exists():
        return json.loads(p.read_text())
    return None
