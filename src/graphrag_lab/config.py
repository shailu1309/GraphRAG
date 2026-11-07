"""Single source of configuration for the GraphRAG lab.

Every module takes a Config argument instead of holding literals, and nothing
outside load_config() reads os.environ. A function's behaviour is therefore a
function of its arguments, and one Config can be logged next to every result.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv

REPO_ROOT = Path(__file__).resolve().parents[2]


@dataclass(frozen=True)
class Config:
    # Opus answers and judges; Haiku does the bulk extraction (~40x cheaper).
    answer_model: str = "claude-opus-5-5"
    judge_model: str = "claude-opus-5-5"
    extract_model: str = "claude-haiku-5-5"

    # Corpus generation: Opus for prose that reads like real internal docs.
    # Low effort is enough - the facts are given, only the writing is asked for.
    corpus_model: str = "claude-opus-5-5"
    corpus_effort: str = "low"
    corpus_max_tokens: int = 16000
    corpus_workers: int = 6
    llm_max_retries: int = 4

    # embed_dim must match the model: a mismatch surfaces much later as a
    # Chroma or Neo4j vector-index error, far from the cause.
    embed_model: str = "BAAI/bge-small-en-v1.5"
    embed_dim: int = 384
    # BGE is trained with this instruction on queries only, never on passages.
    embed_query_prefix: str = "Represent this sentence for searching relevant passages: "
    embed_batch_size: int = 32
    embed_device: str | None = None  # None: sentence-transformers picks mps/cuda/cpu

    # Shared by both systems - same chunks, only the retrieval differs.
    chunk_size_tokens: int = 600
    chunk_overlap_tokens: int = 80
    # A local tokenizer, used only to size chunks - not Claude's token count.
    chunk_tokenizer: str = "cl100k_base"

    top_k: int = 5
    seed: int = 0

    # Baseline retrieval. Hybrid fuses dense and BM25 ranks with reciprocal-rank
    # fusion; it keeps the baseline honest on exact names like "INC-0407".
    chroma_collection: str = "baseline_chunks"
    hybrid_candidates: int = 20
    rrf_k: int = 60

    answer_max_tokens: int = 16000
    answer_effort: str = "medium"

    # Graph construction. Extraction is one Haiku call per chunk.
    extract_effort: str = "medium"
    extract_max_tokens: int = 16000
    extract_workers: int = 8
    # Name+description cosine above this makes two entities a merge *candidate*;
    # the LLM tie-break still decides. It never merges on similarity alone.
    resolve_similarity: float = 0.85
    resolve_effort: str = "low"
    resolve_max_tokens: int = 4000
    max_merged_descriptions: int = 8
    neo4j_batch_size: int = 500
    entity_vector_index: str = "entity_embedding"

    # Evaluation.
    judge_effort: str = "medium"
    judge_max_tokens: int = 16000
    eval_workers: int = 6
    spot_check_n: int = 5
    results_dir: Path = REPO_ROOT / "results"

    # USD per million tokens (input, output), first-party API rates.
    price_per_mtok: dict = field(default_factory=lambda: {
        "claude-opus-5-5": (4.00, 20.00),
        "claude-haiku-5-5": (0.10, 0.50),
    })

    repo_root: Path = REPO_ROOT
    corpus_dir: Path = REPO_ROOT / "corpus"
    data_dir: Path = REPO_ROOT / "data"

    anthropic_api_key: str = field(default="", repr=False)
    neo4j_uri: str = "bolt://localhost:7687"
    neo4j_user: str = "neo4j"
    neo4j_password: str = field(default="", repr=False)

    def __post_init__(self) -> None:
        if not 0 <= self.chunk_overlap_tokens < self.chunk_size_tokens:
            raise ValueError(
                f"need 0 <= chunk_overlap_tokens ({self.chunk_overlap_tokens}) "
                f"< chunk_size_tokens ({self.chunk_size_tokens})"
            )
        if self.top_k < 1:
            raise ValueError(f"top_k must be >= 1, got {self.top_k}")
        if self.hybrid_candidates < self.top_k:
            raise ValueError(
                f"hybrid_candidates ({self.hybrid_candidates}) must be >= top_k ({self.top_k})"
            )

    # Derived paths are properties, not fields, so they cannot drift from data_dir.
    @property
    def chroma_dir(self) -> Path:
        return self.data_dir / "chroma"

    @property
    def extractions_dir(self) -> Path:
        return self.data_dir / "extractions"

    @property
    def graph_dir(self) -> Path:
        return self.data_dir / "graph"

    @property
    def usage_ledger(self) -> Path:
        return self.data_dir / "usage.jsonl"

    @property
    def chunks_path(self) -> Path:
        return self.data_dir / "chunks.jsonl"

    @property
    def embed_cache_dir(self) -> Path:
        return self.data_dir / "embed_cache" / self.embed_model.replace("/", "__")

    @property
    def synthetic_dir(self) -> Path:
        return self.corpus_dir / "synthetic"

    @property
    def ground_truth_path(self) -> Path:
        return self.corpus_dir / "ground_truth.yaml"

    # Server-side refusal fallback is offered on Opus, not on Haiku.
    @property
    def fallback_models(self) -> frozenset[str]:
        return frozenset({self.answer_model, self.judge_model, self.corpus_model})


def load_config() -> Config:
    """Resolve the environment exactly once, at the entry point."""
    load_dotenv(REPO_ROOT / ".env")

    required = ("ANTHROPIC_API_KEY", "NEO4J_PASSWORD")
    missing = [name for name in required if not os.environ.get(name)]
    if missing:
        raise RuntimeError(f"missing environment variables (check .env): {missing}")

    return Config(
        anthropic_api_key=os.environ["ANTHROPIC_API_KEY"],
        neo4j_uri=os.environ.get("NEO4J_URI", Config.neo4j_uri),
        neo4j_user=os.environ.get("NEO4J_USER", Config.neo4j_user),
        neo4j_password=os.environ["NEO4J_PASSWORD"],
    )
