"""Claude-as-judge, with the ground truth in the prompt.

    PYTHONPATH=src python -m graphrag_lab.eval.judge               # re-judge the latest run
    PYTHONPATH=src python -m graphrag_lab.eval.judge --run 20261107-153000

Scores three separate things, not one blurred number:
  correctness  0-2, against the reference answer
  fact recall  fraction of the question's atomic facts present - computed here
               from per-fact verdicts, not asked of the judge as a number
  grounded     no claim in the answer goes beyond the context the system saw

An unaudited LLM judge is not evidence: report.md lists a seeded sample of
judgements to check by hand.
"""

from __future__ import annotations

import argparse
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from graphrag_lab import world
from graphrag_lab.config import Config, load_config
from graphrag_lab.llm import complete, make_client

logger = logging.getLogger(__name__)

JUDGEMENTS_FILE = "judgements.jsonl"
CORRECTNESS_LEVELS = (0, 1, 2)

JUDGE_SYSTEM = """\
You grade answers from a question-answering system. Be strict and literal. \
Judge only against the reference material in the user message, never against \
your own knowledge."""

RUBRIC = """\
Grade the SYSTEM ANSWER.

correctness:
  2 = correct and complete compared with the reference answer
  1 = partly correct, incomplete, or correct but hedged as uncertain
  0 = wrong, no real answer, or it states things that contradict the reference
  For a question whose reference says the documents do NOT contain the
  information: 2 = the answer clearly says so and invents nothing;
  0 = the answer invents details; 1 = anything in between.

facts: for EACH required fact listed, present = true if the system answer
states it (a paraphrase is fine; a different name or number is not).

unsupported_claims: every claim in the system answer that the CONTEXT
PASSAGES do not support. Statements that the context lacks information are not
claims. Use an empty list if there are none.

rationale: two sentences at most."""

JUDGE_SCHEMA = {
    "type": "object",
    "properties": {
        "correctness": {"type": "integer", "enum": list(CORRECTNESS_LEVELS)},
        "facts": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "fact_id": {"type": "string"},
                    "present": {"type": "boolean"},
                },
                "required": ["fact_id", "present"],
                "additionalProperties": False,
            },
        },
        "unsupported_claims": {"type": "array", "items": {"type": "string"}},
        "rationale": {"type": "string"},
    },
    "required": ["correctness", "facts", "unsupported_claims", "rationale"],
    "additionalProperties": False,
}


def build_prompt(record: dict, question: world.Question) -> str:
    facts = "\n".join(
        f"- [{fid}] {world.FACT_BY_ID[fid].text}" for fid in question.fact_ids
    ) or "(none - the information does not exist in the documents)"
    return (
        f"QUESTION:\n{question.text}\n\n"
        f"REFERENCE ANSWER:\n{question.answer}\n\n"
        f"REQUIRED FACTS:\n{facts}\n\n"
        f"CONTEXT PASSAGES THE SYSTEM SAW:\n{record['context_text']}\n\n"
        f"SYSTEM ANSWER:\n{record['answer']}\n\n"
        f"{RUBRIC}"
    )


def judge_one(client, cfg: Config, record: dict) -> dict:
    question = world.QUESTION_BY_ID[record["qid"]]
    completion = complete(
        client,
        cfg,
        model=cfg.judge_model,
        system=JUDGE_SYSTEM,
        prompt=build_prompt(record, question),
        max_tokens=cfg.judge_max_tokens,
        effort=cfg.judge_effort,
        json_schema=JUDGE_SCHEMA,
        stage=f"judge:{record['system']}",
    )
    verdict = completion.json

    present = {f["fact_id"]: f["present"] for f in verdict["facts"]}
    if set(present) != set(question.fact_ids):
        raise ValueError(
            f"{record['qid']}: judge returned facts {sorted(present)}, "
            f"expected {sorted(question.fact_ids)}"
        )
    recall = (
        sum(present.values()) / len(present) if question.fact_ids else None
    )  # None for absent_info: there are no facts to recall

    return {
        "system": record["system"],
        "qid": record["qid"],
        "shape": record["shape"],
        "correctness": verdict["correctness"],
        "fact_recall": recall,
        "facts_missing": sorted(fid for fid, ok in present.items() if not ok),
        "unsupported_claims": verdict["unsupported_claims"],
        "grounded": not verdict["unsupported_claims"],
        "rationale": verdict["rationale"],
        "judge_cost_usd": completion.usage["cost_usd"],
    }


def judge_run(cfg: Config, run_dir: Path) -> int:
    # Imported here: runner imports this module, so a top-level import would cycle.
    from graphrag_lab.eval.runner import ANSWERS_FILE, read_jsonl, write_jsonl

    records = read_jsonl(run_dir / ANSWERS_FILE)
    client = make_client(cfg)
    judgements, failed = [], []
    with ThreadPoolExecutor(max_workers=cfg.eval_workers) as pool:
        futures = {pool.submit(judge_one, client, cfg, r): r for r in records}
        for future in as_completed(futures):
            r = futures[future]
            try:
                judgements.append(future.result())
            except Exception as exc:
                failed.append(f"{r['system']}/{r['qid']}")
                logger.error("FAIL judge %s/%s  %s: %s", r["system"], r["qid"],
                             type(exc).__name__, exc)
    judgements.sort(key=lambda j: (j["system"], j["qid"]))
    write_jsonl(run_dir / JUDGEMENTS_FILE, judgements)
    logger.info("judged %d answers -> %s", len(judgements), run_dir / JUDGEMENTS_FILE)
    return len(failed)


def main() -> int:
    from graphrag_lab.eval import report
    from graphrag_lab.eval.runner import latest_run_dir

    logging.basicConfig(level=logging.INFO, format="%(message)s")
    logging.getLogger("httpx").setLevel(logging.WARNING)
    parser = argparse.ArgumentParser(description="Judge an evaluation run")
    parser.add_argument("--run", help="run id under results/ (default: latest)")
    args = parser.parse_args()

    cfg = load_config()
    run_dir = cfg.results_dir / args.run if args.run else latest_run_dir(cfg)
    failures = judge_run(cfg, run_dir)
    print(report.write_report(cfg, run_dir))
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
