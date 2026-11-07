"""Connectivity smoke test for the GraphRAG lab.

Checks the four moving parts independently and reports every failure in one run,
rather than dying on the first one:

  1. Anthropic API - credentials valid, required models visible, inference works
  2. Embeddings    - sentence-transformers model loads, returns the expected dim
  3. Chroma        - persistent client round-trips a document
  4. Neo4j         - Bolt driver writes, reads back, and cleans up

Deliberately standalone: it imports nothing from graphrag_lab, so it can run
before that package exists, and a failure is never ambiguous between
"infrastructure is down" and "my own package does not import".

Usage:
    python scripts/smoke_test.py

Exits 0 only if all four checks pass.
"""

from __future__ import annotations

import logging
import os
import sys
import uuid
from dataclasses import dataclass, field
from pathlib import Path

logger = logging.getLogger("smoke_test")

REPO_ROOT = Path(__file__).resolve().parents[1]


@dataclass(frozen=True)
class SmokeConfig:
    """Everything this script needs, in one place. No literals below this point.

    `embed_model` and `embed_dim` must stay in step with src/graphrag_lab/config.py
    once that exists - they are duplicated here only to keep this script standalone.
    """

    # Cheapest model that still proves inference works end to end. The expensive
    # model is checked for *availability* only, not called.
    ping_model: str = "claude-haiku-5-5"
    answer_model: str = "claude-opus-5-5"
    ping_prompt: str = "Reply with exactly: OK"
    ping_max_tokens: int = 256
    ping_effort: str = "low"

    embed_model: str = "BAAI/bge-small-en-v1.5"
    embed_dim: int = 384
    embed_probe_text: str = "Project Meridian depends on the Atlas platform."

    chroma_dir: Path = REPO_ROOT / "data" / "chroma_smoke"
    chroma_collection: str = "smoke_test"

    neo4j_label: str = "SmokeTest"

    # Resolved from the environment at the entry point, never read inside a check.
    anthropic_api_key: str = field(default="", repr=False)
    neo4j_uri: str = "bolt://localhost:7687"
    neo4j_user: str = "neo4j"
    neo4j_password: str = field(default="", repr=False)


def check_claude(cfg: SmokeConfig) -> str:
    """Prove the API key works, the models we need are visible, and inference runs."""
    import anthropic

    if not cfg.anthropic_api_key:
        raise RuntimeError("ANTHROPIC_API_KEY is not set (check .env)")

    client = anthropic.Anthropic(api_key=cfg.anthropic_api_key)

    # models.list() costs no tokens, so it is the cheapest possible proof that the
    # credentials are valid and that this Console org can see both models.
    available = {m.id for m in client.models.list()}
    missing = [m for m in (cfg.ping_model, cfg.answer_model) if m not in available]
    if missing:
        raise RuntimeError(
            f"models not available to this API key: {missing}. "
            f"Visible models: {sorted(available)}"
        )

    response = client.messages.create(
        model=cfg.ping_model,
        max_tokens=cfg.ping_max_tokens,
        output_config={"effort": cfg.ping_effort},
        messages=[{"role": "user", "content": cfg.ping_prompt}],
    )

    # Guard stop_reason before touching content: a refusal returns HTTP 200.
    if response.stop_reason == "refusal":
        raise RuntimeError(f"request refused: {response.stop_details}")
    if response.stop_reason == "max_tokens":
        raise RuntimeError(
            f"hit max_tokens ({cfg.ping_max_tokens}) before finishing - raise it"
        )

    # Thinking is on by default on current models, so content[0] is not
    # necessarily the text block. Filter by type instead of indexing.
    text = "".join(b.text for b in response.content if b.type == "text").strip()
    if not text:
        raise RuntimeError(
            f"no text block in response (stop_reason={response.stop_reason})"
        )

    usage = response.usage
    return (
        f"{cfg.ping_model} replied {text!r} "
        f"({usage.input_tokens} in / {usage.output_tokens} out); "
        f"{cfg.answer_model} available"
    )


def check_embeddings(cfg: SmokeConfig) -> str:
    """Prove the embedding model loads locally and returns the expected shape."""
    from sentence_transformers import SentenceTransformer

    model = SentenceTransformer(cfg.embed_model)
    vector = model.encode(cfg.embed_probe_text, normalize_embeddings=True)

    # Shape is load-bearing: a dim mismatch here would surface much later as a
    # silent Chroma or Neo4j vector-index error.
    assert vector.ndim == 1, f"expected (embed_dim,), got {tuple(vector.shape)}"
    assert vector.shape[0] == cfg.embed_dim, (
        f"expected dim {cfg.embed_dim}, got {vector.shape[0]} - "
        f"update SmokeConfig.embed_dim and config.py together"
    )

    norm = float((vector**2).sum() ** 0.5)
    return (
        f"{cfg.embed_model} -> shape {tuple(vector.shape)}, "
        f"L2 norm {norm:.4f}, device {model.device}"
    )


