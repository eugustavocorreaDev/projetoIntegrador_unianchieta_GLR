"""Tipos de domínio compartilhados entre ingestão, recuperação e geração."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Document:
    source: str  # caminho relativo ao diretório de documentos, ex.: "dependencias.md"
    title: str
    text: str


@dataclass(frozen=True)
class Chunk:
    id: str
    text: str
    source: str
    section: str  # caminho de títulos, ex.: "Dependências > Dependências com yield"
    chunk_index: int
    strategy: str

    def embedding_text(self) -> str:
        """Texto enviado ao modelo de embeddings: origem + seção + conteúdo.

        As duas estratégias usam o mesmo formato, então a comparação experimental
        isola o efeito das fronteiras dos chunks.
        """
        header = f"{self.source} › {self.section}" if self.section else self.source
        return f"{header}\n{self.text}"

    def to_payload(self) -> dict:
        return {
            "text": self.text,
            "source": self.source,
            "section": self.section,
            "chunk_index": self.chunk_index,
            "strategy": self.strategy,
        }

    @classmethod
    def from_payload(cls, point_id: str, payload: dict) -> Chunk:
        return cls(
            id=str(point_id),
            text=payload["text"],
            source=payload["source"],
            section=payload.get("section", ""),
            chunk_index=int(payload.get("chunk_index", 0)),
            strategy=payload.get("strategy", ""),
        )


@dataclass
class RetrievedChunk:
    chunk: Chunk
    score: float  # pontuação do último estágio que ordenou a lista
    vector_score: float | None = None
    bm25_score: float | None = None
    rerank_score: float | None = None
    stages: list[str] = field(default_factory=list)


@dataclass
class Citation:
    id: int
    source: str
    section: str
    chunk_id: str
    excerpt: str


@dataclass
class AskResult:
    question: str
    answer: str
    refused: bool
    refusal_reason: str | None
    citations: list[Citation]
    retrieved: list[RetrievedChunk]
    strategy: str
    mode: str
    mode_effective: str
    latency_ms: float
    timings_ms: dict[str, float]
    raw_answer: str | None = None
    image_text: str | None = None  # texto lido do print enviado com a pergunta
