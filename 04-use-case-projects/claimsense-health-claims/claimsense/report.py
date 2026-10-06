"""Render a processed claim as the assessor's worksheet."""


def _inr(x) -> str:
    return "pending review" if x is None else f"INR {x:,.0f}"


def render(state: dict) -> str:
    c, a, f = state["claim"], state["adjudication"], state["final"]
    lines = [
        f"## {c['claim_id']}: {f['decision'].upper()}  →  {_inr(f['payable'])}",
        f"**Route:** {f['route'].replace('_', ' ')}  |  **Claimed:** {_inr(a['claimed'])}  |  "
        f"**Cover:** {a['policy_months']} months  |  **PII redacted:** {state.get('redactions', 0)}",
    ]
    if f["flags"]:
        lines.append(f"**Flags:** {', '.join(f['flags'])}")
    fx = state["facts"]
    lines += ["", f"**Diagnosis:** {fx['primary_diagnosis']}  |  **Procedure:** {fx['procedure']}  |  "
              f"**Accident:** {fx['is_accident']}  |  **PED-related:** {fx['related_to_declared_ped']}  |  "
              f"**Alcohol-related:** {fx['alcohol_or_substance_related']}", "",
              "| Item | Claimed | Payable | Reason | Clause |", "|---|---:|---:|---|---|"]
    lines += [f"| {l['description']} | {l['claimed']:,.0f} | {l['payable']:,.0f} | {l['reason']} | {l['clause']} |"
              for l in a["lines"]]
    lines += ["", "**Decision basis:**"]
    lines += [f"- [{r['clause']}] {r['text']}" for r in a["reasons"]] or ["- No deductions."]
    if f["guard_notes"]:
        lines += ["", "**Guardrail notes:**", *[f"- {n}" for n in f["guard_notes"]]]
    m = f["memo"]
    lines += ["", "**Assessor summary:** " + m["assessor_summary"], "", "**Customer letter (draft):**", "",
              *[f"> {l}" for l in m["customer_letter"].splitlines()]]
    return "\n".join(lines)
