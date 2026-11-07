"""Step 3 of graph construction: load the resolved graph into Neo4j.

    PYTHONPATH=src python -m graphrag_lab.graph.build

Schema:
    (:Document {doc_id, title})
    (:Chunk {chunk_id, doc_id, header_path, text})-[:PART_OF]->(:Document)
    (:Entity {id, name, type, aliases, description, embedding})-[:MENTIONED_IN]->(:Chunk)
    (:Entity)-[:RELATED {type, description, strength, count}]->(:Entity)

MENTIONED_IN is what lets a graph traversal reach back to the source text.
The build is a full rebuild: it deletes every node first.
"""

from __future__ import annotations

import json
import logging

from neo4j import Driver, GraphDatabase

from graphrag_lab.chunking import read_chunks
from graphrag_lab.config import Config, load_config
from graphrag_lab.embeddings import Embedder
from graphrag_lab.graph.resolve import ENTITIES_FILE, RELATIONS_FILE

logger = logging.getLogger(__name__)

CONSTRAINTS = (
    "CREATE CONSTRAINT document_id IF NOT EXISTS FOR (d:Document) REQUIRE d.doc_id IS UNIQUE",
    "CREATE CONSTRAINT chunk_id IF NOT EXISTS FOR (c:Chunk) REQUIRE c.chunk_id IS UNIQUE",
    "CREATE CONSTRAINT entity_id IF NOT EXISTS FOR (e:Entity) REQUIRE e.id IS UNIQUE",
)

VECTOR_INDEX = """
CREATE VECTOR INDEX {name} IF NOT EXISTS FOR (e:Entity) ON e.embedding
OPTIONS {{indexConfig: {{`vector.dimensions`: {dim}, `vector.similarity_function`: 'cosine'}}}}
"""

LOAD_DOCUMENTS = """
UNWIND $rows AS row
MERGE (d:Document {doc_id: row.doc_id}) SET d.title = row.title
"""
LOAD_CHUNKS = """
UNWIND $rows AS row
MERGE (c:Chunk {chunk_id: row.chunk_id})
SET c.doc_id = row.doc_id, c.header_path = row.header_path, c.text = row.text
WITH c, row
MATCH (d:Document {doc_id: row.doc_id})
MERGE (c)-[:PART_OF]->(d)
"""
LOAD_ENTITIES = """
UNWIND $rows AS row
MERGE (e:Entity {id: row.id})
SET e.name = row.name, e.type = row.type, e.aliases = row.aliases,
    e.description = row.description, e.embedding = row.embedding
WITH e, row
UNWIND row.chunk_ids AS cid
MATCH (c:Chunk {chunk_id: cid})
MERGE (e)-[:MENTIONED_IN]->(c)
"""
LOAD_RELATIONS = """
UNWIND $rows AS row
MATCH (s:Entity {id: row.source}), (t:Entity {id: row.target})
MERGE (s)-[r:RELATED {type: row.type}]->(t)
SET r.description = row.description, r.strength = row.strength, r.count = row.count
"""

# The planted chain of q_multi_1, found by the graph alone.
CHAIN_CHECK = """
MATCH (a:Entity), (b:Entity)
WHERE toLower(a.name) CONTAINS 'inc-0312' AND toLower(b.name) CONTAINS 'voxroute'
MATCH p = shortestPath((a)-[:RELATED*..6]-(b))
RETURN [n IN nodes(p) | n.name] AS path, [r IN relationships(p) | r.type] AS relations
"""


def _batches(rows: list[dict], size: int):
    for i in range(0, len(rows), size):
        yield rows[i : i + size]


def _write(driver: Driver, query: str, rows: list[dict], cfg: Config) -> None:
    for batch in _batches(rows, cfg.neo4j_batch_size):
        driver.execute_query(query, rows=batch)


def entity_embed_text(entity: dict) -> str:
    return f"{entity['name']} ({entity['type']}): {entity['description']}"


def build(cfg: Config) -> None:
    entities = json.loads((cfg.graph_dir / ENTITIES_FILE).read_text())
    relations = json.loads((cfg.graph_dir / RELATIONS_FILE).read_text())
    chunks = read_chunks(cfg)

    vectors = Embedder(cfg).embed_documents([entity_embed_text(e) for e in entities])
    for entity, vector in zip(entities, vectors):
        entity["embedding"] = vector.tolist()

    documents = {c.doc_id: c.doc_title for c in chunks}
    # The UNWIND + MATCH (s), (t) lookups are unique-index seeks, not real
    # cartesian products, so INFORMATION-level notifications are noise here.
    driver = GraphDatabase.driver(
        cfg.neo4j_uri,
        auth=(cfg.neo4j_user, cfg.neo4j_password),
        notifications_min_severity="WARNING",
    )
    try:
        driver.verify_connectivity()
        driver.execute_query("MATCH (n) DETACH DELETE n")
        for query in CONSTRAINTS:
            driver.execute_query(query)
        driver.execute_query(VECTOR_INDEX.format(name=cfg.entity_vector_index, dim=cfg.embed_dim))

        _write(driver, LOAD_DOCUMENTS, [{"doc_id": d, "title": t} for d, t in documents.items()], cfg)
        _write(driver, LOAD_CHUNKS, [
            {"chunk_id": c.chunk_id, "doc_id": c.doc_id, "header_path": c.header_path, "text": c.text}
            for c in chunks
        ], cfg)
        _write(driver, LOAD_ENTITIES, entities, cfg)
        _write(driver, LOAD_RELATIONS, relations, cfg)

        counts = driver.execute_query(
            "MATCH (n) RETURN labels(n)[0] AS label, count(*) AS n ORDER BY label"
        ).records
        logger.info("loaded: %s", ", ".join(f"{r['label']}={r['n']}" for r in counts))

        chain = driver.execute_query(CHAIN_CHECK).records
        if chain:
            logger.info("planted chain INC-0312 -> VoxRoute: %s via %s",
                        " -> ".join(chain[0]["path"]), chain[0]["relations"])
        else:
            logger.warning("no path from INC-0312 to VoxRoute - inspect extraction and resolution")
    finally:
        driver.close()


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    logging.getLogger("sentence_transformers").setLevel(logging.WARNING)
    build(load_config())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
