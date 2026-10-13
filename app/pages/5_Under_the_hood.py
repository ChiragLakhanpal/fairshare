import json
import os

import pandas as pd
import streamlit as st

from common import ROOT, setup

setup("Under the hood")
from fairshare import db  # noqa: E402

st.title("Under the hood")
st.caption("What Austin sees. Three layers, then one deeper only if asked.")

st.image(str(ROOT / "docs" / "architecture.svg"), use_container_width=True)

st.markdown("""
**Three sentences per layer.**
The data: files land in a Unity Catalog volume, bronze keeps them as landed, silver fixes types, channel labels and duplicate tickets, gold holds the facts and dimensions the business recognises.
The definitions: one metric view where AA share, fair share, share gap and year over year are written once; Power BI gets the same definitions as DAX and a nightly parity job proves they agree.
The agent: Genie for numbers, a deterministic decomposition for "why", the agreements for contract terms, a harness that picks the tool and a verifier that refuses to show a number no query returned.
""")

c1, c2, c3 = st.columns(3)
with c1:
    st.markdown("**Links**")
    for label, var in [("Databricks workspace", "DATABRICKS_HOST"), ("AI/BI dashboard (the Power BI stand-in)", "DASHBOARD_URL"), ("Genie Agent", "GENIE_SPACE_URL"),
                       ("This app inside Databricks", "DATABRICKS_APP_URL"), ("MLflow traces", "MLFLOW_TRACES_URL"),
                       ("Foundry project", "FOUNDRY_PROJECT_URL"), ("Repository", "REPO_URL")]:
        v = os.environ.get(var)
        st.markdown(f"- [{label}]({v})" if v else f"- {label}: not set (`{var}`)")
with c2:
    st.markdown("**Benchmark (Genie and the full harness)**")
    latest = ROOT / "evals" / "results" / "latest.json"
    if latest.exists():
        r = json.loads(latest.read_text())
        st.metric("Genie pass rate", f"{r.get('genie_pass_rate', 0) * 100:.0f}%", help=f"{r.get('n', 0)} questions with ground-truth SQL")
        st.metric("Harness: numbers supported", f"{r.get('harness_supported_rate', 0) * 100:.0f}%", help="LLM judge: every number in the answer appears in a tool result")
        st.caption(f"run {r.get('run_at', '')}" + (f" on {r['model']}" if r.get("model") else ""))
        runs = ROOT / "evals" / "results" / "README.md"
        if runs.exists():
            with st.expander("Every run, every model"):
                st.markdown(runs.read_text().split("\n", 2)[-1])
    else:
        st.caption("No benchmark results yet: `python evals/run_benchmark.py`.")
with c3:
    st.markdown("**Row counts**")
    try:
        counts = {t: int(db.query(f"SELECT COUNT(*) n FROM aa_demo.{t}")["n"].iloc[0]) for t in
                  ["gold.fact_agency_sales_monthly", "gold.fact_corporate_bookings", "gold.fact_market_capacity", "ops.decomposition", "ops.kpi_definitions"]}
        st.dataframe(pd.DataFrame({"table": counts.keys(), "rows": counts.values()}), hide_index=True, use_container_width=True)
    except Exception as e:
        st.caption(f"not connected: {e}")

st.divider()
st.markdown("**Why this shape, in one line each**")
st.markdown("""
- Metric view, not a table: share is a ratio; a table of pre-computed shares is wrong the moment someone groups differently.
- Genie inside a harness, not alone: Genie answers numbers; the harness adds documents, the decomposition, the refusal, and the verifier.
- Verifier before the human: the Monday-morning failure is a number nobody queried; matching numbers to query results is deterministic and cheap.
- Decomposition in SQL, not in the model: the parts must sum; arithmetic belongs in the warehouse, prose belongs to the model.
- Per-user identity: Genie runs as the asking user, so an agency portal shows each agency only itself with no extra code.
- Benchmarks before changes: twenty questions with known answers, rerun on every prompt or definition change, in a pre-commit hook.
""")

limits = ROOT / "docs" / "limits.md"
if limits.exists():
    with st.expander("Platform limits met while building (docs/limits.md)"):
        st.markdown(limits.read_text())
