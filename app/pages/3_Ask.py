import streamlit as st

from common import badges_html, drawer, esc, get_agent, load_cache, setup

setup("Ask")
from harness import agent as harness_agent  # noqa: E402

st.title("Ask the sales agent")
st.caption("The number, the comparison, the SQL, the source. Unknown is an allowed answer.")

SCRIPTED = [
    "How did Summit Travel Partners do on DFW to ORD in Q3 2026 versus Q3 2025, and are they ahead of fair share?",
    "What does Summit Travel Partners' agreement say happens if their share drops under 45% for two quarters, and has that happened?",
    "Which agencies are about to churn?",
]
cached = load_cache("answers.json") or {}
agent = get_agent()

cols = st.columns(3)
for i, q in enumerate(SCRIPTED):
    if cols[i].button(q, use_container_width=True):
        st.session_state["ask_q"] = q
typed = st.chat_input("Ask about an agency, a market, a period, or a contract")
if typed:
    st.session_state["ask_q"] = typed

q = st.session_state.get("ask_q")
if q:
    st.chat_message("user").write(q)
    with st.chat_message("assistant"):
        if agent is not None:
            with st.spinner("Asking the tools..."):
                try:
                    ans = harness_agent.ask(q, agent)
                except Exception as e:
                    ans = None
                    st.error(f"The agent failed: {e}")
            if ans:
                st.markdown(badges_html(ans.verification.badges()), unsafe_allow_html=True)
                if ans.flagged:
                    st.error(esc("Removed before showing: " + " | ".join(f["reason"] for f in ans.flagged)))
                drawer(ans.calls, ans.sources)
        elif q in cached:
            c = cached[q]
            st.markdown(esc(c["text"]))
            st.caption(f"Cached answer recorded {c.get('recorded', '')} with model {c.get('model', '')} (offline mode).")
            if c.get("sql"):
                with st.expander("How I got this"):
                    for s in c["sql"]:
                        st.code(s, language="sql")
                    if c.get("sources"):
                        st.markdown("**Sources:** " + ", ".join(f"`{s}`" for s in c["sources"]))
        else:
            st.warning("No model configured and no cached answer for this question. Set FAIRSHARE_MODEL in .env, or pick one of the three scripted questions.")
