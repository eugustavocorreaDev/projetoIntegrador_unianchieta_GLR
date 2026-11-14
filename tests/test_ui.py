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
DOCS = [
    {
        "source": "testes.md",
        "title": "Testes",
        "chars": 1200,
        "sections": 4,
        "chunks": {"fixed": 2, "recursive": 4},
    },
    {
        "source": "seguranca.md",
        "title": "Segurança",
        "chars": 900,
        "sections": 3,
        "chunks": {"fixed": 2, "recursive": 3},
    },
]
DOC_DETAIL = {
    "source": "testes.md",
    "title": "Testes",
    "path": "data/raw_docs/testes.md",
    "text": "# Testes\n\nUse o dicionário app.dependency_overrides.",
    "sections": ["Testes"],
    "strategy": "recursive",
    "chunks": [{"index": 0, "section": "Testes", "text": CHUNK["text"], "chars": 42}],
}
QUESTIONS = [
    {
        "id": "q01",
        "question": "Como sobrescrever uma dependência?",
        "answerable": True,
        "expected_source": "testes.md",
        "expected_snippets": ["dependency_overrides"],
    },
    {
        "id": "q02",
        "question": "Como proteger uma rota?",
        "answerable": True,
        "expected_source": "seguranca.md",
        "expected_snippets": ["OAuth2PasswordBearer"],
    },
    {"id": "u01", "question": "Como configurar GraphQL?", "answerable": False},
]


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
        "mode": "hybrid",
        "mode_effective": "hybrid",
        "latency_ms": 1234.0,
        "timings_ms": {"retrieval": 100.0, "generation": 1100.0},
    }


def _retrieval_rows(ids: list[str]) -> list[dict]:
    by_id = {q["id"]: q for q in QUESTIONS}
    return [
        {
            "id": qid,
            "question": by_id[qid]["question"],
            "expected_source": by_id[qid]["expected_source"],
            "rank": 1 if qid == "q01" else None,
            "hit": qid == "q01",
            "retrieved_sources": ["testes.md"],
            "strategy": "recursive",
            "mode_effective": "hybrid_rerank",
            "latency_ms": 10.0,
        }
        for qid in ids
    ]


@pytest.fixture
def fake_api(monkeypatch):
    """API simulada: responde cada endpoint pelo caminho e guarda o que foi enviado."""
    state = {"answer": _answer(False), "fail": False, "health": HEALTH, "posts": []}

    def fake_get(url, **kwargs):
        path = url.removeprefix("http://localhost:8000")
        if path == "/health":
            body = state["health"]
        elif path == "/documents":
            body = DOCS
        elif path.startswith("/documents/"):
            body = DOC_DETAIL
        elif path == "/validation/questions":
            body = QUESTIONS
        else:
            return httpx.Response(404, json={"detail": "?"}, request=httpx.Request("GET", url))
        return httpx.Response(200, json=body, request=httpx.Request("GET", url))

    def fake_post(url, json=None, **kwargs):
        state["posts"].append((url, json))
        if state["fail"]:
            raise httpx.ConnectError("recusado")
        if url.endswith("/validation/retrieval"):
            body = {"rows": _retrieval_rows(json["ids"])}
        elif json and json.get("question") == "Como configurar GraphQL?":
            body = _answer(True)
        else:
            body = state["answer"]
        return httpx.Response(200, json=body, request=httpx.Request("POST", url))

    monkeypatch.setattr(httpx, "get", fake_get)
    monkeypatch.setattr(httpx, "post", fake_post)
    st.cache_data.clear()  # as chamadas GET são cacheadas entre execuções no mesmo processo
    return state


def _app() -> AppTest:
    at = AppTest.from_file(APP, default_timeout=30)
    at.run()
    return at


def _ask(question: str) -> AppTest:
    at = _app()
    at.chat_input[0].set_value(question).run()  # equivale a digitar e teclar Enter
    return at


def _html(at: AppTest) -> str:
    return "\n".join(m.value for m in at.markdown)


def _button(at: AppTest, text: str):
    return next(b for b in at.button if text in b.label)


def test_enter_in_chat_input_sends_the_question(fake_api):
    at = _ask("Como sobrescrever uma dependência?")
    assert not at.exception
    url, payload = fake_api["posts"][-1]
    assert url.endswith("/ask")
    assert payload["question"] == "Como sobrescrever uma dependência?"
    assert "image_base64" not in payload
    assert "Você perguntou: <b>Como sobrescrever uma dependência?</b>" in _html(at)


