# Context handoff

Upload or open this file in a new Claude session to continue the project. It
records the goal, the decisions, the current state, and my working preferences.

Updated 2026-11-07, at the end of Phase 4.

---

## 1. Goal

I learn GraphRAG by building it. The project holds **two retrieval systems over
the same corpus and the same chunks**. Only the retrieval is different. An
evaluation harness then shows where the two systems are different, and why.

Read these files first:

- [../README.md](../README.md) - the entry point: setup, phases, files, and the commands to run.
- [plan.md](plan.md) - the original 9-phase design and the gate for each phase.
- [rag-vs-graphrag.md](rag-vs-graphrag.md) - the concepts, with diagrams.
- [learning-notes.md](learning-notes.md) - notes on single topics.

---

## 2. How I want to work

These preferences changed during the first session. Please follow them.

1. **You write the code. Then you explain only the 2 or 3 ideas that matter**
   to understand the concept. Do not explain boilerplate.
2. **Go fast.** I want to finish the project quickly. Keep each answer short and
   on one topic.
3. **Do not run anything without my instruction.** No installs, no Docker
   commands, no scripts that call the API. Read-only checks of files on disk
   are acceptable.
4. **For a setup problem, give the quick fix first** (restart, reset). Diagnose
   only if the quick fix does not work. Do not ask me to run a check again if it
   already passed.
5. **Use the `ml-code-style` skill before you write Python.** It holds my
   conventions: a frozen dataclass for configuration, no magic numbers, shape
   assertions, loud failures, `pathlib`, the `logging` module, small pure
   functions.
6. **Write prose in Simplified Technical English (ASD-STE100).** My global
   output style `STE` does this. The style does not apply to code, identifiers,
   comments, commands, paths, or model names.
7. **Update the README after each phase**: the status in the phases table, a
   "What each phase built" part (a files table plus key steps), and the commands.

---

## 3. The stack (decided - do not re-open)

| Concern | Choice |
|---|---|
| Answers, judge, corpus writing | Claude `claude-opus-5-5`, with `fallbacks="default"` |
| Extraction, alias tie-break | Claude `claude-haiku-5-5` |
| Embeddings | `sentence-transformers`, `BAAI/bge-small-en-v1.5`, 384 dimensions, local |
| Vector store (baseline) | Chroma `1.5.9`, persistent, local |
| Graph store | Neo4j Community `2026.10.1` in Docker, driver `6.4.1` |
| Communities | `networkx.community.louvain_communities` |
| Orchestration | None. Plain Python. No LangChain, no LlamaIndex. |

Machine: Apple M4, 16 GB RAM, macOS. Python 3.12 in `.venv`. Anthropic SDK `2.6.0`.

Run all modules from the repository root with `PYTHONPATH=src`.

---

## 4. Decisions made in the first session

- **Corpus:** a contact centre for the fictional company "Kestrel Telecom". It
  has 20 documents and 12 questions (2 for each of the 6 shapes). The plan had
  35 documents and 30 questions. We made it smaller for speed.
- **Phase 8 (real corpus) is skipped.**
- **The answer key is code:** `src/graphrag_lab/world.py`. Each fact is a
  triple plus a sentence, and each fact is in exactly one document.
  `validate_world()` checks that no single document answers a cross-document
  question.
- **System code must not import `world.py`.** Only evaluation code reads it.
  The extractor gets only the entity types. Do not put corpus facts in prompts
  as examples. This happened once, and I corrected it.
- **One answer step for all systems:** `answer_from_context()` in
  `baseline/answer.py`. Each system only builds a `Context`. GraphRAG systems
  are added to the registry in `eval/systems.py`.
- **All Claude calls go through `llm.complete()`.** It returns a `Completion`
  (the text, plus a usage record with the cost), and writes `data/usage.jsonl`.

---

## 5. Current state - Phases 0 to 4 done

| # | Phase | Result |
|---|---|---|
| 0 | Infrastructure | Smoke test 4/4 PASS. Neo4j Browser works. |
| 1 | Corpus | 20 documents, about 600 words each. The chains are not in single documents. |
| 2 | Baseline RAG | 40 chunks. `q_local_1` passes. `q_multi_1` fails in dense and hybrid mode. |
| 3 | Evaluation | Run `results/20261107-141122/`. Spot-checks agree with the judge. One judgement (`baseline_hybrid/q_global_1`) failed; we skipped it. |
| 4 | Knowledge graph | 85 entities. Resolution: 0 splits, 0 false merges. The path INC-0312 → Wei Lin → NETESC → Switchboard IVR → VoxRoute exists. |

Baseline scores (correctness 0-2, dense / hybrid): `local_factual` 2.00 / 2.00,
`multi_hop` 1.00 / 1.00, `global_thematic` 0.50 / 1.00, `entity_gather`
1.50 / 1.50, `set_count` 1.00 / 1.50, `absent_info` 2.00 / 2.00.

The baseline is better than expected on `set_count` and `q_global_2`. The cause
is the small corpus: there are only 3 vendor contracts, so top-5 retrieval can
get all of them. `FINDINGS.md` must state this limit.

API cost so far: about 2 US dollars (corpus 0.54, answers 0.72, judge 0.61,
graph 0.09).

### Lessons from Phase 4 (for `learning-notes.md`)

1. **A name-rule bug broke the chain.** `person_match` depended on the order of
   its arguments, so "W. Lin" and "Wei Lin" stayed as two nodes. The fix is
   `_shorter_first()`.
2. **Generic roles made noise.** The corpus uses "a supervisor" and "the finance
   team" in place of names. The extractor made them into entities (262 in
   total), and they gave false shortcuts in the graph. Prompt version 2 skips
   unnamed roles. The result was 85 entities.
3. **The extractor missed an edge.** One run returned zero relations for the
   INC-0312 chunk. Prompt version 3 asks for every relation. Phase 6 local
   search must also hop `entity → chunk → entity` through `MENTIONED_IN`, so
   that one missed edge does not stop the search.
4. Change `PROMPT_VERSION` in `graph/extract.py` after each prompt change.
   Then run `extract`, `resolve`, and `build` in this order.

### Not done

- `git init` has not run. The repository is not under version control.
- Neo4j is stopped with `docker compose down`. The graph is kept in the
  `neo4j_data` volume. Start it with `docker compose up -d`.

---

## 6. Next: Phase 5 - communities

1. Read the entity graph from Neo4j (or from `data/graph/*.json`) into
   `networkx`. Use the relation strength and count as edge weights.
2. Run `louvain_communities` at two resolution levels, with `seed` from `Config`.
   Write `community_id` for each level to the Neo4j nodes.
3. Generate a report for each community with Claude: title, summary, key
   entities, key findings. Store the reports as `(:Community)` nodes, and embed
   their summaries.
4. Gate: read 3 reports. Each report must describe a real cluster, for example
   one team's work or the vendor overage problem.

Then Phase 6 (local and global search, added to `eval/systems.py`) and Phase 7
(run all systems through `eval.runner`, then write `FINDINGS.md`).
