"""Reranking local com FlashRank (cross-encoder em ONNX, roda em CPU sem PyTorch).

O modelo padrão, ms-marco-MultiBERT-L-12, é multilíngue, adequado a perguntas em
português. Ele é baixado do Hugging Face no primeiro uso e fica em RERANKER_CACHE_DIR.
"""

from __future__ import annotations

import logging
import threading
import time
from types import SimpleNamespace
from typing import Any, Protocol

from core.errors import RerankerError
from core.schemas import RetrievedChunk

logger = logging.getLogger("rag.retrieval.reranker")


class Reranker(Protocol):
    def rerank(self, query: str, candidates: list[RetrievedChunk]) -> list[RetrievedChunk]: ...


class FlashRankReranker:
    # Depois de uma falha de carga (ex.: download interrompido), espera antes de tentar de
    # novo: sem isso, cada pergunta repetiria um download de ~100 MB antes de responder.
    retry_after_s: float = 300.0

    def __init__(self, model_name: str, cache_dir: str, ranker: Any | None = None) -> None:
        self.model_name = model_name
        self.cache_dir = cache_dir
        self._ranker = ranker
        self._lock = threading.Lock()
        self._failed_at: float | None = None
        self._last_error = ""

    def _get_ranker(self) -> Any:
        if self._ranker is None:
            with self._lock:
                if self._ranker is None:
                    if (
                        self._failed_at is not None
                        and time.monotonic() - self._failed_at < self.retry_after_s
                    ):
                        raise RerankerError(f"Reranker indisponível: {self._last_error}")
                    try:
                        from flashrank import Ranker

                        logger.info("reranker.loading", extra={"model": self.model_name})
                        self._ranker = Ranker(model_name=self.model_name, cache_dir=self.cache_dir)
                        self._failed_at = None
                    except Exception as exc:  # download ou ONNX podem falhar de várias formas
                        self._failed_at = time.monotonic()
                        self._last_error = str(exc)[:300]
                        raise RerankerError(f"Falha ao carregar o reranker: {exc}") from exc
        return self._ranker

    @staticmethod
    def _request(query: str, passages: list[dict]) -> Any:
        try:
            from flashrank import RerankRequest

            return RerankRequest(query=query, passages=passages)
        except ImportError:
            return SimpleNamespace(query=query, passages=passages)

    def rerank(self, query: str, candidates: list[RetrievedChunk]) -> list[RetrievedChunk]:
        if not candidates:
            return []
        ranker = self._get_ranker()
        passages = [{"id": i, "text": c.chunk.embedding_text()} for i, c in enumerate(candidates)]
        try:
            results = ranker.rerank(self._request(query, passages))
        except Exception as exc:
            raise RerankerError(f"Falha ao executar o reranker: {exc}") from exc
        reranked: list[RetrievedChunk] = []
        for result in results:
            item = candidates[int(result["id"])]
            item.rerank_score = float(result["score"])
            item.score = item.rerank_score
            item.stages.append("rerank")
            reranked.append(item)
        reranked.sort(key=lambda r: -r.score)
        return reranked
