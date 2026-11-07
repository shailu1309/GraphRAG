# Baseline RAG vs GraphRAG — a hands-on comparison lab

## Context

You want to *understand* GraphRAG, not just run it. The goal is a single project containing
two retrieval systems over **the same corpus and the same chunks**, differing only in how they
retrieve, plus an evaluation harness that makes the difference visible and explainable.

The key insight shaping this plan: **GraphRAG does not beat vector RAG on average.** It wins on
specific question shapes (multi-hop, whole-corpus synthesis, entity-centric gather, set/count) and
loses on cost and latency everywhere. A comparison that doesn't separate questions by shape just
produces a muddy "both are fine" result and teaches you nothing. So the question bank is the
centre of this project, not an afterthought.

Second design decision: we build and evaluate the **baseline first**, and look at its failures,
*before* building GraphRAG. Seeing baseline RAG confidently answer a multi-hop question wrong is
what makes the rest of the work feel necessary.

**Your role vs mine:** you write and run the code. For each step I give you the spec — what the
module does, the function signatures, the concept to understand, and how to verify it worked.
You implement; I review, debug, and explain. If you'd rather see a reference implementation for a
given step, ask and I'll write it, ideally after you've taken a pass yourself.

### Stack (decided)

| Concern | Choice | Why |
|---|---|---|
| Generation | Claude `claude-opus-5-5` | Answer synthesis and judging |
| Bulk extraction | Claude `claude-haiku-5-5` | ~300 extraction calls; 40x cheaper, ample for structured extraction |
| Embeddings | `sentence-transformers`, `BAAI/bge-small-en-v1.5` (384-d) | Local, free, offline, runs on M4 MPS. No second API account |
| Vector store | **Chroma** (persistent, local) | The leanest real vector DB. pgvector/Pinecone add infra that teaches nothing here — noted as a later swap |
| Graph store | **Neo4j Community via Docker** | Neo4j Browser is the point: you need to *see* the graph. Cypher is the standard |
| Communities | `networkx.community.louvain_communities` | Zero extra deps. `leidenalg` + `python-igraph` as an optional upgrade — Leiden is what MS GraphRAG uses |
| Orchestration | None (plain Python) | No LangChain/LlamaIndex — frameworks hide exactly the mechanisms you're trying to learn |

Machine is fine for this: Apple M4, 16 GB RAM, 297 GB free. Docker Desktop is installed but
**the daemon is not running** — you'll need to start it in Step 0.

### Expected cost

Roughly **$3–8 total** in Claude API spend across the whole project, dominated by GraphRAG
indexing and global search. We'll put a token/cost ledger in the eval harness from the start,
because *"GraphRAG costs 20x more to index"* is one of the findings you're after, not a nuisance.

---

## Phase 0 — Scaffold and infrastructure

**Files:** `pyproject.toml`, `.env.example`, `docker-compose.yml`, `Makefile`,
`src/graphrag_lab/config.py`, `scripts/smoke_test.py`

1. `python3 -m venv .venv` and a `requirements.txt`: `anthropic`, `sentence-transformers`,
   `chromadb`, `neo4j`, `networkx`, `python-dotenv`, `pydantic`, `rich`, `tiktoken`.
2. `docker-compose.yml` with one Neo4j Community service: ports `7474` (Browser) and `7687`
   (Bolt), a named volume for `/data`, `NEO4J_AUTH=neo4j/<password>`. No APOC needed — plain
   Cypher plus the native vector index covers everything we do.
   Pin an explicit image tag rather than `latest`; we'll confirm a current one when we run it.
3. `config.py` — one frozen dataclass holding model IDs, chunk size/overlap, `top_k`, embedding
   model name, Neo4j URI/creds, paths, and a global `SEED`. Every script reads config; no magic
   numbers scattered across modules.
4. `scripts/smoke_test.py` must prove four things independently: Claude responds, the embedding
   model loads and returns a 384-vector, Chroma persists and round-trips a document, and Neo4j
   accepts a Cypher write and read.

