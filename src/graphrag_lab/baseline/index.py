"""Chunk the corpus, embed the chunks, and rebuild the Chroma collection.

    PYTHONPATH=src python -m graphrag_lab.baseline.index

Also writes data/chunks.jsonl - the shared chunk set that GraphRAG reads too.
"""

from __future__ import annotations

import logging
from collections import Counter

import chromadb

from graphrag_lab.chunking import chunk_corpus, write_chunks
from graphrag_lab.config import Config, load_config
from graphrag_lab.embeddings import Embedder

logger = logging.getLogger(__name__)


def open_collection(cfg: Config, *, rebuild: bool = False):
    client = chromadb.PersistentClient(path=str(cfg.chroma_dir))
    if rebuild and cfg.chroma_collection in {c.name for c in client.list_collections()}:
        client.delete_collection(cfg.chroma_collection)
    # embedding_function=None: we always pass our own vectors, so Chroma must
    # never embed (or download a default model) behind our back.
    return client.get_or_create_collection(
        cfg.chroma_collection,
        configuration={"hnsw": {"space": "cosine"}},
        embedding_function=None,
    )


def build_index(cfg: Config) -> None:
    chunks = chunk_corpus(cfg)
    write_chunks(cfg, chunks)

    vectors = Embedder(cfg).embed_documents([c.embed_text for c in chunks])
    collection = open_collection(cfg, rebuild=True)
    collection.add(
        ids=[c.chunk_id for c in chunks],
        embeddings=vectors.tolist(),
        documents=[c.embed_text for c in chunks],
        metadatas=[{"doc_id": c.doc_id, "header_path": c.header_path} for c in chunks],
    )

    per_doc = Counter(c.doc_id for c in chunks)
    logger.info(
        "indexed %d chunks from %d documents (%d-%d chunks per document) into %s",
        len(chunks), len(per_doc), min(per_doc.values()), max(per_doc.values()),
        cfg.chroma_dir,
    )


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    build_index(load_config())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
