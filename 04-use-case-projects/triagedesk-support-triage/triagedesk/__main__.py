"""CLI:  python -m triagedesk [path/to/tickets.jsonl]   (default: data/incoming/new_tickets.jsonl)"""
import json
import sys
from pathlib import Path

from . import create_app, render
from .config import INCOMING


def main() -> None:
    path = Path(sys.argv[1]) if len(sys.argv) > 1 else INCOMING
    app = create_app()
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            state = app.invoke({"ticket": json.loads(line)})
            print(render(state), end="\n\n" + "-" * 80 + "\n\n")


if __name__ == "__main__":
    main()
