"""Render the ground-truth world into markdown documents, and write the answer key.

    PYTHONPATH=src python -m graphrag_lab.corpus_gen          # only missing documents
    PYTHONPATH=src python -m graphrag_lab.corpus_gen --force  # regenerate all

LLM generation is not deterministic, so the reproducible artifact is the
generated corpus itself: corpus/ is committed to git, data/ is not.
"""

from __future__ import annotations

import argparse
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed

import yaml

from graphrag_lab import world
from graphrag_lab.config import Config, load_config
from graphrag_lab.llm import complete, make_client

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = f"""\
You write internal documents for the customer contact centre of {world.COMPANY}, \
a fictional broadband and mobile provider. The documents must read like real \
working documents written by busy staff: specific, a little dry, with the \
details and structure that the genre normally has. Not marketing copy."""

PROMPT_TEMPLATE = """\
Write the document below in markdown.

Title: {title}
Genre: {genre}

The document MUST state each of these facts. You may rephrase a fact, but keep
every name, number and date exactly as written:
{facts}

Rules:
- Start with "# {title}". Use 3 to 5 "##" sections that suit the genre.
- Write 350 to 600 words.
- The only named people, teams, queues, systems, vendors, incidents and projects
  you may mention are the ones in the facts above. For anyone or anything else,
  use a generic role ("a supervisor", "the finance team") with no name.
- Do not state any relation that is not in the facts. For example, do not say
  who leads a team, which vendor supplies a system, or which system a queue uses,
  unless a fact above says so.
- You may add generic, harmless detail (meeting cadence, a checklist, an action
  item) that names nothing new.

Output only the document."""


def build_prompt(doc: world.Document) -> str:
    facts = "\n".join(f"- {world.FACT_BY_ID[fid].text}" for fid in doc.fact_ids)
    return PROMPT_TEMPLATE.format(title=doc.title, genre=doc.genre, facts=facts)


def render_document(client, cfg: Config, doc: world.Document) -> str:
    text = complete(
        client,
        cfg,
        model=cfg.corpus_model,
        system=SYSTEM_PROMPT,
        prompt=build_prompt(doc),
        max_tokens=cfg.corpus_max_tokens,
        effort=cfg.corpus_effort,
        stage=f"corpus:{doc.id}",
    ).text
    if not text.startswith("# "):
        raise ValueError(f"{doc.id}: output does not start with a '# ' title")
    return text + "\n"


def ground_truth() -> dict:
    """The answer key, in the shape the eval harness and the graph checks read."""
    return {
        "company": world.COMPANY,
        "entities": [
            {"id": e.id, "name": e.name, "type": e.type, "aliases": list(e.aliases)}
            for e in world.ENTITIES
        ],
        "facts": [
            {
                "id": f.id,
                "subject": f.subject,
                "predicate": f.predicate,
                "object": f.object,
                "text": f.text,
                "doc_id": world.DOC_OF_FACT[f.id],
            }
            for f in world.FACTS
        ],
        "questions": [
            {
                "id": q.id,
                "shape": q.shape,
                "question": q.text,
                "answer": q.answer,
                "fact_ids": list(q.fact_ids),
                "atomic_facts": [world.FACT_BY_ID[fid].text for fid in q.fact_ids],
                "required_docs": world.required_docs(q),
            }
            for q in world.QUESTIONS
        ],
    }


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    # httpx logs one line per request at INFO; that drowns the progress lines.
    logging.getLogger("httpx").setLevel(logging.WARNING)

    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--force", action="store_true", help="regenerate every document")
    args = parser.parse_args()

    cfg = load_config()
    world.validate_world()
    cfg.synthetic_dir.mkdir(parents=True, exist_ok=True)

    todo = [
        doc
        for doc in world.DOCUMENTS
        if args.force or not (cfg.synthetic_dir / f"{doc.id}.md").exists()
    ]
    logger.info("%d of %d documents to generate", len(todo), len(world.DOCUMENTS))

    client = make_client(cfg)
    failed: list[str] = []
    with ThreadPoolExecutor(max_workers=cfg.corpus_workers) as pool:
        futures = {pool.submit(render_document, client, cfg, doc): doc for doc in todo}
        for future in as_completed(futures):
            doc = futures[future]
            try:
                text = future.result()
            # Keep the documents that succeeded; a re-run fills in only the gaps.
            except Exception as exc:
                failed.append(doc.id)
                logger.error("FAIL  %s  %s: %s", doc.id, type(exc).__name__, exc)
                continue
            (cfg.synthetic_dir / f"{doc.id}.md").write_text(text)
            logger.info("wrote %s (%d words)", doc.id, len(text.split()))

    with cfg.ground_truth_path.open("w") as f:
        yaml.safe_dump(ground_truth(), f, sort_keys=False, allow_unicode=True, width=100)
    logger.info("wrote %s", cfg.ground_truth_path)

    if failed:
        logger.error("%d documents failed: %s - re-run to retry them", len(failed), failed)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
