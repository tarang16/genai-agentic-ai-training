"""OpsPilot: a runbook-grounded incident copilot for Kubernetes, Jenkins and Terraform."""
from .config import RUNBOOK_DIR, get_embeddings, get_llm
from .graph import build_graph
from .report import render
from .retrieval import RunbookIndex, load_runbooks


def create_app(offline_retrieval: bool = False, llm=None):
    """Build the index and graph with default settings. `offline_retrieval` uses BM25 only."""
    chunks = load_runbooks(RUNBOOK_DIR)
    index = RunbookIndex(chunks, embeddings=None if offline_retrieval else get_embeddings())
    return build_graph(index, llm or get_llm())


__all__ = ["build_graph", "create_app", "load_runbooks", "render", "RunbookIndex"]
