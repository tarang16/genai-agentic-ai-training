"""PRDForge: meeting transcripts, Slack threads and feedback in; a traceable PRD out."""
from .config import DEFAULT_CONTEXT, SOURCES_DIR, get_llm
from .critique import coverage, critique
from .graph import build_graph
from .render import render
from .sources import load_sources


def generate(source_dir=SOURCES_DIR, product_context: str = DEFAULT_CONTEXT, llm=None, max_revisions: int = 2) -> dict:
    app = build_graph(llm or get_llm(), max_revisions=max_revisions)
    return app.invoke({"source_dir": str(source_dir), "product_context": product_context})


__all__ = ["build_graph", "coverage", "critique", "generate", "load_sources", "render"]
