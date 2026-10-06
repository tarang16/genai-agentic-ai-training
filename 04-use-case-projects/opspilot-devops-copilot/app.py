"""Streamlit UI:  streamlit run app.py"""
import uuid

import streamlit as st
from langgraph.types import Command

from opspilot import create_app, render
from opspilot.config import INCIDENT_DIR

st.set_page_config(page_title="OpsPilot", page_icon="🛠️", layout="wide")
st.title("OpsPilot: runbook-grounded incident copilot")
st.caption("Paste a kubectl / Jenkins / Terraform log. Secrets are redacted before anything reaches the model; "
           "state-changing commands stop for human approval.")


@st.cache_resource
def get_app(offline: bool):
    return create_app(offline_retrieval=offline)


with st.sidebar:
    offline = st.toggle("BM25-only retrieval (no embedding calls)", value=False)
    sample = st.selectbox("Load a sample incident", ["(none)"] + sorted(p.name for p in INCIDENT_DIR.glob("*.log")))

default = (INCIDENT_DIR / sample).read_text(encoding="utf-8") if sample != "(none)" else ""
log = st.text_area("Incident log", value=default, height=280)

if st.button("Diagnose", type="primary", disabled=not log.strip()):
    st.session_state.thread = str(uuid.uuid4())
    cfg = {"configurable": {"thread_id": st.session_state.thread}}
    with st.spinner("Parsing, retrieving runbooks, diagnosing..."):
        st.session_state.state = get_app(offline).invoke({"log": log}, cfg)

state = st.session_state.get("state")
if state:
    left, right = st.columns([3, 2])
    with left:
        st.markdown(render(state))
    with right:
        st.subheader("Retrieved runbook sections")
        for s in state.get("sections", []):
            with st.expander(f"{s['id']}  (RRF {s['score']})"):
                st.markdown(s["text"])
        st.subheader("What the model saw")
        st.code(state.get("log_excerpt", ""), language="text")

    if "__interrupt__" in state:
        st.warning("These commands change state and need approval:")
        for cmd in state["__interrupt__"][0].value["commands"]:
            st.code(cmd, language="bash")
        approver = st.text_input("Your name", value="on-call engineer")
        a, r = st.columns(2)
        cfg = {"configurable": {"thread_id": st.session_state.thread}}
        if a.button("Approve"):
            st.session_state.state = get_app(offline).invoke(Command(resume={"approved": True, "approver": approver}), cfg)
            st.rerun()
        if r.button("Reject"):
            st.session_state.state = get_app(offline).invoke(Command(resume={"approved": False, "approver": approver}), cfg)
            st.rerun()
