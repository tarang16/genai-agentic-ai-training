"""Redact personal identifiers from clinical text before it is sent to an LLM.

Health data is sensitive personal data under India's DPDP Act 2023 (and PHI under HIPAA elsewhere).
The model needs the clinical story, not who the patient is. Age and sex stay; they matter clinically.
"""
import re

PATTERNS = [
    (re.compile(r"\b(Mr|Mrs|Ms|Miss|Dr|Shri|Smt)\.?\s+(?:[A-Z]\.\s*)*[A-Z][a-z]+(?:\s+[A-Z][a-z]+){0,3}"), r"\1. [NAME]"),
    (re.compile(r"\b[\w.+-]+@[\w-]+\.[\w.-]+\b"), "[EMAIL]"),
    (re.compile(r"(?<!\d)(?:\+91[\s-]?)?[6-9]\d{4}[\s-]?\d{5}(?!\d)"), "[PHONE]"),
    (re.compile(r"\b[A-Z]{2}/[A-Z]{3}/\d{4}/\d{6}\b"), "[POLICY_NO]"),
    (re.compile(r"\bUHID\s*[:#]?\s*\w+", re.I), "UHID [ID]"),
]


def redact(text: str) -> tuple[str, int]:
    total = 0
    for rx, repl in PATTERNS:
        text, n = rx.subn(repl, text)
        total += n
    return text, total
