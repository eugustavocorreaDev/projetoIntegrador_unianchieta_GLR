"""Utilitários de Markdown que respeitam blocos de código.

Linhas que começam com "#" dentro de um bloco ``` são comentários de código, não títulos.
Tratar isso corretamente evita seções fantasmas em documentação técnica.
"""

from __future__ import annotations

import re
from collections.abc import Iterator
from dataclasses import dataclass

HEADING_RE = re.compile(r"^(#{1,6})\s+(.+?)\s*#*\s*$")
FENCE_RE = re.compile(r"^\s*(```|~~~)")


@dataclass(frozen=True)
class Heading:
    offset: int  # posição do início da linha do título no texto
    level: int
    title: str
    path: tuple[str, ...]  # títulos ancestrais + este


@dataclass(frozen=True)
class Section:
    path: tuple[str, ...]
    body: str  # conteúdo sem a linha do título

    @property
    def path_str(self) -> str:
        return " > ".join(self.path)


def iter_lines(text: str) -> Iterator[tuple[int, str, bool]]:
    """Itera (offset, linha, dentro_de_bloco_de_codigo)."""
    offset = 0
    in_fence = False
    for line in text.splitlines(keepends=True):
        is_fence = bool(FENCE_RE.match(line))
        yield offset, line, in_fence or is_fence
        if is_fence:
            in_fence = not in_fence
        offset += len(line)


def find_headings(text: str) -> list[Heading]:
    headings: list[Heading] = []
    stack: list[tuple[int, str]] = []
    for offset, line, in_code in iter_lines(text):
        if in_code:
            continue
        match = HEADING_RE.match(line.rstrip("\r\n"))
        if not match:
            continue
        level, title = len(match.group(1)), match.group(2).strip()
        while stack and stack[-1][0] >= level:
            stack.pop()
        stack.append((level, title))
        headings.append(Heading(offset, level, title, tuple(t for _, t in stack)))
    return headings


def split_sections(text: str) -> list[Section]:
    """Divide o texto em seções delimitadas por títulos, preservando o caminho de títulos."""
    headings = find_headings(text)
    sections: list[Section] = []

    preamble_end = headings[0].offset if headings else len(text)
    preamble = text[:preamble_end].strip()
    if preamble:
        sections.append(Section(path=(), body=preamble))

    for i, heading in enumerate(headings):
        line_end = text.find("\n", heading.offset)
        body_start = len(text) if line_end == -1 else line_end + 1
        body_end = headings[i + 1].offset if i + 1 < len(headings) else len(text)
        body = text[body_start:body_end].strip()
        if body:
            sections.append(Section(path=heading.path, body=body))
    return sections


def split_blocks(text: str) -> list[str]:
    """Divide em parágrafos (linhas em branco), mantendo cada bloco de código inteiro."""
    blocks: list[str] = []
    current: list[str] = []
    in_fence = False
    for line in text.splitlines():
        if FENCE_RE.match(line):
            in_fence = not in_fence
            current.append(line)
            if not in_fence:  # fechou o bloco de código
                blocks.append("\n".join(current))
                current = []
            continue
        if not in_fence and not line.strip():
            if current:
                blocks.append("\n".join(current))
                current = []
            continue
        current.append(line)
    if current:
        blocks.append("\n".join(current))
    return [b.strip() for b in blocks if b.strip()]
