"""The OpsPilot LangGraph.

    parse -> retrieve -> diagnose -> guard --(escalate)--> escalate -> END
                                          --(approval)--> approval -> report -> END
                                          --(report)----> report -> END

`approval` pauses the graph with `interrupt()` whenever a proposed command changes state.
The run is checkpointed, so a human can approve minutes later and the graph resumes from
exactly that point with `Command(resume={"approved": True, "approver": "..."})`.
"""
from __future__ import annotations

from typing import Any, TypedDict

from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.types import interrupt

from .retrieval import RunbookIndex
from .schemas import Diagnosis
from .signals import detect_platform, detect_signals, excerpt, is_mutating, redact


class OpsState(TypedDict, total=False):
    log: str
    redacted_log: str
    redactions: int
    platform: str
    signals: list[dict]
    log_excerpt: str
    sections: list[dict]
    diagnosis: dict
    escalation_reasons: list[str]
    approved: bool | None
    approver: str
    status: str  # read_only | approved | rejected | escalated


SYSTEM_PROMPT = """You are OpsPilot, a senior SRE assistant for Kubernetes, Jenkins and Terraform incidents.
Diagnose the incident using ONLY the runbook sections provided.

Rules:
- Every claim about what to do must come from a runbook section. Put the ids you used in `citations`,
  copied exactly as shown in the [id] headers.
- Copy the log lines that prove the root cause into `evidence_lines`, verbatim.
- Order steps read-only first (get/describe/logs/plan/df), changing actions last.
- Mark a step `mutating` if it changes anything: deploy, delete, scale, restart, unlock, prune.
- If the runbooks do not cover this failure, set insufficient_evidence=true, give the best
  read-only investigation steps you can, and do not invent a fix.
- Never repeat secrets. Never suggest disabling TLS verification, locking or security controls."""


def _format_sections(sections: list[dict]) -> str:
    return "\n\n".join(f"[{s['id']}]\n{s['text']}" for s in sections)


def build_graph(index: RunbookIndex, llm, checkpointer=None, k: int = 4):
    """`llm` is any LangChain chat model that supports `.with_structured_output()`."""
    diagnoser = llm.with_structured_output(Diagnosis)

    def parse(state: OpsState) -> OpsState:
        clean, n = redact(state["log"])
        signals = detect_signals(clean)
        return {
            "redacted_log": clean,
            "redactions": n,
            "signals": [s.__dict__ for s in signals],
            "platform": detect_platform(clean, signals),
            "log_excerpt": excerpt(clean, signals),
        }

    def retrieve(state: OpsState) -> OpsState:
        # Query = signal ids + the matched error lines. Fall back to the excerpt tail if nothing matched.
        sig = state["signals"]
        query = " ".join(s["id"] + " " + s["line"] for s in sig) or state["log_excerpt"][-1500:]
        hits = index.expand(index.search(query, k=k, platform=state["platform"]))
        return {"sections": [{"id": c.id, "text": c.text, "score": round(score, 4)} for c, score in hits]}

    def diagnose(state: OpsState) -> OpsState:
        signals = ", ".join(s["id"] for s in state["signals"]) or "none matched"
        user = (
            f"Platform: {state['platform']}\nDetected signals: {signals}\n\n"
            f"RUNBOOK SECTIONS\n{_format_sections(state['sections'])}\n\n"
            f"LOG EXCERPT (secrets redacted, line numbers on the left)\n{state['log_excerpt']}"
        )
        result: Diagnosis = diagnoser.invoke([SystemMessage(SYSTEM_PROMPT), HumanMessage(user)])
        return {"diagnosis": result.model_dump()}

    def guard(state: OpsState) -> OpsState:
        """Deterministic checks on the model's output. The model proposes; code disposes."""
        diag = dict(state["diagnosis"])
        valid = {s["id"] for s in state["sections"]}
        diag["citations"] = [c for c in diag["citations"] if c in valid]
        diag["steps"] = [{**s, "mutating": s["mutating"] or is_mutating(s["command"])} for s in diag["steps"]]
        reasons = []
        if diag["insufficient_evidence"]:
            reasons.append("Runbooks do not cover this failure.")
        if not diag["citations"]:
            reasons.append("Diagnosis is not grounded in any retrieved runbook section.")
        if not state["signals"] and diag["confidence"] != "high":
            reasons.append("No known failure signature in the log and model confidence is not high.")
        return {"diagnosis": diag, "escalation_reasons": reasons}

    def route(state: OpsState) -> str:
        if state["escalation_reasons"]:
            return "escalate"
        if any(s["mutating"] for s in state["diagnosis"]["steps"]):
            return "approval"
        return "report"

    def approval(state: OpsState) -> OpsState:
        commands = [s["command"] for s in state["diagnosis"]["steps"] if s["mutating"]]
        decision: Any = interrupt({"question": "Approve these state-changing commands?", "commands": commands})
        return {"approved": bool(decision.get("approved")), "approver": decision.get("approver", "")}

    def report(state: OpsState) -> OpsState:
        if state.get("approved") is None:
            return {"status": "read_only"}
        return {"status": "approved" if state["approved"] else "rejected"}

    def escalate(state: OpsState) -> OpsState:
        return {"status": "escalated"}

    g = StateGraph(OpsState)
    for name, fn in [("parse", parse), ("retrieve", retrieve), ("diagnose", diagnose), ("guard", guard),
                     ("approval", approval), ("report", report), ("escalate", escalate)]:
        g.add_node(name, fn)
    g.add_edge(START, "parse")
    g.add_edge("parse", "retrieve")
    g.add_edge("retrieve", "diagnose")
    g.add_edge("diagnose", "guard")
    g.add_conditional_edges("guard", route, {"escalate": "escalate", "approval": "approval", "report": "report"})
    g.add_edge("approval", "report")
    g.add_edge("report", END)
    g.add_edge("escalate", END)
    return g.compile(checkpointer=checkpointer or InMemorySaver())