def check_chroma(cfg: SmokeConfig) -> str:
    """Prove a persistent collection round-trips a document, then clean up."""
    import chromadb

    cfg.chroma_dir.mkdir(parents=True, exist_ok=True)
    client = chromadb.PersistentClient(path=str(cfg.chroma_dir))

    # Drop any collection left behind by an earlier failed run, so a stale
    # document cannot make this check pass for the wrong reason.
    if cfg.chroma_collection in {c.name for c in client.list_collections()}:
        client.delete_collection(cfg.chroma_collection)

    doc_id = f"smoke-{uuid.uuid4().hex[:8]}"
    collection = client.create_collection(cfg.chroma_collection)
    try:
        collection.add(
            ids=[doc_id],
            documents=[cfg.embed_probe_text],
            embeddings=[[0.0] * cfg.embed_dim],
        )
        got = collection.get(ids=[doc_id])
        if got["ids"] != [doc_id]:
            raise RuntimeError(f"round-trip failed: wrote {doc_id}, read {got['ids']}")
        count = collection.count()
    finally:
        client.delete_collection(cfg.chroma_collection)

    return f"persisted and read back {doc_id} (count {count}) at {cfg.chroma_dir}"


def check_neo4j(cfg: SmokeConfig) -> str:
    """Prove Bolt connectivity with a write, a read back, and a delete."""
    from neo4j import GraphDatabase

    if not cfg.neo4j_password:
        raise RuntimeError("NEO4J_PASSWORD is not set (check .env)")

    driver = GraphDatabase.driver(
        cfg.neo4j_uri, auth=(cfg.neo4j_user, cfg.neo4j_password)
    )
    node_id = f"smoke-{uuid.uuid4().hex[:8]}"
    try:
        driver.verify_connectivity()
        with driver.session() as session:
            try:
                session.run(
                    f"CREATE (n:{cfg.neo4j_label} {{id: $id}})", id=node_id
                ).consume()
                record = session.run(
                    f"MATCH (n:{cfg.neo4j_label} {{id: $id}}) RETURN n.id AS id",
                    id=node_id,
                ).single()
                if record is None or record["id"] != node_id:
                    raise RuntimeError(f"wrote {node_id} but could not read it back")
            finally:
                session.run(
                    f"MATCH (n:{cfg.neo4j_label} {{id: $id}}) DELETE n", id=node_id
                ).consume()

        server = driver.get_server_info()
        agent = server.agent
    finally:
        driver.close()

    return f"wrote, read and deleted {node_id} on {agent} at {cfg.neo4j_uri}"


# Ordered so the cheapest and most likely-to-be-misconfigured check runs first.
CHECKS = (
    ("Anthropic API", check_claude),
    ("Embeddings", check_embeddings),
    ("Chroma", check_chroma),
    ("Neo4j", check_neo4j),
)


def load_config() -> SmokeConfig:
    """Resolve the environment exactly once, at the entry point."""
    try:
        from dotenv import load_dotenv
    except ImportError:
        logger.warning("python-dotenv not installed; reading the ambient environment")
    else:
        load_dotenv(REPO_ROOT / ".env")

    return SmokeConfig(
        anthropic_api_key=os.environ.get("ANTHROPIC_API_KEY", ""),
        neo4j_uri=os.environ.get("NEO4J_URI", SmokeConfig.neo4j_uri),
        neo4j_user=os.environ.get("NEO4J_USER", SmokeConfig.neo4j_user),
        neo4j_password=os.environ.get("NEO4J_PASSWORD", ""),
    )


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    cfg = load_config()

    failures: list[str] = []
    for name, check in CHECKS:
        try:
            detail = check(cfg)
        # A diagnostic tool is the one place a broad catch is right: the point is
        # to report all four verdicts, not to fail fast. The exception type is
        # printed so nothing is actually swallowed, and the exit code is non-zero.
        except Exception as exc:
            failures.append(name)
            logger.error("FAIL  %-14s %s: %s", name, type(exc).__name__, exc)
            logger.debug("traceback for %s", name, exc_info=True)
        else:
            logger.info("PASS  %-14s %s", name, detail)

    if failures:
        logger.error("\n%d/%d checks failed: %s", len(failures), len(CHECKS), failures)
        return 1

    logger.info("\nall %d checks passed", len(CHECKS))
    return 0


if __name__ == "__main__":
    sys.exit(main())
