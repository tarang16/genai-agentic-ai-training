"""The support knowledge the agent can search: KB articles, past Freshdesk tickets, Jira issues.

In production these would be API calls (Freshdesk /api/v2/search/tickets, Jira /rest/api/3/search,
your KB's search endpoint). Here they are local files behind the same function signatures, so
swapping in the real APIs changes this module only; the graph and the MCP server stay the same.
"""
from __future__ import annotations

import csv
import json
import re
from dataclasses import dataclass
from pathlib import Path

from rank_bm25 import BM25Okapi

from .config import JIRA_JSON, KB_DIR, TICKETS_CSV

# Keep version strings ("1.0.7", "24h2") and model numbers ("vx2780") as single tokens:
# in support data the exact firmware or model is often the strongest signal.
_TOKEN = re.compile(r"[a-z0-9]+(?:[._-][a-z0-9]+)*")
_STOP = {"the", "a", "an", "and", "or", "to", "of", "in", "on", "is", "it", "my", "i", "for", "with",
         "not", "does", "do", "this", "that", "at", "after", "from", "me", "be", "are", "was"}


def tokens(text: str) -> list[str]:
    return [t for t in _TOKEN.findall(text.lower()) if t not in _STOP]


@dataclass
class Record:
    id: str
    kind: str            # kb | ticket | jira
    products: list[str]
    title: str
    text: str            # what gets searched and shown to the model
    links: list[str]     # ids this record points at (ticket -> KB / Jira)
    raw: dict


def _load_kb(folder: Path) -> list[Record]:
    out = []
    for path in sorted(folder.glob("*.md")):
        raw = path.read_text(encoding="utf-8")
        _, fm, body = raw.split("---", 2)
        meta = dict(line.split(":", 1) for line in fm.strip().splitlines())
        meta = {k.strip(): v.strip() for k, v in meta.items()}
        out.append(Record(meta["id"], "kb", [p.strip() for p in meta["products"].split(",")],
                          meta["title"], f"{meta['title']}\n{body.strip()}", [], meta))
    return out


def _load_tickets(path: Path) -> list[Record]:
    out = []
    with open(path, encoding="utf-8") as f:
        for row in csv.DictReader(f):
            links = [x for x in (row["kb_id"], row["jira_key"]) if x]
            text = f"{row['subject']}. {row['description']}\nResolution: {row['resolution']}"
            out.append(Record(row["ticket_id"], "ticket", [row["product"]], row["subject"], text, links, row))
    return out


def _load_jira(path: Path) -> list[Record]:
    out = []
    for issue in json.loads(path.read_text(encoding="utf-8")):
        text = (f"{issue['summary']}\nStatus: {issue['status']}. Fix: {issue['fix_version'] or 'none yet'}. "
                f"Workaround: {issue['workaround']}")
        out.append(Record(issue["key"], "jira", issue["products"], issue["summary"], text, [], issue))
    return out


class SupportKnowledge:
    def __init__(self, kb_dir: Path = KB_DIR, tickets_csv: Path = TICKETS_CSV, jira_json: Path = JIRA_JSON):
        self.records = {r.id: r for r in _load_kb(kb_dir) + _load_tickets(tickets_csv) + _load_jira(jira_json)}
        self._index: dict[str, tuple[list[Record], BM25Okapi]] = {}
        for kind in ("kb", "ticket", "jira"):
            recs = [r for r in self.records.values() if r.kind == kind]
            self._index[kind] = (recs, BM25Okapi([tokens(r.text + " " + " ".join(r.products)) for r in recs]))

    def search(self, kind: str, query: str, product: str | None = None, k: int = 3) -> list[dict]:
        recs, bm25 = self._index[kind]
        scores = bm25.get_scores(tokens(query))
        ranked = sorted(zip(recs, scores), key=lambda rs: -rs[1])
        hits = [(r, s) for r, s in ranked if s > 0 and (not product or product in r.products)][:k]
        return [{"id": r.id, "kind": r.kind, "title": r.title, "score": round(float(s), 2),
                 "links": r.links, "text": r.text} for r, s in hits]

    # The four tool functions below are what the LangGraph agent and the MCP server both expose.
    def search_kb(self, query: str, product: str | None = None, k: int = 3) -> list[dict]:
        return self.search("kb", query, product, k)

    def search_past_tickets(self, query: str, product: str | None = None, k: int = 3) -> list[dict]:
        return self.search("ticket", query, product, k)

    def search_jira(self, query: str, product: str | None = None, k: int = 2) -> list[dict]:
        return self.search("jira", query, product, k)

    def get(self, record_id: str) -> dict | None:
        r = self.records.get(record_id)
        return None if r is None else {"id": r.id, "kind": r.kind, "title": r.title, "text": r.text,
                                       "links": r.links, "raw": r.raw}
