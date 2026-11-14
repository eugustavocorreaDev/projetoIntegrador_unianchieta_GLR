"""Métricas de avaliação, sem dependência de serviços externos (testadas na CI)."""

from __future__ import annotations

import math
from collections.abc import Sequence

# A comparação de trechos fica em core.text, compartilhada com a validação interativa da API
from core.text import contains_snippet, first_relevant_rank, normalize

__all__ = [
    "contains_snippet",
    "first_relevant_rank",
    "generation_metrics",
    "mean_reciprocal_rank",
    "normalize",
    "recall_at_k",
    "threshold_sweep",
    "wilson_interval",
]


def recall_at_k(ranks: Sequence[int | None], k: int) -> float:
    """Fração das perguntas com pelo menos um trecho relevante entre os k primeiros."""
    if not ranks:
        return 0.0
    return sum(1 for r in ranks if r is not None and r <= k) / len(ranks)


def mean_reciprocal_rank(ranks: Sequence[int | None]) -> float:
    if not ranks:
        return 0.0
    return sum(1.0 / r for r in ranks if r is not None) / len(ranks)


def threshold_sweep(
    answerable_scores: Sequence[float], unanswerable_scores: Sequence[float]
) -> dict:
    """Escolhe o limite de similaridade que melhor separa perguntas com e sem resposta.

    Acurácia = (respondíveis com score >= t + sem resposta com score < t) / total.
    """
    total = len(answerable_scores) + len(unanswerable_scores)
    if total == 0:
        return {"best_threshold": None, "accuracy": None}
    candidates = sorted(set(answerable_scores) | set(unanswerable_scores))
    best_t, best_acc = 0.0, -1.0
    for t in [0.0, *candidates]:
        hits = sum(s >= t for s in answerable_scores) + sum(s < t for s in unanswerable_scores)
        acc = hits / total
        if acc > best_acc:
            best_t, best_acc = t, acc
    return {"best_threshold": round(best_t, 4), "accuracy": round(best_acc, 4)}


def wilson_interval(successes: int, n: int, z: float = 1.96) -> tuple[float, float]:
    """Intervalo de confiança de Wilson (95% com z=1,96) para uma proporção.

    Com 50 perguntas, cada uma vale 2 pontos percentuais: o intervalo mostra se a diferença
    entre duas estratégias é maior que a incerteza da própria medida.
    """
    if n == 0:
        return (0.0, 0.0)
    p = successes / n
    denominator = 1 + z * z / n
    center = (p + z * z / (2 * n)) / denominator
    margin = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / denominator
    return (max(0.0, center - margin), min(1.0, center + margin))


def _rate(numerator: int, denominator: int) -> float | None:
    return round(numerator / denominator, 4) if denominator else None


def generation_metrics(rows: Sequence[dict]) -> dict:
    """Agrega as linhas da avaliação de geração.

    Cada linha precisa de: answerable, refused, refusal_reason, grounded_snippet,
    grounded_source, citation_coverage.
    """
    answerable = [r for r in rows if r["answerable"]]
    unanswerable = [r for r in rows if not r["answerable"]]
    answered = [r for r in rows if not r["refused"]]
    llm_called = [r for r in rows if r["refusal_reason"] not in ("no_context", "low_relevance")]
    coverages = [r["citation_coverage"] for r in answered]

    return {
        "questions": len(rows),
        "answerable": len(answerable),
        "unanswerable": len(unanswerable),
        "answer_rate": _rate(sum(not r["refused"] for r in answerable), len(answerable)),
        "grounded_rate_snippet": _rate(
            sum(bool(r["grounded_snippet"]) for r in answerable), len(answerable)
        ),
        # Separa "respondeu sem fundamento" de "recusou indevidamente"
        "grounded_among_answered": _rate(
            sum(bool(r["grounded_snippet"]) for r in answerable if not r["refused"]),
            sum(not r["refused"] for r in answerable),
        ),
        "grounded_rate_source": _rate(
            sum(bool(r["grounded_source"]) for r in answerable), len(answerable)
        ),
        "correct_refusal_rate": _rate(sum(r["refused"] for r in unanswerable), len(unanswerable)),
        "false_refusal_rate": _rate(sum(r["refused"] for r in answerable), len(answerable)),
        "ungrounded_blocked_rate": _rate(
            sum(r["refusal_reason"] == "ungrounded_answer" for r in llm_called), len(llm_called)
        ),
        "mean_citation_coverage": round(sum(coverages) / len(coverages), 4) if coverages else None,
        "hallucination_candidates": [
            r["id"]
            for r in rows
            if not r["refused"] and (not r["answerable"] or not r["grounded_source"])
        ],
    }
