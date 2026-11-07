"""Run every question through every system, then judge and report.

    PYTHONPATH=src python -m graphrag_lab.eval.runner                       # all systems
    PYTHONPATH=src python -m graphrag_lab.eval.runner --systems baseline_dense
    PYTHONPATH=src python -m graphrag_lab.eval.runner --skip-judge

Each run gets results/<run_id>/ with config.json, answers.jsonl,
judgements.jsonl and report.md. Answers are kept on disk, so the judge and the
report can run again without new answer calls.
"""

from __future__ import annotations

import argparse
import json
import logging
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import fields
from datetime import datetime
from pathlib import Path

from graphrag_lab import world
from graphrag_lab.baseline.answer import answer_from_context
from graphrag_lab.config import Config, load_config
from graphrag_lab.eval import judge, report
from graphrag_lab.eval.systems import SYSTEMS, build_system
from graphrag_lab.llm import make_client

logger = logging.getLogger(__name__)

ANSWERS_FILE = "answers.jsonl"
CONFIG_FILE = "config.json"


def new_run_dir(cfg: Config) -> Path:
    run_dir = cfg.results_dir / datetime.now().strftime("%Y%m%d-%H%M%S")
    run_dir.mkdir(parents=True, exist_ok=False)
    # Secrets are the repr=False fields; everything else is recorded with the run.
    public = {f.name: getattr(cfg, f.name) for f in fields(cfg) if f.repr}
    (run_dir / CONFIG_FILE).write_text(json.dumps(public, indent=2, default=str))
    return run_dir


def latest_run_dir(cfg: Config) -> Path:
    runs = sorted(p for p in cfg.results_dir.glob("*") if (p / ANSWERS_FILE).exists())
    if not runs:
        raise FileNotFoundError(f"no runs in {cfg.results_dir} - run eval.runner first")
    return runs[-1]


def read_jsonl(path: Path) -> list[dict]:
    with path.open() as f:
        return [json.loads(line) for line in f]


def write_jsonl(path: Path, records: list[dict]) -> None:
    with path.open("w") as f:
        for record in records:
            f.write(json.dumps(record) + "\n")


def run_answers(cfg: Config, systems: list[str], questions: list[world.Question], run_dir: Path) -> int:
    # Contexts first, in this thread: the local embedding model is not shared
    # across threads. Only the Claude calls run in parallel.
    jobs = []
    for name in systems:
        build = build_system(cfg, name)
        for q in questions:
            started = time.perf_counter()
            context = build(q.text)
            jobs.append((name, q, context, time.perf_counter() - started))
    logger.info("built %d contexts; answering with %d workers", len(jobs), cfg.eval_workers)

    client = make_client(cfg)
    records, failed = [], []
    with ThreadPoolExecutor(max_workers=cfg.eval_workers) as pool:
        futures = {
            pool.submit(answer_from_context, client, cfg, name, q.text, context): (name, q, context, rt)
            for name, q, context, rt in jobs
        }
        for future in as_completed(futures):
            name, q, context, retrieval_s = futures[future]
            try:
                a = future.result()
            # One failed answer must not discard the rest of the run.
            except Exception as exc:
                failed.append(f"{name}/{q.id}")
                logger.error("FAIL  %s/%s  %s: %s", name, q.id, type(exc).__name__, exc)
                continue
            records.append({
                "system": name,
                "qid": q.id,
                "shape": q.shape,
                "question": q.text,
                "answer": a.answer,
                "sufficient_context": a.sufficient_context,
                "cited_ids": list(a.cited_ids),
                "context_ids": list(a.context_ids),
                "invalid_citations": list(a.invalid_citations),
                "context_text": context.text,
                "input_tokens": a.usage["input_tokens"],
                "output_tokens": a.usage["output_tokens"],
                "cost_usd": a.usage["cost_usd"],
                "answer_latency_s": a.usage["latency_s"],
                "retrieval_latency_s": round(retrieval_s, 3),
            })
            logger.info("answered %s/%s", name, q.id)

    records.sort(key=lambda r: (r["system"], r["qid"]))
    write_jsonl(run_dir / ANSWERS_FILE, records)
    if failed:
        logger.error("%d answers failed: %s", len(failed), failed)
    return len(failed)


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    for noisy in ("httpx", "sentence_transformers"):
        logging.getLogger(noisy).setLevel(logging.WARNING)

    parser = argparse.ArgumentParser(description="Run the evaluation")
    parser.add_argument("--systems", nargs="+", choices=SYSTEMS, default=list(SYSTEMS))
    parser.add_argument("--qids", nargs="+", choices=sorted(world.QUESTION_BY_ID))
    parser.add_argument("--skip-judge", action="store_true")
    args = parser.parse_args()

    cfg = load_config()
    world.validate_world()
    questions = [world.QUESTION_BY_ID[q] for q in args.qids] if args.qids else list(world.QUESTIONS)

    run_dir = new_run_dir(cfg)
    logger.info("run %s: %d systems x %d questions", run_dir.name, len(args.systems), len(questions))
    failures = run_answers(cfg, args.systems, questions, run_dir)

    if not args.skip_judge:
        failures += judge.judge_run(cfg, run_dir)
        print(report.write_report(cfg, run_dir))
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
