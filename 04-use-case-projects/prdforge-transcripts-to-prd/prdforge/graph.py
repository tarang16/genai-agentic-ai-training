"""PRDForge LangGraph: map-reduce extraction, synthesis, drafting and a critique/revise loop.

    load --Send per source--> extract (parallel) --> synthesize --> draft --> critique
                                                                        ^          |
                                                                        +- revise <+  (while issues and budget left)

load        deterministic: number every line of every source (M1-07, S-03, F-10), scrub PII
extract     LLM, one call per source, run in parallel with LangGraph's Send API (map step)
synthesize  LLM: merge insights into themes, surface conflicts between stakeholders (reduce step)
draft       LLM: structured PRD with user stories, Given/When/Then criteria and evidence ids
critique    code: testable criteria, traceability, conflicts handled, constraints captured
revise      LLM: fix exactly the issues the critique listed
"""
from __future__ import annotations

import json
import operator
from typing import Annotated, TypedDict

from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.graph import END, START, StateGraph
from langgraph.types import Send

from .critique import critique
from .schemas import PRD, SourceInsights, Synthesis
from .sources import evidence_index, format_source, load_sources


class PRDState(TypedDict, total=False):
    source_dir: str
    product_context: str
    sources: list[dict]
    evidence: dict[str, dict]
    insights: Annotated[list[dict], operator.add]  # reducer: parallel extract calls append here
    synthesis: dict
    prd: dict
    issues: list[str]
    issue_history: list[int]
    revisions: int


EXTRACT_PROMPT = """You are a senior product analyst. Extract product insights from ONE source.
Types: pain_point, request, decision, constraint (compliance/data/technical limits), metric (baselines,
targets, numbers), open_question. Be specific: keep numbers, roles, regions and timings.
Every insight must cite the evidence ids (in square brackets) it comes from. Do not invent ids.
Do not merge different stakeholders' opinions into one insight; disagreement is valuable."""

SYNTH_PROMPT = """Merge insights from several sources into 4-8 themes. Then list every CONFLICT: a topic
where stakeholders or sources disagree (e.g. frequency, channel, visibility, scope). Give each conflict an
id C1, C2... and each side's position with evidence ids. Only cite evidence ids that appear in the insights."""

DRAFT_PROMPT = """Write a PRD for the product team from the synthesis and insights.
Rules:
- 5-8 user stories, MoSCoW priority, each with 2-4 acceptance criteria in Given/When/Then form.
- Acceptance criteria must be testable: numbers, states, roles. Never 'fast', 'easy', 'intuitive'.
- Every story, goal, constraint, decision and open question cites evidence ids from the input.
- Goals need a metric with a numeric target (use baselines from the evidence when they exist).
- Each conflict id must appear EITHER in decisions (only if the evidence actually resolves it, with rationale)
  OR in open_questions with an owner. Do not silently pick a side.
- Capture every compliance and data constraint in `constraints`.
- Things explicitly ruled out go to non_goals or Won't (v1) stories."""

REVISE_PROMPT = """You are revising a PRD. Fix EVERY issue listed, change nothing else, and return the full PRD."""


def build_graph(llm, max_revisions: int = 2):
    extractor = llm.with_structured_output(SourceInsights)
    synthesizer = llm.with_structured_output(Synthesis)
    drafter = llm.with_structured_output(PRD)

    def load(state: PRDState) -> PRDState:
        sources = load_sources(state["source_dir"])
        return {"sources": sources, "evidence": evidence_index(sources), "revisions": 0, "issue_history": []}

    def fan_out(state: PRDState) -> list[Send]:
        return [Send("extract", {"source": s, "evidence": state["evidence"]}) for s in state["sources"]]

    def extract(payload: dict) -> PRDState:
        src = payload["source"]
        msg = f"SOURCE: {src['title']} ({src['kind']})\n\n{format_source(src)}"
        out: SourceInsights = extractor.invoke([SystemMessage(EXTRACT_PROMPT), HumanMessage(msg)])
        known = payload["evidence"]
        kept = []
        for ins in out.insights:
            ids = [e for e in ins.evidence_ids if e in known]
            if ids:  # an insight that cannot point at a real line is dropped, not trusted
                kept.append({**ins.model_dump(), "evidence_ids": ids, "source": src["id"]})
        return {"insights": kept}

    def synthesize(state: PRDState) -> PRDState:
        msg = "INSIGHTS\n" + json.dumps(state["insights"], indent=1)
        out: Synthesis = synthesizer.invoke([SystemMessage(SYNTH_PROMPT), HumanMessage(msg)])
        return {"synthesis": out.model_dump()}

    def _context(state: PRDState) -> str:
        return (f"PRODUCT CONTEXT: {state.get('product_context', '')}\n\n"
                f"SYNTHESIS\n{json.dumps(state['synthesis'], indent=1)}\n\n"
                f"INSIGHTS\n{json.dumps(state['insights'], indent=1)}")

    def draft(state: PRDState) -> PRDState:
        out: PRD = drafter.invoke([SystemMessage(DRAFT_PROMPT), HumanMessage(_context(state))])
        return {"prd": out.model_dump()}

    def _constraint_ids(state: PRDState) -> set[str]:
        return {e for i in state["insights"] if i["type"] == "constraint" for e in i["evidence_ids"]}

    def review(state: PRDState) -> PRDState:
        issues = critique(state["prd"], state["evidence"], state["synthesis"], _constraint_ids(state))
        return {"issues": issues, "issue_history": state["issue_history"] + [len(issues)]}

    def revise(state: PRDState) -> PRDState:
        msg = (_context(state) + f"\n\nCURRENT PRD\n{json.dumps(state['prd'], indent=1)}\n\n"
               "ISSUES TO FIX\n" + "\n".join(f"- {i}" for i in state["issues"]))
        out: PRD = drafter.invoke([SystemMessage(DRAFT_PROMPT + "\n\n" + REVISE_PROMPT), HumanMessage(msg)])
        return {"prd": out.model_dump(), "revisions": state["revisions"] + 1}

    def should_revise(state: PRDState) -> str:
        return "revise" if state["issues"] and state["revisions"] < max_revisions else "done"

    g = StateGraph(PRDState)
    g.add_node("load", load)
    g.add_node("extract", extract)
    g.add_node("synthesize", synthesize)
    g.add_node("draft", draft)
    g.add_node("critique", review)
    g.add_node("revise", revise)
    g.add_edge(START, "load")
    g.add_conditional_edges("load", fan_out, ["extract"])
    g.add_edge("extract", "synthesize")
    g.add_edge("synthesize", "draft")
    g.add_edge("draft", "critique")
    g.add_conditional_edges("critique", should_revise, {"revise": "revise", "done": END})
    g.add_edge("revise", "critique")
    return g.compile()
