import os
from pathlib import Path

try:  # pick up OPENAI_API_KEY etc. from a local .env if python-dotenv is installed
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

ROOT = Path(__file__).resolve().parent.parent
SOURCES_DIR = ROOT / "data" / "sources"
OUTPUT_DIR = ROOT / "output"

CHAT_MODEL = os.getenv("PRDFORGE_CHAT_MODEL", "gpt-4o-mini")
DEFAULT_CONTEXT = ("Commercial analytics platform used by pharma field sales reps (iPad app + web dashboard) "
                   "and their managers. HCP = healthcare professional. Rx/TRx/NRx = prescriptions.")


def get_llm():
    from langchain_openai import ChatOpenAI
    return ChatOpenAI(model=CHAT_MODEL, temperature=0.2)
