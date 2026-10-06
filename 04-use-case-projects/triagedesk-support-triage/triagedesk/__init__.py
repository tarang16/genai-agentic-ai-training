"""TriageDesk: known-vs-new triage for support tickets, grounded in past tickets, KB and Jira."""
from .config import get_llm
from .graph import build_graph
from .report import render
from .store import SupportKnowledge


def create_app(llm=None):
    return build_graph(SupportKnowledge(), llm or get_llm())


__all__ = ["build_graph", "create_app", "render", "SupportKnowledge"]
