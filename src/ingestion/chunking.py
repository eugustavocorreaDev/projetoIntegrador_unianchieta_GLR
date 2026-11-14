"""Estratégias de divisão de texto (chunking) comparadas na avaliação.

- fixed: janelas de N caracteres com sobreposição, cortando em espaços. Ignora a
  estrutura do documento (baseline).
- recursive: respeita a estrutura do Markdown. Divide por seções (títulos), depois
  agrupa parágrafos até o limite e só quebra um parágrafo grande por linhas, frases
  e palavras, nessa ordem. Um bloco de código só é quebrado (por linhas) quando,
  sozinho, passa do limite.
"""

from __future__ import annotations

import bisect
import uuid
from typing import Protocol

from core.schemas import Chunk, Document
from ingestion.markdown import find_headings, split_blocks, split_sections


def make_chunk_id(strategy: str, source: str, index: int) -> str:
    return str(uuid.uuid5(uuid.NAMESPACE_URL, f"{strategy}:{source}:{index}"))


class Chunker(Protocol):
    strategy: str

    def split(self, document: Document) -> list[Chunk]: ...


class FixedSizeChunker:
    strategy = "fixed"

    def __init__(self, chunk_size: int = 800, chunk_overlap: int = 120) -> None:
        if chunk_size <= 0:
            raise ValueError("chunk_size deve ser positivo")
        if not 0 <= chunk_overlap < chunk_size:
            raise ValueError("chunk_overlap deve estar entre 0 e chunk_size - 1")
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

    def _windows(self, text: str) -> list[tuple[int, str]]:
        size, overlap, n = self.chunk_size, self.chunk_overlap, len(text)
        windows: list[tuple[int, str]] = []
        start = 0
        while start < n:
            end = min(start + size, n)
            if end < n:
                # Recua até o último espaço da segunda metade da janela, para não cortar palavras
                cut = max(
                    text.rfind(" ", start + size // 2, end),
                    text.rfind("\n", start + size // 2, end),
                )
                if cut > start:
                    end = cut
            piece = text[start:end]
            if piece.strip():
                lead = len(piece) - len(piece.lstrip())
                windows.append((start + lead, piece.strip()))
            if end >= n:
                break
            next_start = max(end - overlap, start + 1)
            # Recua até o espaço anterior: a janela seguinte começa numa palavra inteira e a
            # sobreposição nunca fica menor que `overlap`, mesmo com tokens longos sem espaço
            back = max(
                text.rfind(" ", start + 1, next_start), text.rfind("\n", start + 1, next_start)
            )
            start = back + 1 if back > start else next_start
        return windows

    def split(self, document: Document) -> list[Chunk]:
        headings = find_headings(document.text)
        offsets = [h.offset for h in headings]
        chunks: list[Chunk] = []
        for index, (start, piece) in enumerate(self._windows(document.text)):
            pos = bisect.bisect_right(offsets, start) - 1
            section = " > ".join(headings[pos].path) if pos >= 0 else document.title
            chunks.append(
                Chunk(
                    id=make_chunk_id(self.strategy, document.source, index),
                    text=piece,
                    source=document.source,
                    section=section,
                    chunk_index=index,
                    strategy=self.strategy,
                )
            )
        return chunks


def _split_oversized(text: str, size: int, separators: tuple[str, ...]) -> list[str]:
    """Quebra recursivamente um bloco maior que `size` pelos separadores, em ordem."""
    if len(text) <= size:
        return [text]
    if not separators:
        return [text[i : i + size] for i in range(0, len(text), size)]
    sep, rest = separators[0], separators[1:]
    raw = text.split(sep)
    # Mantém o separador grudado em cada parte para não perder pontuação nas fronteiras
    parts = [p for p in [r + sep for r in raw[:-1]] + raw[-1:] if p.strip()]
    if len(parts) == 1:
        return _split_oversized(text, size, rest)
    pieces: list[str] = []
    current = ""
    for part in parts:
        candidate = current + part
        if len(candidate) <= size:
            current = candidate
            continue
        if current:
            pieces.append(current)
        if len(part) > size:
            pieces.extend(_split_oversized(part, size, rest))
            current = ""
        else:
            current = part
    if current:
        pieces.append(current)
    return [p.strip() for p in pieces if p.strip()]


class RecursiveSectionChunker:
    strategy = "recursive"
    separators: tuple[str, ...] = ("\n", ". ", " ")

    def __init__(self, chunk_size: int = 800, chunk_overlap: int = 0) -> None:
        if chunk_size <= 0:
            raise ValueError("chunk_size deve ser positivo")
        self.chunk_size = chunk_size
        # Sem sobreposição: as fronteiras já seguem a estrutura (seções e parágrafos).
        self.chunk_overlap = chunk_overlap

    def _pack(self, blocks: list[str]) -> list[str]:
        pieces: list[str] = []
        current = ""
        for block in blocks:
            for part in _split_oversized(block, self.chunk_size, self.separators):
                candidate = f"{current}\n\n{part}" if current else part
                if len(candidate) <= self.chunk_size:
                    current = candidate
                else:
                    if current:
                        pieces.append(current)
                    current = part
        if current:
            pieces.append(current)
        return pieces

    def split(self, document: Document) -> list[Chunk]:
        chunks: list[Chunk] = []
        for section in split_sections(document.text):
            section_name = section.path_str or document.title
            for piece in self._pack(split_blocks(section.body)):
                index = len(chunks)
                chunks.append(
                    Chunk(
                        id=make_chunk_id(self.strategy, document.source, index),
                        text=piece,
                        source=document.source,
                        section=section_name,
                        chunk_index=index,
                        strategy=self.strategy,
                    )
                )
        return chunks


def get_chunker(strategy: str, chunk_size: int = 800, chunk_overlap: int = 120) -> Chunker:
    if strategy == "fixed":
        return FixedSizeChunker(chunk_size, chunk_overlap)
    if strategy == "recursive":
        return RecursiveSectionChunker(chunk_size)
    raise ValueError(f"Estratégia de chunking desconhecida: {strategy!r}")
