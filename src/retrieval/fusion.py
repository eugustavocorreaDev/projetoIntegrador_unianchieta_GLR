"""Reciprocal Rank Fusion (Cormack, Clarke e Büttcher, 2009).

Combina listas ordenadas usando só a posição de cada item, o que dispensa normalizar
pontuações de escalas diferentes (cosseno do Qdrant e BM25).
"""

from __future__ import annotations

from core.schemas import RetrievedChunk


def reciprocal_rank_fusion(
    rankings: list[list[RetrievedChunk]], k: int = 60, limit: int | None = None
) -> list[RetrievedChunk]:
    fused: dict[str, RetrievedChunk] = {}
    totals: dict[str, float] = {}
    for ranking in rankings:
        for rank, item in enumerate(ranking, start=1):
            key = item.chunk.id
            totals[key] = totals.get(key, 0.0) + 1.0 / (k + rank)
            if key not in fused:
                fused[key] = RetrievedChunk(
                    chunk=item.chunk,
                    score=0.0,
                    vector_score=item.vector_score,
                    bm25_score=item.bm25_score,
                    stages=list(item.stages),
                )
            else:
                merged = fused[key]
                merged.vector_score = (
                    merged.vector_score if merged.vector_score is not None else item.vector_score
                )
                merged.bm25_score = (
                    merged.bm25_score if merged.bm25_score is not None else item.bm25_score
                )
                merged.stages.extend(s for s in item.stages if s not in merged.stages)
    for key, item in fused.items():
        item.score = totals[key]
        item.stages.append("rrf")
    ordered = sorted(fused.values(), key=lambda r: -r.score)
    return ordered[:limit] if limit is not None else ordered
