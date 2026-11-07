"""Step 1 of graph construction: extract entities and relations from each chunk.

    PYTHONPATH=src python -m graphrag_lab.graph.extract           # only new or changed chunks
    PYTHONPATH=src python -m graphrag_lab.graph.extract --force

One Haiku call per chunk, with a strict JSON schema. The raw output is kept in
data/extractions/<chunk_id>.json: read it to see where extraction goes wrong,
and a schema change does not force a re-run of every chunk.

This module never imports world.py. The system under test must not see the
answer key - only the entity *types* are given, as any GraphRAG setup does.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed

from graphrag_lab.chunking import Chunk, read_chunks
from graphrag_lab.config import Config, load_config
from graphrag_lab.llm import complete, make_client

logger = logging.getLogger(__name__)

# Bump when the prompt or schema changes, so cached extractions are redone.
PROMPT_VERSION = "3"

ENTITY_TYPES = (
    "person", "team", "queue", "system", "vendor", "incident", "project",
    "issue", "organization",
)
STRENGTHS = tuple(range(1, 11))

EXTRACT_SYSTEM = """\
You build a knowledge graph from internal documents of a telecom contact centre. \
Extract only what the passage states. Do not infer and do not use outside knowledge."""

EXTRACT_PROMPT = """\
Extract the entities and the relations between them from the passage.

Entities:
- Extract only specific, named entities: people with a name, named teams,
  queues, systems, vendors, incidents with an ID, named projects. Skip generic
  roles and unnamed groups ("a supervisor", "the finance team", "agents",
  "the duty manager") - they are not entities.
- name: exactly as written in the passage (keep forms like "W. Lin" or "Relay CRM").
- type: one of {types}. Use "issue" for a recurring problem or risk
  (for example outdated articles, understaffing, failed callbacks, cost overruns).
- description: one sentence about the entity, from this passage only.

Relations:
- List EVERY relation the passage states between your entities, including
  roles and actions ("J. Doe chaired the audit of INC-9001" is a relation). A
  passage that names two or more entities almost always states at least one.
- source and target: names exactly as in your entity list.
- type: a short snake_case verb phrase, for example leads, manages, routed_by,
  supplies, caused, handled, depends_on, owns, affected_by.
- description: one sentence, from this passage only.
- strength: 1-10, how explicit and important the relation is in the passage.

<passage>
{passage}
</passage>"""

EXTRACT_SCHEMA = {
    "type": "object",
    "properties": {
        "entities": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "type": {"type": "string", "enum": list(ENTITY_TYPES)},
                    "description": {"type": "string"},
                },
                "required": ["name", "type", "description"],
                "additionalProperties": False,
            },
        },
        "relations": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "source": {"type": "string"},
                    "target": {"type": "string"},
                    "type": {"type": "string"},
                    "description": {"type": "string"},
                    "strength": {"type": "integer", "enum": list(STRENGTHS)},
                },
                "required": ["source", "target", "type", "description", "strength"],
                "additionalProperties": False,
            },
        },
    },
    "required": ["entities", "relations"],
    "additionalProperties": False,
}


def _fingerprint(chunk: Chunk) -> str:
    return hashlib.sha256(f"{PROMPT_VERSION}\n{chunk.embed_text}".encode()).hexdigest()


def extract_chunk(client, cfg: Config, chunk: Chunk) -> dict:
    data = complete(
        client,
        cfg,
        model=cfg.extract_model,
        system=EXTRACT_SYSTEM,
        prompt=EXTRACT_PROMPT.format(types=", ".join(ENTITY_TYPES), passage=chunk.embed_text),
        max_tokens=cfg.extract_max_tokens,
        effort=cfg.extract_effort,
        json_schema=EXTRACT_SCHEMA,
        stage="graph:extract",
    ).json
    return {"chunk_id": chunk.chunk_id, "fingerprint": _fingerprint(chunk), **data}


def read_extractions(cfg: Config) -> list[dict]:
    paths = sorted(cfg.extractions_dir.glob("*.json"))
    if not paths:
        raise FileNotFoundError(f"no extractions in {cfg.extractions_dir} - run graph.extract")
    return [json.loads(p.read_text()) for p in paths]


def _path(cfg: Config, chunk: Chunk):
    return cfg.extractions_dir / f"{chunk.chunk_id.replace('#', '__')}.json"


def _is_current(cfg: Config, chunk: Chunk) -> bool:
    path = _path(cfg, chunk)
    return path.exists() and json.loads(path.read_text())["fingerprint"] == _fingerprint(chunk)


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    logging.getLogger("httpx").setLevel(logging.WARNING)
    parser = argparse.ArgumentParser(description="Extract entities and relations per chunk")
    parser.add_argument("--force", action="store_true", help="re-extract every chunk")
    args = parser.parse_args()

    cfg = load_config()
    cfg.extractions_dir.mkdir(parents=True, exist_ok=True)
    chunks = read_chunks(cfg)
    # Drop extractions of chunks that no longer exist (the corpus was re-chunked).
    live = {_path(cfg, c) for c in chunks}
    for stale in set(cfg.extractions_dir.glob("*.json")) - live:
        stale.unlink()

    todo = [c for c in chunks if args.force or not _is_current(cfg, c)]
    logger.info("%d of %d chunks to extract", len(todo), len(chunks))

    client = make_client(cfg)
    failed = []
    with ThreadPoolExecutor(max_workers=cfg.extract_workers) as pool:
        futures = {pool.submit(extract_chunk, client, cfg, c): c for c in todo}
        for future in as_completed(futures):
            chunk = futures[future]
            try:
                result = future.result()
            except Exception as exc:
                failed.append(chunk.chunk_id)
                logger.error("FAIL  %s  %s: %s", chunk.chunk_id, type(exc).__name__, exc)
                continue
            _path(cfg, chunk).write_text(json.dumps(result, indent=2))
            logger.info("%s: %d entities, %d relations", chunk.chunk_id,
                        len(result["entities"]), len(result["relations"]))

    if failed:
        logger.error("%d chunks failed: %s - re-run to retry them", len(failed), failed)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
