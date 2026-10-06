import os
from pathlib import Path

try:  # pick up OPENAI_API_KEY etc. from a local .env if python-dotenv is installed
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
KB_DIR = DATA / "kb"
TICKETS_CSV = DATA / "past_tickets.csv"
JIRA_JSON = DATA / "jira_issues.json"
INCOMING = DATA / "incoming" / "new_tickets.jsonl"
GOLDEN_PATH = DATA / "eval" / "golden.jsonl"
OUTBOX = DATA / "outbox"

CHAT_MODEL = os.getenv("TRIAGEDESK_CHAT_MODEL", "gpt-4o-mini")


def get_llm():
    from langchain_openai import ChatOpenAI
    return ChatOpenAI(model=CHAT_MODEL, temperature=0)
