"""Testes de integração: ingestão real + Qdrant em memória + LLM falso."""

import re

import pytest

from core.errors import LLMError
from generation.prompts import REFUSAL_MESSAGE
from tests.conftest import FakeLLM, make_pipeline


def test_ingest_indexes_both_strategies():
    pipeline = make_pipeline(ingest=False)
    stats = {s["strategy"]: s for s in pipeline.ingest()}
    assert set(stats) == {"fixed", "recursive"}
    assert all(s["documents"] == 20 and s["chunks"] > 20 for s in stats.values())
    store = pipeline.retriever.store
    assert store.count("fixed") == stats["fixed"]["chunks"]
    assert store.count("recursive") == stats["recursive"]["chunks"]


def test_reingest_replaces_collection_instead_of_duplicating():
    pipeline = make_pipeline()
    before = pipeline.retriever.store.count("recursive")
    pipeline.ingest(["recursive"])
    assert pipeline.retriever.store.count("recursive") == before


def test_answer_has_citations_pointing_to_retrieved_chunks():
    def responder(system, user):
        # Cita o trecho que fala de dependency_overrides, onde quer que ele esteja no contexto
        for number, body in re.findall(
            r"\[(\d+)\] fonte: (.*?)(?=\n\[\d+\] fonte:|\n\nPERGUNTA)", user, re.S
        ):
            if "dependency_overrides" in body:
                return f"Use o dicionário app.dependency_overrides [{number}]."
        return REFUSAL_MESSAGE

    llm = FakeLLM(responder)
    pipeline = make_pipeline(llm=llm)
    result = pipeline.ask(
        "Como substituo uma dependência por uma versão de teste com dependency_overrides?"
    )
    assert not result.refused
    assert result.citations and result.citations[0].source == "testes.md"
    assert "dependency_overrides" in result.citations[0].excerpt
    assert result.timings_ms["retrieval"] >= 0 and "generation" in result.timings_ms
    system, user = llm.calls[0]
    assert "SOMENTE" in system and "PERGUNTA:" in user


def test_llm_refusal_is_propagated():
    pipeline = make_pipeline(llm=FakeLLM(lambda s, u: REFUSAL_MESSAGE))
    result = pipeline.ask("Como configuro GraphQL com Strawberry?")
    assert result.refused and result.refusal_reason == "llm_refusal"
    assert result.answer == REFUSAL_MESSAGE


def test_hallucinated_answer_without_citation_is_blocked():
    pipeline = make_pipeline(
        llm=FakeLLM(lambda s, u: "O FastAPI tem rate limiting nativo via app.limit().")
    )
    result = pipeline.ask("Como ativo o rate limiting nativo?")
    assert result.refused and result.refusal_reason == "ungrounded_answer"
    assert result.raw_answer.startswith("O FastAPI tem rate limiting")


def test_relevance_gate_refuses_without_calling_llm():
    llm = FakeLLM()
    pipeline = make_pipeline(llm=llm, min_vector_score=0.95)
    result = pipeline.ask("Qual é a receita de um bolo de cenoura?", mode="vector")
    assert result.refused and result.refusal_reason == "low_relevance"
    assert llm.calls == []


def test_bm25_without_matches_returns_no_context():
    llm = FakeLLM()
    pipeline = make_pipeline(llm=llm)
    result = pipeline.ask("xyzzy plugh", mode="bm25")
    assert result.refused and result.refusal_reason == "no_context"
    assert llm.calls == []


def test_llm_failure_raises_domain_error():
    def broken(system, user):
        raise LLMError("Ollama fora do ar")

    pipeline = make_pipeline(llm=FakeLLM(broken))
    with pytest.raises(LLMError):
        pipeline.ask("Como usar CORS?")


def test_invalid_strategy_is_rejected(indexed_pipeline):
    with pytest.raises(ValueError):
        indexed_pipeline.search("CORS", "semantico", "vector", 3)


def test_health_reports_collections(indexed_pipeline):
    health = indexed_pipeline.health()
    assert health["status"] == "ok"
    assert health["collections"]["fixed"] > 0 and health["collections"]["recursive"] > 0