**Auth note:** `ANTHROPIC_API_KEY` is not set and the `ant` CLI isn't installed. Simplest path is
to export an API key from the Anthropic Console into `.env`. Put `.env` in `.gitignore`.

**Verify:** `python scripts/smoke_test.py` prints four green checks, and
`http://localhost:7474` opens Neo4j Browser.

---

## Phase 1 — Corpus and ground truth

**Files:** `src/graphrag_lab/corpus_gen.py`, `corpus/synthetic/*.md`, `corpus/ground_truth.yaml`

This phase is where the experiment is won or lost. We generate a corpus whose facts are
*deliberately distributed across documents* so that no single chunk answers a multi-hop question.

Domain: a fictional research/biotech organisation — **~35–40 markdown documents**, mixed genres
(team pages, project charters, quarterly updates, incident post-mortems, acquisition memos,
personnel announcements, external partnership agreements, platform dependency docs).

Entities: ~25 people, ~12 projects, ~6 teams, ~4 acquired companies, ~8 technologies/platforms,
~5 external partners.

The generation script builds this in two stages, which matters:
1. **Define the ground-truth graph first, in code** — a hand-written Python structure of entities
   and relations (`person_a --led--> acquisition_x`, `project_p --depends_on--> platform_q`).
   This is your answer key, and it exists before any text does.
2. **Then ask Claude to write each document** rendering only a *slice* of that graph, in natural
   prose, with the cross-document connections left implicit. Never state a multi-hop chain inside
   one document.

Deliberately plant:
- **Chains of length 3+** for multi-hop questions
- **Scattered entities** — one person mentioned across 8 documents, each with a different detail
- **Corpus-wide themes** (recurring risk categories, a cost-overrun pattern) that no single
  document summarises
- **Aliases** — "Dr. Chen", "Wei Chen", "W. Chen" — so entity resolution is a real problem
- **Near-miss distractors** — two similarly named projects, so dense retrieval can plausibly
  grab the wrong one
- **One genuine absence** — a plausible-sounding event that never happened, for hallucination tests

`ground_truth.yaml` records, per planned question: the answer, the specific documents required,
and the atomic facts a correct answer must contain. Fact-level recall scoring depends on this.

**Verify:** `grep` for a planted chain and confirm no single file contains the whole path.
Read 3 documents and check they sound like real org documents, not LLM filler.

---

## Phase 2 — Baseline RAG

**Files:** `src/graphrag_lab/chunking.py`, `embeddings.py`, `llm.py`,
`baseline/index.py`, `baseline/retrieve.py`, `baseline/answer.py`

`chunking.py` is **shared by both systems** — this is the fairness guarantee, and worth being
strict about. Markdown-header-aware splitting, ~600 tokens with ~80 overlap, each chunk carrying
`{chunk_id, doc_id, doc_title, header_path, text}`.

`embeddings.py` wraps sentence-transformers with a small on-disk cache keyed by text hash, so
re-indexing doesn't recompute. Normalise vectors; use cosine.

`llm.py` is the single Claude call site for the whole project — one function that takes a prompt
and model and returns text plus a usage record appended to a JSONL ledger. Every token the
project spends flows through here. Don't let API calls sprout in other modules.

Baseline retrieval is deliberately a *good-faith* baseline, not a straw man: dense top-k
(`k=5`), with an optional BM25 hybrid and reciprocal-rank fusion you can toggle. If GraphRAG only
wins against a crippled baseline, the comparison is worthless.

`answer.py`: stuff retrieved chunks into a prompt with source labels, instruct Claude to answer
only from context and to say so when the context is insufficient, return the answer plus the
chunk IDs used.

**Verify:** ask "What is Project `<name>`?" — expect a correct, well-sourced answer. Then ask a
planted multi-hop question and watch it fail or hedge. That failure is the point of this phase.

---

## Phase 3 — Evaluation harness (before GraphRAG)

**Files:** `src/graphrag_lab/eval/questions.py`, `runner.py`, `judge.py`, `report.py`

**~30 questions across 6 shapes**, each tagged with its shape and linked to `ground_truth.yaml`:

