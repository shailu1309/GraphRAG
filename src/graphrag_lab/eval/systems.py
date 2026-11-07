"""Registry of the retrieval systems under evaluation.

A system is anything that turns a question into a Context. The answer step,
the judge and the report are the same for all of them. GraphRAG systems are
added here in Phase 6.
"""

from __future__ import annotations

from collections.abc import Callable

from graphrag_lab.baseline.answer import Context, baseline_context
from graphrag_lab.baseline.retrieve import BaselineRetriever
from graphrag_lab.config import Config

ContextBuilder = Callable[[str], Context]

SYSTEMS = ("baseline_dense", "baseline_hybrid")


def build_system(cfg: Config, name: str) -> ContextBuilder:
    if name in ("baseline_dense", "baseline_hybrid"):
        retriever = BaselineRetriever(cfg, hybrid=name == "baseline_hybrid")
        return lambda question: baseline_context(retriever.retrieve(question))
    raise ValueError(f"unknown system {name!r}; known: {SYSTEMS}")
