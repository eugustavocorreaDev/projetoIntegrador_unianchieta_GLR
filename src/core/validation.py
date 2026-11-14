"""Inspeção da base de conhecimento e validação interativa com o conjunto de teste.

Alimenta as abas "Documentos" e "Validação" da interface. O critério de acerto é o mesmo de
eval/run_eval.py: o trecho literal esperado aparece entre os k primeiros trechos recuperados.
Os chunks mostrados são recalculados a partir dos arquivos, com a mesma configuração da
ingestão; enquanto a impressão digital do índice estiver em dia, são os mesmos do Qdrant.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING

from core.config import CHUNK_STRATEGIES
from core.errors import InvalidInputError, NotFoundError
from core.text import first_relevant_rank
from ingestion.chunking import Chunker, get_chunker
from ingestion.loader import load_documents
from ingestion.markdown import split_sections

if TYPE_CHECKING:
    from core.pipeline import RAGPipeline

QUESTION_FIELDS = (
    "id",
    "question",
    "answerable",
    "expected_answer",
    "expected_source",
    "expected_section",
    "expected_snippets",
    "note",
)


def _chunkers(chunk_size: int, chunk_overlap: int) -> dict[str, Chunker]:
    return {s: get_chunker(s, chunk_size, chunk_overlap) for s in CHUNK_STRATEGIES}


def document_summaries(docs_dir: Path, chunk_size: int, chunk_overlap: int) -> list[dict]:
    """Um resumo por arquivo: título, tamanho, seções e chunks por estratégia."""
    chunkers = _chunkers(chunk_size, chunk_overlap)
    return [
        {
            "source": doc.source,
            "title": doc.title,
            "chars": len(doc.text),
            "sections": len(split_sections(doc.text)),
            "chunks": {name: len(chunker.split(doc)) for name, chunker in chunkers.items()},
        }
        for doc in load_documents(docs_dir)
    ]


def document_detail(
    docs_dir: Path, source: str, strategy: str, chunk_size: int, chunk_overlap: int
) -> dict:
    """Texto, seções e chunks de um arquivo. Só aceita arquivos que a ingestão carregaria."""
    if strategy not in CHUNK_STRATEGIES:
        raise InvalidInputError(f"Estratégia inválida: {strategy}")
    documents = {doc.source: doc for doc in load_documents(docs_dir)}
    doc = documents.get(source)
    if doc is None:
        raise NotFoundError(f"Documento '{source}' não está na base indexada ({docs_dir}).")
    chunks = _chunkers(chunk_size, chunk_overlap)[strategy].split(doc)
    return {
        "source": doc.source,
        "title": doc.title,
        "path": (Path(docs_dir) / doc.source).as_posix(),
        "text": doc.text,
        "sections": [s.path_str or "(introdução)" for s in split_sections(doc.text)],
        "strategy": strategy,
        "chunks": [
            {"index": c.chunk_index, "section": c.section, "text": c.text, "chars": len(c.text)}
            for c in chunks
        ],
    }


def load_validation_questions(path: Path) -> list[dict]:
    """Perguntas do conjunto de teste, só com os campos que a interface usa."""
    path = Path(path)
    if not path.is_file():
        raise NotFoundError(f"Conjunto de teste não encontrado: {path}")
    data = json.loads(path.read_text(encoding="utf-8"))
    questions = data["questions"] if isinstance(data, dict) else data
    return [{k: q[k] for k in QUESTION_FIELDS if k in q} for q in questions]


def check_retrieval(
    pipeline: RAGPipeline,
    questions: list[dict],
    ids: list[str],
    strategy: str | None,
    mode: str | None,
    top_k: int | None,
) -> list[dict]:
    """Para cada pergunta com resposta: em que posição o trecho esperado foi recuperado."""
    by_id = {q["id"]: q for q in questions}
    unknown = [i for i in ids if i not in by_id]
    if unknown:
        raise InvalidInputError(f"Perguntas inexistentes no conjunto de teste: {unknown}")
    rows = []
    for qid in ids:
        q = by_id[qid]
        if not q.get("answerable"):
            raise InvalidInputError(
                f"A pergunta {qid} não tem resposta na base; valide-a pela recusa (/ask)."
            )
        chunks, used_strategy, effective, latency = pipeline.search(
            q["question"], strategy, mode, top_k
        )
        rank = first_relevant_rank([c.chunk.text for c in chunks], q["expected_snippets"])
        rows.append(
            {
                "id": qid,
                "question": q["question"],
                "expected_source": q.get("expected_source", ""),
                "rank": rank,
                "hit": rank is not None,
                "retrieved_sources": [c.chunk.source for c in chunks],
                "strategy": used_strategy,
                "mode_effective": effective,
                "latency_ms": latency,
            }
        )
    return rows
