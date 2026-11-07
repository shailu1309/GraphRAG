"""Step 2 of graph construction: resolve entity mentions into canonical entities.

    PYTHONPATH=src python -m graphrag_lab.graph.resolve

  1. Normalise names ("the Relay CRM" -> "relay") and merge exact matches.
  2. Find merge candidates of the same type:
       - person names: "W. Lin" ~ "Wei Lin", "Lin" ~ "Wei Lin"
       - token containment: "corvane" ~ "corvane systems"
       - embedding similarity of name + description
  3. Decide. A person match with exactly one possible full name merges at once.
     Every other candidate goes to an LLM tie-break - similarity alone never
     merges, because "Switchboard" ~ "Switchboard Lite" and "Clearline" ~
     "Clearview" are similar AND different.
  4. Write data/graph/entities.json and relations.json, then score the
     resolution against the ground truth: splits and false merges.
"""

from __future__ import annotations

import json
import logging
import re
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field

import numpy as np

from graphrag_lab.config import Config, load_config
from graphrag_lab.embeddings import Embedder
from graphrag_lab.graph.extract import read_extractions
from graphrag_lab.llm import complete, make_client

logger = logging.getLogger(__name__)

ENTITIES_FILE = "entities.json"
RELATIONS_FILE = "relations.json"
PERSON = "person"

_WORD = re.compile(r"[a-z0-9]+")
_TITLES = frozenset({"dr", "mr", "mrs", "ms"})
# Words that name the kind of thing, not the thing: "Billing Support team".
_GENERIC = frozenset({"the", "team", "queue", "project", "system", "platform",
                      "tool", "ivr", "crm", "campaign"})

SAME_SYSTEM = "You decide whether two records from a knowledge graph name the same entity."

SAME_PROMPT = """\
Both records come from internal documents of one telecom contact centre.
Do they refer to the same real-world entity?

Answer same=true only if they clearly do. Similar names are not enough:
variants, editions, versions and similarly named projects are different entities.

A: {a}
B: {b}"""

SAME_SCHEMA = {
    "type": "object",
    "properties": {"same": {"type": "boolean"}, "reason": {"type": "string"}},
    "required": ["same", "reason"],
    "additionalProperties": False,
}


def normalise(name: str) -> str:
    words = [w for w in _WORD.findall(name.lower()) if w not in _TITLES | _GENERIC]
    return " ".join(words) or name.lower().strip()


def _shorter_first(a: str, b: str) -> tuple[str, str]:
    # Fewer words first; on equal word count, fewer characters ("w lin" < "wei lin").
    # Without the tie-break the result depends on argument order.
    return tuple(sorted((a, b), key=lambda s: (len(s.split()), len(s))))


def person_match(a: str, b: str) -> bool:
    """'w lin' ~ 'wei lin', 'dan reyes' ~ 'daniel reyes', 'lin' ~ 'wei lin'."""
    short, long = (s.split() for s in _shorter_first(a, b))
    if short == long:
        return True
    if len(short) == 1:
        return short[0] in (long[0], long[-1])
    if len(short) != len(long) or short[-1] != long[-1]:
        return False
    # Same surname; each given name equal, an initial, or a short form of it.
    return all(l.startswith(s) for s, l in zip(short[:-1], long[:-1]))


def _contains(a: str, b: str) -> bool:
    sa, sb = set(a.split()), set(b.split())
    return sa < sb or sb < sa


@dataclass
class Group:
    """All mentions that share one normalised name. Mutable while resolving."""
    key: str
    names: Counter = field(default_factory=Counter)
    types: Counter = field(default_factory=Counter)
    descriptions: list[str] = field(default_factory=list)
    chunk_ids: set[str] = field(default_factory=set)

    @property
    def type(self) -> str:
        return self.types.most_common(1)[0][0]

    @property
    def name(self) -> str:
        return max(self.names, key=lambda n: (self.names[n], len(n)))

    def card(self, limit: int) -> str:
        return f"{self.name} ({self.type}): " + " | ".join(self.descriptions[:limit])


