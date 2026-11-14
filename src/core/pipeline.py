"""Pipeline RAG: recuperar → decidir se há contexto → gerar → verificar citações."""

from __future__ import annotations

import logging
import time
from pathlib import Path

from core.config import CHUNK_STRATEGIES, RETRIEVAL_MODES, Settings
from core.errors import InvalidInputError, ServiceUnavailableError
from core.factory import (
    build_embedder,
    build_image_reader,
    build_llm,
    build_reranker,
    build_store,
    embedder_identity,
)
from core.logging_setup import truncate
from core.schemas import AskResult, RetrievedChunk
from generation.grounding import ground_answer
from generation.llm import LLM
from generation.prompts import REFUSAL_MESSAGE, SYSTEM_PROMPT, build_user_prompt
from generation.vision import ImageReader, decode_image
from ingestion.indexer import Indexer
from ingestion.loader import load_documents
from retrieval.retriever import Retriever

logger = logging.getLogger("rag.pipeline")


def _ms(start: float) -> float:
    return round((time.perf_counter() - start) * 1000, 1)


def _summarize(chunks: list[RetrievedChunk]) -> list[dict]:
    return [
        {
            "source": c.chunk.source,
            "section": c.chunk.section,
            "score": round(c.score, 4),
            "vector_score": None if c.vector_score is None else round(c.vector_score, 4),
        }
        for c in chunks
    ]


def relevance_signal(chunks: list[RetrievedChunk]) -> float | None:
    """Maior similaridade de cosseno entre os trechos que serão enviados ao LLM.

    É a estatística comparada com MIN_VECTOR_SCORE e também a que eval/run_eval.py usa
    para calibrar o limite, para que calibração e produção meçam a mesma coisa. Fica
    None quando nenhum trecho veio da busca vetorial (ex.: modo bm25).
    """
    scores = [c.vector_score for c in chunks if c.vector_score is not None]
    return max(scores) if scores else None


def compose_query(question: str, image_text: str | None) -> str:
    """Junta a pergunta digitada e o texto lido do print; o resultado vai para a busca e o LLM."""
    question = question.strip()
    if not image_text:
        return question
    lead = question or "O que a documentação diz sobre o conteúdo desta imagem?"
    return f"{lead}\n\nTexto lido da imagem enviada:\n{image_text.strip()}"


