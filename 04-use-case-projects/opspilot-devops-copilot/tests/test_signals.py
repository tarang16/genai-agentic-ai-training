import json

import pytest

from opspilot.config import GOLDEN_PATH, INCIDENT_DIR
from opspilot.signals import detect_platform, detect_signals, excerpt, is_mutating, redact

GOLDEN = [json.loads(l) for l in GOLDEN_PATH.read_text().splitlines() if l.strip()]


@pytest.mark.parametrize("case", GOLDEN, ids=[c["incident"] for c in GOLDEN])
def test_signals_and_platform_match_golden_set(case):
    log = (INCIDENT_DIR / case["incident"]).read_text(encoding="utf-8")
    signals = detect_signals(log)
    ids = {s.id for s in signals}
    assert set(case["signals"]) <= ids
    assert detect_platform(log, signals) == case["platform"]


def test_redaction_removes_secrets():
    log = (INCIDENT_DIR / "06_jenkins_scm_auth.log").read_text(encoding="utf-8")
    clean, n = redact(log)
    assert n >= 2
    assert "Sup3rS3cret" not in clean and "AKIAIOSFODNN7EXAMPLE" not in clean
    assert "NEXUS_PASSWORD=[REDACTED]" in clean


@pytest.mark.parametrize("cmd", [
    "kubectl rollout undo deployment/checkout-web -n checkout",
    "kubectl -n payments scale deployment/payments-api --replicas=4",
    "terraform force-unlock 5c7e2a91",
    "docker system prune -af",
    "helm upgrade payments ./chart",
])
def test_mutating_commands_detected(cmd):
    assert is_mutating(cmd)


@pytest.mark.parametrize("cmd", [
    "kubectl logs payments-api-7f9c -n payments --previous",
    "kubectl describe pod x -n y",
    "kubectl get nodes --show-labels",
    "terraform plan -refresh-only",
    "df -h",
])
def test_read_only_commands_not_flagged(cmd):
    assert not is_mutating(cmd)


def test_excerpt_keeps_signal_line_and_is_shorter():
    log = "\n".join(f"noise line {i}" for i in range(500)) + "\nReason: OOMKilled\n" + "\n".join(
        f"tail {i}" for i in range(5))
    out = excerpt(log, detect_signals(log))
    assert "OOMKilled" in out
    assert len(out.splitlines()) < 40
