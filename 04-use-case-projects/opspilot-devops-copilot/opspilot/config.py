import os
from pathlib import Path

try:  # pick up OPENAI_API_KEY etc. from a local .env if python-dotenv is installed
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

ROOT = Path(__file__).resolve().parent.parent
RUNBOOK_DIR = ROOT / "data" / "runbooks"
INCIDENT_DIR = ROOT / "data" / "incidents"
GOLDEN_PATH = ROOT / "data" / "eval" / "golden.jsonl"

CHAT_MODEL = os.getenv("OPSPILOT_CHAT_MODEL", "gpt-4o-mini")
EMBED_MODEL = os.getenv("OPSPILOT_EMBED_MODEL", "text-embedding-3-small")


def get_llm():
    from langchain_openai import ChatOpenAI
    return ChatOpenAI(model=CHAT_MODEL, temperature=0)


def get_embeddings():
    from langchain_openai import OpenAIEmbeddings
    return OpenAIEmbeddings(model=EMBED_MODEL)