class UnionFind:
    def __init__(self, n: int) -> None:
        self.parent = list(range(n))

    def find(self, i: int) -> int:
        while self.parent[i] != i:
            self.parent[i] = self.parent[self.parent[i]]
            i = self.parent[i]
        return i

    def union(self, i: int, j: int) -> None:
        self.parent[self.find(i)] = self.find(j)


def collect(extractions: list[dict]) -> tuple[list[Group], list[dict]]:
    """Step 1: exact merge on the normalised name. Returns groups and raw relations."""
    groups: dict[str, Group] = {}
    for ex in extractions:
        for e in ex["entities"]:
            g = groups.setdefault(normalise(e["name"]), Group(key=normalise(e["name"])))
            g.names[e["name"]] += 1
            g.types[e["type"]] += 1
            if e["description"] not in g.descriptions:
                g.descriptions.append(e["description"])
            g.chunk_ids.add(ex["chunk_id"])
    relations = [{**r, "chunk_id": ex["chunk_id"]} for ex in extractions for r in ex["relations"]]
    return list(groups.values()), relations


def candidates(groups: list[Group], cfg: Config) -> tuple[list[tuple[int, int]], list[tuple[int, int]]]:
    """Step 2: return (auto_merge, ask_llm) index pairs."""
    vectors = Embedder(cfg).embed_documents([g.card(1) for g in groups])  # (G, D), normalised
    sims = vectors @ vectors.T  # (G, G) cosine

    person_hits: dict[int, list[int]] = defaultdict(list)
    ask: list[tuple[int, int]] = []
    for i in range(len(groups)):
        for j in range(i + 1, len(groups)):
            a, b = groups[i], groups[j]
            if a.type != b.type:
                continue
            if a.type == PERSON:
                if person_match(a.key, b.key):
                    short = i if _shorter_first(a.key, b.key)[0] == a.key else j
                    person_hits[short].append(j if short == i else i)
                elif sims[i, j] >= cfg.resolve_similarity:
                    ask.append((i, j))  # e.g. a nickname the name rule cannot see
            elif _contains(a.key, b.key) or sims[i, j] >= cfg.resolve_similarity:
                ask.append((i, j))

    auto = []
    for short, longs in person_hits.items():
        # "Lin" with two possible full names is ambiguous: let the LLM decide each.
        target = auto if len(longs) == 1 else ask
        target.extend((short, other) for other in longs)
    return auto, ask


def same_entity(client, cfg: Config, a: Group, b: Group) -> bool:
    verdict = complete(
        client,
        cfg,
        model=cfg.extract_model,
        system=SAME_SYSTEM,
        prompt=SAME_PROMPT.format(a=a.card(cfg.max_merged_descriptions),
                                  b=b.card(cfg.max_merged_descriptions)),
        max_tokens=cfg.resolve_max_tokens,
        effort=cfg.resolve_effort,
        json_schema=SAME_SCHEMA,
        stage="graph:resolve",
    ).json
    logger.info("  %-5s %s  <->  %s  (%s)", "MERGE" if verdict["same"] else "keep",
                a.name, b.name, verdict["reason"])
    return verdict["same"]


def _slug(text: str) -> str:
    return "-".join(_WORD.findall(text.lower()))


