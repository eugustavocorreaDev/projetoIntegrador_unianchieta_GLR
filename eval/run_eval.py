"""Avaliação experimental do RAG.

Exemplos (a partir da raiz do repositório, com Qdrant e Ollama no ar):

    # Recuperação: todas as estratégias e modos, reindexando antes
    python -m eval.run_eval --reindex

    # Recuperação + geração (citações e recusas) com a configuração padrão
    python -m eval.run_eval --generate

    # Geração do baseline (chunking fixo + busca só vetorial), para comparar
    python -m eval.run_eval --generate --gen-strategy fixed --gen-mode vector

    # Dentro do docker compose
    docker compose run --rm api python -m eval.run_eval --reindex --generate

Saídas em eval/results/<data-hora>/: CSVs por pergunta, summary.json e report.md.
O limite de relevância (MIN_VECTOR_SCORE) é calibrado no conjunto de DESENVOLVIMENTO
(--dev-dataset), nunca no conjunto de teste.
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
import time
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from core.config import CHUNK_STRATEGIES, RETRIEVAL_MODES, get_settings  # noqa: E402
from core.logging_setup import setup_logging  # noqa: E402
from core.pipeline import RAGPipeline, build_pipeline, relevance_signal  # noqa: E402
from eval.metrics import (  # noqa: E402
    contains_snippet,
    first_relevant_rank,
    generation_metrics,
    mean_reciprocal_rank,
    recall_at_k,
    threshold_sweep,
    wilson_interval,
)
from generation.grounding import citation_coverage  # noqa: E402

BASELINE = ("fixed", "vector")
DATASETS = ROOT / "eval" / "datasets"


def load_dataset(path: Path) -> list[dict]:
    data = json.loads(path.read_text(encoding="utf-8"))
    questions = data["questions"] if isinstance(data, dict) else data
    for q in questions:
        if q["answerable"] and not q.get("expected_snippets"):
            raise ValueError(f"Pergunta {q['id']} sem expected_snippets")
    return questions


def _modes(pipeline: RAGPipeline) -> dict:
    """Marca cada linha bruta com os modos, para nenhuma saída de mock passar por resultado."""
    return {
        "llm_mode": pipeline.settings.llm_mode,
        "embed_mode": pipeline.settings.embed_mode,
    }


def warm_up(pipeline: RAGPipeline, strategies: list[str]) -> None:
    """Carrega embeddings, BM25 e reranker antes de medir latências."""
    for strategy in strategies:
        try:
            pipeline.search("aquecimento", strategy, "hybrid_rerank", 1)
        except Exception as exc:  # o aquecimento nunca impede a avaliação
            print(f"aviso: aquecimento falhou em {strategy}: {exc}")


def _avg_chunk_chars(pipeline: RAGPipeline, strategy: str) -> float | None:
    try:
        chunks = pipeline.retriever.bm25_index(strategy).chunks
    except Exception:
        return None
    return round(sum(len(c.text) for c in chunks) / len(chunks), 1) if chunks else None


def evaluate_retrieval(
    pipeline: RAGPipeline,
    questions: list[dict],
    strategies: list[str],
    modes: list[str],
    ks: list[int],
) -> tuple[list[dict], list[dict]]:
    max_k = max(ks)
    ci_k = 5 if 5 in ks else max_k
    answerable = [q for q in questions if q["answerable"]]
    rows: list[dict] = []
    summary: list[dict] = []
    for strategy in strategies:
        avg_chars = _avg_chunk_chars(pipeline, strategy)
        for mode in modes:
            ranks: list[int | None] = []
            latencies: list[float] = []
            effective_modes: set[str] = set()
            for q in answerable:
                chunks, _, effective, latency = pipeline.search(
                    q["question"], strategy, mode, max_k
                )
                effective_modes.add(effective)
                rank = first_relevant_rank([c.chunk.text for c in chunks], q["expected_snippets"])
                ranks.append(rank)
                latencies.append(latency)
                rows.append(
                    {
                        "strategy": strategy,
                        "mode": mode,
                        "mode_effective": effective,
                        "id": q["id"],
                        "question": q["question"],
                        "relevant_rank": rank if rank is not None else "",
                        "top1_source": chunks[0].chunk.source if chunks else "",
                        "expected_source": q["expected_source"],
                        "source_hit_top1": bool(chunks)
                        and chunks[0].chunk.source == q["expected_source"],
                        "latency_ms": latency,
                        **_modes(pipeline),
                    }
                )
            hits = sum(1 for r in ranks if r is not None and r <= ci_k)
            low, high = wilson_interval(hits, len(ranks))
            entry = {
                "strategy": strategy,
                "mode": mode,
                "mode_effective": ",".join(sorted(effective_modes)),
                "baseline": (strategy, mode) == BASELINE,
                "n": len(ranks),
                "avg_chunk_chars": avg_chars,
                **{f"recall@{k}": round(recall_at_k(ranks, k), 4) for k in ks},
                f"hits@{ci_k}": hits,
                f"recall@{ci_k}_ci95": f"[{low:.2f}, {high:.2f}]",
                "mrr": round(mean_reciprocal_rank(ranks), 4),
                "mean_latency_ms": round(sum(latencies) / len(latencies), 1) if latencies else None,
            }
            summary.append(entry)
            print(json.dumps(entry, ensure_ascii=False))
    return rows, summary


def calibrate_gate(
    pipeline: RAGPipeline, questions: list[dict], strategies: list[str], mode: str, top_k: int
) -> dict:
    """Sugere MIN_VECTOR_SCORE a partir de um conjunto de DESENVOLVIMENTO.

    Usa `relevance_signal`, a mesma estatística que o filtro aplica em produção, sobre os
    trechos que o modo configurado realmente enviaria ao LLM.
    """
    gate: dict = {}
    for strategy in strategies:
        signals: dict[bool, list[float]] = {True: [], False: []}
        for q in questions:
            chunks, *_ = pipeline.search(q["question"], strategy, mode, top_k)
            signal = relevance_signal(chunks)
            if signal is not None:
                signals[q["answerable"]].append(signal)
        ans, una = signals[True], signals[False]
        gate[strategy] = {
            "mode": mode,
            "n_answerable": len(ans),
            "n_unanswerable": len(una),
            "mean_signal_answerable": round(sum(ans) / len(ans), 4) if ans else None,
            "mean_signal_unanswerable": round(sum(una) / len(una), 4) if una else None,
            **threshold_sweep(ans, una),
        }
    return gate


def evaluate_generation(
    pipeline: RAGPipeline, questions: list[dict], strategy: str, mode: str, top_k: int
) -> tuple[list[dict], dict]:
    rows: list[dict] = []
    for q in questions:
        result = pipeline.ask(q["question"], strategy, mode, top_k)
        texts = {r.chunk.id: r.chunk.text for r in result.retrieved}
        cited_texts = [texts.get(c.chunk_id, "") for c in result.citations]
        cited_sources = sorted({c.source for c in result.citations})
        answerable = q["answerable"]
        rows.append(
            {
                "id": q["id"],
                "question": q["question"],
                "answerable": answerable,
                "refused": result.refused,
                "refusal_reason": result.refusal_reason or "",
                "answer": result.answer,
                "raw_answer": result.raw_answer or "",
                "n_citations": len(result.citations),
                "cited_sources": ";".join(cited_sources),
                "expected_source": q.get("expected_source", ""),
                "grounded_snippet": answerable
                and not result.refused
                and any(contains_snippet(t, q["expected_snippets"]) for t in cited_texts),
                "grounded_source": answerable
                and not result.refused
                and q.get("expected_source") in cited_sources,
                "citation_coverage": round(citation_coverage(result.answer), 4)
                if not result.refused
                else 0.0,
                "latency_ms": result.latency_ms,
                **_modes(pipeline),
            }
        )
        print(
            f"[{q['id']}] refused={result.refused} reason={result.refusal_reason} "
            f"citations={len(result.citations)} {result.latency_ms:.0f}ms"
        )
    metrics = generation_metrics(rows)
    metrics.update({"strategy": strategy, "mode": mode, "top_k": top_k, **_modes(pipeline)})
    return rows, metrics


def write_csv(path: Path, rows: list[dict]) -> None:
    if not rows:
        return
    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def _md_table(rows: list[dict], columns: list[str]) -> str:
    lines = ["| " + " | ".join(columns) + " |", "| " + " | ".join("---" for _ in columns) + " |"]
    for row in rows:
        lines.append("| " + " | ".join(str(row.get(c, "")) for c in columns) + " |")
    return "\n".join(lines)


def build_report(
    meta: dict, summary: list[dict], gate: dict, gen: dict | None, gen_rows: list[dict]
) -> str:
    first = summary[0] if summary else {}
    ks = [c for c in first if c.startswith("recall@") and not c.endswith("_ci95")]
    extra = [c for c in first if c.startswith("hits@") or c.endswith("_ci95")]
    cfg = meta["config"]
    parts = [
        f"# Relatório de avaliação — {meta['timestamp']}",
        "",
        f"- Conjunto de teste: `{meta['dataset']}` ({meta['n_questions']} perguntas)",
        f"- Corpus: `{cfg['docs_dir']}` · embeddings `{cfg['embed_model']}` · "
        f"LLM `{cfg['llm_model']}` · reranker `{cfg['reranker_model']}`",
        f"- chunk_size={cfg['chunk_size']} · chunk_overlap={cfg['chunk_overlap']} · "
        f"candidates_k={cfg['candidates_k']}",
        f"- Comando: `{meta['command']}`",
        f"- Modos: llm_mode={cfg['llm_mode']} · embed_mode={cfg['embed_mode']} · "
        f"qdrant_mode={cfg['qdrant_mode']}",
        "",
        *(
            [
                "> **ATENÇÃO: execução em modo de desenvolvimento (mock/hash).** Estes números "
                "não medem o sistema oficial e não podem ser usados como resultado.",
                "",
            ]
            if cfg["llm_mode"] != "ollama" or cfg["embed_mode"] != "ollama"
            else []
        ),
        "## Recuperação",
        "",
        "Baseline: chunking `fixed` + busca `vector`. Um trecho é relevante quando contém o "
        "trecho-fonte esperado. `avg_chunk_chars` mostra o tamanho médio dos chunks de cada "
        "estratégia: com o mesmo k, chunks menores entregam menos texto ao LLM. O intervalo de "
        "95% (Wilson) indica a incerteza com o número de perguntas usado.",
        "",
        _md_table(
            summary,
            [
                "strategy",
                "mode",
                "mode_effective",
                "baseline",
                "n",
                "avg_chunk_chars",
                *ks,
                *extra,
                "mrr",
                "mean_latency_ms",
            ],
        ),
    ]
    if gate:
        parts += [
            "",
            "## Calibração do limite de relevância "
            f"(conjunto de desenvolvimento `{meta['dev_dataset']}`)",
            "",
            _md_table(
                [{"strategy": s, **v} for s, v in gate.items()],
                [
                    "strategy",
                    "mode",
                    "n_answerable",
                    "n_unanswerable",
                    "mean_signal_answerable",
                    "mean_signal_unanswerable",
                    "best_threshold",
                    "accuracy",
                ],
            ),
            "",
            "Calibrado fora do conjunto de teste. Use `best_threshold` como `MIN_VECTOR_SCORE` "
            "e rode a avaliação do conjunto de teste uma única vez com esse valor.",
        ]
    if gen:
        parts += [
            "",
            f"## Geração ({gen['strategy']} + {gen['mode']}, top_k={gen['top_k']})",
            "",
            _md_table(
                [gen],
                [
                    "questions",
                    "answer_rate",
                    "grounded_rate_snippet",
                    "grounded_among_answered",
                    "grounded_rate_source",
                    "correct_refusal_rate",
                    "false_refusal_rate",
                    "ungrounded_blocked_rate",
                    "mean_citation_coverage",
                ],
            ),
            "",
            "### Candidatos a alucinação (analisar manualmente)",
            "",
        ]
        flagged = [r for r in gen_rows if r["id"] in gen["hallucination_candidates"]]
        if flagged:
            parts.append(
                _md_table(flagged, ["id", "answerable", "question", "answer", "cited_sources"])
            )
        else:
            parts.append("Nenhum.")
    return "\n".join(parts) + "\n"


def _rel(path: Path) -> str:
    return str(path.relative_to(ROOT) if path.is_relative_to(ROOT) else path)


def main(argv: list[str] | None = None) -> int:
    settings = get_settings()
    parser = argparse.ArgumentParser(description="Avaliação experimental do RAG.")
    parser.add_argument("--dataset", type=Path, default=DATASETS / "perguntas_teste.json")
    parser.add_argument(
        "--dev-dataset",
        type=Path,
        default=DATASETS / "perguntas_dev.json",
        help="Conjunto de desenvolvimento para calibrar MIN_VECTOR_SCORE (nunca o de teste)",
    )
    parser.add_argument(
        "--strategies", nargs="+", choices=CHUNK_STRATEGIES, default=list(CHUNK_STRATEGIES)
    )
    parser.add_argument(
        "--modes", nargs="+", choices=RETRIEVAL_MODES, default=list(RETRIEVAL_MODES)
    )
    parser.add_argument("--k", nargs="+", type=int, default=[1, 3, 5, 10])
    parser.add_argument(
        "--reindex", action="store_true", help="Reindexa as estratégias antes de avaliar"
    )
    parser.add_argument(
        "--generate", action="store_true", help="Avalia também a geração (usa o LLM)"
    )
    parser.add_argument("--gen-strategy", choices=CHUNK_STRATEGIES, default=settings.chunk_strategy)
    parser.add_argument("--gen-mode", choices=RETRIEVAL_MODES, default=settings.retrieval_mode)
    parser.add_argument("--out", type=Path, default=ROOT / "eval" / "results")
    args = parser.parse_args(argv)

    if args.dev_dataset.resolve() == args.dataset.resolve():
        parser.error("--dev-dataset não pode ser o conjunto de teste (vazamento na calibração)")

    setup_logging(settings.log_level, settings.log_dir)
    questions = load_dataset(args.dataset)
    pipeline = build_pipeline(settings)

    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    out_dir = args.out / timestamp
    out_dir.mkdir(parents=True, exist_ok=True)
    started = time.perf_counter()

    if args.reindex:
        for stats in pipeline.ingest(args.strategies):
            print(json.dumps(stats, ensure_ascii=False))
    warm_up(pipeline, args.strategies)

    rows, summary = evaluate_retrieval(pipeline, questions, args.strategies, args.modes, args.k)
    write_csv(out_dir / "retrieval_per_question.csv", rows)
    write_csv(out_dir / "retrieval_summary.csv", summary)

    gate: dict = {}
    if args.dev_dataset.exists():
        gate = calibrate_gate(
            pipeline,
            load_dataset(args.dev_dataset),
            args.strategies,
            settings.retrieval_mode,
            settings.top_k,
        )

    gen_rows: list[dict] = []
    gen: dict | None = None
    if args.generate:
        gen_rows, gen = evaluate_generation(
            pipeline, questions, args.gen_strategy, args.gen_mode, settings.top_k
        )
        write_csv(out_dir / "generation_per_question.csv", gen_rows)

    meta = {
        "timestamp": timestamp,
        "dataset": _rel(args.dataset),
        "dev_dataset": _rel(args.dev_dataset),
        "n_questions": len(questions),
        "command": "python -m eval.run_eval "
        + " ".join(argv if argv is not None else sys.argv[1:]),
        "config": settings.public_dict(),
        "seconds": round(time.perf_counter() - started, 1),
    }
    (out_dir / "summary.json").write_text(
        json.dumps(
            {"meta": meta, "retrieval": summary, "gate": gate, "generation": gen},
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    (out_dir / "report.md").write_text(
        build_report(meta, summary, gate, gen, gen_rows), encoding="utf-8"
    )
    print(f"\nResultados em {out_dir}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
