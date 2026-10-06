"""Render a triage result as the card an agent sees when they open the ticket."""

VERDICT_LABEL = {"known_bug": "KNOWN BUG", "known_issue": "KNOWN ISSUE", "new_issue": "NEW / UNKNOWN"}


def render(state: dict) -> str:
    t, f = state["ticket"], state["final"]
    c = state.get("classification") or {}
    lines = [
        f"### {t['ticket_id']} - {t['subject']}  ({t['product']})",
        f"**Verdict:** {VERDICT_LABEL.get(f.get('verdict'), '?')}  |  **Action:** `{f.get('action')}`  |  "
        f"**Confidence:** {f.get('confidence')}  |  **Auto-send OK:** {'yes' if f.get('auto_send_ok') else 'no'}",
    ]
    if c:
        lines.append(f"**Category:** {c['category']}  |  **Severity:** {c['severity']}  |  **Sentiment:** {c['sentiment']}")
    if f.get("flags"):
        lines.append(f"**Flags:** {', '.join(f['flags'])}")
    lines += ["", f"**Matched:** {', '.join(f.get('matched_refs') or []) or 'nothing'}",
              f"**Why:** {f.get('reasoning', '')}"]
    if f.get("guard_notes"):
        lines += ["", "**Guardrails:**", *[f"- {n}" for n in f["guard_notes"]]]
    if f.get("internal_note"):
        lines += ["", f"**Internal note:** {f['internal_note']}"]
    if f.get("customer_reply"):
        lines += ["", "**Draft reply:**", "", *[f"> {l}" for l in f["customer_reply"].splitlines()]]
    return "\n".join(lines)
