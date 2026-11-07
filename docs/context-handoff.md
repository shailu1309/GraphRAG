# Context handoff

Upload or open this file in a new Claude session to continue the project. It
records the goal, the decisions, the current state, and my working preferences.

Written 2026-11-07.

---

## 1. Goal

I learn GraphRAG by building it. The project holds **two retrieval systems over
the same corpus and the same chunks**. Only the retrieval is different. An
evaluation harness then shows where the two systems are different, and why.

The full 9-phase plan is in [plan.md](plan.md). Read it. It holds the design
decisions and the gate for each phase.

Supporting docs:

- [rag-vs-graphrag.md](rag-vs-graphrag.md) - the concepts, with diagrams.
- [learning-notes.md](learning-notes.md) - notes on single topics, as they come up.

---

## 2. How I want to work

These preferences are important. Please follow them.

1. **I write the code. You give the spec.** For each step, give me the module
   purpose, the function signatures, the concept to understand, and the way to
   verify the result. I implement. You review, debug and explain. Write the code
   for me only if I ask for a file by name.
2. **Keep each answer short and precise.** One answer must be a size that a
   person can read and understand. Do not put four topics in one answer.
3. **Move in small steps.** One step for each turn. Wait for my result before
   you continue to the next step.
4. **Do not run anything without my instruction.** No installs, no Docker
   commands, no scripts, no tests.
5. **Use the `ml-code-style` skill before you write Python.** It holds my
   conventions: a frozen dataclass for configuration, no magic numbers, shape
   assertions, loud failures, `pathlib`, the `logging` module, small pure
   functions.
6. **Write prose in Simplified Technical English (ASD-STE100).** My global
   output style `STE` does this. The style does not apply to code, identifiers,
   comments, commands, paths, or model names.
7. **Append new concept explanations to `docs/learning-notes.md`** when I ask.

---

## 3. The stack (decided - do not re-open)

| Concern | Choice |
|---|---|
| Answers, judge | Claude `claude-opus-5-5` |
| Bulk extraction | Claude `claude-haiku-5-5` (about 40 times cheaper) |
| Embeddings | `sentence-transformers`, `BAAI/bge-small-en-v1.5`, 384 dimensions, local |
| Vector store (baseline) | Chroma, persistent, local |
| Graph store | Neo4j Community `2026.10.1` in Docker |
| Communities | `networkx.community.louvain_communities` |
| Orchestration | None. Plain Python. No LangChain, no LlamaIndex. |

The reason for no framework: a framework hides the mechanisms that I want to
learn.

Expected cost: about 5 US dollars of Claude API use for the whole project. The
cost is mostly in global search and the judge, not in the entity extraction.

Machine: Apple M4, 16 GB RAM, macOS.

---

## 4. Current state - Phase 0, almost complete

Files in the repository:

| File | State |
|---|---|
| `.gitignore` | Done. `corpus/` is deliberately not ignored. |
| `requirements.txt` | Done. All libraries installed in `.venv`. |
| `Makefile` | Done. Holds the `test-claude` target, which reads the key from `.env`. |
| `docker-compose.yml` | Done. Neo4j, ports 7474 and 7687, named volume, healthcheck. |
| `scripts/smoke_test.py` | Done. **Not run yet.** Four checks: Claude, embeddings, Chroma, Neo4j. |
| `docs/` | Four markdown files, including this one. |

### What is not done

1. `.env` holds `ANTHROPIC_API_KEY` only. It needs these three lines:
   ```
   NEO4J_URI=bolt://localhost:7687
   NEO4J_USER=neo4j
   NEO4J_PASSWORD=graphrag123
   ```
   `docker-compose.yml` reads `NEO4J_PASSWORD` and stops with an error if the
   variable is absent.
2. `docker compose up -d` is not run. Neo4j is not started. The image is about
   600 MB.
3. `src/graphrag_lab/config.py` does not exist. This file is the next code to
   write. It must be one frozen dataclass that holds the model IDs, the chunk
   size and overlap, `top_k`, the embedding model name, the Neo4j URI and
   credentials, the paths, and a global `SEED`.
4. `git init` is not run. The repository is not under version control, so
   `.gitignore` protects nothing at this time.
5. **An API key was exposed in the previous chat transcript.** I must delete that
   key in the Anthropic Console and put a new key in `.env`. Ask me if this is
   complete.

### The Phase 0 gate

`python scripts/smoke_test.py` prints 4 of 4 checks as PASS, and
`http://localhost:7474` opens the Neo4j Browser.

---

## 5. The first three things to do in the new session

1. Ask me to confirm the two items above: the key rotation, and the three Neo4j
   lines in `.env`.
2. Give me the spec for `src/graphrag_lab/config.py`. I write it.
3. Tell me to start Neo4j and run the smoke test. Then help me read the result.

After the gate is green, continue to Phase 1 of [plan.md](plan.md): the synthetic
corpus and the ground truth.
