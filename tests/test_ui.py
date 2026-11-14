"""Testes da interface com o AppTest do Streamlit, com a API simulada (sem rede)."""

from pathlib import Path

import pytest

pytest.importorskip("streamlit")
import httpx  # noqa: E402
import streamlit as st  # noqa: E402
from streamlit.testing.v1 import AppTest  # noqa: E402

APP = str(Path(__file__).resolve().parents[1] / "src" / "ui" / "app.py")

HEALTH = {"status": "ok", "qdrant": True, "ollama": True, "collections": {"recursive": 30}}
CHUNK = {
    "rank": 1,
    "chunk_id": "c1",
    "source": "testes.md",
    "section": "Testes > Sobrescrevendo dependências",
    "text": "Use o dicionário app.dependency_overrides.",
    "score": 0.91,
    "vector_score": 0.7,
    "bm25_score": 5.0,
    "rerank_score": 0.91,
    "stages": ["vector", "bm25", "rrf", "rerank"],
}


def _answer(refused: bool) -> dict:
    return {
        "answer": "Não encontrei essa informação na documentação indexada."
        if refused
        else "Use `app.dependency_overrides` [1].",
        "refused": refused,
        "refusal_reason": "ungrounded_answer" if refused else None,
        "citations": []
        if refused
        else [
            {
                "id": 1,
                "source": "testes.md",
                "section": CHUNK["section"],
                "chunk_id": "c1",
                "excerpt": CHUNK["text"],
            }
        ],
        "retrieved": [CHUNK],
        "strategy": "recursive",
        "mode": "hybrid_rerank",
        "mode_effective": "hybrid_rerank",
        "latency_ms": 1234.0,
        "timings_ms": {"retrieval": 100.0, "generation": 1100.0},
    }


@pytest.fixture
def fake_api(monkeypatch):
    state = {"answer": _answer(False), "fail": False}

    def fake_get(url, **kwargs):
        return httpx.Response(200, json=HEALTH, request=httpx.Request("GET", url))

    def fake_post(url, **kwargs):
        if state["fail"]:
            raise httpx.ConnectError("recusado")
        return httpx.Response(200, json=state["answer"], request=httpx.Request("POST", url))

    monkeypatch.setattr(httpx, "get", fake_get)
    monkeypatch.setattr(httpx, "post", fake_post)
    st.cache_data.clear()  # fetch_health é cacheado entre execuções no mesmo processo
    return state


def _submit_button(at: AppTest):
    return next(b for b in at.button if b.label == "Perguntar")


def _ask(question: str) -> AppTest:
    at = AppTest.from_file(APP, default_timeout=30)
    at.run()
    at.text_area(key="question").input(question)
    _submit_button(at).click()
    at.run()
    return at


def _html(at: AppTest) -> str:
    return "\n".join(m.value for m in at.markdown)


def test_renders_answer_with_citation_badges_and_sources(fake_api):
    at = _ask("Como sobrescrever uma dependência?")
    assert not at.exception
    page = _html(at)
    assert "Resposta fundamentada" in page
    assert '<span class="cite">1</span>' in page
    assert "<code>app.dependency_overrides</code>" in page
    assert any("[1] testes.md" in e.label for e in at.expander)


def test_renders_refusal_indicator(fake_api):
    fake_api["answer"] = _answer(True)
    at = _ask("Como configurar GraphQL?")
    assert not at.exception
    page = _html(at)
    assert "Recusa anti-alucinação acionada" in page
    assert "descartada" in page  # explica o motivo ungrounded_answer


def test_shows_error_when_api_is_down(fake_api):
    fake_api["fail"] = True
    at = _ask("Pergunta qualquer")
    assert not at.exception
    assert at.error and "Não foi possível falar com a API" in at.error[0].value


def test_example_button_fills_question(fake_api):
    at = AppTest.from_file(APP, default_timeout=30)
    at.run()
    example = next(b for b in at.button if "GraphQL" in b.label)
    example.click()
    at.run()
    assert at.text_area(key="question").value == "Como configurar GraphQL no FastAPI?"


def test_short_question_shows_warning(fake_api):
    at = _ask("oi")
    assert at.warning and "pelo menos 3" in at.warning[0].value


def test_model_output_is_html_escaped(fake_api):
    fake_api["answer"] = {**_answer(False), "answer": "<script>alert(1)</script> ok [1]"}
    at = _ask("teste de escape")
    assert "<script>" not in _html(at)
    assert "&lt;script&gt;" in _html(at)


def test_demo_banner_only_in_mock_mode(fake_api, monkeypatch):
    at = AppTest.from_file(APP, default_timeout=30)
    at.run()
    assert "Modo de Visualização (Mock)" not in _html(at)

    mock_health = {**HEALTH, "llm_mode": "mock", "embed_mode": "hash", "qdrant_mode": "local"}
    monkeypatch.setattr(
        httpx,
        "get",
        lambda url, **k: httpx.Response(200, json=mock_health, request=httpx.Request("GET", url)),
    )
    st.cache_data.clear()
    at = AppTest.from_file(APP, default_timeout=30)
    at.run()
    assert "Modo de Visualização (Mock)" in _html(at)
    assert "ollama pull llama3.2:3b" in _html(at)


def test_open_source_fonts_only():
    import sys

    sys.path.insert(0, str(Path(APP).parent))
    from styles import CSS

    assert "Plus+Jakarta+Sans" in CSS and "'Plus Jakarta Sans'" in CSS
    assert "Arial" in CSS
    assert "Nexa" not in CSS


def test_answer_lists_and_bold_are_rendered(fake_api):
    fake_api["answer"] = {
        **_answer(False),
        "answer": (
            "Resumo direto [1].\n\n- **Passo um**: faça X [1]\n- Passo dois [1]\n\n"
            "1. Primeiro [1]"
        ),
    }
    page = _html(_ask("Como faço X?"))
    assert "<ul><li><b>Passo um</b>: faça X" in page
    assert "<ol><li>Primeiro" in page
    assert "<p>Resumo direto" in page
