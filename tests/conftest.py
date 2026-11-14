"""Fixtures e dublês de teste.

A CI não baixa modelos: os embeddings vêm do HashEmbedder (hashing determinístico dos
tokens), o LLM é uma função Python e o Qdrant roda em memória (modo local do
qdrant-client). Assim os testes exercitam o pipeline real de ponta a ponta em segundos.
"""

from __future__ import annotations

import re
from collections.abc import Callable
from pathlib import Path

import pytest
from qdrant_client import QdrantClient

from core.config import Settings
from core.pipeline import RAGPipeline
from core.schemas import RetrievedChunk
from core.text import tokenize
from generation.prompts import REFUSAL_MESSAGE, parse_user_prompt
from ingestion.embeddings import HashEmbedder
from ingestion.indexer import Indexer
from ingestion.loader import load_documents
from retrieval.retriever import Retriever
from retrieval.vector_store import QdrantStore

ROOT = Path(__file__).resolve().parents[1]
DOCS_DIR = ROOT / "data" / "raw_docs"
DATASET = ROOT / "eval" / "datasets" / "perguntas_teste.json"


def quote_first_chunk(system: str, user: str) -> str:
    """Resposta fundamentada mínima: a primeira frase do trecho [1], com a citação."""
    _, blocks = parse_user_prompt(user)
    if not blocks:
        return REFUSAL_MESSAGE
    prose = re.sub(r"```.*?```", " ", blocks[0][2], flags=re.DOTALL).strip()
    first = re.split(r"(?<=[.!?])\s|\n", prose)[0].strip() if prose else ""
    return f"{first or blocks[0][1]} [1]"


class FakeLLM:
    """LLM falso: por padrão cita a primeira frase do trecho [1]; `responder` simula o resto."""

    def __init__(self, responder: Callable[[str, str], str] | None = None) -> None:
        self.responder = responder or quote_first_chunk
        self.calls: list[tuple[str, str]] = []

    def generate(self, system: str, user: str) -> str:
        self.calls.append((system, user))
        return self.responder(system, user)

    def ping(self) -> bool:
        return True


class OverlapReranker:
    """Reranker falso: pontua pela quantidade de termos da pergunta presentes no trecho."""

    def rerank(self, query: str, candidates: list[RetrievedChunk]) -> list[RetrievedChunk]:
        terms = set(tokenize(query))
        for item in candidates:
            item.rerank_score = float(len(terms & set(tokenize(item.chunk.embedding_text()))))
            item.score = item.rerank_score
            item.stages.append("rerank")
        return sorted(candidates, key=lambda r: -r.score)


def make_settings(**overrides) -> Settings:
    base = {
        "docs_dir": DOCS_DIR,
        "chunk_strategy": "recursive",
        "retrieval_mode": "hybrid",
        "top_k": 5,
        "candidates_k": 20,
        "min_vector_score": 0.0,
        "log_dir": None,
    }
    base.update(overrides)
    return Settings(_env_file=None, **base)


def make_pipeline(
    llm: FakeLLM | None = None, reranker=None, ingest: bool = True, **settings_overrides
) -> RAGPipeline:
    settings = make_settings(**settings_overrides)
    store = QdrantStore(QdrantClient(location=":memory:"), prefix="test")
    embedder = HashEmbedder()
    retriever = Retriever(
        store, embedder, reranker, candidates_k=settings.candidates_k, rrf_k=settings.rrf_k
    )
    indexer = Indexer(store, embedder, settings.chunk_size, settings.chunk_overlap)
    pipeline = RAGPipeline(retriever, llm or FakeLLM(), indexer, settings)
    if ingest:
        pipeline.ingest()
    return pipeline


@pytest.fixture(scope="session")
def documents():
    return load_documents(DOCS_DIR)


@pytest.fixture(scope="session")
def indexed_pipeline() -> RAGPipeline:
    """Pipeline indexado uma vez por sessão (somente leitura nos testes que o usam)."""
    return make_pipeline(reranker=OverlapReranker())