def test_renders_answer_with_citation_badges_and_sources(fake_api):
    at = _ask("Como sobrescrever uma dependência?")
    page = _html(at)
    assert "Resposta fundamentada" in page
    assert '<span class="cite">1</span>' in page
    assert "<code>app.dependency_overrides</code>" in page
    assert "data/raw_docs/testes.md" in page  # mostra onde o arquivo citado está
    assert any("[1] testes.md" in e.label for e in at.expander)


def test_renders_refusal_and_explains_nearest_chunks(fake_api):
    fake_api["answer"] = _answer(True)
    at = _ask("Como faz um ovo frito?")
    assert not at.exception
    page = _html(at)
    assert "Recusa anti-alucinação acionada" in page
    assert "descartada" in page  # explica o motivo ungrounded_answer
    assert "Trechos mais próximos encontrados" in page
    assert "Todos os trechos enviados ao modelo" not in page


def test_shows_error_when_api_is_down(fake_api):
    fake_api["fail"] = True
    at = _ask("Pergunta qualquer")
    assert not at.exception
    assert at.error and "Não foi possível falar com a API" in at.error[0].value


def test_example_button_sends_question_directly(fake_api):
    at = _app()
    _button(at, "GraphQL").click()
    at.run()
    assert fake_api["posts"][-1][1]["question"] == "Como configurar GraphQL no FastAPI?"


def test_short_question_shows_warning_and_is_not_sent(fake_api):
    at = _ask("oi")
    assert at.warning and "pelo menos 3" in at.warning[0].value
    assert fake_api["posts"] == []


def test_only_search_toggle_calls_search(fake_api):
    at = _app()
    at.toggle[0].set_value(True).run()
    at.chat_input[0].set_value("dependency_overrides").run()
    assert fake_api["posts"][-1][0].endswith("/search")


def test_model_output_is_html_escaped(fake_api):
    fake_api["answer"] = {**_answer(False), "answer": "<script>alert(1)</script> ok [1]"}
    at = _ask("teste de escape")
    assert "<script>" not in _html(at)
    assert "&lt;script&gt;" in _html(at)


def test_image_text_is_shown_when_api_read_a_print(fake_api):
    fake_api["answer"] = {**_answer(False), "image_text": "ImportError: cannot import name"}
    at = _ask("O que é este erro?")
    assert any("Texto lido do print" in e.label for e in at.expander)
    assert any("ImportError" in c.value for c in at.code)


def test_demo_banner_only_in_mock_mode(fake_api):
    at = _app()
    assert "Modo de Visualização (Mock)" not in _html(at)

    fake_api["health"] = {**HEALTH, "llm_mode": "mock", "embed_mode": "hash"}
    st.cache_data.clear()
    at = _app()
    assert "Modo de Visualização (Mock)" in _html(at)
    assert "scripts\\instalar.ps1" in _html(at)
    assert any("desativada no Modo de Visualização" in c.value for c in at.caption)


def test_documents_tab_lists_files_and_opens_one(fake_api):
    at = _app()
    assert not at.exception
    metrics = {m.label: m.value for m in at.metric}
    assert metrics["Documentos"] == "2"
    assert metrics["Chunks (recursivo)"] == "7"
    assert "data/raw_docs/testes.md" in _html(at)  # caminho do documento aberto
    at.radio[0].set_value("Chunks").run()
    assert any("#0 · Testes" in e.label for e in at.expander)
    at.radio[0].set_value("Perguntas de teste").run()
    _button(at, "Testar a recuperação destas perguntas").click()
    at.run()
    assert any("1/1" in s.value for s in at.success)


def test_validation_tab_measures_recall(fake_api):
    at = _app()
    _button(at, "Rodar as 2 perguntas com resposta").click()
    at.run()
    assert not at.exception
    metrics = {m.label: m.value for m in at.metric}
    assert metrics["Recall@5"] == "50%"
    assert metrics["Acertos"] == "1/2"
    url, payload = next(p for p in fake_api["posts"] if p[0].endswith("/validation/retrieval"))
    assert payload["ids"] == ["q01", "q02"] and payload["top_k"] == 5
    assert payload["mode"] == "hybrid"  # padrão recomendado pela medição (ADR 002)


def test_validation_tab_checks_answers_and_refusals(fake_api):
    at = _app()
    _button(at, "perguntas com o LLM").click()
    at.run()
    assert not at.exception
    metrics = {m.label: m.value for m in at.metric}
    # q01 respondida citando testes.md; q02 respondida, mas sem citar seguranca.md
    assert metrics["Respostas fundamentadas"] == "1/2 (50%)"
    assert metrics["Recusas corretas"] == "1/1 (100%)"


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
