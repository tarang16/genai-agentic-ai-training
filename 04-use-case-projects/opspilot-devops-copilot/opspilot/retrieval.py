"""Runbook loading, header-aware chunking and hybrid retrieval (BM25 + vectors, fused with RRF)."""
from __future__ import annotations

import re
import uuid
from dataclasses import dataclass, field
from pathlib import Path

from rank_bm25 import BM25Okapi


@dataclass
class Chunk:
    id: str             # "k8s-oomkilled.md#remediation" -- what the model must cite
    source: str         # runbook file name
    title: str          # runbook title
    section: str        # section heading
    platform: str
    signals: list[str] = field(default_factory=list)
    text: str = ""


def _slug(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")


def _front_matter(raw: str) -> tuple[dict, str]:
    meta: dict[str, str] = {}
    if raw.startswith("---"):
        _, fm, raw = raw.split("---", 2)
        for line in fm.strip().splitlines():
            k, _, v = line.partition(":")
            meta[k.strip()] = v.strip()
    return meta, raw.strip()


def load_runbooks(folder: str | Path) -> list[Chunk]:
    """One chunk per `## ` section. Each chunk starts with the runbook title so it still
    makes sense when retrieved alone (a cheap form of contextual retrieval)."""
    chunks: list[Chunk] = []
    for path in sorted(Path(folder).glob("*.md")):
        meta, body = _front_matter(path.read_text(encoding="utf-8"))
        title = next((l[2:].strip() for l in body.splitlines() if l.startswith("# ")), path.stem)
        signals = [s.strip() for s in meta.get("signals", "").split(",") if s.strip()]
        for part in re.split(r"(?m)^## ", body)[1:]:
            heading, _, text = part.partition("\n")
            chunks.append(Chunk(
                id=f"{path.name}#{_slug(heading)}",
                source=path.name, title=title, section=heading.strip(),
                platform=meta.get("platform", "any"), signals=signals,
                text=f"{title}\n## {heading.strip()}\n{text.strip()}",
            ))
    return chunks


def _tokens(text: str) -> list[str]:
    return re.findall(r"[a-z0-9_]+", text.lower())


class RunbookIndex:
    """Hybrid search. BM25 catches exact error strings ("OOMKilled", "ConditionalCheckFailed")
    that embeddings blur; vectors catch paraphrases. Reciprocal Rank Fusion merges the two
    rankings without having to calibrate their scores against each other.

    Pass `embeddings=None` for BM25-only mode: no API key needed (used by tests and --offline).
    """

    def __init__(self, chunks: list[Chunk], embeddings=None):
        self.chunks = chunks
        self.by_id = {c.id: c for c in chunks}
        # Index signal ids too, so a detected signal matches its runbook's front matter.
        self.bm25 = BM25Okapi([_tokens(c.text + " " + " ".join(c.signals)) for c in chunks])
        self.vectors = None
        if embeddings is not None:
            from langchain_chroma import Chroma
            self.vectors = Chroma.from_texts(
                texts=[c.text for c in chunks],
                ids=[c.id for c in chunks],
                metadatas=[{"id": c.id, "platform": c.platform, "source": c.source} for c in chunks],
                embedding=embeddings,
                collection_name=f"runbooks-{uuid.uuid4().hex[:8]}",
            )

    def _allowed(self, chunk: Chunk, platform: str | None) -> bool:
        return platform in (None, "unknown") or chunk.platform in (platform, "any")

    def search(self, query: str, k: int = 4, platform: str | None = None, rrf_k: int = 60) -> list[tuple[Chunk, float]]:
        scores = self.bm25.get_scores(_tokens(query))
        bm25_rank = [self.chunks[i].id for i in sorted(range(len(scores)), key=lambda i: -scores[i]) if scores[i] > 0]
        rankings = [bm25_rank]
        if self.vectors is not None:
            hits = self.vectors.similarity_search(query, k=min(12, len(self.chunks)))
            rankings.append([h.metadata["id"] for h in hits])
        fused: dict[str, float] = {}
        for ranking in rankings:
            for rank, cid in enumerate(ranking):
                if cid and self._allowed(self.by_id[cid], platform):
                    fused[cid] = fused.get(cid, 0.0) + 1.0 / (rrf_k + rank + 1)
        best = sorted(fused.items(), key=lambda kv: -kv[1])[:k]
        return [(self.by_id[cid], score) for cid, score in best]

    def expand(self, hits: list[tuple[Chunk, float]], max_sections: int = 8) -> list[tuple[Chunk, float]]:
        """Small-to-big (parent-document) retrieval.

        Small chunks match precisely, but a 'Symptoms' section alone is useless: the model also
        needs that runbook's Diagnosis and Remediation. When a hit is one of the generic sections
        of a single-topic runbook, pull in its sibling sections. Multi-topic runbooks (one heading
        per failure, like the Jenkins one) keep only the matched section plus its Escalation.
        """
        out: dict[str, tuple[Chunk, float]] = {}
        for chunk, score in hits:
            siblings = [c for c in self.chunks if c.source == chunk.source]
            if chunk.section.lower() in GENERIC_SECTIONS:
                family = [c for c in siblings if c.section.lower() in GENERIC_SECTIONS]
            else:
                family = [chunk] + [c for c in siblings if c.section.lower() == "escalation"]
            for c in family:
                if c.id not in out:
                    out[c.id] = (c, score if c.id == chunk.id else 0.0)
            if len(out) >= max_sections:
                break
        return list(out.values())[:max_sections]


GENERIC_SECTIONS = {"symptoms", "diagnosis", "remediation", "escalation"}
