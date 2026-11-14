"""Orquestra os modos de recuperação comparados na avaliação.

- vector: só busca vetorial no Qdrant (baseline semântico)
- bm25: só busca lexical
- hybrid: vetorial + BM25 combinados por RRF
- hybrid_rerank: hybrid seguido de reranking com cross-encoder
"""

from __future__ import annotations

import logging
import threading

from core.errors import CollectionNotFoundError, RerankerError
from core.schemas import RetrievedChunk
from ingestion.embeddings import Embedder
from retrieval.bm25 import BM25Index
from retrieval.fusion import reciprocal_rank_fusion
from retrieval.reranker import Reranker
from retrieval.vector_store import QdrantStore

logger = logging.getLogger("rag.retrieval")


class Retriever:
    def __init__(
        self,
        store: QdrantStore,
        embedder: Embedder,
        reranker: Reranker | None = None,
        *,
        candidates_k: int = 20,
        rrf_k: int = 60,
    ) -> None:
        self.store = store
        self.embedder = embedder
        self.reranker = reranker
        self.candidates_k = candidates_k
        self.rrf_k = rrf_k
        self._bm25: dict[str, BM25Index] = {}
        self._lock = threading.Lock()

    def bm25_index(self, strategy: str) -> BM25Index:
        index = self._bm25.get(strategy)
        if index is None:
            with self._lock:
                index = self._bm25.get(strategy)
                if index is None:
                    chunks = self.store.all_chunks(strategy)
                    if not chunks:
                        raise CollectionNotFoundError(
                            f"Coleção '{self.store.collection_name(strategy)}' está vazia."
                        )
                    index = BM25Index(chunks)
                    self._bm25[strategy] = index
                    logger.info("bm25.built", extra={"strategy": strategy, "chunks": len(index)})
        return index

    def invalidate(self, strategy: str | None = None) -> None:
        with self._lock:
            if strategy is None:
                self._bm25.clear()
            else:
                self._bm25.pop(strategy, None)

    def _vector(self, query: str, strategy: str, limit: int) -> list[RetrievedChunk]:
        return self.store.search(strategy, self.embedder.embed_query(query), limit)

    def _lexical(self, query: str, strategy: str, limit: int) -> list[RetrievedChunk]:
        return self.bm25_index(strategy).search(query, limit)

    def retrieve(
        self, query: str, strategy: str, mode: str, top_k: int
    ) -> tuple[list[RetrievedChunk], str]:
        """Retorna (trechos, modo efetivamente usado)."""
        if mode == "vector":
            return self._vector(query, strategy, top_k), mode
        if mode == "bm25":
            return self._lexical(query, strategy, top_k), mode
        if mode not in ("hybrid", "hybrid_rerank"):
            raise ValueError(f"Modo de recuperação desconhecido: {mode!r}")

        candidates = max(self.candidates_k, top_k)
        fused = reciprocal_rank_fusion(
            [self._vector(query, strategy, candidates), self._lexical(query, strategy, candidates)],
            k=self.rrf_k,
            limit=candidates,
        )
        if mode == "hybrid":
            return fused[:top_k], mode

        if self.reranker is None:
            logger.warning("reranker.missing_fallback_hybrid")
            return fused[:top_k], "hybrid"
        try:
            return self.reranker.rerank(query, fused)[:top_k], mode
        except RerankerError as exc:
            # Degrada com elegância: responde com a busca híbrida e registra o motivo.
            logger.warning("reranker.failed_fallback_hybrid", extra={"error": str(exc)})
            return fused[:top_k], "hybrid"
