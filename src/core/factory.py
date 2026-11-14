"""Constrói os componentes de acordo com os modos configurados (ver core/config.py).

Único lugar que decide entre Ollama ou mock, Qdrant servidor ou em disco. A API, a CLI de
ingestão e a avaliação usam estas funções, então os três sempre enxergam o mesmo índice.
"""

from __future__ import annotations

from core.config import Settings
from generation.llm import LLM, OllamaLLM
from generation.mock_llm import ExtractiveMockLLM
from ingestion.embeddings import Embedder, HashEmbedder, OllamaEmbedder
from retrieval.reranker import FlashRankReranker
from retrieval.vector_store import QdrantStore


def collection_prefix(settings: Settings) -> str:
    # Embeddings por hashing têm outra dimensão: coleções separadas evitam misturar índices
    suffix = "_hash" if settings.embed_mode == "hash" else ""
    return settings.qdrant_collection_prefix + suffix


def build_store(settings: Settings) -> QdrantStore:
    prefix = collection_prefix(settings)
    if settings.qdrant_mode == "local":
        return QdrantStore.from_path(settings.qdrant_path, prefix)
    return QdrantStore.from_url(settings.qdrant_url, prefix)


def embedder_identity(settings: Settings) -> str:
    """Identifica o espaço vetorial; entra na impressão digital do índice."""
    return "hash" if settings.embed_mode == "hash" else f"ollama:{settings.embed_model}"


def build_embedder(settings: Settings) -> Embedder:
    if settings.embed_mode == "hash":
        return HashEmbedder()
    return OllamaEmbedder(
        settings.ollama_base_url,
        settings.embed_model,
        query_prefix=settings.embed_query_prefix,
        document_prefix=settings.embed_document_prefix,
        batch_size=settings.embed_batch_size,
        timeout_s=settings.request_timeout_s,
    )


def build_llm(settings: Settings) -> LLM:
    if settings.llm_mode == "mock":
        return ExtractiveMockLLM()
    return OllamaLLM(
        settings.ollama_base_url,
        settings.llm_model,
        temperature=settings.llm_temperature,
        num_ctx=settings.llm_num_ctx,
        max_tokens=settings.llm_max_tokens,
        seed=settings.llm_seed,
        timeout_s=settings.request_timeout_s,
    )


def build_reranker(settings: Settings) -> FlashRankReranker:
    return FlashRankReranker(settings.reranker_model, settings.reranker_cache_dir)