| Shape | n | Example | Expectation |
|---|---|---|---|
| `local_factual` | 6 | "What is Project Meridian's objective?" | Baseline fine; may even beat GraphRAG (less noise) |
| `multi_hop` | 6 | "Which platform does the project led by the person who ran the Halcyon acquisition depend on?" | GraphRAG wins |
| `global_thematic` | 5 | "What are the recurring causes of project delay across the organisation?" | GraphRAG wins decisively — baseline structurally cannot see the whole corpus |
| `entity_gather` | 5 | "Everything we know about Dr. Chen" | GraphRAG wins — top-5 can't reach 8 documents |
| `set_count` | 4 | "How many projects depend on the Atlas platform, and which?" | Baseline fails badly |
| `absent_info` | 4 | "What were the findings of the 2024 safety audit?" (never happened) | Tests hallucination both ways |

`runner.py` runs every question through every configured system, recording answer, retrieved
context, context token count, latency, and cost. Results to disk as JSONL so you can re-score
without re-querying.

`judge.py` — Claude-as-judge with the ground truth in the prompt, scoring **three separate
things** rather than one blurry number: correctness (0–2), fact recall (fraction of required
atomic facts present, computed against `ground_truth.yaml`), and groundedness (any claim not
supported by retrieved context → unfaithful). Judge with `claude-opus-5-5`, and spot-check ~5
judgements by hand: an unaudited LLM judge is not evidence.

`report.py` emits a markdown/HTML table broken down **by question shape**, plus side-by-side
answer diffs for the most interesting individual questions.

**Verify:** run the full eval against baseline only. You now have a quantified map of exactly
where vector RAG breaks, per shape. Read the failures before continuing — they're the curriculum.

---

## Phase 4 — Knowledge graph construction

**Files:** `src/graphrag_lab/graph/extract.py`, `resolve.py`, `build.py`

1. **Extract** (`claude-haiku-5-5`, one call per chunk, ~300 calls): structured output giving
   entities (`name`, `type`, `description`) and relations (`source`, `target`, `type`,
   `description`, `strength`). Use a strict schema and keep raw output in `data/extractions/` —
   you'll want to inspect extraction quality, and it saves re-running on a schema tweak.
   Expect this to be imperfect. Looking at *where* extraction is wrong is itself a lesson.
2. **Resolve** entities: normalise, then merge aliases. Start with exact + fuzzy name matching;
   upgrade to embedding-similarity clustering with an LLM tie-break for the hard cases. Your
   planted aliases ("Dr. Chen" / "Wei Chen") are the test. Merge descriptions on collapse.
3. **Build** in Neo4j: `(:Entity {name, type, description, embedding})`,
   `(:Chunk {chunk_id, text, doc_id})`, `(:Document)`, with `[:RELATED {type, description,
   strength}]` between entities and `[:MENTIONED_IN]` from entity to chunk. The entity→chunk edge
   is what lets graph traversal reach back to source text. Create a native vector index on
   `Entity.embedding`, and uniqueness constraints on the IDs.

**Verify — this is the fun part:** open Neo4j Browser and run
`MATCH (e:Entity)-[r:RELATED]->(t) RETURN * LIMIT 100`. You should be able to trace a planted
multi-hop chain visually, with your own eyes. Then run the hop as Cypher and confirm it returns
the right answer. That is GraphRAG's advantage, made concrete.

---

## Phase 5 — Communities and community reports

**Files:** `src/graphrag_lab/graph/communities.py`, `summarize.py`

1. Project the entity graph out of Neo4j into networkx, weighting edges by relation strength
   and co-occurrence count.
2. `louvain_communities` at **two or three resolution levels** to get a hierarchy — coarse
   communities for broad questions, fine for specific ones. Write `community_id` per level back
   onto the Neo4j nodes.
3. For each community, generate a **community report** with Claude: title, summary, key entities,
   key findings, with the entity/relation descriptions as input. Build the hierarchy bottom-up so
   higher-level reports summarise their children rather than re-reading everything. Store reports
   in Neo4j as `(:Community)` nodes and embed their summaries.

