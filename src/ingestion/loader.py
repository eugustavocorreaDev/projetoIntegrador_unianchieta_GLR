"""Carrega e limpa arquivos Markdown de um diretório de documentação."""

from __future__ import annotations

import logging
import re
from pathlib import Path

from core.schemas import Document
from ingestion.markdown import FENCE_RE, find_headings

logger = logging.getLogger("rag.ingestion.loader")

SUPPORTED_EXTENSIONS = {".md", ".mdx", ".markdown", ".txt"}
_FRONT_MATTER_RE = re.compile(r"\A---\s*\n(.*?)\n---\s*\n", re.DOTALL)
_HTML_COMMENT_RE = re.compile(r"<!--.*?-->", re.DOTALL)
# Só tags HTML conhecidas: textos como "Bearer <token>" precisam sobreviver à limpeza
_HTML_TAG_RE = re.compile(
    r"</?(?:a|abbr|b|br|center|code|details|div|em|font|i|img|kbd|p|small|span|strong|sub"
    r"|summary|sup|table|tbody|td|th|thead|tr|u)\b[^>\n]*>",
    re.IGNORECASE,
)
_INLINE_CODE_RE = re.compile(r"(`[^`]*`)")
# Diretivas de inclusão usadas na documentação do FastAPI, ex.: {* ../../docs_src/x.py *}
_INCLUDE_RE = re.compile(r"^\s*\{[*!].*[*!]\}\s*$")
# Admonições no formato "/// tip | Dica"
_ADMONITION_RE = re.compile(r"^\s*///\s*(\w+)?\s*(?:\|\s*(.+))?$")


def _parse_front_matter(text: str) -> tuple[dict[str, str], str]:
    match = _FRONT_MATTER_RE.match(text)
    if not match:
        return {}, text
    meta: dict[str, str] = {}
    for line in match.group(1).splitlines():
        if ":" in line:
            key, value = line.split(":", 1)
            meta[key.strip().lower()] = value.strip().strip("'\"")
    return meta, text[match.end() :]


def clean_markdown(text: str) -> str:
    """Remove ruído (comentários, tags HTML, diretivas) sem mexer nos blocos de código."""
    text = text.replace("\r\n", "\n").replace("﻿", "")
    text = _HTML_COMMENT_RE.sub("", text)
    out: list[str] = []
    in_fence = False
    for line in text.split("\n"):
        if FENCE_RE.match(line):
            in_fence = not in_fence
            out.append(line)
            continue
        if in_fence:
            out.append(line)
            continue
        if _INCLUDE_RE.match(line):
            continue
        admonition = _ADMONITION_RE.match(line)
        if admonition:
            label = admonition.group(2) or admonition.group(1)
            if label:
                out.append(f"{label.strip()}:")
            continue
        parts = _INLINE_CODE_RE.split(line)
        # Partes ímpares são código inline e ficam intactas
        line = "".join(p if i % 2 else _HTML_TAG_RE.sub("", p) for i, p in enumerate(parts))
        out.append(line.rstrip())
    cleaned = "\n".join(out)
    return re.sub(r"\n{3,}", "\n\n", cleaned).strip() + "\n"


def load_document(path: Path, root: Path) -> Document:
    raw = path.read_text(encoding="utf-8")
    meta, body = _parse_front_matter(raw)
    text = clean_markdown(body)
    title = meta.get("title")
    if not title:
        h1 = next((h for h in find_headings(text) if h.level == 1), None)
        title = h1.title if h1 else path.stem.replace("-", " ").replace("_", " ").title()
    return Document(source=path.relative_to(root).as_posix(), title=title, text=text)


def load_documents(docs_dir: Path) -> list[Document]:
    docs_dir = Path(docs_dir)
    if not docs_dir.is_dir():
        raise FileNotFoundError(f"Diretório de documentos não encontrado: {docs_dir}")
    documents: list[Document] = []
    for path in sorted(docs_dir.rglob("*")):
        if not path.is_file() or path.suffix.lower() not in SUPPORTED_EXTENSIONS:
            continue
        document = load_document(path, docs_dir)
        if document.text.strip():
            documents.append(document)
    logger.info("documents.loaded", extra={"docs_dir": str(docs_dir), "count": len(documents)})
    return documents
