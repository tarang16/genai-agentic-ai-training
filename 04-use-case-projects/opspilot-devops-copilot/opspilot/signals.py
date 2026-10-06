"""Deterministic log parsing: secret redaction, failure signatures, log excerpting.

Everything in this file runs without an LLM. Pattern matching is cheaper, faster and
more predictable than a model for things a regex can recognise, so the model only
sees what is left after this step: a redacted, trimmed log plus named signals.
"""
from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass

# --- 1. Secret redaction ---------------------------------------------------------------
# Logs routinely leak credentials (env dumps, verbose curl, debug prints). Redact BEFORE
# anything leaves the machine: the LLM provider, the vector store, the trace store.
SECRET_PATTERNS: list[tuple[re.Pattern, str]] = [
    (re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----.*?-----END [A-Z ]*PRIVATE KEY-----", re.S),
     "[REDACTED_PRIVATE_KEY]"),
    (re.compile(r"\bAKIA[0-9A-Z]{16}\b"), "[REDACTED_AWS_KEY]"),
    (re.compile(r"\bgh[pousr]_[A-Za-z0-9]{36,}\b"), "[REDACTED_GITHUB_TOKEN]"),
    (re.compile(r"(?i)\bbearer\s+[A-Za-z0-9\-._~+/]+=*"), "Bearer [REDACTED]"),
    (re.compile(r"(?i)\b([A-Z0-9_]*(?:PASSWORD|PASSWD|SECRET|TOKEN|API_?KEY)[A-Z0-9_]*)\s*([:=])\s*\S+"),
     r"\1\2[REDACTED]"),
]


def redact(text: str) -> tuple[str, int]:
    """Return (redacted_text, number_of_redactions)."""
    total = 0
    for pattern, replacement in SECRET_PATTERNS:
        text, n = pattern.subn(replacement, text)
        total += n
    return text, total


# --- 2. Failure signatures -------------------------------------------------------------
# (signal_id, platform, regex). Signal ids match the `signals:` front matter in the runbooks,
# which is what lets retrieval filter on them.
SIGNATURES: list[tuple[str, str, re.Pattern]] = [
    (sid, platform, re.compile(rx, re.I)) for sid, platform, rx in [
        ("k8s_oomkilled", "kubernetes", r"OOMKilled|Exit Code:\s*137"),
        ("k8s_crashloop", "kubernetes", r"CrashLoopBackOff|Back-off restarting failed container"),
        ("k8s_imagepull", "kubernetes", r"ImagePullBackOff|ErrImagePull|manifest unknown|pull access denied"),
        ("k8s_scheduling", "kubernetes", r"FailedScheduling|Insufficient (cpu|memory)|untolerated taint|didn't match Pod's node affinity"),
        ("k8s_probe", "kubernetes", r"(Readiness|Liveness) probe failed"),
        ("jenkins_disk", "jenkins", r"No space left on device"),
        ("jenkins_scm_auth", "jenkins", r"Permission denied \(publickey\)|Authentication failed for|Could not read from remote repository"),
        ("jenkins_agent_offline", "jenkins", r"Waiting for next available executor|There are no nodes with the label|\bis offline\b"),
        ("jenkins_build_tool", "jenkins", r"npm ERR!|\[ERROR\] Failed to execute goal|BUILD FAILURE"),
        ("tf_state_lock", "terraform", r"Error acquiring the state lock"),
        ("tf_auth", "terraform", r"No valid credential sources found|ExpiredToken|InvalidClientTokenId|AuthorizationFailed"),
        ("tf_drift", "terraform", r"changed outside of Terraform"),
        ("tls_expired", "any", r"x509: certificate has expired|certificate verify failed|CERT_HAS_EXPIRED"),
        ("dns_resolution", "any", r"Could not resolve host|no such host|Temporary failure in name resolution"),
    ]
]

# Weak hints used only when no platform-specific signal fired.
PLATFORM_HINTS: list[tuple[str, re.Pattern]] = [
    ("kubernetes", re.compile(r"\bkubectl\b|\bkubelet\b|\bnamespace:", re.I)),
    ("jenkins", re.compile(r"\[Pipeline\]|Started by (timer|user|GitLab|GitHub)|Finished: FAILURE")),
    ("terraform", re.compile(r"\bterraform\b|tfstate", re.I)),
]


@dataclass(frozen=True)
class Signal:
    id: str
    platform: str
    line_no: int  # 1-based
    line: str


def detect_signals(log: str) -> list[Signal]:
    """First matching line for each signature, in log order."""
    found: dict[str, Signal] = {}
    for i, line in enumerate(log.splitlines(), start=1):
        for sid, platform, rx in SIGNATURES:
            if sid not in found and rx.search(line):
                found[sid] = Signal(sid, platform, i, line.strip())
    return sorted(found.values(), key=lambda s: s.line_no)


def detect_platform(log: str, signals: list[Signal]) -> str:
    votes = Counter(s.platform for s in signals if s.platform != "any")
    if votes:
        return votes.most_common(1)[0][0]
    for platform, rx in PLATFORM_HINTS:
        if rx.search(log):
            return platform
    return "unknown"


# --- 3. Context engineering: send the model the lines that matter -------------------
def excerpt(log: str, signals: list[Signal], window: int = 3, tail: int = 15, max_lines: int = 80) -> str:
    """Lines around each signal plus the tail of the log, with line numbers.

    A 5,000-line Jenkins log is mostly noise. Keeping the neighbourhood of each matched
    signature and the last lines (where the final error usually is) cuts tokens by 10-50x
    and stops the real error being 'lost in the middle'.
    """
    lines = log.splitlines()
    keep: set[int] = set(range(max(0, len(lines) - tail), len(lines)))
    for s in signals:
        keep.update(range(max(0, s.line_no - 1 - window), min(len(lines), s.line_no + window)))
    if not signals and len(lines) <= max_lines:
        keep = set(range(len(lines)))
    out, prev = [], -2
    for idx in sorted(keep)[-max_lines:]:
        if idx != prev + 1:
            out.append("...")
        out.append(f"{idx + 1:>4}| {lines[idx]}")
        prev = idx
    return "\n".join(out)


# --- 4. Safety: which commands change things --------------------------------------------
MUTATING = re.compile(
    r"\b(kubectl\s+(\S+\s+)*?(delete|apply|patch|scale|edit|replace|drain|cordon|taint|set|annotate|label|create)\b"
    r"|kubectl\s+rollout\s+(restart|undo)"
    r"|terraform\s+(apply|destroy|import|force-unlock|taint|state\s+(rm|mv|push))"
    r"|helm\s+(upgrade|install|uninstall|rollback)"
    r"|docker\s+(system\s+prune|rmi|rm|volume\s+rm)"
    r"|systemctl\s+(restart|stop|start)"
    r"|\brm\s+-|\bchmod\b|\bchown\b"
    r"|aws\s+\S+\s+(delete|put|update|create|terminate)\S*"
    r"|az\s+\S+\s+(delete|update|create)\b)",
    re.I,
)


def is_mutating(command: str) -> bool:
    """Deterministic check. The LLM also labels commands, but a safety gate must not
    depend on the model getting the label right, so this check can only ADD the flag."""
    return bool(MUTATING.search(command or ""))
