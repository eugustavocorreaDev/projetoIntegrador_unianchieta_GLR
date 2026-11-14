"""Acesso ao Qdrant: uma coleção por estratégia de chunking (ex.: techdocs_recursive)."""

from __future__ import annotations

import logging
import threading
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Any

from qdrant_client import QdrantClient
from qdrant_client.models import Distance, PointStruct, VectorParams

from core.errors import CollectionNotFoundError, ServiceUnavailableError
from core.schemas import Chunk, RetrievedChunk

logger = logging.getLogger("rag.retrieval.vector_store")


class SerializedClient:
    """Envolve um QdrantClient e executa uma chamada por vez.

    O modo local em disco (QdrantClient(path=...)) não foi feito para acesso concorrente,
    e o FastAPI atende rotas síncronas num pool de threads.
    """

    def __init__(self, client: QdrantClient) -> None:
        self._client = client
        self._lock = threading.RLock()

    def __getattr__(self, name: str) -> Any:
        attr = getattr(self._client, name)
        if not callable(attr):
            return attr

        def locked(*args: Any, **kwargs: Any) -> Any:
            with self._lock:
                return attr(*args, **kwargs)

        return locked


class QdrantStore:
    def __init__(self, client: QdrantClient, prefix: str = "techdocs") -> None:
        self.client = client
        self.prefix = prefix

    @classmethod
    def from_url(cls, url: str, prefix: str, timeout: int = 30) -> QdrantStore:
        return cls(QdrantClient(url=url, timeout=timeout), prefix)

    @classmethod
    def from_path(cls, path: Path, prefix: str) -> QdrantStore:
        """Qdrant embutido, gravado em disco, sem servidor (QDRANT_MODE=local).

        Só um processo por vez pode abrir a pasta: pare a API antes de rodar a ingestão
        ou a avaliação pela linha de comando.
        """
        Path(path).mkdir(parents=True, exist_ok=True)
        return cls(SerializedClient(QdrantClient(path=str(path))), prefix)

    def collection_name(self, strategy: str) -> str:
        return f"{self.prefix}_{strategy}"

    @contextmanager
    def _guard(self, strategy: str) -> Iterator[None]:
        try:
            yield
        except CollectionNotFoundError:
            raise
        except Exception as exc:
            if self.ping() and not self.exists(strategy):
                raise CollectionNotFoundError(
                    f"Coleção '{self.collection_name(strategy)}' não indexada. "
                    f"Rode: python -m ingestion.cli --strategy {strategy}"
                ) from exc
            raise ServiceUnavailableError(f"Erro ao acessar o Qdrant: {exc}") from exc

    def ping(self) -> bool:
        try:
            self.client.get_collections()
            return True
        except Exception:
            return False

    def exists(self, strategy: str) -> bool:
        try:
            return self.client.collection_exists(self.collection_name(strategy))
        except Exception as exc:
            raise ServiceUnavailableError(f"Erro ao acessar o Qdrant: {exc}") from exc

    def count(self, strategy: str) -> int:
        if not self.exists(strategy):
            return 0
        with self._guard(strategy):
            return self.client.count(self.collection_name(strategy), exact=True).count

    def recreate(self, strategy: str, dim: int) -> None:
        name = self.collection_name(strategy)
        with self._guard(strategy):
            if self.client.collection_exists(name):
                self.client.delete_collection(name)
            self.client.create_collection(
                name, vectors_config=VectorParams(size=dim, distance=Distance.COSINE)
            )
        logger.info("collection.recreated", extra={"collection": name, "dim": dim})

    def upsert(
        self,
        strategy: str,
        chunks: list[Chunk],
        vectors: list[list[float]],
        batch_size: int = 128,
        extra_payload: dict | None = None,
    ) -> None:
        name = self.collection_name(strategy)
        extra = extra_payload or {}
        with self._guard(strategy):
            for i in range(0, len(chunks), batch_size):
                points = [
                    PointStruct(id=chunk.id, vector=vector, payload={**chunk.to_payload(), **extra})
                    for chunk, vector in zip(
                        chunks[i : i + batch_size], vectors[i : i + batch_size], strict=True
                    )
                ]
                self.client.upsert(name, points=points, wait=True)

    def search(self, strategy: str, vector: list[float], limit: int) -> list[RetrievedChunk]:
        with self._guard(strategy):
            response = self.client.query_points(
                self.collection_name(strategy), query=vector, limit=limit, with_payload=True
            )
        return [
            RetrievedChunk(
                chunk=Chunk.from_payload(point.id, point.payload or {}),
                score=float(point.score),
                vector_score=float(point.score),
                stages=["vector"],
            )
            for point in response.points
        ]

    def stored_fingerprint(self, strategy: str) -> str | None:
        """Impressão digital do corpus gravada na última indexação (None se não houver)."""
        if not self.exists(strategy):
            return None
        with self._guard(strategy):
            points, _ = self.client.scroll(
                self.collection_name(strategy), limit=1, with_payload=True, with_vectors=False
            )
        return (points[0].payload or {}).get("corpus_fingerprint") if points else None

    def all_chunks(self, strategy: str) -> list[Chunk]:
        chunks: list[Chunk] = []
        offset = None
        with self._guard(strategy):
            while True:
                points, offset = self.client.scroll(
                    self.collection_name(strategy),
                    limit=256,
                    offset=offset,
                    with_payload=True,
                    with_vectors=False,
                )
                chunks.extend(Chunk.from_payload(p.id, p.payload or {}) for p in points)
                if offset is None:
                    break
        chunks.sort(key=lambda c: (c.source, c.chunk_index))
        return chunks
