"""ClaimSense LangGraph.

    redact -> extract_facts -> adjudicate -> retrieve_clauses -> write_memo -> guard -> END

redact            mask name, phone, email, policy number, UHID (no LLM)
extract_facts     LLM reads the discharge summary into ClinicalFacts, with verbatim quotes
adjudicate        deterministic rules: waiting periods, exclusions, room-rent ratio, co-pay, SI cap
retrieve_clauses  the clauses the decision relied on, plus BM25 hits for the diagnosis (RAG for the memo)
write_memo        LLM writes the assessor summary and customer letter from the computed numbers
guard             quotes must exist in the summary, cited clauses must exist, every amount in the
                  letter must be one the rules engine produced; otherwise route to a human
"""
from __future__ import annotations

import json
import re
from dataclasses import asdict
from typing import TypedDict

from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.graph import END, START, StateGraph

from .policy import PolicyWording
from .privacy import redact
from .rules import adjudicate
from .schemas import ClinicalFacts, Memo


class ClaimState(TypedDict, total=False):
    claim: dict
    redacted_summary: str
    redactions: int
    facts: dict
    quote_check: dict
    adjudication: dict
    clauses: list[dict]
    memo: dict
    final: dict


FACTS_PROMPT = """You are a medical claims analyst. Read the discharge summary and fill in the facts.
- Judge only what the summary documents. If it documents something as a possible cause, answer 'unclear'.
- related_to_declared_ped: compare with the declared pre-existing diseases provided.
- specific_disease: choose from the allowed list if the diagnosis or surgery is one of them, else 'none'.
- evidence_quotes: copy short phrases verbatim from the summary that support your answers.
Do not decide whether the claim is payable."""

MEMO_PROMPT = """Write the claim decision memo and the customer letter.
- The decision and every amount are already computed. Use ONLY the amounts given; do not calculate new ones.
- Cite the policy clauses that support each deduction or rejection, by clause id.
- For a rejection, name the clause and explain it in plain language, as the regulator requires.
- For a referral, tell the customer the claim is under medical review; do not hint at the outcome.
- Address the customer as 'Dear Policyholder'. Never include names, phone numbers or policy numbers."""

_AMOUNT = re.compile(r"(?:INR|Rs\.?|₹)\s*([\d,]+(?:\.\d+)?)", re.I)


def _amounts_in(text: str) -> set[float]:
    return {float(m.replace(",", "")) for m in _AMOUNT.findall(text)}


def build_graph(policy: PolicyWording, llm):
    fact_reader = llm.with_structured_output(ClinicalFacts)
    memo_writer = llm.with_structured_output(Memo)

    def redact_node(state: ClaimState) -> ClaimState:
        text, n = redact(state["claim"]["discharge_summary"])
        return {"redacted_summary": text, "redactions": n}

    def extract_facts(state: ClaimState) -> ClaimState:
        ped = ", ".join(state["claim"]["policy"]["declared_ped"]) or "none declared"
        msg = f"Declared pre-existing diseases: {ped}\n\nDISCHARGE SUMMARY\n{state['redacted_summary']}"
        facts: ClinicalFacts = fact_reader.invoke([SystemMessage(FACTS_PROMPT), HumanMessage(msg)])
        summary = state["redacted_summary"].lower()
        found = [q for q in facts.evidence_quotes if q.lower().strip(" .") in summary]
        return {"facts": facts.model_dump(),
                "quote_check": {"total": len(facts.evidence_quotes), "verified": len(found),
                                "unverified": [q for q in facts.evidence_quotes if q not in found]}}

    def adjudicate_node(state: ClaimState) -> ClaimState:
        return {"adjudication": asdict(adjudicate(state["claim"], state["facts"]))}

    def retrieve_clauses(state: ClaimState) -> ClaimState:
        used = {r["clause"] for r in state["adjudication"]["reasons"]}
        f = state["facts"]
        hits = policy.search(f"{f['primary_diagnosis']} {f['procedure']}", k=3)
        clauses = [policy.get(c) for c in sorted(used) if c in policy.clauses]
        clauses += [h for h in hits if h["id"] not in used]
        return {"clauses": clauses}

    def write_memo(state: ClaimState) -> ClaimState:
        a = state["adjudication"]
        payable = "pending medical review" if a["payable"] is None else f"INR {a['payable']:,.0f}"
        msg = (f"CLAIM {state['claim']['claim_id']} ({state['claim']['claim_type']}), hospital: {state['claim']['hospital']}\n"
               f"FACTS: {json.dumps(state['facts'])}\n\n"
               f"DECISION: {a['decision']} | claimed INR {a['claimed']:,.0f} | payable {payable}\n"
               f"LINE ITEMS: {json.dumps(a['lines'])}\nREASONS: {json.dumps(a['reasons'])}\nFLAGS: {a['flags']}\n\n"
               "POLICY CLAUSES\n" + "\n".join(f"[{c['id']}] {c['title']}: {c['text']}" for c in state["clauses"]))
        memo: Memo = memo_writer.invoke([SystemMessage(MEMO_PROMPT), HumanMessage(msg)])
        return {"memo": memo.model_dump()}

    def guard(state: ClaimState) -> ClaimState:
        a, m = state["adjudication"], dict(state["memo"])
        flags, notes = list(a["flags"]), []
        valid = set(policy.clauses)
        bad = [c for c in m["clauses_cited"] if c not in valid]
        m["clauses_cited"] = [c for c in m["clauses_cited"] if c in valid]
        if bad:
            notes.append(f"Removed non-existent clauses cited by the model: {bad}")
        if a["decision"] == "reject":
            for r in a["reasons"][:1]:
                if r["clause"] not in m["clauses_cited"]:
                    m["clauses_cited"].insert(0, r["clause"])
                    notes.append(f"Added rejection clause {r['clause']} the letter failed to cite.")

        allowed = {round(a["claimed"]), round(a["provisional_payable"])}
        allowed |= {round(x) for ln in a["lines"] for x in (ln["claimed"], ln["payable"], ln["claimed"] - ln["payable"])}
        allowed |= {round(float(x.replace(",", ""))) for r in a["reasons"] for x in re.findall(r"\d[\d,]*(?:\.\d+)?", r["text"])}
        stray = sorted(x for x in _amounts_in(m["customer_letter"] + " " + m["assessor_summary"]) if round(x) not in allowed)
        if stray:
            flags.append("memo_amount_mismatch")
            notes.append(f"Letter contains amounts the rules engine did not produce: {stray}")

        qc = state["quote_check"]
        if qc["total"] and qc["verified"] == 0:
            flags.append("facts_unverified")
            notes.append("None of the model's evidence quotes were found in the discharge summary.")

        route = "auto" if a["route"] == "auto" and not flags else "human_review"
        return {"final": {"decision": a["decision"], "payable": a["payable"], "route": route, "flags": flags,
                          "guard_notes": notes, "memo": m}}

    g = StateGraph(ClaimState)
    for name, fn in [("redact", redact_node), ("extract_facts", extract_facts), ("adjudicate", adjudicate_node),
                     ("retrieve_clauses", retrieve_clauses), ("write_memo", write_memo), ("guard", guard)]:
        g.add_node(name, fn)
    g.add_edge(START, "redact")
    g.add_edge("redact", "extract_facts")
    g.add_edge("extract_facts", "adjudicate")
    g.add_edge("adjudicate", "retrieve_clauses")
    g.add_edge("retrieve_clauses", "write_memo")
    g.add_edge("write_memo", "guard")
    g.add_edge("guard", END)
    return g.compile()
