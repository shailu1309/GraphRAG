# Baseline RAG vs GraphRAG

A hands-on lab that builds two retrieval systems over the **same corpus and the
same chunks**. Only the retrieval is different. An evaluation harness then shows
where the two systems give different results, and why.

- **Baseline RAG:** dense vector search over chunks (Chroma).
- **GraphRAG:** a knowledge graph of entities and relations (Neo4j), with
  community summaries for questions about the whole corpus.

No framework (no LangChain, no LlamaIndex). Plain Python, so that each
mechanism is visible.

The full design is in [docs/plan.md](docs/plan.md). The concepts are in
[docs/rag-vs-graphrag.md](docs/rag-vs-graphrag.md).

---

## Stack

| Concern | Choice |
|---|---|
| Answers, judge, corpus writing | `claude-opus-5-5` |
| Bulk entity extraction | `claude-haiku-5-5` |
| Embeddings | `BAAI/bge-small-en-v1.5` (384 dimensions, local) |
| Vector store | Chroma (persistent, local) |
| Graph store | Neo4j Community `2026.10.1` (Docker) |
| Communities | `networkx` Louvain |

---

## The corpus

A synthetic contact centre for **Kestrel Telecom**, a fictional broadband and
mobile provider: 20 documents (team pages, queue runbooks, incident reports,
vendor contracts, project charters, monthly reviews).

The answer key ([src/graphrag_lab/world.py](src/graphrag_lab/world.py)) is
written first, in code, as facts in the form `(subject, predicate, object)`.
Claude then writes each document from its own small set of facts. The corpus
has these features on purpose:

- **Chains across documents.** An example: incident review → review lead →
  team → queue → IVR → vendor. No single document holds the full chain.
- **Aliases.** "Wei Lin", "W. Lin" and "Lin" are the same person.
- **Near-miss names.** `Project Clearline` / `Project Clearview`, and
  `Switchboard` / `Switchboard Lite`.
- **Themes across the corpus.** Recurring causes of escalations, and vendor
  overage charges.
- **Absences.** Questions about events that never happened.

---

## Setup

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```

Make a `.env` file in the repository root:

```
ANTHROPIC_API_KEY=...
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=...
```

`NEO4J_USER` must be `neo4j`. Neo4j Community makes only this user at the
first start.

Start Neo4j:

```bash
docker compose up -d
docker compose ps            # wait for "healthy" (about 40 s)
```

Neo4j Browser: <http://localhost:7474>. Bolt (for the Python driver):
`bolt://localhost:7687`. A web browser cannot open the Bolt address.

> Neo4j reads the password only when its data volume is empty. If you change
> `NEO4J_PASSWORD` later, run `docker compose down -v` to reset the volume.
> This deletes the graph.

Check that all four services work:

```bash
python scripts/smoke_test.py           # expect 4/4 PASS
```

Run all project modules from the repository root with `PYTHONPATH=src`.

---

## Phases

| # | Phase | Status | What we build | What we test |
|---|---|---|---|---|
| 0 | Infrastructure | Done | `config.py`, `docker-compose.yml`, smoke test | Claude, embeddings, Chroma and Neo4j all work |
| 1 | Corpus and ground truth | Done | `world.py`, `corpus_gen.py`, `llm.py` | No single document answers a cross-document question; the documents read like real ones |
| 2 | Baseline RAG | Done | Shared chunking, embeddings, Chroma index, answer step | Simple questions pass; multi-hop questions fail |
| 3 | Evaluation harness | Done | Question runner, Claude judge, report by question shape | Baseline scored by shape; some judgements checked by hand |
| 4 | Knowledge graph | Built | Entity and relation extraction, alias resolution, Neo4j load | A planted chain can be followed in Neo4j Browser and in Cypher |
| 5 | Communities | Planned | Louvain communities, community reports | Each report describes a real cluster (a team, a vendor problem) |
| 6 | GraphRAG retrieval | Planned | Local search (graph hops), global search (map-reduce over reports) | Phase 3 failures now pass |
| 7 | Comparison | Planned | All systems through the harness, `FINDINGS.md` | Scores by shape, plus cost and latency |

