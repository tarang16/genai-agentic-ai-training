"""ClaimSense: explainable health-insurance claim adjudication. LLM reads, rules decide, humans sign off."""
from .config import get_llm
from .graph import build_graph
from .policy import PolicyWording
from .report import render
from .rules import adjudicate


def create_app(llm=None):
    return build_graph(PolicyWording(), llm or get_llm())


__all__ = ["adjudicate", "build_graph", "create_app", "PolicyWording", "render"]
