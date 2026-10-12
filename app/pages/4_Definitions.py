import pandas as pd
import streamlit as st

from common import CACHE, setup

setup("Definitions")
from fairshare import db  # noqa: E402

st.title("Definitions and parity")
st.caption("Each KPI is written once in English, implemented in the metric view (for Genie and the agent) and in Power BI (DAX). "
           "A nightly job computes both and shows where they disagree, before a VP does.")

defs = db.query("SELECT * FROM aa_demo.ops.kpi_definitions")
kpi = st.selectbox("KPI", defs["kpi"].tolist(), format_func=lambda k: defs.set_index("kpi").loc[k, "display_name"])
d = defs.set_index("kpi").loc[kpi]

st.markdown(f"### {d['display_name']}")
st.markdown(d["definition_en"])
st.caption(f"Owner: {d['owner']}. Source: {d['source_columns']}.")
a, b = st.columns(2)
with a:
    st.markdown("**Metric view (Databricks, YAML measure)**")
    st.code(d["metric_view_expr"], language="yaml")
    st.markdown("**Second implementation used by the parity job (SQL twin)**")
    st.code(d["twin_sql"], language="sql")
with b:
    st.markdown("**Power BI twin (DAX)**")
    st.code(d["dax_twin"], language="text")
    if isinstance(d.get("twin_sql_retired"), str) and d["twin_sql_retired"]:
        st.markdown("**Retired definition (what parity caught)**")
        st.code(d["twin_sql_retired"], language="sql")
        st.warning(d["retired_note"])

st.divider()
st.subheader("Parity: metric view vs twin, by KPI and month")
par = pd.DataFrame()
if db.is_databricks():
    try:
        par = db.query("SELECT * FROM aa_demo.ops.kpi_parity")
    except Exception:
        par = pd.DataFrame()
if par.empty and (CACHE / "kpi_parity.csv").exists():
    par = pd.read_csv(CACHE / "kpi_parity.csv")
    st.caption("Showing the last exported parity run (offline mode).")
if par.empty:
    st.info("No parity runs yet. On Databricks: `python lakehouse/parity.py` (and `--retired` to reproduce the red run that caught the passenger-based share).")
else:
    par["sales_month"] = par["sales_month"].astype(str).str[:7]
    runs = par.groupby(["run_id", "run_at"]).agg(kpis=("kpi", "nunique"), rows=("kpi", "size"), drift=("status", lambda s: (s == "drift").sum())).reset_index().sort_values("run_at", ascending=False)
    st.dataframe(runs, hide_index=True, use_container_width=True)
    run_id = st.selectbox("Run", runs["run_id"].tolist(), format_func=lambda r: f"{r}  ({runs.set_index('run_id').loc[r, 'run_at']}, {runs.set_index('run_id').loc[r, 'drift']} drift)")
    sel = par[par["run_id"] == run_id]
    grid = sel.pivot_table(index="kpi", columns="sales_month", values="status", aggfunc=lambda s: "drift" if (s == "drift").any() else "ok")
    st.dataframe(grid.style.map(lambda v: "background-color:#fdecec;color:#a12626" if v == "drift" else "background-color:#e4f3e8;color:#1e6b36"),
                 use_container_width=True)
    bad = sel[sel["status"] == "drift"]
    if not bad.empty:
        st.markdown(f"**{len(bad)} drifting rows** (first 20)")
        st.dataframe(bad[["kpi", "twin_version", "agency", "sales_month", "mv_value", "twin_value", "abs_diff"]].head(20), hide_index=True, use_container_width=True)
