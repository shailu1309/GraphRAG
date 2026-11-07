"""Answer a question from a given context only.

    PYTHONPATH=src python -m graphrag_lab.baseline.answer --qid q_local_1
    PYTHONPATH=src python -m graphrag_lab.baseline.answer --qid q_multi_1 --hybrid
    PYTHONPATH=src python -m graphrag_lab.baseline.answer "Who leads Billing Support?"

answer_from_context() is shared by every system. Baseline and GraphRAG get the
same instructions and the same model; only the context differs.
"""

from __future__ import annotations

import argparse
import logging
from dataclasses import dataclass

from graphrag_lab import world
from graphrag_lab.baseline.retrieve import BaselineRetriever, Retrieved
from graphrag_lab.config import Config, load_config
from graphrag_lab.llm import complete, make_client

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = f"""\
You answer questions about the contact centre of {world.COMPANY}. Use ONLY the \
context passages in the user message. Do not use outside knowledge, and do not \
guess. If the passages do not contain enough information to answer fully, say \
what is missing and set sufficient_context to false. Cite the id of every \
passage you used."""

ANSWER_SCHEMA = {
    "type": "object",
    "properties": {
        "answer": {"type": "string"},
        "sufficient_context": {"type": "boolean"},
        "cited_ids": {"type": "array", "items": {"type": "string"}},
    },
    "required": ["answer", "sufficient_context", "cited_ids"],
    "additionalProperties": False,
}


@dataclass(frozen=True)
class Context:
    """What a retrieval system hands to the answer step."""
    text: str
    ids: tuple[str, ...]


@dataclass(frozen=True)
class Answer:
    system: str
    question: str
    answer: str
    sufficient_context: bool
    cited_ids: tuple[str, ...]
    context_ids: tuple[str, ...]
    invalid_citations: tuple[str, ...]  # cited ids that were not in the context
    usage: dict


def baseline_context(retrieved: list[Retrieved]) -> Context:
    text = "\n\n".join(
        f'<passage id="{r.chunk.chunk_id}">\n{r.chunk.embed_text}\n</passage>'
        for r in retrieved
    )
    return Context(text=text, ids=tuple(r.chunk.chunk_id for r in retrieved))


def answer_from_context(client, cfg: Config, system: str, question: str, context: Context) -> Answer:
    completion = complete(
        client,
        cfg,
        model=cfg.answer_model,
        system=SYSTEM_PROMPT,
        prompt=f"<context>\n{context.text}\n</context>\n\nQuestion: {question}",
        max_tokens=cfg.answer_max_tokens,
        effort=cfg.answer_effort,
        json_schema=ANSWER_SCHEMA,
        stage=f"answer:{system}",
    )
    reply = completion.json
    cited = tuple(reply["cited_ids"])
    return Answer(
        system=system,
        question=question,
        answer=reply["answer"],
        sufficient_context=reply["sufficient_context"],
        cited_ids=cited,
        context_ids=context.ids,
        invalid_citations=tuple(c for c in cited if c not in context.ids),
        usage=completion.usage,
    )


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    for noisy in ("httpx", "sentence_transformers"):
        logging.getLogger(noisy).setLevel(logging.WARNING)

    parser = argparse.ArgumentParser(description="Answer one question with baseline RAG")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("question", nargs="?", help="free-text question")
    group.add_argument("--qid", choices=sorted(world.QUESTION_BY_ID), help="ground-truth question")
    parser.add_argument("--hybrid", action="store_true", help="dense + BM25 with RRF")
    args = parser.parse_args()

    cfg = load_config()
    expected = world.QUESTION_BY_ID[args.qid] if args.qid else None
    question = expected.text if expected else args.question

    retriever = BaselineRetriever(cfg, hybrid=args.hybrid)
    context = baseline_context(retriever.retrieve(question))
    result = answer_from_context(make_client(cfg), cfg, retriever.name, question, context)

    print(f"\n[{result.system}] {question}\n")
    print(result.answer)
    print(f"\nsufficient_context: {result.sufficient_context}")
    print(f"retrieved: {', '.join(result.context_ids)}")
    print(f"cited:     {', '.join(result.cited_ids) or '-'}")
    if result.invalid_citations:
        print(f"INVALID citations (not in context): {result.invalid_citations}")
    if expected:
        print(f"\nexpected:      {expected.answer}")
        print(f"required docs: {', '.join(world.required_docs(expected)) or '(none - absent)'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
