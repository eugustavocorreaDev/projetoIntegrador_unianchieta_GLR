"""Modelos de entrada e saída da API."""

from __future__ import annotations

from pydantic import BaseModel, Field, model_validator

from core.config import ChunkStrategy, RetrievalMode
from core.schemas import AskResult, RetrievedChunk

# ~5 MB de imagem viram ~6,7 milhões de caracteres em base64
MAX_IMAGE_B64_CHARS = 7_000_000


class QueryRequest(BaseModel):
    question: str = Field(
        default="",
        max_length=1000,
        examples=["Como sobrescrever uma dependência em testes?"],
        description="Obrigatória (3+ caracteres), a não ser que image_base64 seja enviado",
    )
    image_base64: str | None = Field(
        default=None,
        max_length=MAX_IMAGE_B64_CHARS,
        description="Print opcional (PNG, JPG ou WEBP em base64); o texto lido entra na pergunta",
    )
    strategy: ChunkStrategy | None = Field(default=None, description="Padrão: CHUNK_STRATEGY")
    mode: RetrievalMode | None = Field(default=None, description="Padrão: RETRIEVAL_MODE")
    top_k: int | None = Field(default=None, ge=1, le=20, description="Padrão: TOP_K")

    @model_validator(mode="after")
    def _question_or_image(self) -> QueryRequest:
        if not self.image_base64 and len(self.question.strip()) < 3:
            raise ValueError(
                "Escreva uma pergunta com pelo menos 3 caracteres ou envie uma imagem."
            )
        return self


class RetrievedOut(BaseModel):
    rank: int
    chunk_id: str
    source: str
    section: str
    text: str
    score: float
    vector_score: float | None
    bm25_score: float | None
    rerank_score: float | None
    stages: list[str]

    @classmethod
    def from_domain(cls, rank: int, item: RetrievedChunk) -> RetrievedOut:
        return cls(
            rank=rank,
            chunk_id=item.chunk.id,
            source=item.chunk.source,
            section=item.chunk.section,
            text=item.chunk.text,
            score=item.score,
            vector_score=item.vector_score,
            bm25_score=item.bm25_score,
            rerank_score=item.rerank_score,
            stages=item.stages,
        )


class CitationOut(BaseModel):
    id: int
    source: str
    section: str
    chunk_id: str
    excerpt: str


class AskResponse(BaseModel):
    answer: str
    refused: bool
    refusal_reason: str | None = Field(
        description="no_context, low_relevance, llm_refusal ou ungrounded_answer"
    )
    citations: list[CitationOut]
    retrieved: list[RetrievedOut]
    strategy: str
    mode: str
    mode_effective: str
    latency_ms: float
    timings_ms: dict[str, float]
    image_text: str | None = Field(default=None, description="Texto lido do print, se houver")

    @classmethod
    def from_domain(cls, result: AskResult) -> AskResponse:
        return cls(
            answer=result.answer,
            refused=result.refused,
            refusal_reason=result.refusal_reason,
            citations=[CitationOut(**vars(c)) for c in result.citations],
            retrieved=[RetrievedOut.from_domain(i, r) for i, r in enumerate(result.retrieved, 1)],
            strategy=result.strategy,
            mode=result.mode,
            mode_effective=result.mode_effective,
            latency_ms=result.latency_ms,
            timings_ms=result.timings_ms,
            image_text=result.image_text,
        )


class SearchResponse(BaseModel):
    retrieved: list[RetrievedOut]
    strategy: str
    mode_effective: str
    latency_ms: float
    image_text: str | None = None


class DocumentSummary(BaseModel):
    source: str
    title: str
    chars: int
    sections: int
    chunks: dict[str, int] = Field(description="Quantidade de chunks por estratégia")


class DocumentChunk(BaseModel):
    index: int
    section: str
    text: str
    chars: int


class DocumentDetail(BaseModel):
    source: str
    title: str
    path: str = Field(description="Caminho do arquivo no repositório")
    text: str
    sections: list[str]
    strategy: str
    chunks: list[DocumentChunk]


class ValidationQuestion(BaseModel):
    id: str
    question: str
    answerable: bool
    expected_answer: str | None = None
    expected_source: str | None = None
    expected_section: str | None = None
    expected_snippets: list[str] = Field(default_factory=list)
    note: str | None = None


class RetrievalCheckRequest(BaseModel):
    ids: list[str] = Field(min_length=1, max_length=100)
    strategy: ChunkStrategy | None = None
    mode: RetrievalMode | None = None
    top_k: int | None = Field(default=None, ge=1, le=20)


class RetrievalCheckRow(BaseModel):
    id: str
    question: str
    expected_source: str
    rank: int | None = Field(description="Posição do trecho esperado (None = não recuperado)")
    hit: bool
    retrieved_sources: list[str]
    strategy: str
    mode_effective: str
    latency_ms: float


class RetrievalCheckResponse(BaseModel):
    rows: list[RetrievalCheckRow]


class IngestRequest(BaseModel):
    strategies: list[ChunkStrategy] | None = Field(default=None, description="Padrão: todas")


class IngestResponse(BaseModel):
    results: list[dict]


class HealthResponse(BaseModel):
    status: str
    qdrant: bool
    ollama: bool
    collections: dict[str, int | None]
    llm_mode: str = Field(default="ollama", description="ollama ou mock (desenvolvimento)")
    embed_mode: str = Field(default="ollama", description="ollama ou hash (desenvolvimento)")
    qdrant_mode: str = Field(default="server", description="server ou local (em disco)")
