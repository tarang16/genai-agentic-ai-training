"""Policy wording as clause-level chunks, searchable with BM25 and addressable by clause id."""
from __future__ import annotations

import re
from pathlib import Path

from rank_bm25 import BM25Okapi

from .config import POLICY_PATH


def _tokens(text: str) -> list[str]:
    return re.findall(r"[a-z0-9]+", text.lower())


class PolicyWording:
    def __init__(self, path: Path = POLICY_PATH):
        body = path.read_text(encoding="utf-8").split("---", 2)[-1]
        self.clauses: dict[str, dict] = {}
        for part in re.split(r"(?m)^## ", body)[1:]:
            heading, _, text = part.partition("\n")
            m = re.match(r"(\d+\.\d+)\s+(.*)", heading.strip())
            cid, title = (m.group(1), m.group(2)) if m else (heading.strip().split(":")[0], heading.strip())
            self.clauses[cid] = {"id": cid, "title": title, "text": " ".join(text.split())}
        self._ids = list(self.clauses)
        self._bm25 = BM25Okapi([_tokens(c["title"] + " " + c["text"]) for c in self.clauses.values()])

    def get(self, clause_id: str) -> dict:
        return self.clauses[clause_id]

    def search(self, query: str, k: int = 4) -> list[dict]:
        scores = self._bm25.get_scores(_tokens(query))
        order = sorted(range(len(scores)), key=lambda i: -scores[i])
        return [self.clauses[self._ids[i]] for i in order[:k] if scores[i] > 0]
