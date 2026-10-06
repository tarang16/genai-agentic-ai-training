"""Score ClaimSense on the eight labelled sample claims.

    python evaluate.py --offline   # rules engine on reference facts (no API key): should be 100%
    python evaluate.py             # full pipeline: LLM extraction -> rules -> memo -> guard

Metrics
  fact_acc        LLM-extracted facts that match the reference facts (accident, specific disease, PED, alcohol)
  decision_acc    approve / partial / reject / refer correct
  payable_acc     payable amount exact to the rupee
  route_acc       auto vs human review correct
  memo_clean      letter passes the guard (no invented amounts or clauses)
"""
import argparse
import json

from claimsense import PolicyWording, adjudicate, build_graph
from claimsense.config import CLAIMS_DIR, GOLDEN_PATH, ROOT, get_llm

FACT_KEYS = ["is_accident", "specific_disease", "related_to_declared_ped", "alcohol_or_substance_related"]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--offline", action="store_true")
    args = ap.parse_args()

    golden = [json.loads(l) for l in GOLDEN_PATH.read_text().splitlines() if l.strip()]
    ref = json.loads((ROOT / "data" / "eval" / "reference_facts.json").read_text(encoding="utf-8"))
    app = None if args.offline else build_graph(PolicyWording(), get_llm())

    rows, totals = [], {}
    for g in golden:
        claim = json.loads((CLAIMS_DIR / f"{g['claim_id']}.json").read_text(encoding="utf-8"))
        r = {"claim": g["claim_id"]}
        if app is None:
            a = adjudicate(claim, ref[g["claim_id"]])
            decision, payable, route = a.decision, a.payable, a.route
        else:
            state = app.invoke({"claim": claim})
            f = state["final"]
            decision, payable, route = f["decision"], f["payable"], f["route"]
            r["fact_acc"] = sum(state["facts"][k] == ref[g["claim_id"]][k] for k in FACT_KEYS) / len(FACT_KEYS)
            r["memo_clean"] = float(not any(fl in f["flags"] for fl in ("memo_amount_mismatch", "facts_unverified")))
        r["decision_acc"] = float(decision == g["decision"])
        r["payable_acc"] = float(payable == g["payable"])
        r["route_acc"] = float(route == g["route"])
        r["detail"] = f"{decision} / {payable} / {route}"
        rows.append(r)
        for k, v in r.items():
            if isinstance(v, float):
                totals.setdefault(k, []).append(v)

    print(f"{'claim':9} " + " ".join(f"{k:>13}" for k in totals) + "   decision / payable / route")
    for r in rows:
        print(f"{r['claim']:9} " + " ".join(f"{r[k]:>13.2f}" if k in r else f"{'-':>13}" for k in totals) + f"   {r['detail']}")
    print("-" * (10 + 14 * len(totals)))
    print(f"{'MEAN':9} " + " ".join(f"{sum(v) / len(v):>13.2f}" for v in totals.values()))


if __name__ == "__main__":
    main()
