"""Configuração central lida de variáveis de ambiente (ver .env.example)."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict

ChunkStrategy = Literal["fixed", "recursive"]
RetrievalMode = Literal["vector", "bm25", "hybrid", "hybrid_rerank"]
LLMMode = Literal["ollama", "mock"]
EmbedMode = Literal["ollama", "hash"]
QdrantMode = Literal["server", "local"]

CHUNK_STRATEGIES: tuple[str, ...] = ("fixed", "recursive")
RETRIEVAL_MODES: tuple[str, ...] = ("vector", "bm25", "hybrid", "hybrid_rerank")


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # Modos de execução. O padrão oficial (Docker e avaliação) é ollama + ollama + server.
    # mock/hash/local existem só para desenvolvimento numa máquina sem Ollama nem Docker
    # (ver scripts/run_local.ps1): o "mock" NÃO é um LLM, é um respondedor extrativo.
    llm_mode: LLMMode = "ollama"
    embed_mode: EmbedMode = "ollama"
    qdrant_mode: QdrantMode = "server"
    qdrant_path: Path = Path(".qdrant_local")

    # Ollama
    ollama_base_url: str = "http://localhost:11434"
    embed_model: str = "nomic-embed-text"
    embed_query_prefix: str = "search_query: "
    embed_document_prefix: str = "search_document: "
    embed_batch_size: int = 32
    llm_model: str = "qwen2.5:3b"
    llm_temperature: float = 0.0
    llm_num_ctx: int = 4096
    llm_max_tokens: int = 512
    llm_seed: int = 42
    request_timeout_s: float = 180.0

    # Qdrant
    qdrant_url: str = "http://localhost:6333"
    qdrant_collection_prefix: str = "techdocs"

    # Ingestão
    docs_dir: Path = Path("data/raw_docs")
    chunk_strategy: ChunkStrategy = "recursive"
    chunk_size: int = 800
    chunk_overlap: int = 120

    # Recuperação
    retrieval_mode: RetrievalMode = "hybrid_rerank"
    top_k: int = 5
    candidates_k: int = 20
    rrf_k: int = 60
    reranker_model: str = "ms-marco-MultiBERT-L-12"
    reranker_cache_dir: str = ".cache/flashrank"
    min_vector_score: float = 0.0

    # Verificação das respostas (generation/grounding.py)
    min_citation_coverage: float = 0.5  # fração mínima de afirmações com citação
    min_support_ratio: float = 0.3  # fração mínima dos termos de cada afirmação no trecho citado

    # API
    # O POST /ingest recria as coleções; desative em qualquer ambiente compartilhado.
    enable_ingest_endpoint: bool = True

    # Logs
    log_level: str = "INFO"
    log_dir: Path | None = Path("logs")

    def public_dict(self) -> dict:
        """Configuração exposta pela API e gravada nos resultados de avaliação."""
        data = self.model_dump(mode="json")
        data.pop("log_dir", None)
        return data


@lru_cache
def get_settings() -> Settings:
    return Settings()
