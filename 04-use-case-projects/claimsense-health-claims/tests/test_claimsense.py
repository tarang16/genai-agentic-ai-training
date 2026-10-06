import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from claimsense import PolicyWording, adjudicate, build_graph, render  # noqa: E402
from claimsense.config import CLAIMS_DIR, GOLDEN_PATH, ROOT  # noqa: E402
from claimsense.privacy import redact  # noqa: E402

CLAIMS = {p.stem: json.loads(p.read_text(encoding="utf-8")) for p in CLAIMS_DIR.glob("*.json")}
FACTS = json.loads((ROOT / "data" / "eval" / "reference_facts.json").read_text(encoding="utf-8"))
GOLDEN = [json.loads(l) for l in GOLDEN_PATH.read_text().splitlines() if l.strip()]
POLICY = PolicyWording()


# ---- rules engine: the part that moves money is fully tested without an LLM -----------
@pytest.mark.parametrize("g", GOLDEN, ids=lambda g: g["claim_id"])
def test_rules_engine_matches_golden(g):
    a = adjudicate(CLAIMS[g["claim_id"]], FACTS[g["claim_id"]])
    assert a.decision == g["decision"]
    assert a.payable == g["payable"]
    assert a.route == g["route"]
    assert set(g["clauses"]) <= {r["clause"] for r in a.reasons}


def test_room_rent_proportionate_deduction_spares_medicines():
    a = adjudicate(CLAIMS["CLM-003"], FACTS["CLM-003"])
    by_cat = {l.category: l for l in a.lines}
    assert by_cat["surgeon"].payable == 60000 * 0.625 and by_cat["surgeon"].clause == "4.1"
    assert by_cat["pharmacy"].payable == by_cat["pharmacy"].claimed  # not an associated expense


def test_keyword_backstop_catches_specific_disease_model_missed():
    facts = {**FACTS["CLM-002"], "specific_disease": "none"}  # model missed it
    assert adjudicate(CLAIMS["CLM-002"], facts).decision == "reject"


def test_accident_overrides_initial_waiting_period_only_for_accidents():
    facts = {**FACTS["CLM-006"], "is_accident": False}
    a = adjudicate(CLAIMS["CLM-006"], facts)
    assert a.decision == "reject" and a.reasons[0]["clause"] == "3.1"


def test_si_cap():
    claim = json.loads(json.dumps(CLAIMS["CLM-008"]))
    claim["policy"]["balance_sum_insured"] = 100000
    a = adjudicate(claim, FACTS["CLM-008"])
    assert a.payable == 100000 and a.decision == "partial"


# ---- privacy and policy -----------------------------------------------------------------
def test_redaction():
    text, n = redact(CLAIMS["CLM-001"]["discharge_summary"] + " " + CLAIMS["CLM-002"]["discharge_summary"]
                     + " " + CLAIMS["CLM-003"]["discharge_summary"])
    for secret in ["Rahul Deshmukh", "98220 11234", "448812", "Sunita Rao", "CP/IND/2025/019876", "kavya.iyer@example.com"]:
        assert secret not in text
    assert "36 y/o male" in text and n >= 6


def test_policy_clauses_parsed_and_searchable():
    assert {"3.1", "3.2", "3.3", "4.1", "4.2", "5.3", "5.5"} <= set(POLICY.clauses)
    assert POLICY.search("cataract surgery waiting", k=2)[0]["id"] in {"3.2", "4.3"}


# ---- graph with a fake LLM ----------------------------------------------------------------
class FakeLLM:
    def __init__(self, facts, memo):
        self.out = {"ClinicalFacts": facts, "Memo": memo}
        self.prompts = []

    def with_structured_output(self, schema):
        llm = self

        class Bound:
            def invoke(self, messages):
                llm.prompts.append(messages[-1].content)
                return schema(**llm.out[schema.__name__])
        return Bound()


def _memo(**kw):
    base = {"assessor_summary": "Partial approval: room rent proportionate deduction under 4.1.",
            "customer_letter": "Dear Policyholder, we will pay INR 1,17,625 against the claimed INR 1,64,500.",
            "clauses_cited": ["4.1", "5.5"]}
    return {**base, **kw}


def test_graph_end_to_end_and_pii_not_sent():
    llm = FakeLLM(FACTS["CLM-003"], _memo())
    state = build_graph(POLICY, llm).invoke({"claim": CLAIMS["CLM-003"]})
    f = state["final"]
    assert f["decision"] == "partial" and f["payable"] == 117625 and f["flags"] == []
    assert all("kavya" not in p.lower() for p in llm.prompts)
    assert "4.1" in {c["id"] for c in state["clauses"]}
    assert "CLM-003: PARTIAL" in render(state)


def test_guard_catches_invented_amount_and_clause():
    llm = FakeLLM(FACTS["CLM-001"], _memo(customer_letter="Dear Policyholder, we will pay INR 1,20,000.",
                                          clauses_cited=["9.9", "5.5"]))
    f = build_graph(POLICY, llm).invoke({"claim": CLAIMS["CLM-001"]})["final"]
    assert "memo_amount_mismatch" in f["flags"] and f["route"] == "human_review"
    assert f["memo"]["clauses_cited"] == ["5.5"]


def test_guard_adds_missing_rejection_clause():
    llm = FakeLLM(FACTS["CLM-002"], _memo(customer_letter="Dear Policyholder, your claim is not payable.",
                                          clauses_cited=[]))
    f = build_graph(POLICY, llm).invoke({"claim": CLAIMS["CLM-002"]})["final"]
    assert f["memo"]["clauses_cited"][0] == "3.2" and f["decision"] == "reject"


def test_unverifiable_quotes_force_human_review():
    facts = {**FACTS["CLM-001"], "evidence_quotes": ["patient has a perforated appendix"]}
    f = build_graph(POLICY, FakeLLM(facts, _memo(customer_letter="Dear Policyholder, INR 1,15,000 approved."))).invoke(
        {"claim": CLAIMS["CLM-001"]})["final"]
    assert "facts_unverified" in f["flags"] and f["route"] == "human_review"
