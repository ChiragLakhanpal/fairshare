import json

import pandas as pd
import streamlit as st

from common import MONTHS, badges_html, drawer, esc, get_agent, setup

setup("Monday")
from harness import summary  # noqa: E402

st.title("Monday: the verified summary")
st.caption("Fixed metric calls, a model writes the prose, the verifier matches every number to a query result, a person presses send.")

col1, col2, col3 = st.columns([1, 1, 2])
region = col1.selectbox("Region", ["Central", "East", "West"], index=0)
month = col2.selectbox("Month", MONTHS[::-1], index=0)
mode = col3.radio("Writer", ["Agent (guarded prompt)", "Agent (unguarded prompt: for the demo, shows what the verifier catches)", "Template (no model)"],
                  index=0 if get_agent() else 2, horizontal=False)

UNGUARDED = ("Write a confident, insightful Monday performance summary for the Sales VP from the FACTS below. "
             "Add context, comparisons and interpretation where helpful. Six to nine sentences of plain prose.")

if st.button("Build the summary", type="primary"):
    writer = None
    if mode.startswith("Agent"):
        writer = summary.make_writer(UNGUARDED) if "unguarded" in mode else summary.make_writer()
        if writer is None:
            st.warning("No model configured; using the template writer.")
    with st.spinner("Running the metric calls, drafting, verifying..."):
        res = summary.run(region, month, writer)
        summary.save(res, "draft")
    st.session_state["monday"] = res

res = st.session_state.get("monday")
if res:
    st.subheader(f"{res['region']} region, {res['month']}")
    st.markdown(badges_html(res["badges"]), unsafe_allow_html=True)
    if res["flagged"]:
        st.error(esc(f"{len(res['flagged'])} sentence(s) removed before sending: " + " | ".join(f["reason"] for f in res["flagged"])))
    else:
        st.success("Every number traces to a query. Nothing removed.")
    st.markdown("**What the VP would receive**")
    st.info(esc(res["verified_text"]) or "(nothing survived verification)")
    a, b, _ = st.columns([1, 1, 4])
    if a.button("Approve and send"):
        summary.save(res, "approved")
        st.toast("Approved. In production this is the step that posts to Teams or mail; here it records status=approved.")
    if b.button("Reject"):
        summary.save(res, "rejected")
        st.toast("Rejected and recorded.")
    with st.expander("Every number and the query behind it"):
        rows = [{"sentence": b["sentence"][:80], "number": n["raw"], "matched fact": n["fact"], "query": n["source"]}
                for b in res["badges"] for n in b["numbers"]]
        st.dataframe(pd.DataFrame(rows), hide_index=True, use_container_width=True)
    drawer(res["calls"], ["sales_metrics" if any(c.sql and "MEASURE" in c.sql for c in res["calls"]) else "gold tables"], "The metric calls (SQL and results)")

st.divider()
st.markdown("**Runs**")
h = summary.history()
if not h.empty:
    h["flagged"] = h["flagged_json"].map(lambda j: len(json.loads(j)) if j else 0)
    st.dataframe(h.drop(columns=["flagged_json"]), hide_index=True, use_container_width=True)
else:
    st.caption("No runs yet.")
