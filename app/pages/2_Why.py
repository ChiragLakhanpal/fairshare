import pandas as pd
import streamlit as st

from common import drawer, esc, get_agent, money, pct, setup

setup("Why")
from fairshare import db  # noqa: E402
from harness import facts  # noqa: E402
from harness.tools import explain_change  # noqa: E402

st.title("Why is my number down?")
st.caption("A deterministic decomposition of the year-over-year change. The parts sum to the total by construction; the model only writes.")

agencies = db.query("SELECT agency_id, agency_name FROM aa_demo.gold.dim_agency ORDER BY agency_name")
months = db.query("SELECT DISTINCT sales_month FROM aa_demo.ops.decomposition ORDER BY sales_month DESC")["sales_month"].map(lambda d: str(d)[:7]).tolist()
c1, c2 = st.columns(2)
name = c1.selectbox("Agency", agencies["agency_name"].tolist(), index=int((agencies["agency_name"] == "Harbor Business Travel").idxmax()))
month = c2.selectbox("Month (vs the same month last year)", months, index=0)

facts.reset()
note = explain_change.func(agency=name, month=month)
ctx = facts.current()
if not ctx.calls or ctx.calls[0].preview is None:
    st.warning(note)
    st.stop()
s = ctx.calls[0].preview.iloc[0]
markets = ctx.calls[1].preview

prior_year = int(month[:4]) - 1
st.subheader(f"{name}, {month} vs {prior_year}-{month[5:]}")
k1, k2, k3, k4 = st.columns(4)
k1.metric("AA revenue", money(s["revenue_now"]), f"{s['delta_pct']:+.1f}% ({money(s['delta_revenue'])})")
k2.metric("Agency total market", f"{s['market_delta_pct']:+.1f}%", help="All-carrier revenue the agency sold on these markets, vs last year")
k3.metric("AA share", pct(s["aa_share_now_pct"]), f"{s['aa_share_now_pct'] - s['aa_share_prior_pct']:+.1f} pts vs {pct(s['aa_share_prior_pct'])}")
k4.metric("Fair share", pct(s["fair_share_now_pct"]), f"{s['fair_share_now_pct'] - s['fair_share_prior_pct']:+.1f} pts vs {pct(s['fair_share_prior_pct'])}")

eff = pd.DataFrame({"effect": ["volume", "mix", "share"], "usd": [s["volume_effect"], s["mix_effect"], s["share_effect"]]}).set_index("effect")
left, right = st.columns([1, 1])
left.bar_chart(eff, horizontal=True, height=220)
right.markdown(esc(f"""**Where the {money(abs(s['delta_revenue']))} went**

- Volume (the agency sold {'more' if s['market_delta_pct'] >= 0 else 'less'} travel overall): **{money(s['volume_effect'])}**
- Mix (shifted which markets it sells): **{money(s['mix_effect'])}**
- Share (AA won or lost share within markets): **{money(s['share_effect'])}**
- Check: {money(s['volume_effect'])} + {money(s['mix_effect'])} + {money(s['share_effect'])} = **{money(s['parts_sum'])}** (total {money(s['delta_revenue'])})

Fair share moved {s['fair_share_now_pct'] - s['fair_share_prior_pct']:+.1f} pts, worth about {money(s['fair_share_effect'])}: {'AA did not change its capacity much, so the share move is the agency' if abs(s['fair_share_effect']) < abs(s['share_effect']) / 5 else 'part of the share move follows AA capacity'}.
"""))

st.markdown("**Markets that moved most (share effect, dollars)**")
st.dataframe(markets.rename(columns={"share_effect": "share effect $", "mix_effect": "mix effect $", "aa_share_now_pct": "AA share now %",
                                     "aa_share_prior_pct": "AA share prior %", "market_revenue_now": "agency market $"}),
             hide_index=True, use_container_width=True)

st.markdown('<span class="muted">Could not verify: whether the agency changed a preferred-carrier setting or lost a client; not in the data.</span>', unsafe_allow_html=True)

if get_agent() is not None and st.button("Write the account manager's note from these numbers"):
    from harness import agent as harness_agent
    with st.spinner("Writing..."):
        ans = harness_agent.ask(f"Write a five-sentence performance note an account manager could send to {name} explaining the {month} "
                                f"change versus last year. Use explain_change for {name} {month}. Quote only returned numbers.", get_agent())
    st.markdown(esc(ans.text))
    if ans.flagged:
        st.error(esc("Removed before sending: " + " | ".join(f["reason"] for f in ans.flagged)))
    drawer(ans.calls, ans.sources)
else:
    drawer(ctx.calls, ctx.sources, "The decomposition rows (ops.decomposition)")
