"""Render a finished (or paused) run as a Markdown incident note."""


def render(state: dict) -> str:
    d = state.get("diagnosis") or {}
    status = state.get("status", "awaiting_approval")
    lines = [
        f"# OpsPilot incident note: {status.replace('_', ' ').upper()}",
        "",
        f"**Platform:** {state.get('platform', '?')}  ",
        f"**Signals:** {', '.join(s['id'] for s in state.get('signals', [])) or 'none'}  ",
        f"**Secrets redacted before analysis:** {state.get('redactions', 0)}",
        "",
    ]
    if status == "escalated":
        lines += ["## Escalated to on-call", *[f"- {r}" for r in state.get("escalation_reasons", [])], ""]
    if d:
        lines += [f"## Root cause ({d['confidence']} confidence)", d["root_cause"], "", "## Evidence"]
        lines += [f"    {e}" for e in d["evidence_lines"]] or ["_none quoted_"]
        lines += ["", "## Steps"]
        for i, s in enumerate(d["steps"], 1):
            tag = " **[CHANGES STATE - needs approval]**" if s["mutating"] else ""
            lines.append(f"{i}. {s['description']}{tag}")
            if s["command"]:
                lines.append(f"   `{s['command']}`")
        lines += ["", "## Runbook sources"]
        lines += [f"- {c}" for c in d["citations"]] or ["- none"]
    if status in ("approved", "rejected"):
        lines += ["", f"**Change decision:** {status} by {state.get('approver') or 'unknown'}"]
    return "\n".join(lines)
