"""Streamlit UI:  streamlit run app.py"""
import json

import pandas as pd
import streamlit as st

from claimsense import create_app, render
from claimsense.config import AUTO_APPROVE_LIMIT, CLAIMS_DIR

st.set_page_config(page_title="ClaimSense", page_icon="🩺", layout="wide")
st.title("ClaimSense: explainable health-claim adjudication")
st.caption(f"The LLM reads the discharge summary; deterministic rules compute every rupee with a clause reference; "
           f"rejections, referrals and anything above INR {AUTO_APPROVE_LIMIT:,} go to a human assessor.")


@st.cache_resource
def get_app():
    return create_app()


files = sorted(CLAIMS_DIR.glob("*.json"))
with st.sidebar:
    pick = st.selectbox("Sample claim", [p.stem for p in files])
    uploaded = st.file_uploader("...or upload a claim JSON", type=["json"])
claim = json.loads(uploaded.getvalue()) if uploaded else json.loads((CLAIMS_DIR / f"{pick}.json").read_text(encoding="utf-8"))

with st.expander("Claim input", expanded=False):
    st.json(claim["policy"])
    st.dataframe(pd.DataFrame(claim["bill"]), hide_index=True, width="stretch")
    st.text_area("Discharge summary (raw, contains PII)", claim["discharge_summary"], height=120, disabled=True)

if st.button("Adjudicate", type="primary"):
    with st.spinner("Redacting, extracting facts, applying policy rules, drafting letter..."):
        st.session_state.claim_state = get_app().invoke({"claim": claim})

state = st.session_state.get("claim_state")
if state and state["claim"]["claim_id"] == claim["claim_id"]:
    f = state["final"]
    a, b, c = st.columns(3)
    a.metric("Decision", f["decision"].upper())
    b.metric("Payable", "pending" if f["payable"] is None else f"INR {f['payable']:,.0f}")
    c.metric("Route", f["route"].replace("_", " "))
    st.markdown(render(state))
    with st.expander("What the model saw (redacted)"):
        st.text(state["redacted_summary"])
    with st.expander("Policy clauses retrieved"):
        for cl in state["clauses"]:
            st.markdown(f"**{cl['id']} {cl['title']}**: {cl['text']}")
