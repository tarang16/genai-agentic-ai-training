"""Load raw inputs (meeting transcripts, a Slack export, a feedback CSV) into numbered evidence.

Every line a model may rely on gets a short, stable id (M1-07, S-03, F-10). The model cites
those ids; code then checks the ids exist. That is what makes the final PRD traceable: any
user story can be followed back to the exact sentence someone said.
"""
from __future__ import annotations

import csv
import json
import re
from pathlib import Path

PII = [
    (re.compile(r"\b[\w.+-]+@[\w-]+\.[\w.-]+\b"), "[EMAIL]"),
    (re.compile(r"(?<!\w)\+?\d[\d\s-]{8,}\d\b"), "[PHONE]"),
]


def scrub(text: str) -> str:
    for rx, repl in PII:
        text = rx.sub(repl, text)
    return text


def _transcript(path: Path, prefix: str) -> dict:
    lines = path.read_text(encoding="utf-8").splitlines()
    title = lines[0].replace("Meeting:", "").strip() if lines else path.stem
    items, n = [], 0
    for line in lines:
        m = re.match(r"^([A-Z][\w ]{0,30}):\s+(.+)$", line)
        if m and m.group(1) not in ("Meeting", "Date", "Attendees"):
            n += 1
            items.append({"id": f"{prefix}-{n:02d}", "speaker": m.group(1), "text": scrub(m.group(2))})
    return {"id": prefix, "kind": "meeting", "title": title, "file": path.name, "items": items}


def _slack(path: Path) -> dict:
    data = json.loads(path.read_text(encoding="utf-8"))
    items = [{"id": f"S-{i:02d}", "speaker": m["user"], "text": scrub(m["text"]), "ts": m["ts"]}
             for i, m in enumerate(data["messages"], 1)]
    return {"id": "S", "kind": "slack", "title": data.get("channel", path.stem), "file": path.name, "items": items}


def _feedback(path: Path) -> dict:
    with open(path, encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    items = [{"id": f"F-{int(r['id']):02d}", "speaker": f"{r['role']} ({r['region']})",
              "text": scrub(r["feedback"]), "rating": r.get("rating")} for r in rows]
    return {"id": "F", "kind": "feedback", "title": "Customer and field feedback", "file": path.name, "items": items}


def load_sources(folder: str | Path) -> list[dict]:
    folder = Path(folder)
    sources = [_transcript(p, f"M{i}") for i, p in enumerate(sorted(folder.glob("*.txt")), 1)]
    sources += [_slack(p) for p in sorted(folder.glob("*.json"))]
    sources += [_feedback(p) for p in sorted(folder.glob("*.csv"))]
    return sources


def evidence_index(sources: list[dict]) -> dict[str, dict]:
    return {it["id"]: {**it, "source": s["title"]} for s in sources for it in s["items"]}


def format_source(source: dict) -> str:
    return "\n".join(f"[{it['id']}] {it['speaker']}: {it['text']}" for it in source["items"])
