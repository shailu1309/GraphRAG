"""Markdown-header-aware chunking, shared by BOTH retrieval systems.

This module is the fairness guarantee of the experiment: baseline RAG and
GraphRAG read the same chunks, so any difference in results comes from the
retrieval, not from the text each system saw.

Strategy: split a document on its "## " sections, then pack whole sections
into a chunk until chunk_size_tokens. A single section larger than the limit
is cut into overlapping token windows.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass

import tiktoken

from graphrag_lab.config import Config

TITLE_PREFIX = "# "
SECTION_PREFIX = "## "
PREAMBLE_HEADER = "Overview"


@dataclass(frozen=True)
class Chunk:
    chunk_id: str
    doc_id: str
    doc_title: str
    header_path: str
    text: str

    @property
    def embed_text(self) -> str:
        # The title and headers carry the names ("INC-0312", "NETESC") that a
        # section body often leaves implicit - so they are embedded too.
        return f"{self.doc_title} > {self.header_path}\n\n{self.text}"


def split_sections(markdown: str) -> tuple[str, list[tuple[str, str]]]:
    """Return (title, [(section_header, section_body), ...])."""
    lines = markdown.strip().splitlines()
    if not lines or not lines[0].startswith(TITLE_PREFIX):
        raise ValueError(f"document must start with '{TITLE_PREFIX}': {lines[:1]}")
    title = lines[0][len(TITLE_PREFIX):].strip()

    sections: list[tuple[str, list[str]]] = [(PREAMBLE_HEADER, [])]
    for line in lines[1:]:
        if line.startswith(SECTION_PREFIX):
            sections.append((line[len(SECTION_PREFIX):].strip(), []))
        else:
            sections[-1][1].append(line)

    bodies = [(header, "\n".join(body).strip()) for header, body in sections]
    return title, [(header, body) for header, body in bodies if body]


def _windows(text: str, enc, size: int, overlap: int) -> list[str]:
    tokens = enc.encode(text)
    step = size - overlap
    return [enc.decode(tokens[i : i + size]) for i in range(0, len(tokens), step)
            if tokens[i : i + size]]


def chunk_document(doc_id: str, markdown: str, cfg: Config, enc) -> list[Chunk]:
    title, sections = split_sections(markdown)
    size, overlap = cfg.chunk_size_tokens, cfg.chunk_overlap_tokens

    # Each piece is (header, text) and fits within `size` on its own.
    pieces: list[tuple[str, str]] = []
    for header, body in sections:
        if len(enc.encode(body)) <= size:
            pieces.append((header, body))
        else:
            pieces.extend((header, w) for w in _windows(body, enc, size, overlap))

    groups: list[list[tuple[str, str]]] = [[]]
    used = 0
    for header, text in pieces:
        n = len(enc.encode(text))
        if groups[-1] and used + n > size:
            groups.append([])
            used = 0
        groups[-1].append((header, text))
        used += n

    chunks = []
    for i, group in enumerate(groups):
        headers = list(dict.fromkeys(h for h, _ in group))  # ordered, de-duplicated
        chunks.append(Chunk(
            chunk_id=f"{doc_id}#{i:02d}",
            doc_id=doc_id,
            doc_title=title,
            header_path="; ".join(headers),
            text="\n\n".join(f"{SECTION_PREFIX}{h}\n{t}" for h, t in group),
        ))
    return chunks


def chunk_corpus(cfg: Config) -> list[Chunk]:
    paths = sorted(cfg.synthetic_dir.glob("*.md"))
    if not paths:
        raise FileNotFoundError(f"no documents in {cfg.synthetic_dir} - run corpus_gen")
    enc = tiktoken.get_encoding(cfg.chunk_tokenizer)
    return [c for p in paths for c in chunk_document(p.stem, p.read_text(), cfg, enc)]


def write_chunks(cfg: Config, chunks: list[Chunk]) -> None:
    cfg.chunks_path.parent.mkdir(parents=True, exist_ok=True)
    with cfg.chunks_path.open("w") as f:
        for chunk in chunks:
            f.write(json.dumps(asdict(chunk)) + "\n")


def read_chunks(cfg: Config) -> list[Chunk]:
    if not cfg.chunks_path.exists():
        raise FileNotFoundError(f"{cfg.chunks_path} missing - run baseline.index first")
    with cfg.chunks_path.open() as f:
        return [Chunk(**json.loads(line)) for line in f]
