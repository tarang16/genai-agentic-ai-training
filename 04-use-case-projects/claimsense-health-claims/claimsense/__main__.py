"""CLI:  python -m claimsense data/claims/CLM-003.json [more.json ...]   (default: all sample claims)"""
import json
import sys
from pathlib import Path

from . import create_app, render
from .config import CLAIMS_DIR


def main() -> None:
    paths = [Path(p) for p in sys.argv[1:]] or sorted(CLAIMS_DIR.glob("*.json"))
    app = create_app()
    for p in paths:
        state = app.invoke({"claim": json.loads(p.read_text(encoding="utf-8"))})
        print(render(state), end="\n\n" + "-" * 80 + "\n\n")


if __name__ == "__main__":
    main()
