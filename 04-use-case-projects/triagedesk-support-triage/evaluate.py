"""Score TriageDesk on the labelled incoming tickets.

    python evaluate.py --offline   # guardrails + evidence recall (search only), no API key
    python evaluate.py             # full pipeline with the LLM

Metrics
  evidence_recall   expected refs found by the search + link-following step
  verdict_acc       known_bug / known_issue / new_issue correct
  ref_acc           expected refs appear in matched_refs
  escalation_acc    escalated exactly when it must be (safety, injection, genuinely new)
"""
import argparse
import json

from triagedesk import build_graph
from triagedesk.config import GOLDEN_PATH, INCOMING, get_llm
from triagedesk.store import SupportKnowledge


class _QueriesOnly:
    """Offline stand-in: no query rewriting, just the raw ticket text."""
    def with_structured_output(self, schema):
        canned = {
            "Classification": dict(category="other", severity="medium", sentiment="neutral", search_queries=[]),
            "TriageDecision": dict(verdict="new_issue", matched_refs=[], confidence="low", reasoning="offline",
                                   action="escalate_l2", customer_reply="", internal_note=""),
        }[schema.__name__]
        return type("Bound", (), {"invoke": lambda self, _: schema(**canned)})()


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--offline", action="store_true")
    args = ap.parse_args()

    tickets = {t["ticket_id"]: t for t in map(json.loads, INCOMING.read_text(encoding="utf-8").splitlines()) if t}
    golden = [json.loads(l) for l in GOLDEN_PATH.read_text().splitlines() if l.strip()]
    app = build_graph(SupportKnowledge(), _QueriesOnly() if args.offline else get_llm())

    rows, totals = [], {}
    for g in golden:
        state = app.invoke({"ticket": tickets[g["ticket_id"]]})
        f = state["final"]
        ev = {e["id"] for e in state.get("evidence", [])}
        r = {"ticket": g["ticket_id"]}
        if g["expected_refs"]:
            r["evidence_recall"] = len(ev & set(g["expected_refs"])) / len(g["expected_refs"])
        if not args.offline:  # offline, the stand-in model escalates everything, so this would be meaningless
            r["escalation_acc"] = float((f["action"] == "escalate_l2") == g["must_escalate"])
            r["verdict_acc"] = float(f["verdict"] == g["expected_verdict"])
            if g["expected_refs"]:
                r["ref_acc"] = float(set(g["expected_refs"]) <= set(f["matched_refs"]))
        rows.append(r)
        for k, v in r.items():
            if isinstance(v, float):
                totals.setdefault(k, []).append(v)

    print(f"{'ticket':10} " + " ".join(f"{k:>16}" for k in totals))
    for r in rows:
        print(f"{r['ticket']:10} " + " ".join(f"{r[k]:>16.2f}" if k in r else f"{'-':>16}" for k in totals))
    print("-" * (11 + 17 * len(totals)))
    print(f"{'MEAN':10} " + " ".join(f"{sum(v) / len(v):>16.2f}" for v in totals.values()))


if __name__ == "__main__":
    main()