class RAGPipeline:
    def __init__(
        self,
        retriever: Retriever,
        llm: LLM,
        indexer: Indexer,
        settings: Settings,
        image_reader: ImageReader | None = None,
    ) -> None:
        self.retriever = retriever
        self.llm = llm
        self.indexer = indexer
        self.settings = settings
        self.image_reader = image_reader

    def read_image(self, image_b64: str) -> str:
        """Valida o print e devolve o texto que o modelo de visão leu nele."""
        max_bytes = int(self.settings.max_image_mb * 1024 * 1024)
        clean_b64, _ = decode_image(image_b64, max_bytes)
        if self.image_reader is None:
            raise ServiceUnavailableError(
                "A leitura de imagens precisa do Ollama com o modelo de visão "
                f"({self.settings.vision_model}). Ela fica desativada no Modo de Visualização."
            )
        text = self.image_reader.read(clean_b64)
        if not text:
            raise InvalidInputError("O modelo de visão não conseguiu ler nada na imagem.")
        return text

    def _resolve(self, strategy: str | None, mode: str | None, top_k: int | None):
        strategy = strategy or self.settings.chunk_strategy
        mode = mode or self.settings.retrieval_mode
        top_k = top_k or self.settings.top_k
        if strategy not in CHUNK_STRATEGIES:
            raise ValueError(f"Estratégia inválida: {strategy}")
        if mode not in RETRIEVAL_MODES:
            raise ValueError(f"Modo de recuperação inválido: {mode}")
        return strategy, mode, top_k

    def search(
        self,
        question: str,
        strategy: str | None = None,
        mode: str | None = None,
        top_k: int | None = None,
    ) -> tuple[list[RetrievedChunk], str, str, float]:
        strategy, mode, top_k = self._resolve(strategy, mode, top_k)
        start = time.perf_counter()
        chunks, effective = self.retriever.retrieve(question, strategy, mode, top_k)
        return chunks, strategy, effective, _ms(start)

    def _gate(self, chunks: list[RetrievedChunk]) -> str | None:
        """Decide, antes de chamar o LLM, se há contexto suficiente."""
        if not chunks:
            return "no_context"
        threshold = self.settings.min_vector_score
        signal = relevance_signal(chunks)
        if threshold > 0 and signal is not None and signal < threshold:
            return "low_relevance"
        return None

    def ask(
        self,
        question: str,
        strategy: str | None = None,
        mode: str | None = None,
        top_k: int | None = None,
        image_b64: str | None = None,
    ) -> AskResult:
        question = question.strip()
        strategy, mode, top_k = self._resolve(strategy, mode, top_k)
        timings: dict[str, float] = {}
        start = time.perf_counter()

        image_text: str | None = None
        if image_b64:
            t = time.perf_counter()
            image_text = self.read_image(image_b64)
            timings["image"] = _ms(t)
        query = compose_query(question, image_text)

        t = time.perf_counter()
        chunks, effective = self.retriever.retrieve(query, strategy, mode, top_k)
        timings["retrieval"] = _ms(t)

        raw_answer: str | None = None
        grounding_info: dict = {}
        gate_reason = self._gate(chunks)
        if gate_reason:
            answer, refused, reason, citations = REFUSAL_MESSAGE, True, gate_reason, []
        else:
            t = time.perf_counter()
            raw_answer = self.llm.generate(SYSTEM_PROMPT, build_user_prompt(query, chunks))
            timings["generation"] = _ms(t)
            grounded = ground_answer(
                raw_answer,
                chunks,
                min_coverage=self.settings.min_citation_coverage,
                min_support=self.settings.min_support_ratio,
            )
            grounding_info = {
                "coverage": None if grounded.coverage is None else round(grounded.coverage, 3),
                "unsupported": [truncate(s, 160) for s in grounded.unsupported],
            }
            answer, refused = grounded.answer, grounded.refused
            reason, citations = grounded.refusal_reason, grounded.citations
            if grounded.invalid_citation_ids:
                logger.warning(
                    "ask.invalid_citations_removed",
                    extra={"invalid_ids": grounded.invalid_citation_ids, "n_chunks": len(chunks)},
                )

        result = AskResult(
            question=question,
            answer=answer,
            refused=refused,
            refusal_reason=reason,
            citations=citations,
            retrieved=chunks,
            strategy=strategy,
            mode=mode,
            mode_effective=effective,
            latency_ms=_ms(start),
            timings_ms=timings,
            raw_answer=raw_answer,
            image_text=image_text,
        )
        logger.info(
            "ask.completed",
            extra={
                "question": truncate(question),
                "image_text": truncate(image_text) if image_text else None,
                "strategy": strategy,
                "mode": mode,
                "mode_effective": effective,
                "top_k": top_k,
                "retrieved": _summarize(chunks),
                "decision": f"refused:{reason}" if refused else "answered",
                "citations": [c.id for c in citations],
                "grounding": grounding_info,
                "raw_answer": truncate(raw_answer or "", 400),
                "llm_mode": self.settings.llm_mode,
                "embed_mode": self.settings.embed_mode,
                "latency_ms": result.latency_ms,
                "timings_ms": timings,
            },
        )
        return result

    def ingest(
        self, strategies: list[str] | None = None, docs_dir: Path | None = None
    ) -> list[dict]:
        documents = load_documents(docs_dir or self.settings.docs_dir)
        stats = []
        for strategy in strategies or list(CHUNK_STRATEGIES):
            stats.append(self.indexer.index(strategy, documents))
            self.retriever.invalidate(strategy)
        return stats

    def health(self) -> dict:
        store = self.retriever.store
        qdrant_ok = store.ping()
        ping = getattr(self.llm, "ping", None)
        ollama_ok = bool(ping()) if callable(ping) else True
        collections = {}
        if qdrant_ok:
            for strategy in CHUNK_STRATEGIES:
                try:
                    collections[strategy] = store.count(strategy)
                except Exception:
                    collections[strategy] = None
        ready = qdrant_ok and ollama_ok and any(collections.values())
        return {
            "status": "ok" if ready else "degraded",
            "qdrant": qdrant_ok,
            "ollama": ollama_ok,
            "collections": collections,
            "llm_mode": self.settings.llm_mode,
            "embed_mode": self.settings.embed_mode,
            "qdrant_mode": self.settings.qdrant_mode,
        }


def build_pipeline(settings: Settings) -> RAGPipeline:
    store = build_store(settings)
    embedder = build_embedder(settings)
    retriever = Retriever(
        store,
        embedder,
        build_reranker(settings),
        candidates_k=settings.candidates_k,
        rrf_k=settings.rrf_k,
    )
    indexer = Indexer(
        store,
        embedder,
        settings.chunk_size,
        settings.chunk_overlap,
        embedder_id=embedder_identity(settings),
    )
    return RAGPipeline(
        retriever, build_llm(settings), indexer, settings, image_reader=build_image_reader(settings)
    )
