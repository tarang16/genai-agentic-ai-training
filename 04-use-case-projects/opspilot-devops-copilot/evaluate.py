"""Score OpsPilot against the golden incident set.

    python evaluate.py --offline   # parsing + BM25 retrieval only, no API key needed
    python evaluate.py             # full pipeline: hybrid retrieval + LLM diagnosis

Metrics
  signal_recall     expected failure signatures found by the parser
  platform_acc      platform detected correctly
  retrieval_hit@3   expected runbook/section in the top 3 retrieved
  outcome_acc       escalated exactly when it should (uncovered incidents) and diagnosed otherwise
  citation_acc      final answer cites the expected runbook (diagnosed cases only)
  root_cause_hit    all root-cause keywords appear in the root cause / evidence
"""
import argparse
import json
import uuid

from langgraph.types import Command

from opspilot import build_graph
from opspilot.config import GOLDEN_PATH, INCIDENT_DIR, RUNBOOK_DIR, get_embeddings, get_llm
from opspilot.retrieval import RunbookIndex, load_runbooks
from opspilot.signals import detect_platform, detect_signals


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--offline", action="store_true")
    args = ap.parse_args()

    golden = [json.loads(l) for l in GOLDEN_PATH.read_text().splitlines() if l.strip()]
    index = RunbookIndex(load_runbooks(RUNBOOK_DIR), embeddings=None if args.offline else get_embeddings())
    app = None if args.offline else build_graph(index, get_llm())

    rows, totals = [], {}
    for case in golden:
        log = (INCIDENT_DIR / case["incident"]).read_text(encoding="utf-8")
        sig = detect_signals(log)
        platform = detect_platform(log, sig)
        found = {s.id for s in sig}
        query = " ".join(s.id + " " + s.line for s in sig) or log[-1500:]
        top = [c.id for c, _ in index.search(query, k=3, platform=platform)]
        r = {
            "incident": case["incident"],
            "signal_recall": len(found & set(case["signals"])) / len(case["signals"]) if case["signals"] else 1.0,
            "platform_acc": float(platform == case["platform"]),
        }
        if case["expected_runbook"]:
            r["retrieval_hit@3"] = float(any(t.startswith(case["expected_runbook"]) for t in top))
        if app is not None:
            cfg = {"configurable": {"thread_id": str(uuid.uuid4())}}
            state = app.invoke({"log": log}, cfg)
            if "__interrupt__" in state:  # auto-reject in evaluation: we score the diagnosis, not the change
                state = app.invoke(Command(resume={"approved": False, "approver": "eval"}), cfg)
            escalated = state["status"] == "escalated"
            r["outcome_acc"] = float(escalated == (case["expected_outcome"] == "escalate"))
            d = state["diagnosis"]
            if case["expected_runbook"]:
                r["citation_acc"] = float(any(c.startswith(case["expected_runbook"].split("#")[0]) for c in d["citations"]))
                text = (d["root_cause"] + " " + " ".join(d["evidence_lines"])).lower()
                r["root_cause_hit"] = float(all(k in text for k in case["root_cause_keywords"]))
            r["status"] = state["status"]
        rows.append(r)
        for k, v in r.items():
            if isinstance(v, float):
                totals.setdefault(k, []).append(v)

    print(f"{'incident':32} " + " ".join(f"{k:>15}" for k in totals))
    for r in rows:
        print(f"{r['incident']:32} " + " ".join(f"{r[k]:>15.2f}" if k in r else f"{'-':>15}" for k in totals))
    print("-" * (33 + 16 * len(totals)))
    print(f"{'MEAN':32} " + " ".join(f"{sum(v) / len(v):>15.2f}" for v in totals.values()))


if __name__ == "__main__":
    main()
