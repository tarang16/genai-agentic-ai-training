import json

import pytest
from langgraph.types import Command

from conftest import FakeStructuredLLM
from opspilot import build_graph
from opspilot.config import GOLDEN_PATH, INCIDENT_DIR, RUNBOOK_DIR
from opspilot.retrieval import RunbookIndex, load_runbooks
from opspilot.signals import detect_platform, detect_signals

GOLDEN = [json.loads(l) for l in GOLDEN_PATH.read_text().splitlines() if l.strip()]
INDEX = RunbookIndex(load_runbooks(RUNBOOK_DIR))  # BM25-only: no API key needed


def test_chunks_have_citable_ids():
    ids = [c.id for c in INDEX.chunks]
    assert len(ids) == len(set(ids))
    assert "k8s-oomkilled.md#remediation" in ids
    assert "terraform-state-and-auth.md#state-lock-held" in ids


@pytest.mark.parametrize("case", [c for c in GOLDEN if c["expected_runbook"]], ids=lambda c: c["incident"])
def test_offline_retrieval_hit_at_3(case):
    """The right runbook (or section) is in the top 3 with BM25 alone."""
    log = (INCIDENT_DIR / case["incident"]).read_text(encoding="utf-8")
    sig = detect_signals(log)
    query = " ".join(s.id + " " + s.line for s in sig)
    top = [c.id for c, _ in INDEX.search(query, k=3, platform=detect_platform(log, sig))]
    assert any(t.startswith(case["expected_runbook"]) for t in top), top


def _diag(citations, steps=None, insufficient=False, confidence="high"):
    return {
        "root_cause": "JVM heap (-Xmx1536m) is larger than the 1Gi container limit.",
        "confidence": confidence,
        "evidence_lines": ["Reason:       OOMKilled"],
        "citations": citations,
        "steps": steps or [{"description": "Check usage", "command": "kubectl top pod p -n payments", "mutating": False}],
        "insufficient_evidence": insufficient,
    }


def _run(diag, incident="01_payments_oomkilled.log"):
    llm = FakeStructuredLLM(diag)
    app = build_graph(INDEX, llm)
    cfg = {"configurable": {"thread_id": incident}}
    state = app.invoke({"log": (INCIDENT_DIR / incident).read_text(encoding="utf-8")}, cfg)
    return app, cfg, state, llm


def test_read_only_plan_finishes_without_approval():
    _, _, state, llm = _run(_diag(["k8s-oomkilled.md#diagnosis"]))
    assert state["status"] == "read_only"
    prompt = llm.calls[0][1].content
    assert "[k8s-oomkilled.md#" in prompt and "OOMKilled" in prompt


def test_mutating_step_pauses_for_approval_even_if_llm_mislabels_it():
    steps = [{"description": "Scale out", "command": "kubectl scale deployment/payments-api --replicas=4 -n payments",
              "mutating": False}]  # model got the label wrong; the guard must catch it
    app, cfg, state, _ = _run(_diag(["k8s-oomkilled.md#remediation"], steps))
    assert "__interrupt__" in state
    assert state["__interrupt__"][0].value["commands"] == [steps[0]["command"]]
    final = app.invoke(Command(resume={"approved": False, "approver": "oncall"}), cfg)
    assert final["status"] == "rejected"


def test_hallucinated_citation_is_dropped_and_escalates():
    _, _, state, _ = _run(_diag(["made-up-runbook.md#fix"]))
    assert state["diagnosis"]["citations"] == []
    assert state["status"] == "escalated"


def test_uncovered_incident_escalates():
    _, _, state, _ = _run(_diag([], insufficient=True, confidence="low"), "08_kafka_consumer_lag.log")
    assert state["status"] == "escalated"
    assert state["platform"] == "unknown"


def test_secrets_never_reach_the_model():
    _, _, _, llm = _run(_diag(["jenkins-pipeline-failures.md#scm-checkout-authentication-failure"]),
                        "06_jenkins_scm_auth.log")
    prompt = llm.calls[0][1].content
    assert "Sup3rS3cret" not in prompt and "AKIAIOSFODNN7EXAMPLE" not in prompt


def test_expand_pulls_in_remediation_for_single_topic_runbook():
    hits = INDEX.search("k8s_oomkilled Reason: OOMKilled", k=1, platform="kubernetes")
    ids = [c.id for c, _ in INDEX.expand(hits)]
    assert "k8s-oomkilled.md#remediation" in ids


def test_expand_keeps_multi_topic_runbook_focused():
    hits = INDEX.search("jenkins_disk No space left on device", k=1, platform="jenkins")
    ids = [c.id for c, _ in INDEX.expand(hits)]
    assert ids == ["jenkins-pipeline-failures.md#disk-full-on-agent", "jenkins-pipeline-failures.md#escalation"]


def test_hybrid_mode_with_vector_store():
    """Exercise the Chroma + RRF code path with fake embeddings (no API key). Quality is measured
    by evaluate.py with real embeddings, not here."""
    from langchain_core.embeddings import DeterministicFakeEmbedding
    hybrid = RunbookIndex(load_runbooks(RUNBOOK_DIR), embeddings=DeterministicFakeEmbedding(size=64))
    hits = hybrid.search("tf_state_lock Error acquiring the state lock", k=3, platform="terraform")
    assert len(hits) == 3  # fake vectors are random, so only the mechanics are checked here
    assert all(c.platform in ("terraform", "any") for c, _ in hits)
