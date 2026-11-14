"""Aplicação FastAPI. Rode com: uvicorn api.main:app --app-dir src --port 8000"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse

from api.dependencies import get_pipeline
from api.schemas import (
    AskResponse,
    HealthResponse,
    IngestRequest,
    IngestResponse,
    QueryRequest,
    RetrievedOut,
    SearchResponse,
)
from core.config import get_settings
from core.errors import CollectionNotFoundError, RAGError, ServiceUnavailableError
from core.logging_setup import setup_logging
from core.pipeline import RAGPipeline

logger = logging.getLogger("rag.api")


@asynccontextmanager
async def lifespan(_: FastAPI):
    settings = get_settings()
    setup_logging(settings.log_level, settings.log_dir)
    logger.info("api.started", extra={"config": settings.public_dict()})
    yield


app = FastAPI(
    title="RAG de documentação técnica",
    version="0.1.0",
    description=(
        "Assistente que responde dúvidas sobre uma documentação técnica, sempre citando a fonte, "
        "e recusa quando a resposta não está nos documentos indexados."
    ),
    lifespan=lifespan,
)


@app.exception_handler(ServiceUnavailableError)
async def _service_unavailable(_: Request, exc: ServiceUnavailableError) -> JSONResponse:
    logger.error("request.service_unavailable", extra={"error": str(exc)})
    return JSONResponse(status_code=503, content={"detail": str(exc)})


@app.exception_handler(CollectionNotFoundError)
async def _collection_missing(_: Request, exc: CollectionNotFoundError) -> JSONResponse:
    logger.error("request.collection_missing", extra={"error": str(exc)})
    return JSONResponse(status_code=409, content={"detail": str(exc)})


@app.exception_handler(RAGError)
async def _rag_error(_: Request, exc: RAGError) -> JSONResponse:
    logger.error("request.failed", extra={"error": str(exc)})
    return JSONResponse(status_code=500, content={"detail": str(exc)})


@app.get("/health", response_model=HealthResponse, tags=["sistema"])
def health(pipeline: RAGPipeline = Depends(get_pipeline)) -> dict:
    """Estado do Qdrant, do Ollama e quantidade de chunks por coleção."""
    return pipeline.health()


@app.get("/config", tags=["sistema"])
def config() -> dict:
    """Configuração em uso (não contém segredos)."""
    return get_settings().public_dict()


@app.post("/ask", response_model=AskResponse, tags=["rag"])
def ask(request: QueryRequest, pipeline: RAGPipeline = Depends(get_pipeline)) -> AskResponse:
    """Responde à pergunta com citações, ou recusa quando a documentação não cobre o assunto."""
    result = pipeline.ask(request.question, request.strategy, request.mode, request.top_k)
    return AskResponse.from_domain(result)


@app.post("/search", response_model=SearchResponse, tags=["rag"])
def search(request: QueryRequest, pipeline: RAGPipeline = Depends(get_pipeline)) -> SearchResponse:
    """Só a etapa de recuperação, sem chamar o LLM (útil para depurar e avaliar)."""
    chunks, strategy, effective, latency = pipeline.search(
        request.question, request.strategy, request.mode, request.top_k
    )
    return SearchResponse(
        retrieved=[RetrievedOut.from_domain(i, c) for i, c in enumerate(chunks, 1)],
        strategy=strategy,
        mode_effective=effective,
        latency_ms=latency,
    )


@app.post("/ingest", response_model=IngestResponse, tags=["administração"])
def ingest(request: IngestRequest, pipeline: RAGPipeline = Depends(get_pipeline)) -> IngestResponse:
    """Reindexa DOCS_DIR (recria as coleções). Desative com ENABLE_INGEST_ENDPOINT=false."""
    if not get_settings().enable_ingest_endpoint:
        raise HTTPException(status_code=403, detail="Endpoint de ingestão desativado.")
    return IngestResponse(results=pipeline.ingest(request.strategies))