Community reports are the mechanism that makes global/thematic questions answerable at all. They
are a *pre-computed, multi-resolution summary of the entire corpus* — which is precisely the thing
a top-k vector store cannot produce at query time.

**Verify:** read 3 community reports. They should each describe a recognisable cluster of your
org (one team's work, one acquisition's fallout). If they're generic mush, the extraction or
resolution upstream needs work.

---

## Phase 6 — GraphRAG retrieval

**Files:** `src/graphrag_lab/graph/local_search.py`, `global_search.py`, `answer.py`

**Local search** (entity-anchored — for multi-hop, entity-gather, set/count):
1. Embed the question, vector-search `Entity.embedding` for seed entities.
2. Expand 1–2 hops in Cypher from the seeds.
3. Gather a mixed context budget: entity descriptions, the relations connecting them, source
   chunks via `[:MENTIONED_IN]`, and the reports of the communities those entities belong to.
4. Rank and truncate to a token budget, then answer.

**Global search** (map-reduce — for thematic questions):
1. **Map:** in parallel, ask `claude-haiku-5-5` of each community report at a chosen level for
   points relevant to the question, each with a 0–100 importance score.
2. **Reduce:** sort all points by score, take the top ones within budget, and have
   `claude-opus-5-5` synthesise the final answer.

Note that global search never touches the vector store at all. It reads *summaries of the whole
corpus*. Internalising why that is structurally different from top-k retrieval is most of the
conceptual payoff of this project.

A small router (or an explicit per-question mode in the eval, which is cleaner for a controlled
experiment) decides local vs global.

**Verify:** the multi-hop and thematic questions that baseline failed in Phase 3 should now pass.

---

## Phase 7 — The comparison

Re-run `eval/runner.py` across all three systems — `baseline`, `graph_local`, `graph_global` —
and produce the report. What you should expect to see, and should treat as findings rather than
assumptions:

- `local_factual`: roughly a tie; baseline sometimes **better** (graph context adds noise)
- `multi_hop`, `entity_gather`, `set_count`: large GraphRAG win
- `global_thematic`: baseline near-total failure, GraphRAG strong
- `absent_info`: watch carefully — GraphRAG's richer context can *increase* confident
  hallucination
- **Cost/latency: GraphRAG dramatically worse.** Report indexing cost once, and per-query cost
  and context tokens per shape. The honest conclusion is a trade-off, not a winner.

Write up `FINDINGS.md` with the table, the three or four most illuminating answer diffs, and your
own account of the mechanism behind each win and loss.

---

## Phase 8 — Real corpus validation

Swap `corpus/synthetic/` for a real corpus (a connected set of Wikipedia articles, or arXiv
abstracts in one subfield) and re-run both pipelines end to end. No ground truth here, so scoring
shifts to pairwise preference judging — Claude sees both answers blind and picks, with position
counterbalanced. This confirms the synthetic finding wasn't an artifact of a corpus built to
produce it, which is the honest check on everything above.

---

## Verification summary

| Phase | Gate |
|---|---|
| 0 | `smoke_test.py`: 4/4 green; Neo4j Browser loads |
| 1 | No single document contains a complete planted chain |
| 2 | Local factual question answered correctly; multi-hop fails |
| 3 | Full baseline eval scored and broken down by shape; ~5 judgements hand-audited |
| 4 | Planted chain traceable by eye in Neo4j Browser and by Cypher |
| 5 | Community reports describe recognisable real clusters |
| 6 | Phase-3 multi-hop and thematic failures now pass |
| 7 | `FINDINGS.md` with per-shape scores **and** cost/latency |
| 8 | Finding holds on a real corpus under blind pairwise judging |

## Notes

- I'll load your `ml-code-style` skill before writing any reference Python so it arrives in your
  conventions rather than needing a cleanup pass.
- `git init` is worth doing in Phase 0 — you'll want to diff retrieval behaviour across changes.
- Not in scope unless you ask: pgvector/Pinecone swap, reranker models, Leiden instead of
  Louvain, agentic/multi-step retrieval, Microsoft's `graphrag` library for comparison. All are
  natural follow-ons once the core comparison works.
