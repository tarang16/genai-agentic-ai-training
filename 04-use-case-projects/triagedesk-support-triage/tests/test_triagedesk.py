import asyncio
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from triagedesk import build_graph, render  # noqa: E402
from triagedesk.config import GOLDEN_PATH, INCOMING  # noqa: E402
from triagedesk.guardrails import injection_suspected, mask_pii, safety_risk  # noqa: E402
from triagedesk.store import SupportKnowledge  # noqa: E402

STORE = SupportKnowledge()
TICKETS = {t["ticket_id"]: t for t in map(json.loads, INCOMING.read_text(encoding="utf-8").splitlines())}
GOLDEN = [json.loads(l) for l in GOLDEN_PATH.read_text().splitlines() if l.strip()]


class FakeLLM:
    """Returns canned structured outputs per schema and records every prompt."""

    def __init__(self, classification=None, decision=None):
        self.out = {"Classification": classification or {"category": "power", "severity": "medium",
                                                          "sentiment": "frustrated", "search_queries": []},
                    "TriageDecision": decision}
        self.prompts = []

    def with_structured_output(self, schema):
        llm = self

        class Bound:
            def invoke(self, messages):
                llm.prompts.append(messages[-1].content)
                return schema(**llm.out[schema.__name__])
        return Bound()


def _decision(**kw):
    base = {"verdict": "known_bug", "matched_refs": ["DISP-430", "FD-20602"], "confidence": "high",
            "reasoning": "Same firmware 1.0.7 eco-mode power-off.", "action": "reply_with_workaround",
            "customer_reply": "Hi there, please update firmware to 1.0.8.", "internal_note": "Matches DISP-430."}
    return {**base, **kw}


# ---- guardrails ---------------------------------------------------------------------
def test_pii_masked():
    text, n = mask_pii(TICKETS["FD-21004"]["description"])
    assert n == 2 and "[EMAIL]" in text and "[PHONE]" in text and "rohan" not in text


def test_injection_and_safety_detection():
    assert injection_suspected(TICKETS["FD-21008"]["description"])
    assert safety_risk(TICKETS["FD-21007"]["description"])
    assert not injection_suspected(TICKETS["FD-21004"]["description"])
    assert not safety_risk(TICKETS["FD-21005"]["description"])


# ---- search -------------------------------------------------------------------------
@pytest.mark.parametrize("g", [g for g in GOLDEN if g["expected_refs"]], ids=lambda g: g["ticket_id"])
def test_gather_finds_expected_refs_without_llm(g):
    app = build_graph(STORE, FakeLLM(decision=_decision()))
    state = app.invoke({"ticket": TICKETS[g["ticket_id"]]})
    ids = {e["id"] for e in state["evidence"]}
    assert set(g["expected_refs"]) <= ids, ids


def test_product_filter():
    hits = STORE.search_past_tickets("touch not working", product="TD2455")
    assert hits and all(h["id"] in {"FD-20512", "FD-20760", "FD-20344", "FD-20633"} for h in hits)


# ---- decision guard -----------------------------------------------------------------
def test_known_bug_in_progress_becomes_workaround_and_fixed_bug_becomes_fix():
    app = build_graph(STORE, FakeLLM(decision=_decision(action="reply_with_workaround")))
    f = app.invoke({"ticket": TICKETS["FD-21004"]})["final"]
    assert f["action"] == "reply_with_fix"          # DISP-430 is Done -> fix exists
    assert f["auto_send_ok"] is True


def test_hallucinated_ref_dropped_and_verdict_downgraded():
    app = build_graph(STORE, FakeLLM(decision=_decision(matched_refs=["DISP-999"])))
    f = app.invoke({"ticket": TICKETS["FD-21004"]})["final"]
    assert f["matched_refs"] == [] and f["verdict"] == "new_issue" and f["action"] == "escalate_l2"
    assert f["auto_send_ok"] is False


def test_safety_ticket_always_escalates_with_fixed_reply():
    app = build_graph(STORE, FakeLLM(decision=_decision(verdict="known_issue", matched_refs=["KB-1005"],
                                                        action="start_rma")))
    f = app.invoke({"ticket": TICKETS["FD-21007"]})["final"]
    assert f["action"] == "escalate_l2" and "unplug" in f["customer_reply"] and not f["auto_send_ok"]


def test_injection_never_reaches_the_model():
    llm = FakeLLM(decision=_decision())
    state = build_graph(STORE, llm).invoke({"ticket": TICKETS["FD-21008"]})
    assert llm.prompts == []
    assert state["final"]["action"] == "escalate_l2" and state["final"]["customer_reply"] == ""


def test_masked_text_is_what_the_model_sees():
    llm = FakeLLM(decision=_decision())
    build_graph(STORE, llm).invoke({"ticket": TICKETS["FD-21004"]})
    assert all("rohan.k@example.com" not in p and "98765" not in p for p in llm.prompts)


def test_render_card():
    state = build_graph(STORE, FakeLLM(decision=_decision())).invoke({"ticket": TICKETS["FD-21004"]})
    card = render(state)
    assert "KNOWN BUG" in card and "DISP-430" in card


# ---- MCP server ---------------------------------------------------------------------
def test_mcp_server_tools_in_process(tmp_path, monkeypatch):
    import mcp_server
    from mcp import Client

    monkeypatch.setattr(mcp_server, "OUTBOX", tmp_path)

    async def run():
        async with Client(mcp_server.server) as client:
            names = {t.name for t in (await client.list_tools()).tools}
            res = await client.call_tool("search_jira", {"query": "touch unresponsive", "product": "TD2455"})
            note = await client.call_tool("add_internal_note", {"ticket_id": "FD-1", "note": "call me at a@b.com"})
            return names, res, note

    names, res, note = asyncio.run(run())
    assert {"search_kb", "search_past_tickets", "search_jira", "get_record", "add_internal_note"} <= names
    assert "DISP-455" in res.content[0].text
    saved = (tmp_path / "internal_notes.jsonl").read_text()
    assert "[EMAIL]" in saved and "a@b.com" not in saved