### Question shapes

The evaluation uses six shapes, with two questions each:

| Shape | Example | Expected winner |
|---|---|---|
| `local_factual` | What is the objective of Project Clearview? | About equal |
| `multi_hop` | Which vendor supplies the IVR for the queue of the team whose lead ran the INC-0312 review? | GraphRAG |
| `global_thematic` | What are the recurring causes of escalations? | GraphRAG |
| `entity_gather` | What do we know about Wei Lin? | GraphRAG |
| `set_count` | Which queues does the Switchboard IVR route? | GraphRAG |
| `absent_info` | What were the results of the Switchboard v3 pilot? | Tests hallucination in both systems |

---

## What each phase built

### Phase 1 - Corpus and ground truth

| File | Purpose |
|---|---|
| `world.py` | The answer key: entities, facts as triples, documents, and questions. It exists before any text. |
| `corpus_gen.py` | Gives each document's facts to Claude, and writes the markdown and `ground_truth.yaml`. |
| `llm.py` | The only place that calls Claude. Each call adds one line to the usage ledger. |
| `config.py` | All settings, in one frozen dataclass. |

Key steps:

1. Write the graph in code first. Each fact is `(subject, predicate, object)`
   plus one sentence.
2. Put each fact in exactly one document. Claude writes the document from those
   facts only, and must not name other entities.
3. Run `validate_world()`. It stops the program if one document can answer a
   cross-document question.

### Phase 2 - Baseline RAG

| File | Purpose |
|---|---|
| `chunking.py` | Divides each document at its `##` headers into chunks of up to 600 tokens. Both systems use these chunks. |
| `embeddings.py` | Makes local BGE embeddings, with a cache on disk. |
| `baseline/index.py` | Writes `data/chunks.jsonl` and loads the vectors into Chroma. |
| `baseline/retrieve.py` | Finds the top 5 chunks: dense search, or dense plus BM25 (hybrid). |
| `baseline/answer.py` | Claude answers from the retrieved chunks only, and replies in JSON. |

Key steps:

1. Make the baseline strong. Embed the document title and headers with each
   chunk, give BGE its query instruction, and add BM25 for exact IDs such as
   `INC-0407`.
2. Fuse the dense and BM25 rankings with reciprocal-rank fusion. RRF uses only
   the ranks, so the two score scales never mix.
3. Make Claude report `sufficient_context` and cite chunk IDs. Then a hedged
   answer, or a citation of a chunk it did not get, can be measured.

The structural limit: the corpus has about 40 chunks, and top-5 retrieval
reaches 5 documents at most. A multi-hop question needs specific documents
that the question does not name.

### Phase 3 - Evaluation harness

| File | Purpose |
|---|---|
| `eval/systems.py` | Registry of systems. Each system turns a question into a context. |
| `eval/runner.py` | Runs each question through each system. Writes `results/<run_id>/answers.jsonl` and `config.json`. |
| `eval/judge.py` | Claude judge with the ground truth. Writes `judgements.jsonl`. |
| `eval/report.py` | Writes `report.md`: scores by system, by shape, by question, and a spot-check list. |

Key steps:

1. Give all systems the same answer step (`answer_from_context`). Only the
   context is different.
2. Score three things separately:
   - **Correctness** (0-2), against the reference answer.
   - **Fact recall**, calculated in code from a present/absent verdict for each
     required fact.
   - **Groundedness**: no claim goes beyond the context that the system saw.
3. Keep the answers on disk. The judge and the report can run again without
   new answer calls.
4. Check a seeded sample of judgements by hand. An LLM judge that nobody
   checks is not evidence.

### Phase 4 - Knowledge graph

| File | Purpose |
|---|---|
| `graph/extract.py` | One Haiku call per chunk: entities and relations, with a strict JSON schema. Raw output goes to `data/extractions/`. |
| `graph/resolve.py` | Merges aliases into one entity, and scores the result against the ground truth. |
| `graph/build.py` | Loads documents, chunks, entities and relations into Neo4j, with a vector index on entities. |

