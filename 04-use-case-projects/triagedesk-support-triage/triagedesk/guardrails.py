"""Input guardrails that run before the model sees a ticket. Customer text is untrusted input."""
import re

PII_PATTERNS = [
    (re.compile(r"\b[\w.+-]+@[\w-]+\.[\w.-]+\b"), "[EMAIL]"),
    (re.compile(r"(?<!\w)(?:\+?\d{1,3}[\s-]?)?\d{5}[\s-]?\d{5}\b|\+?\d{1,3}[\s-]?\(?\d{3}\)?[\s-]?\d{3}[\s-]?\d{4}\b"), "[PHONE]"),
    (re.compile(r"\b(?:\d[ -]?){13,16}\b"), "[CARD]"),
]

INJECTION_PATTERNS = re.compile(
    r"ignore (all |any )?(previous|prior|above) instructions|you are now|admin mode|developer mode"
    r"|system prompt|reveal (your|the) (instructions|prompt)|internal (notes|escalation notes)|act as",
    re.I,
)

# Physical-safety words: these tickets must reach a human immediately, whatever the KB says.
SAFETY_PATTERNS = re.compile(r"burn(ing)? smell|smells? of burning|smoke|sparks?|fire|electric shock|melt(ed|ing)|swollen", re.I)


def mask_pii(text: str) -> tuple[str, int]:
    total = 0
    for rx, repl in PII_PATTERNS:
        text, n = rx.subn(repl, text)
        total += n
    return text, total


def injection_suspected(text: str) -> bool:
    return bool(INJECTION_PATTERNS.search(text))


def safety_risk(text: str) -> bool:
    return bool(SAFETY_PATTERNS.search(text))
