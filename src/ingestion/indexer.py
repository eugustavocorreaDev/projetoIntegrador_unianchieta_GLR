"""Gera chunks, calcula embeddings e grava tudo no Qdrant."""

from __future__ import annotations

import hashlib
import logging
import time

from core.errors import RAGError
from core.schemas import Chunk, Document
from ingestion.chunking import get_chunker
from ingestion.embeddings import Embedder
from retrieval.vector_store import QdrantStore

logger = logging.getLogger("rag.ingestion.indexer")


class Indexer:
    def __init__(
        self,
        store: QdrantStore,
        embedder: Embedder,
        chunk_size: int = 800,
        chunk_overlap: int = 120,
        embedder_id: str = "",
    ) -> None:
        self.store = store
        self.embedder = embedder
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.embedder_id = embedder_id

    def build_chunks(self, strategy: str, documents: list[Document]) -> list[Chunk]:
        chunker = get_chunker(strategy, self.chunk_size, self.chunk_overlap)
        return [chunk for document in documents for chunk in chunker.split(document)]

    def fingerprint(self, strategy: str, documents: list[Document]) -> str:
        """Muda quando o corpus, a estratégia, o chunking ou o modelo de embeddings mudam.

        Gravada em cada ponto, permite que `--skip-existing` reindexe sozinho uma base
        alterada em vez de continuar respondendo com o índice antigo.
        """
        digest = hashlib.sha256()
        config = f"{strategy}|{self.chunk_size}|{self.chunk_overlap}|{self.embedder_id}"
        digest.update(config.encode())
        for document in sorted(documents, key=lambda d: d.source):
            digest.update(document.source.encode())
            digest.update(document.text.encode())
        return digest.hexdigest()[:16]

    def is_current(self, strategy: str, documents: list[Document]) -> bool:
        return self.store.stored_fingerprint(strategy) == self.fingerprint(strategy, documents)

    def index(self, strategy: str, documents: list[Document]) -> dict:
        started = time.perf_counter()
        chunks = self.build_chunks(strategy, documents)
        if not chunks:
            raise RAGError("Nenhum chunk gerado: verifique o diretório de documentos.")
        fingerprint = self.fingerprint(strategy, documents)
        # Calcula todos os embeddings antes de recriar a coleção, para não deixar
        # o índice vazio se o Ollama falhar no meio do caminho.
        vectors = self.embedder.embed_documents([c.embedding_text() for c in chunks])
        self.store.recreate(strategy, dim=len(vectors[0]))
        self.store.upsert(
            strategy, chunks, vectors, extra_payload={"corpus_fingerprint": fingerprint}
        )
        lengths = [len(c.text) for c in chunks]
        stats = {
            "strategy": strategy,
            "collection": self.store.collection_name(strategy),
            "documents": len(documents),
            "chunks": len(chunks),
            "avg_chunk_chars": round(sum(lengths) / len(lengths), 1),
            "max_chunk_chars": max(lengths),
            "fingerprint": fingerprint,
            "seconds": round(time.perf_counter() - started, 2),
        }
        logger.info("index.completed", extra=stats)
        return stats