Key steps:

1. Extract from the same chunks as the baseline. The extractor gets only the
   entity types, never the answer key.
2. Resolve aliases in three steps:
   - Normalise the names and merge exact matches.
   - Find candidates: name rules for persons ("W. Lin" ~ "Wei Lin"), name
     containment, and embedding similarity.
   - Let an LLM decide each candidate. Similarity alone never merges, because
     "Switchboard" / "Switchboard Lite" are similar but different.
3. Link each entity to its chunks with `MENTIONED_IN`. Then a graph traversal
   can get back to the source text.
4. Count the splits and false merges against the ground truth.

---

## Run

```bash
# Phase 0 - check the infrastructure
python scripts/smoke_test.py

# Phase 1 - generate the corpus and the answer key
PYTHONPATH=src python -m graphrag_lab.corpus_gen           # only missing documents
PYTHONPATH=src python -m graphrag_lab.corpus_gen --force   # regenerate all
```

Phase 1 writes `corpus/synthetic/*.md` and `corpus/ground_truth.yaml`. The
corpus is committed to git, because LLM output is not deterministic.

```bash
# Phase 2 - baseline RAG
PYTHONPATH=src python -m graphrag_lab.baseline.index                      # chunk, embed, load Chroma
PYTHONPATH=src python -m graphrag_lab.baseline.answer --qid q_local_1     # expect: correct
PYTHONPATH=src python -m graphrag_lab.baseline.answer --qid q_multi_1     # expect: fails or hedges
PYTHONPATH=src python -m graphrag_lab.baseline.answer --qid q_multi_1 --hybrid
PYTHONPATH=src python -m graphrag_lab.baseline.answer "Who leads Billing Support?"
```

Phase 2 also writes `data/chunks.jsonl`. GraphRAG reads the same file, so
both systems use the same chunks.

```bash
# Phase 3 - evaluate (answers, then judge, then report)
PYTHONPATH=src python -m graphrag_lab.eval.runner                  # all systems, all questions
PYTHONPATH=src python -m graphrag_lab.eval.runner --qids q_multi_1 q_local_1
PYTHONPATH=src python -m graphrag_lab.eval.judge                   # re-judge the latest run
PYTHONPATH=src python -m graphrag_lab.eval.report                  # re-write the latest report
```

Each run writes `results/<run_id>/report.md`.

```bash
# Phase 4 - knowledge graph (Neo4j must be running)
PYTHONPATH=src python -m graphrag_lab.graph.extract     # Haiku, one call per chunk
PYTHONPATH=src python -m graphrag_lab.graph.resolve     # merge aliases, score vs ground truth
PYTHONPATH=src python -m graphrag_lab.graph.build       # full rebuild of the Neo4j graph
```

In Neo4j Browser, look at the graph:

```cypher
MATCH (e:Entity)-[r:RELATED]->(t:Entity) RETURN * LIMIT 150
```

Commands for the later phases are added here when those phases are built.

Each Claude call adds one line to `data/usage.jsonl` (model, tokens, latency,
stage). Use this file to see the cost of each phase.

---

## Layout

```
src/graphrag_lab/
  config.py        all settings, one frozen dataclass
  llm.py           the only Claude call site; writes the usage ledger
  world.py         ground-truth entities, facts, documents, questions
  corpus_gen.py    renders world.py into markdown with Claude
  chunking.py      header-aware chunks, shared by both systems
  embeddings.py    local embeddings with a disk cache
  baseline/        index.py, retrieve.py (dense / hybrid), answer.py
  eval/            systems.py, runner.py, judge.py, report.py
  graph/           extract.py, resolve.py, build.py
scripts/
  smoke_test.py    Phase 0 check
corpus/            generated documents and ground_truth.yaml (committed)
data/              indexes, caches, ledger (not committed)
docs/              plan, concepts, learning notes
```