def resolve(cfg: Config) -> tuple[list[dict], list[dict]]:
    groups, raw_relations = collect(read_extractions(cfg))
    auto, ask = candidates(groups, cfg)
    logger.info("%d name groups; %d automatic person merges; %d pairs for the LLM",
                len(groups), len(auto), len(ask))

    client = make_client(cfg)
    with ThreadPoolExecutor(max_workers=cfg.extract_workers) as pool:
        verdicts = list(pool.map(lambda p: same_entity(client, cfg, groups[p[0]], groups[p[1]]), ask))

    uf = UnionFind(len(groups))
    for i, j in auto + [p for p, same in zip(ask, verdicts) if same]:
        uf.union(i, j)

    # Merge each union-find cluster into one entity.
    clusters: dict[int, list[Group]] = defaultdict(list)
    for i, g in enumerate(groups):
        clusters[uf.find(i)].append(g)

    entities, id_of_root, used_ids = [], {}, Counter()
    for root, members in clusters.items():
        merged = Group(key=members[0].key)
        for g in members:
            merged.names.update(g.names)
            merged.types.update(g.types)
            merged.descriptions += [d for d in g.descriptions if d not in merged.descriptions]
            merged.chunk_ids |= g.chunk_ids
        base = f"{merged.type}:{_slug(merged.name)}"
        used_ids[base] += 1
        eid = base if used_ids[base] == 1 else f"{base}-{used_ids[base]}"
        id_of_root[root] = eid
        entities.append({
            "id": eid,
            "name": merged.name,
            "type": merged.type,
            "aliases": sorted(set(merged.names) - {merged.name}),
            "description": " ".join(merged.descriptions[: cfg.max_merged_descriptions]),
            "chunk_ids": sorted(merged.chunk_ids),
        })

    index_of_key = {g.key: i for i, g in enumerate(groups)}
    aggregated: dict[tuple, dict] = {}
    dangling = 0
    for r in raw_relations:
        src, tgt = index_of_key.get(normalise(r["source"])), index_of_key.get(normalise(r["target"]))
        if src is None or tgt is None:
            dangling += 1  # the extractor named an endpoint it did not list as an entity
            continue
        s, t = id_of_root[uf.find(src)], id_of_root[uf.find(tgt)]
        if s == t:
            continue  # a relation between two aliases of one entity
        agg = aggregated.setdefault((s, t, r["type"]), {
            "source": s, "target": t, "type": r["type"],
            "descriptions": [], "strengths": [], "chunk_ids": set(),
        })
        if r["description"] not in agg["descriptions"]:
            agg["descriptions"].append(r["description"])
        agg["strengths"].append(r["strength"])
        agg["chunk_ids"].add(r["chunk_id"])

    relations = [{
        "source": a["source"], "target": a["target"], "type": a["type"],
        "description": " ".join(a["descriptions"][: cfg.max_merged_descriptions]),
        "strength": round(float(np.mean(a["strengths"])), 2),
        "count": len(a["strengths"]),
        "chunk_ids": sorted(a["chunk_ids"]),
    } for a in aggregated.values()]
    logger.info("%d entities, %d relations (%d dangling relations dropped)",
                len(entities), len(relations), dangling)
    return entities, relations


def score_against_ground_truth(entities: list[dict]) -> None:
    """Evaluation only - the one place in graph/ that reads the answer key."""
    from graphrag_lab import world

    forms_of = {e.id: {normalise(n) for n in (e.name, *e.aliases)} for e in world.ENTITIES}
    resolved_forms = {e["id"]: {normalise(n) for n in (e["name"], *e["aliases"])} for e in entities}

    splits, missing, merges = [], [], []
    for wid, forms in forms_of.items():
        hits = [rid for rid, rf in resolved_forms.items() if rf & forms]
        if not hits:
            missing.append(wid)
        elif len(hits) > 1:
            splits.append((wid, hits))
    for rid, rf in resolved_forms.items():
        owners = [wid for wid, forms in forms_of.items() if rf & forms]
        if len(owners) > 1:
            merges.append((rid, owners))

    logger.info("\nresolution vs ground truth (%d true entities)", len(forms_of))
    logger.info("  split (one true entity, several nodes): %d", len(splits))
    for wid, hits in splits:
        logger.info("    %s -> %s", wid, hits)
    logger.info("  false merge (one node, several true entities): %d", len(merges))
    for rid, owners in merges:
        logger.info("    %s <- %s", rid, owners)
    logger.info("  not found by name (extracted under another name, or not at all): %d", len(missing))
    if missing:
        logger.info("    %s", ", ".join(missing))


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    for noisy in ("httpx", "sentence_transformers"):
        logging.getLogger(noisy).setLevel(logging.WARNING)

    cfg = load_config()
    entities, relations = resolve(cfg)
    cfg.graph_dir.mkdir(parents=True, exist_ok=True)
    (cfg.graph_dir / ENTITIES_FILE).write_text(json.dumps(entities, indent=2))
    (cfg.graph_dir / RELATIONS_FILE).write_text(json.dumps(relations, indent=2))
    logger.info("wrote %s", cfg.graph_dir)
    score_against_ground_truth(entities)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
