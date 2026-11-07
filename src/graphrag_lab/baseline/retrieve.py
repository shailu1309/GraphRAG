"""Baseline retrieval: dense top-k, or dense + BM25 fused with reciprocal-rank fusion.

This is a good-faith baseline, not a straw man. If GraphRAG only beats a weak
baseline, the comparison proves nothing.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

import numpy as np
from rank_bm25 import BM25Okapi

from graphrag_lab.baseline.index import open_collection
from graphrag_lab.chunking import Chunk, read_chunks
from graphrag_lab.config import Config
from graphrag_lab.embeddings import Embedder

# Keeps hyphenated IDs whole: "INC-0407" -> "inc-0407", "TECH-1" -> "tech-1".
_TOKEN = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)*")


def tokenize(text: str) -> list[str]:
    return _TOKEN.findall(text.lower())


@dataclass(frozen=True)
class Retrieved:
    chunk: Chunk
    rank: int
    score: float  # cosine similarity (dense) or fused RRF score (hybrid)


class BaselineRetriever:
    def __init__(self, cfg: Config, *, hybrid: bool) -> None:
        self.cfg = cfg
        self.hybrid = hybrid
        self.chunks = read_chunks(cfg)
        self.by_id = {c.chunk_id: c for c in self.chunks}
        self.embedder = Embedder(cfg)
        self.collection = open_collection(cfg)
        if self.collection.count() != len(self.chunks):
            raise RuntimeError(
                f"Chroma has {self.collection.count()} chunks, chunks.jsonl has "
                f"{len(self.chunks)} - re-run baseline.index"
            )
        self.bm25 = BM25Okapi([tokenize(c.embed_text) for c in self.chunks]) if hybrid else None

    @property
    def name(self) -> str:
        return "baseline_hybrid" if self.hybrid else "baseline_dense"

    def _dense(self, question: str, n: int) -> list[tuple[str, float]]:
        query = self.embedder.embed_query(question)
        result = self.collection.query(query_embeddings=[query.tolist()], n_results=n)
        # Chroma returns cosine *distance*; 1 - distance is the similarity.
        return [(cid, 1.0 - d) for cid, d in zip(result["ids"][0], result["distances"][0])]

    def _sparse(self, question: str, n: int) -> list[tuple[str, float]]:
        scores = self.bm25.get_scores(tokenize(question))  # (num_chunks,)
        top = np.argsort(-scores)[:n]
        return [(self.chunks[i].chunk_id, float(scores[i])) for i in top]

    def retrieve(self, question: str) -> list[Retrieved]:
        k = self.cfg.top_k
        if not self.hybrid:
            ranked = self._dense(question, k)
        else:
            n = self.cfg.hybrid_candidates
            fused: dict[str, float] = {}
            # RRF uses only ranks, so the two incomparable score scales never mix.
            for ranking in (self._dense(question, n), self._sparse(question, n)):
                for rank, (cid, _) in enumerate(ranking, start=1):
                    fused[cid] = fused.get(cid, 0.0) + 1.0 / (self.cfg.rrf_k + rank)
            ranked = sorted(fused.items(), key=lambda kv: kv[1], reverse=True)[:k]

        return [
            Retrieved(chunk=self.by_id[cid], rank=rank, score=score)
            for rank, (cid, score) in enumerate(ranked, start=1)
        ]
