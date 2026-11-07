"""Local sentence-transformers embeddings with an on-disk cache.

Vectors are L2-normalised, so a dot product is the cosine similarity. The cache
key is a hash of (model, text), so a re-index computes only new or changed text.
"""

from __future__ import annotations

import hashlib
import logging

import numpy as np
from sentence_transformers import SentenceTransformer

from graphrag_lab.config import Config

logger = logging.getLogger(__name__)


class Embedder:
    def __init__(self, cfg: Config) -> None:
        self.cfg = cfg
        self.model = SentenceTransformer(cfg.embed_model, device=cfg.embed_device)
        cfg.embed_cache_dir.mkdir(parents=True, exist_ok=True)

    def _cache_path(self, text: str):
        digest = hashlib.sha256(f"{self.cfg.embed_model}\n{text}".encode()).hexdigest()
        return self.cfg.embed_cache_dir / f"{digest}.npy"

    def _encode(self, texts: list[str]) -> np.ndarray:
        vectors = self.model.encode(
            texts,
            batch_size=self.cfg.embed_batch_size,
            normalize_embeddings=True,
            convert_to_numpy=True,
        )
        # vectors: (N, embed_dim)
        assert vectors.shape == (len(texts), self.cfg.embed_dim), (
            f"expected ({len(texts)}, {self.cfg.embed_dim}), got {vectors.shape}"
        )
        return vectors

    def embed_documents(self, texts: list[str]) -> np.ndarray:
        """Passages -> (N, embed_dim). Uses the cache."""
        paths = [self._cache_path(t) for t in texts]
        missing = [i for i, p in enumerate(paths) if not p.exists()]
        if missing:
            logger.info("embedding %d of %d texts (rest cached)", len(missing), len(texts))
            fresh = self._encode([texts[i] for i in missing])
            for i, vec in zip(missing, fresh):
                np.save(paths[i], vec)
        return np.stack([np.load(p) for p in paths])

    def embed_query(self, query: str) -> np.ndarray:
        """Question -> (embed_dim,). Not cached: queries are cheap and rarely repeat."""
        return self._encode([self.cfg.embed_query_prefix + query])[0]
