"""Aplicação FastAPI. Rode com: uvicorn api.main:app --app-dir src --port 8000"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse

from api.dependencies import get_pipeline
from api.schemas import (
    AskResponse,
    DocumentDetail,
    DocumentSummary,
    HealthResponse,
    IngestRequest,
    IngestResponse,
    QueryRequest,
    RetrievalCheckRequest,
    RetrievalCheckResponse,
    RetrievedOut,
    SearchResponse,
    ValidationQuestion,
)
from core.config import ChunkStrategy, get_settings
from core.errors import (
    CollectionNotFoundError,
    InvalidInputError,
    NotFoundError,
    RAGError,
    ServiceUnavailableError,
)
from core.logging_setup import setup_logging
from core.pipeline import RAGPipeline, compose_query
from core.validation import (
    check_retrieval,
    document_detail,
    document_summaries,
    load_validation_questions,
)

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


@app.exception_handler(InvalidInputError)
async def _invalid_input(_: Request, exc: InvalidInputError) -> JSONResponse:
    return JSONResponse(status_code=422, content={"detail": str(exc)})


@app.exception_handler(NotFoundError)
async def _not_found(_: Request, exc: NotFoundError) -> JSONResponse:
    return JSONResponse(status_code=404, content={"detail": str(exc)})


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
    """Responde à pergunta com citações, ou recusa quando a documentação não cobre o assunto.

    Com `image_base64`, o modelo de visão lê o print e o texto lido entra na pergunta.
    """
    result = pipeline.ask(
        request.question,
        request.strategy,
        request.mode,
        request.top_k,
        image_b64=request.image_base64,
    )
    return AskResponse.from_domain(result)


@app.post("/search", response_model=SearchResponse, tags=["rag"])
def search(request: QueryRequest, pipeline: RAGPipeline = Depends(get_pipeline)) -> SearchResponse:
    """Só a etapa de recuperação, sem chamar o LLM (útil para depurar e avaliar)."""
    image_text = pipeline.read_image(request.image_base64) if request.image_base64 else None
    chunks, strategy, effective, latency = pipeline.search(
        compose_query(request.question, image_text), request.strategy, request.mode, request.top_k
    )
    return SearchResponse(
        retrieved=[RetrievedOut.from_domain(i, c) for i, c in enumerate(chunks, 1)],
        strategy=strategy,
        mode_effective=effective,
        latency_ms=latency,
        image_text=image_text,
    )


@app.get("/documents", response_model=list[DocumentSummary], tags=["base de conhecimento"])
def documents(pipeline: RAGPipeline = Depends(get_pipeline)) -> list[dict]:
    """Arquivos da base (DOCS_DIR), com seções e quantidade de chunks por estratégia."""
    s = pipeline.settings
    return document_summaries(s.docs_dir, s.chunk_size, s.chunk_overlap)


@app.get("/documents/{source:path}", response_model=DocumentDetail, tags=["base de conhecimento"])
def document(
    source: str,
    strategy: ChunkStrategy = "recursive",
    pipeline: RAGPipeline = Depends(get_pipeline),
) -> dict:
    """Texto, seções e chunks de um arquivo da base, na estratégia escolhida."""
    s = pipeline.settings
    return document_detail(s.docs_dir, source, strategy, s.chunk_size, s.chunk_overlap)


@app.get("/validation/questions", response_model=list[ValidationQuestion], tags=["validação"])
def validation_questions(pipeline: RAGPipeline = Depends(get_pipeline)) -> list[dict]:
    """Perguntas do conjunto de teste (com e sem resposta) e os trechos esperados."""
    return load_validation_questions(pipeline.settings.eval_dataset)


@app.post("/validation/retrieval", response_model=RetrievalCheckResponse, tags=["validação"])
def validation_retrieval(
    request: RetrievalCheckRequest, pipeline: RAGPipeline = Depends(get_pipeline)
) -> dict:
    """Confere, pergunta a pergunta, se o trecho esperado está entre os top-k recuperados."""
    questions = load_validation_questions(pipeline.settings.eval_dataset)
    rows = check_retrieval(
        pipeline, questions, request.ids, request.strategy, request.mode, request.top_k
    )
    return {"rows": rows}


@app.post("/ingest", response_model=IngestResponse, tags=["administração"])
def ingest(request: IngestRequest, pipeline: RAGPipeline = Depends(get_pipeline)) -> IngestResponse:
    """Reindexa DOCS_DIR (recria as coleções). Desative com ENABLE_INGEST_ENDPOINT=false."""
    if not get_settings().enable_ingest_endpoint:
        raise HTTPException(status_code=403, detail="Endpoint de ingestão desativado.")
    return IngestResponse(results=pipeline.ingest(request.strategies))
