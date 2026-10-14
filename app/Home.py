"""fairshare: one sales agent, one semantic layer, every number with its query.

  streamlit run app/Home.py
"""
import streamlit as st

from common import setup

setup("Start")

st.title("fairshare")
st.markdown("An account manager's Monday, with an agent that shows its work. Airline indirect sales (agencies and corporate "
            "accounts) on public BTS T-100 seat data plus a synthetic agency layer. Nothing here is confidential.")

c1, c2, c3 = st.columns(3)
c1.page_link("pages/1_Monday.py", label="1. Monday: the verified summary", icon="📋")
c1.caption("The month's close for a region, every number badged with its query, anything unsupported quarantined before a human presses send.")
c2.page_link("pages/2_Why.py", label="2. Why: the decomposition", icon="🧭")
c2.caption("Why an agency's revenue moved: volume, mix, share, and what AA's own capacity explains. Parts sum to the total.")
c3.page_link("pages/3_Ask.py", label="3. Ask: the sales agent", icon="💬")
c3.caption("Share vs last year vs fair share, what the contract says, and a question it refuses to guess at.")
c4, c5, _ = st.columns(3)
c4.page_link("pages/4_Definitions.py", label="4. Definitions and parity", icon="📐")
c4.caption("Each KPI defined once (metric view), its Power BI twin, and the nightly check that keeps them equal.")
c5.page_link("pages/5_Under_the_hood.py", label="5. Under the hood", icon="🔧")
c5.caption("Architecture, where it would live at an airline, benchmarks, traces, limits.")

st.divider()
st.markdown("""**One sentence per layer.** The data: bronze, silver, gold in Databricks (Unity Catalog). The definitions: one metric view where
"share" and "fair share" mean one thing, so the agent and the Power BI report give the same number. The agent: Genie for the numbers,
a decomposition for "why", the agreements for contract terms, a harness (Microsoft Agent Framework) that picks the tool and a
verifier that refuses to show a number no query returned.""")
