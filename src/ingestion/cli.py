"""Indexa a documentação no Qdrant.

Uso:
    python -m ingestion.cli --strategy all
    python -m ingestion.cli --strategy recursive --docs-dir data/external/fastapi
    python -m ingestion.cli --strategy all --skip-existing   # usado pelo docker compose
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
import time
from pathlib import Path

from core.config import CHUNK_STRATEGIES, get_settings
from core.errors import RAGError, RerankerError
from core.factory import build_embedder, build_reranker, build_store, embedder_identity
from core.logging_setup import setup_logging
from core.schemas import Chunk, RetrievedChunk
from ingestion.indexer import Indexer
from ingestion.loader import load_documents

logger = logging.getLogger("rag.ingestion.cli")

_WARMUP_CHUNK = Chunk(
    id="warmup", text="texto de aquecimento", source="-", section="", chunk_index=0, strategy="-"
)


def wait_for(check, name: str, timeout_s: float) -> None:
    deadline = time.monotonic() + timeout_s
    while not check():
        if time.monotonic() > deadline:
            raise RAGError(f"{name} não respondeu em {timeout_s:.0f}s")
        logger.info("waiting_for_service", extra={"service": name})
        time.sleep(2)


def main(argv: list[str] | None = None) -> int:
    settings = get_settings()
    parser = argparse.ArgumentParser(description="Indexa a documentação técnica no Qdrant.")
    parser.add_argument("--strategy", choices=[*CHUNK_STRATEGIES, "all"], default="all")
    parser.add_argument("--docs-dir", type=Path, default=settings.docs_dir)
    parser.add_argument(
        "--skip-existing",
        action="store_true",
        help="Pula estratégias já indexadas com a mesma base, chunking e modelo de embeddings.",
    )
    parser.add_argument(
        "--wait", type=float, default=120.0, help="Segundos aguardando os serviços."
    )
    parser.add_argument(
        "--warmup-reranker",
        action="store_true",
        help="Baixa o modelo do reranker agora, para a primeira pergunta não esperar o download.",
    )
    args = parser.parse_args(argv)

    setup_logging(settings.log_level, settings.log_dir)
    strategies = list(CHUNK_STRATEGIES) if args.strategy == "all" else [args.strategy]
    try:
        store = build_store(settings)
    except RuntimeError as exc:
        # QDRANT_MODE=local: a pasta só pode ser aberta por um processo (ex.: a API no ar)
        logger.error("index.failed", extra={"error": f"{exc}. Pare a API e rode de novo."})
        return 1
    embedder = build_embedder(settings)
    embedder_name = "Ollama" if settings.embed_mode == "ollama" else "Embeddings"

    try:
        wait_for(store.ping, "Qdrant", args.wait)
        wait_for(embedder.ping, embedder_name, args.wait)
        documents = load_documents(args.docs_dir)
        indexer = Indexer(
            store,
            embedder,
            settings.chunk_size,
            settings.chunk_overlap,
            embedder_id=embedder_identity(settings),
        )
        for strategy in strategies:
            if args.skip_existing and store.count(strategy) > 0:
                if indexer.is_current(strategy, documents):
                    logger.info("index.skipped_existing", extra={"strategy": strategy})
                    continue
                # A base, o chunking ou o modelo mudaram desde a última indexação
                logger.info("index.outdated_reindexing", extra={"strategy": strategy})
            print(json.dumps(indexer.index(strategy, documents), ensure_ascii=False))
    except (RAGError, FileNotFoundError) as exc:
        logger.error("index.failed", extra={"error": str(exc)})
        return 1

    if args.warmup_reranker:
        reranker = build_reranker(settings)
        try:
            reranker.rerank("aquecimento", [RetrievedChunk(_WARMUP_CHUNK, 0.0)])
            logger.info("reranker.ready", extra={"model": settings.reranker_model})
        except RerankerError as exc:
            # Não é fatal: a API cai para a busca híbrida sem reranking
            logger.warning("reranker.warmup_failed", extra={"error": str(exc)})
    return 0


if __name__ == "__main__":
    sys.exit(main())
