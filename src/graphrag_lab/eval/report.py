"""Turn a judged run into report.md, broken down by question shape.

    PYTHONPATH=src python -m graphrag_lab.eval.report               # latest run
    PYTHONPATH=src python -m graphrag_lab.eval.report --run 20261107-153000
"""

from __future__ import annotations

import argparse
import random
from pathlib import Path
from statistics import mean

from graphrag_lab import world
from graphrag_lab.config import Config, load_config

REPORT_FILE = "report.md"
MISSING = "-"


def _mean(values) -> float | None:
    values = [v for v in values if v is not None]
    return mean(values) if values else None


def _fmt(value, spec: str) -> str:
    return MISSING if value is None else format(value, spec)


def _table(header: list[str], rows: list[list[str]]) -> str:
    lines = ["| " + " | ".join(header) + " |", "|" + "---|" * len(header)]
    lines += ["| " + " | ".join(row) + " |" for row in rows]
    return "\n".join(lines)


def _summary_row(rows: list[dict]) -> list[str]:
    return [
        str(len(rows)),
        _fmt(_mean(r.get("correctness") for r in rows), ".2f"),
        _fmt(_mean(r.get("fact_recall") for r in rows), ".0%"),
        _fmt(_mean(float(r["grounded"]) for r in rows if "grounded" in r), ".0%"),
        _fmt(_mean(float(not r["sufficient_context"]) for r in rows), ".0%"),
        _fmt(_mean(r["input_tokens"] for r in rows), ",.0f"),
        _fmt(_mean(r["cost_usd"] for r in rows), ".4f"),
        _fmt(_mean(r["answer_latency_s"] for r in rows), ".1f"),
    ]


SUMMARY_HEADER = [
    "n", "correct (0-2)", "fact recall", "grounded", "said insufficient",
    "input tokens", "cost $", "latency s",
]


def build_report(cfg: Config, run_dir: Path) -> str:
    from graphrag_lab.eval.judge import CORRECTNESS_LEVELS, JUDGEMENTS_FILE
    from graphrag_lab.eval.runner import ANSWERS_FILE, read_jsonl

    answers = read_jsonl(run_dir / ANSWERS_FILE)
    judged_path = run_dir / JUDGEMENTS_FILE
    judgements = read_jsonl(judged_path) if judged_path.exists() else []
    by_key = {(j["system"], j["qid"]): j for j in judgements}
    # One row per answer; judge fields are absent when the judge has not run or failed.
    rows = [{**a, **by_key.get((a["system"], a["qid"]), {})} for a in answers]
    systems = sorted({r["system"] for r in rows})

    out = [f"# Evaluation report - run {run_dir.name}", ""]
    if len(judgements) < len(answers):
        out += [f"> {len(answers) - len(judgements)} answers have no judgement.", ""]

    out += ["## Overall", "", _table(
        ["system", *SUMMARY_HEADER],
        [[s, *_summary_row([r for r in rows if r["system"] == s])] for s in systems],
    ), ""]

    out += ["## By question shape", ""]
    shape_rows = []
    for shape in world.SHAPES:
        for s in systems:
            subset = [r for r in rows if r["system"] == s and r["shape"] == shape]
            if subset:
                shape_rows.append([shape, s, *_summary_row(subset)])
    out += [_table(["shape", "system", *SUMMARY_HEADER], shape_rows), ""]

    out += ["## Per question (correctness 0-2)", ""]
    q_rows = []
    for q in world.QUESTIONS:
        cells = [_fmt(by_key.get((s, q.id), {}).get("correctness"), "d") for s in systems]
        if any(c != MISSING for c in cells) or any(r["qid"] == q.id for r in rows):
            q_rows.append([q.id, q.shape, *cells])
    out += [_table(["question", "shape", *systems], q_rows), ""]

    judged = [r for r in rows if "correctness" in r]

    # The failures are the curriculum: read them before building GraphRAG.
    failures = sorted(
        (r for r in judged if r["correctness"] < max(CORRECTNESS_LEVELS)),
        key=lambda r: (world.SHAPES.index(r["shape"]), r["qid"], r["system"]),
    )
    out += [f"## Failures - correctness below {max(CORRECTNESS_LEVELS)} ({len(failures)})", ""]
    for r in failures:
        q = world.QUESTION_BY_ID[r["qid"]]
        missing = [f"[{fid}] {world.FACT_BY_ID[fid].text}" for fid in r["facts_missing"]]
        out += [
            f"### {r['qid']} ({r['shape']}) / {r['system']} - scored {r['correctness']}",
            "",
            f"**Question:** {q.text}",
            "",
            f"**Reference:** {q.answer}",
            "",
            f"**System answer:** {r['answer']}",
            "",
            "**Missing facts:**",
            *([f"- {m}" for m in missing] or ["- none"]),
            "",
            f"**Retrieved:** {', '.join(r['context_ids'])}",
            "",
            f"**Needed documents:** {', '.join(world.required_docs(q))}",
            "",
            f"**Judge:** {r['rationale']}",
            "",
        ]

    # Seeded, so the same run always shows the same sample to audit.
    sample = random.Random(cfg.seed).sample(judged, min(cfg.spot_check_n, len(judged)))
    out += ["## Spot-check these judgements by hand", ""]
    for r in sample:
        q = world.QUESTION_BY_ID[r["qid"]]
        out += [
            f"### {r['system']} / {r['qid']} - judge gave {r['correctness']}",
            "",
            f"**Question:** {q.text}",
            "",
            f"**Reference:** {q.answer}",
            "",
            f"**System answer:** {r['answer']}",
            "",
            f"**Judge:** {r['rationale']}"
            + (f" Unsupported: {r['unsupported_claims']}" if r["unsupported_claims"] else ""),
            "",
            "- [ ] I agree with this judgement",
            "",
        ]
    return "\n".join(out)


def write_report(cfg: Config, run_dir: Path) -> str:
    text = build_report(cfg, run_dir)
    (run_dir / REPORT_FILE).write_text(text)
    return text


def main() -> int:
    from graphrag_lab.eval.runner import latest_run_dir

    parser = argparse.ArgumentParser(description="Write report.md for an evaluation run")
    parser.add_argument("--run", help="run id under results/ (default: latest)")
    args = parser.parse_args()
    cfg = load_config()
    run_dir = cfg.results_dir / args.run if args.run else latest_run_dir(cfg)
    print(write_report(cfg, run_dir))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
