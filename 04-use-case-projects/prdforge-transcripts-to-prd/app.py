"""Streamlit UI:  streamlit run app.py"""
import json
import tempfile
from pathlib import Path

import pandas as pd
import streamlit as st

from prdforge import coverage, generate, load_sources, render
from prdforge.config import DEFAULT_CONTEXT, SOURCES_DIR

st.set_page_config(page_title="PRDForge", page_icon="📝", layout="wide")
st.title("PRDForge: from conversations to a traceable PRD")
st.caption("Upload meeting transcripts (.txt, 'Name: text' per line), a Slack export (.json) and a feedback CSV. "
           "Every user story cites the exact lines it came from.")

with st.sidebar:
    uploads = st.file_uploader("Sources (leave empty to use the sample project)", type=["txt", "json", "csv"],
                               accept_multiple_files=True)
    context = st.text_area("Product context", DEFAULT_CONTEXT, height=120)
    max_rev = st.slider("Max critique/revise passes", 0, 3, 2)

source_dir = SOURCES_DIR
if uploads:
    tmp = Path(tempfile.mkdtemp())
    for f in uploads:
        (tmp / f.name).write_bytes(f.getvalue())
    source_dir = tmp

with st.expander("Numbered evidence (what the model can cite)"):
    rows = [{"id": it["id"], "source": s["title"], "who": it["speaker"], "text": it["text"]}
            for s in load_sources(source_dir) for it in s["items"]]
    st.dataframe(pd.DataFrame(rows), hide_index=True, width="stretch")

if st.button("Generate PRD", type="primary"):
    with st.spinner("Extracting insights per source (in parallel), synthesising, drafting, critiquing..."):
        st.session_state.prd_state = generate(source_dir, context, max_revisions=max_rev)

state = st.session_state.get("prd_state")
if state:
    a, b, c, d = st.columns(4)
    a.metric("Insights", len(state["insights"]))
    b.metric("Conflicts found", len(state["synthesis"]["conflicts"]))
    c.metric("User stories", len(state["prd"]["user_stories"]))
    d.metric("Evidence coverage", f"{coverage(state['prd'], state['evidence']):.0%}")
    st.caption(f"Critique issues per pass: {state['issue_history']}  (revisions used: {state['revisions']})")
    md = render(state)
    tab1, tab2, tab3 = st.tabs(["PRD", "Insights", "Conflicts"])
    tab1.markdown(md, unsafe_allow_html=True)
    tab2.dataframe(pd.DataFrame(state["insights"]), hide_index=True, width="stretch")
    tab3.json(state["synthesis"]["conflicts"])
    st.download_button("Download PRD.md", md, file_name="PRD.md")
    st.download_button("Download PRD.json", json.dumps(state["prd"], indent=2), file_name="PRD.json")
