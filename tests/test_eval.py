"""Métricas, integridade do dataset e execução do script de avaliação sem serviços externos."""

import hashlib
import json
import re

import pytest

from eval.metrics import (
    contains_snippet,
    first_relevant_rank,
    generation_metrics,
    mean_reciprocal_rank,
    normalize,
    recall_at_k,
    threshold_sweep,
    wilson_interval,
)
from eval.run_eval import (
    build_report,
    calibrate_gate,
    evaluate_generation,
    evaluate_retrieval,
    load_dataset,
    main,
)
from generation.prompts import REFUSAL_MESSAGE
from ingestion.chunking import get_chunker
from tests.conftest import DATASET, ROOT, FakeLLM, make_pipeline

DEV_DATASET = ROOT / "eval" / "datasets" / "perguntas_dev.json"


@pytest.fixture(scope="module")
def questions():
    return load_dataset(DATASET)


@pytest.fixture(scope="module")
def dev_questions():
    return load_dataset(DEV_DATASET)


def test_test_set_is_frozen():
    """O conjunto de teste está congelado desde a 2.1.0: mudar qualquer pergunta exige subir
    a versão e regravar questions_sha256, o que fica explícito no histórico do Git."""
    data = json.loads(DATASET.read_text(encoding="utf-8"))
    canonical = json.dumps(
        data["questions"], ensure_ascii=False, sort_keys=True, separators=(",", ":")
    )
    assert hashlib.sha256(canonical.encode("utf-8")).hexdigest() == data["questions_sha256"]
    assert data["version"] == "2.1.0"


# --- Métricas ---------------------------------------------------------------


def test_normalize_ignores_accents_case_and_markdown():
    assert normalize("Use `Path(ge=1)`  **já**") == "use path(ge=1) ja"
    assert contains_snippet("O método `add_task` adiciona", ["metodo add_task"])


def test_rank_recall_and_mrr():
    ranks = [first_relevant_rank(["x", "alvo aqui"], ["alvo"]), 1, None, 3]
    assert ranks[0] == 2
    assert recall_at_k(ranks, 1) == 0.25
    assert recall_at_k(ranks, 3) == 0.75
    assert mean_reciprocal_rank(ranks) == pytest.approx((0.5 + 1 + 0 + 1 / 3) / 4)
    assert recall_at_k([], 5) == 0.0


def test_threshold_sweep_separates_scores():
    result = threshold_sweep([0.8, 0.7, 0.75], [0.3, 0.4])
    assert 0.4 < result["best_threshold"] <= 0.7
    assert result["accuracy"] == 1.0


def test_generation_metrics():
    rows = [
        {
            "id": "a",
            "answerable": True,
            "refused": False,
            "refusal_reason": None,
            "grounded_snippet": True,
            "grounded_source": True,
            "citation_coverage": 1.0,
        },
        {
            "id": "b",
            "answerable": True,
            "refused": True,
            "refusal_reason": "ungrounded_answer",
            "grounded_snippet": False,
            "grounded_source": False,
            "citation_coverage": 0.0,
        },
        {
            "id": "c",
            "answerable": False,
            "refused": True,
            "refusal_reason": "llm_refusal",
            "grounded_snippet": False,
            "grounded_source": False,
            "citation_coverage": 0.0,
        },
        {
            "id": "d",
            "answerable": False,
            "refused": False,
            "refusal_reason": None,
            "grounded_snippet": False,
            "grounded_source": False,
            "citation_coverage": 0.5,
        },
    ]
    m = generation_metrics(rows)
    assert m["answer_rate"] == 0.5
    assert m["grounded_rate_snippet"] == 0.5
    assert m["correct_refusal_rate"] == 0.5
    assert m["false_refusal_rate"] == 0.5
    assert m["ungrounded_blocked_rate"] == 0.25
    assert m["hallucination_candidates"] == ["d"]


# --- Integridade do dataset -----------------------------------------------------


def test_dataset_ids_unique_and_balanced(questions):
    ids = [q["id"] for q in questions]
    assert len(ids) == len(set(ids))
    assert sum(q["answerable"] for q in questions) >= 50
    assert sum(not q["answerable"] for q in questions) >= 10


@pytest.mark.parametrize("dataset", [DATASET, DEV_DATASET], ids=["teste", "dev"])
def test_expected_snippets_exist_in_expected_source(dataset, documents):
    by_source = {d.source: d.text for d in documents}
    for q in load_dataset(dataset):
        if q["answerable"]:
            assert q["expected_source"] in by_source, q["id"]
            assert contains_snippet(by_source[q["expected_source"]], q["expected_snippets"]), q[
                "id"
            ]


