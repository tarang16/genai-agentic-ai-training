"""Deterministic PRD review. These are the checks a good product lead does by eye, as code.

Using code (not a second LLM) as the critic makes the revise loop converge: the issue list is
specific, reproducible, and the loop stops when the list is empty or the budget runs out.
"""
from __future__ import annotations

import re

MIN_ACCEPTANCE_CRITERIA = 2
VAGUE = re.compile(r"\b(fast|quick(ly)?|easy|easily|intuitive|user[- ]friendly|seamless(ly)?|robust|efficient(ly)?|"
                   r"appropriate(ly)?|timely|as needed|etc)\b", re.I)


def critique(prd: dict, evidence: dict[str, dict], synthesis: dict, constraint_ids: set[str]) -> list[str]:
    issues: list[str] = []
    known = set(evidence)

    ids = [s["id"] for s in prd["user_stories"]]
    if len(ids) != len(set(ids)):
        issues.append("User story ids are not unique.")

    for s in prd["user_stories"]:
        if len(s["acceptance_criteria"]) < MIN_ACCEPTANCE_CRITERIA:
            issues.append(f"{s['id']}: needs at least {MIN_ACCEPTANCE_CRITERIA} acceptance criteria "
                          f"(has {len(s['acceptance_criteria'])}).")
        valid = [e for e in s["evidence_ids"] if e in known]
        if not valid:
            issues.append(f"{s['id']}: cites no valid evidence id; every story must trace to a source.")
        for i, ac in enumerate(s["acceptance_criteria"], 1):
            m = VAGUE.search(ac["then"])
            if m and not re.search(r"\d", ac["then"]):
                issues.append(f"{s['id']} AC{i}: 'then' uses the untestable word '{m.group(0)}' without a number.")

    for g in prd["goals"]:
        if not re.search(r"\d", g["metric"]):
            issues.append(f"Goal '{g['goal'][:50]}': metric has no numeric target.")

    handled = {d["conflict_id"] for d in prd["decisions"]} | {q["conflict_id"] for q in prd["open_questions"]}
    for c in synthesis.get("conflicts", []):
        if c["id"] not in handled:
            issues.append(f"Conflict {c['id']} ('{c['topic']}') is neither decided nor listed as an open question.")

    cited_in_constraints = {e for c in prd["constraints"] for e in c["evidence_ids"]}
    missing = sorted(constraint_ids - cited_in_constraints)
    if missing:
        issues.append(f"Constraints from evidence {', '.join(missing)} are not captured in the Constraints section.")

    bad = sorted({e for section in ("user_stories", "goals", "constraints", "decisions", "open_questions")
                  for item in prd[section] for e in item["evidence_ids"] if e not in known})
    if bad:
        issues.append(f"Unknown evidence ids cited (remove or fix): {', '.join(bad)}.")
    return issues


def coverage(prd: dict, evidence: dict[str, dict]) -> float:
    """Share of evidence lines that the PRD cites somewhere: a rough 'did we listen to everyone' metric."""
    cited = {e for section in ("user_stories", "goals", "constraints", "decisions", "open_questions")
             for item in prd[section] for e in item["evidence_ids"] if e in evidence}
    return len(cited) / max(1, len(evidence))
