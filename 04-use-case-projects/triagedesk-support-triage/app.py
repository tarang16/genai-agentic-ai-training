"""Streamlit UI:  streamlit run app.py"""
import json

import streamlit as st

from triagedesk import create_app, render
from triagedesk.config import INCOMING

st.set_page_config(page_title="TriageDesk", page_icon="🎫", layout="wide")
st.title("TriageDesk: is this a known issue?")
st.caption("Searches past Freshdesk tickets, KB articles and Jira bugs, then drafts a grounded reply. "
           "PII is masked before the model sees the ticket; safety and injection cases always go to a human.")


@st.cache_resource
def get_app():
    return create_app()


samples = [json.loads(l) for l in INCOMING.read_text(encoding="utf-8").splitlines() if l.strip()]
with st.sidebar:
    pick = st.selectbox("Load a sample ticket", ["(new)"] + [f"{s['ticket_id']} - {s['subject']}" for s in samples])
base = samples[[f"{s['ticket_id']} - {s['subject']}" for s in samples].index(pick)] if pick != "(new)" else \
    {"ticket_id": "FD-NEW", "product": "VX2780", "subject": "", "description": ""}

c1, c2 = st.columns([1, 3])
product = c1.selectbox("Product", ["VX2780", "VX3218", "TD2455", "XG2431"], index=["VX2780", "VX3218", "TD2455", "XG2431"].index(base["product"]))
subject = c2.text_input("Subject", base["subject"])
description = st.text_area("Description", base["description"], height=140)

if st.button("Triage", type="primary", disabled=not description.strip()):
    with st.spinner("Classifying, searching tickets / KB / Jira, deciding..."):
        st.session_state.result = get_app().invoke(
            {"ticket": {"ticket_id": base["ticket_id"], "product": product, "subject": subject, "description": description}})

state = st.session_state.get("result")
if state:
    left, right = st.columns([3, 2])
    left.markdown(render(state))
    with right:
        st.subheader("Evidence the model saw")
        for e in state.get("evidence", []):
            via = f" via {e['via']}" if e.get("via") else ""
            with st.expander(f"{e['id']} ({e['kind']}, score {e['score']}{via})"):
                st.text(e["text"])
        if not state.get("evidence"):
            st.info("No evidence gathered (a guardrail stopped the run before search).")
