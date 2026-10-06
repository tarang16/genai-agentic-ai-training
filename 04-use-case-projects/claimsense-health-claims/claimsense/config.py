import os
from pathlib import Path

try:  # pick up OPENAI_API_KEY etc. from a local .env if python-dotenv is installed
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

ROOT = Path(__file__).resolve().parent.parent
POLICY_PATH = ROOT / "data" / "policy" / "policy_wording.md"
CLAIMS_DIR = ROOT / "data" / "claims"
GOLDEN_PATH = ROOT / "data" / "eval" / "golden.jsonl"

CHAT_MODEL = os.getenv("CLAIMSENSE_CHAT_MODEL", "gpt-4o-mini")

# Business rules that are configuration, not code. Change them here, not in prompts.
AUTO_APPROVE_LIMIT = int(os.getenv("CLAIMSENSE_AUTO_APPROVE_LIMIT", "300000"))   # INR
SUBMISSION_WINDOW_DAYS = 30


def get_llm():
    from langchain_openai import ChatOpenAI
    return ChatOpenAI(model=CHAT_MODEL, temperature=0)
