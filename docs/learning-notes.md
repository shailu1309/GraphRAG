# Learning notes

Short notes on the libraries, tools and concepts in this project. Added as they
come up. See [rag-vs-graphrag.md](rag-vs-graphrag.md) for the main explanation.

---

## networkx

A graph library in pure Python. It holds nodes and edges in memory, and it runs
graph algorithms on them.

This project uses networkx for **community detection** in Phase 5. The steps:

1. Read the entity graph out of Neo4j.
2. Run `networkx.community.louvain_communities` on it.
3. Write the community ID of each entity back to Neo4j.

Neo4j cannot run Louvain without the GDS plugin. The Community edition does not
have this plugin. networkx fills the gap.

`leidenalg` with `python-igraph` is an optional upgrade. Leiden is the algorithm
that Microsoft GraphRAG uses.

---

## rank-bm25

Keyword search of the classic type. BM25 gives a score to each document from the
number of times the query words are in it. The score also uses two corrections:
rare words count more, and long documents count less.

BM25 uses no embeddings. It matches words only, not meaning.

**Why this project needs it.** Embeddings miss exact strings. For example, you ask
about "Project Meridian-7". A vector search can return the chunk about
"Meridian-2", because the two chunks are almost the same text. BM25 matches the
exact token.

This project uses BM25 for the optional hybrid baseline in Phase 2: dense top-k
search plus BM25, with the two result lists fused. A strong baseline matters. If
GraphRAG only wins against a weak baseline, the comparison proves very little.

---

Both libraries run locally. Neither library makes an API call, and neither has a
cost.

---

## Bolt, and the two Neo4j ports

Bolt is the network protocol of Neo4j. It is not a general concept of software
development. Bolt has the same position in the stack as HTTP. It is a different
language on the same type of TCP connection.

Each database makes its own protocol. These URL schemes show the pattern:

| Scheme | Protocol | Which client speaks it |
|---|---|---|
| `http://localhost:3000` | HTTP | a browser, or curl |
| `postgresql://localhost:5432` | the Postgres wire protocol | `psycopg2` |
| `bolt://localhost:7687` | Bolt | the `neo4j` Python driver |

The Neo4j container gives you two ports. You cannot use one port in place of the
other port:

- **Port 7474** uses HTTP. This port gives the Neo4j Browser, which you open in
  Chrome.
- **Port 7687** uses Bolt. `GraphDatabase.driver()` connects to this port from
  Python.

Bolt has three advantages against HTTP:

1. Bolt is binary, not text. The data on the network is smaller.
2. Bolt keeps one connection open for many queries. HTTP needs one request for
   each query.
3. Bolt sends the result rows one at a time. A large `MATCH` query does not put
   all the rows in memory before you see the first row.

In `bolt://localhost:7687`, `localhost` is the host. `bolt` tells the driver
which port to use, and which language to speak.