@pytest.mark.parametrize("dataset", [DATASET, DEV_DATASET], ids=["teste", "dev"])
@pytest.mark.parametrize("strategy", ["fixed", "recursive"])
def test_every_snippet_fits_inside_some_chunk(dataset, documents, strategy):
    """Garante que Recall@k = 100% é atingível nas duas estratégias (comparação justa)."""
    chunks = [c for d in documents for c in get_chunker(strategy, 800, 120).split(d)]
    for q in load_dataset(dataset):
        if q["answerable"]:
            assert any(contains_snippet(c.text, q["expected_snippets"]) for c in chunks), q["id"]


def test_dev_and_test_sets_do_not_overlap(questions, dev_questions):
    """Sem vazamento: a calibração nunca vê perguntas nem trechos do conjunto de teste."""
    assert {q["question"] for q in questions}.isdisjoint(q["question"] for q in dev_questions)
    test_snips = {normalize(s) for q in questions for s in q.get("expected_snippets", [])}
    dev_snips = {normalize(s) for q in dev_questions for s in q.get("expected_snippets", [])}
    assert test_snips.isdisjoint(dev_snips)
    assert any(not q["answerable"] for q in dev_questions)


def test_wilson_interval():
    low, high = wilson_interval(45, 50)
    assert 0.78 < low < 0.80 and 0.95 < high < 0.97
    assert wilson_interval(0, 0) == (0.0, 0.0)
    assert wilson_interval(50, 50)[1] == 1.0


def test_main_refuses_to_calibrate_on_the_test_set():
    with pytest.raises(SystemExit):
        main(["--dataset", str(DATASET), "--dev-dataset", str(DATASET)])


# --- Script de avaliação ponta a ponta (com dublês) ------------------------------


def test_evaluate_retrieval_and_generation_offline(questions):
    def responder(system, user):
        # Responde citando [1] só na pergunta q27 (métodos liberados pelo CORS por padrão)
        return (
            "O CORSMiddleware permite apenas o método GET por padrão [1]."
            if "quais métodos HTTP" in user.split("PERGUNTA:")[1]
            else REFUSAL_MESSAGE
        )

    pipeline = make_pipeline(llm=FakeLLM(responder))
    rows, summary = evaluate_retrieval(
        pipeline, questions, ["fixed", "recursive"], ["vector", "bm25", "hybrid"], [1, 5]
    )
    assert len(summary) == 6
    assert all(r["llm_mode"] == "ollama" and r["embed_mode"] == "ollama" for r in rows)
    assert all(s["avg_chunk_chars"] and s["hits@5"] <= s["n"] for s in summary)
    assert all(s["recall@5_ci95"].startswith("[") for s in summary)
    assert all(0 <= s["recall@1"] <= s["recall@5"] <= 1 for s in summary)
    assert next(s for s in summary if s["strategy"] == "fixed" and s["mode"] == "vector")[
        "baseline"
    ]
    gate = calibrate_gate(pipeline, load_dataset(DEV_DATASET), ["fixed", "recursive"], "hybrid", 5)
    assert set(gate) == {"fixed", "recursive"}
    assert gate["recursive"]["n_answerable"] == 30 and gate["recursive"]["n_unanswerable"] == 12
    assert gate["recursive"]["best_threshold"] is not None
    # Com embeddings lexicais, a busca híbrida já deve achar a maioria dos trechos
    hybrid = next(s for s in summary if s["strategy"] == "recursive" and s["mode"] == "hybrid")
    assert hybrid["recall@5"] >= 0.6

    gen_rows, gen = evaluate_generation(pipeline, questions, "recursive", "hybrid", 5)
    assert gen["questions"] == len(questions)
    assert gen["correct_refusal_rate"] == 1.0
    assert gen["llm_mode"] == "ollama" and "grounded_among_answered" in gen
    cors = next(r for r in gen_rows if r["id"] == "q27")
    assert not cors["refused"] and cors["grounded_source"]

    report = build_report(
        {
            "timestamp": "t",
            "dataset": "d",
            "dev_dataset": "dev",
            "n_questions": len(questions),
            "command": "c",
            "config": pipeline.settings.public_dict(),
        },
        summary,
        gate,
        gen,
        gen_rows,
    )
    assert "## Recuperação" in report and "recall@5" in report
    assert "conjunto de desenvolvimento `dev`" in report and "grounded_among_answered" in report
    assert "llm_mode=ollama" in report and "ATENÇÃO" not in report
    assert re.search(r"\| recursive \| hybrid \|", report)
    json.dumps(gen)  # serializável
