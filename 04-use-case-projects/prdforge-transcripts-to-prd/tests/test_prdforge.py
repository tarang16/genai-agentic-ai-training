import copy
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from prdforge import build_graph, coverage, critique, load_sources, render  # noqa: E402
from prdforge.config import SOURCES_DIR  # noqa: E402
from prdforge.sources import evidence_index  # noqa: E402

SOURCES = load_sources(SOURCES_DIR)
EVIDENCE = evidence_index(SOURCES)


class FakeLLM:
    """Per-schema queue of canned outputs. Records how many calls each schema got."""

    def __init__(self, outputs: dict[str, list]):
        self.outputs, self.calls = outputs, {}

    def with_structured_output(self, schema):
        llm = self

        class Bound:
            def invoke(self, messages):
                name = schema.__name__
                llm.calls[name] = llm.calls.get(name, 0) + 1
                queue = llm.outputs[name]
                out = queue.pop(0) if len(queue) > 1 else queue[0]
                return schema(**(out(messages) if callable(out) else out))
        return Bound()


def _insights(messages):
    """Cite the first evidence id that appears in this source's prompt, plus one fake id."""
    text = messages[-1].content
    first = text.split("[", 1)[1].split("]", 1)[0]
    kind = "constraint" if first == "S-01" else "request"
    return {"insights": [{"type": kind, "statement": "x", "stakeholder": "y", "evidence_ids": [first, "ZZ-99"]}]}


SYNTH = {"themes": [{"name": "Weekly rhythm", "summary": "Reps plan on Monday", "evidence_ids": ["M2-02"]}],
         "conflicts": [{"id": "C1", "topic": "Alert frequency", "positions": [
             {"stakeholder": "Head of Sales", "position": "daily", "evidence_ids": ["M1-06"]},
             {"stakeholder": "Field Ops", "position": "weekly", "evidence_ids": ["M1-07"]}]}]}

GOOD_PRD = {
    "title": "Territory Alerts v1",
    "problem_statement": "Reps learn about prescribing drops weeks too late.",
    "goals": [{"goal": "Act sooner", "metric": "Median days from drop to visit: 35 -> under 10", "evidence_ids": ["M1-21"]}],
    "non_goals": ["Competitor attribution at HCP level"],
    "personas": ["Sales Rep", "District Manager"],
    "user_stories": [{
        "id": "US-01", "as_a": "sales rep", "i_want": "a Monday digest of flagged HCPs", "so_that": "I can plan visits",
        "priority": "Must",
        "acceptance_criteria": [
            {"given": "an HCP in deciles 8-10 with >= 10 baseline TRx", "when": "4-week TRx falls > 20%",
             "then": "the HCP appears in the next Monday 07:00 digest"},
            {"given": "a flagged HCP", "when": "the rep opens it", "then": "TRx change %, and days since last visit are shown"}],
        "evidence_ids": ["M1-18", "M2-02"]}],
    "constraints": [{"constraint": "No patient-level data", "category": "compliance", "evidence_ids": ["M1-14", "S-01"]}],
    "decisions": [],
    "open_questions": [{"question": "Daily vs weekly for decile 10?", "owner": "Head of Sales", "conflict_id": "C1",
                        "evidence_ids": ["M1-06", "M1-07"]}],
    "risks": ["Alert fatigue"],
}


def test_sources_are_numbered_and_scrubbed():
    kinds = {s["kind"] for s in SOURCES}
    assert kinds == {"meeting", "slack", "feedback"}
    assert "M1-01" in EVIDENCE and "S-10" in EVIDENCE and "F-10" in EVIDENCE
    assert EVIDENCE["M1-01"]["speaker"] == "Priya"
    assert "ravi.s@example.com" not in EVIDENCE["F-10"]["text"] and "[EMAIL]" in EVIDENCE["F-10"]["text"]


def test_good_prd_passes_critique():
    assert critique(GOOD_PRD, EVIDENCE, SYNTH, constraint_ids={"S-01"}) == []


def test_critique_catches_each_problem():
    bad = copy.deepcopy(GOOD_PRD)
    bad["user_stories"][0]["acceptance_criteria"] = [{"given": "a rep", "when": "they open the app", "then": "it loads fast"}]
    bad["user_stories"][0]["evidence_ids"] = ["NOPE-1"]
    bad["goals"][0]["metric"] = "Reps act sooner"
    bad["open_questions"] = []
    issues = "\n".join(critique(bad, EVIDENCE, SYNTH, constraint_ids={"S-01", "S-05"}))
    assert "at least 2 acceptance criteria" in issues
    assert "untestable word 'fast'" in issues
    assert "cites no valid evidence" in issues
    assert "no numeric target" in issues
    assert "Conflict C1" in issues
    assert "S-05" in issues
    assert "NOPE-1" in issues


def test_graph_fans_out_one_extract_per_source_and_drops_fake_ids():
    llm = FakeLLM({"SourceInsights": [_insights], "Synthesis": [SYNTH], "PRD": [GOOD_PRD]})
    state = build_graph(llm).invoke({"source_dir": str(SOURCES_DIR)})
    assert llm.calls["SourceInsights"] == len(SOURCES) == 4
    assert all("ZZ-99" not in i["evidence_ids"] for i in state["insights"])
    assert state["issues"] == [] and state["revisions"] == 0


def test_revise_loop_fixes_issues_then_stops():
    flawed = copy.deepcopy(GOOD_PRD)
    flawed["open_questions"] = []  # drops conflict C1
    llm = FakeLLM({"SourceInsights": [_insights], "Synthesis": [SYNTH], "PRD": [flawed, GOOD_PRD]})
    state = build_graph(llm).invoke({"source_dir": str(SOURCES_DIR)})
    assert state["revisions"] == 1
    assert state["issue_history"][0] >= 1 and state["issue_history"][-1] == 0


def test_revise_loop_respects_budget():
    flawed = copy.deepcopy(GOOD_PRD)
    flawed["goals"][0]["metric"] = "better"
    llm = FakeLLM({"SourceInsights": [_insights], "Synthesis": [SYNTH], "PRD": [flawed]})
    state = build_graph(llm, max_revisions=2).invoke({"source_dir": str(SOURCES_DIR)})
    assert state["revisions"] == 2 and len(state["issue_history"]) == 3 and state["issues"]


def test_render_has_traceability_appendix():
    llm = FakeLLM({"SourceInsights": [_insights], "Synthesis": [SYNTH], "PRD": [GOOD_PRD]})
    state = build_graph(llm).invoke({"source_dir": str(SOURCES_DIR)})
    md = render(state)
    assert "### US-01 (Must)" in md and "## Appendix: traceability" in md and "| M1-18 |" in md
    assert 0 < coverage(state["prd"], state["evidence"]) < 1


def test_evaluate_scores_run_without_llm():
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    from evaluate import score
    s = score(GOOD_PRD, [])
    assert s["constraints_captured"] == 0.5  # M1-14 covers patient-level data and templated text; SMS and data lag missing
    assert s["out_of_scope"] == 1.0 and s["critique_clean"] == 1.0
