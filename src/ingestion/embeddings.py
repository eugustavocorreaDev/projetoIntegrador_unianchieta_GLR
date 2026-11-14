"""Embeddings: cliente do Ollama (endpoint /api/embed) e embeddings por hashing."""

from __future__ import annotations

import hashlib
import logging
import math
from typing import Protocol

import httpx

from core.errors import EmbeddingError
from core.text import tokenize

logger = logging.getLogger("rag.ingestion.embeddings")


class Embedder(Protocol):
    def embed_documents(self, texts: list[str]) -> list[list[float]]: ...

    def embed_query(self, text: str) -> list[float]: ...


class HashEmbedder:
    """Embeddings lexicais determinísticos: cada token vira uma dimensão via MD5.

    Não captura semântica (sinônimos, paráfrases). Serve para a CI e para o modo de
    desenvolvimento sem Ollama (EMBED_MODE=hash); nunca para a avaliação oficial.
    """

    def __init__(self, dim: int = 512) -> None:
        self.dim = dim
        self.calls = 0

    def _vector(self, text: str) -> list[float]:
        vec = [0.0] * self.dim
        for token in tokenize(text):
            index = int(hashlib.md5(token.encode()).hexdigest(), 16) % self.dim
            vec[index] += 1.0
        norm = math.sqrt(sum(v * v for v in vec)) or 1.0
        return [v / norm for v in vec]

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        self.calls += 1
        return [self._vector(t) for t in texts]

    def embed_query(self, text: str) -> list[float]:
        self.calls += 1
        return self._vector(text)

    def ping(self) -> bool:
        return True


class OllamaEmbedder:
    def __init__(
        self,
        base_url: str,
        model: str,
        *,
        query_prefix: str = "",
        document_prefix: str = "",
        batch_size: int = 32,
        timeout_s: float = 120.0,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        self.model = model
        self.query_prefix = query_prefix
        self.document_prefix = document_prefix
        self.batch_size = max(1, batch_size)
        self._client = httpx.Client(
            base_url=base_url.rstrip("/"), timeout=timeout_s, transport=transport
        )

    def _embed(self, inputs: list[str]) -> list[list[float]]:
        try:
            response = self._client.post("/api/embed", json={"model": self.model, "input": inputs})
        except httpx.HTTPError as exc:
            raise EmbeddingError(f"Ollama indisponível para embeddings: {exc}") from exc
        if response.status_code == 404:
            raise EmbeddingError(
                f"Modelo de embeddings '{self.model}' não encontrado. "
                f"Rode: ollama pull {self.model}"
            )
        if response.status_code >= 400:
            raise EmbeddingError(f"Erro do Ollama ({response.status_code}): {response.text[:300]}")
        embeddings = response.json().get("embeddings")
        if not embeddings or len(embeddings) != len(inputs):
            raise EmbeddingError("Resposta de embeddings vazia ou com tamanho inesperado")
        return embeddings

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        vectors: list[list[float]] = []
        for i in range(0, len(texts), self.batch_size):
            batch = [self.document_prefix + t for t in texts[i : i + self.batch_size]]
            vectors.extend(self._embed(batch))
        return vectors

    def embed_query(self, text: str) -> list[float]:
        return self._embed([self.query_prefix + text])[0]

    def ping(self) -> bool:
        try:
            return self._client.get("/api/tags", timeout=5).status_code == 200
        except httpx.HTTPError:
            return False
