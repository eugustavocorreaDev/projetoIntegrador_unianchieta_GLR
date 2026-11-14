"""Abas "Documentos" e "Validação": endpoints que mostram a base e rodam o conjunto de teste."""

import pytest
from fastapi.testclient import TestClient

from api.dependencies import get_pipeline
from api.main import app
from core.config import get_settings
from core.errors import InvalidInputError, NotFoundError
from core.validation import check_retrieval, document_detail, load_validation_questions
from tests.conftest import DATASET, DOCS_DIR


@pytest.fixture
def client(indexed_pipeline):
    app.dependency_overrides[get_pipeline] = lambda: indexed_pipeline
    yield TestClient(app)
    app.dependency_overrides = {}
    get_settings.cache_clear()


def test_documents_list_matches_what_was_indexed(client, indexed_pipeline):
    docs = client.get("/documents").json()
    assert len(docs) == 20
    assert {"source", "title", "chars", "sections", "chunks"} <= set(docs[0])
    store = indexed_pipeline.retriever.store
    for strategy in ("fixed", "recursive"):
        # Os chunks mostrados na interface são exatamente os que estão no índice
        assert sum(d["chunks"][strategy] for d in docs) == store.count(strategy)


def test_document_detail_has_path_sections_and_chunks(client):
    detail = client.get("/documents/testes.md", params={"strategy": "fixed"}).json()
    assert detail["path"].endswith("data/raw_docs/testes.md")
    assert detail["strategy"] == "fixed"
    assert detail["sections"] and detail["chunks"]
    assert all(c["chars"] == len(c["text"]) for c in detail["chunks"])


@pytest.mark.parametrize("source", ["nao-existe.md", "../../.env", "..%2F..%2Fpyproject.toml"])
def test_document_outside_the_base_is_404(client, source):
    assert client.get(f"/documents/{source}").status_code == 404


def test_document_invalid_strategy_is_422(client):
    assert client.get("/documents/testes.md", params={"strategy": "magica"}).status_code == 422


def test_validation_questions_endpoint(client):
    questions = client.get("/validation/questions").json()
    assert len(questions) == 64
    assert sum(q["answerable"] for q in questions) == 50
    assert all(q["expected_snippets"] for q in questions if q["answerable"])


def test_validation_retrieval_endpoint(client):
    response = client.post(
        "/validation/retrieval", json={"ids": ["q01", "q02"], "mode": "bm25", "top_k": 5}
    )
    assert response.status_code == 200
    rows = response.json()["rows"]
    assert [r["id"] for r in rows] == ["q01", "q02"]
    for row in rows:
        assert row["hit"] == (row["rank"] is not None)
        assert len(row["retrieved_sources"]) <= 5


@pytest.mark.parametrize(
    ("ids", "message"), [(["q999"], "inexistentes"), (["u01"], "não tem resposta")]
)
def test_validation_retrieval_rejects_bad_ids(client, ids, message):
    response = client.post("/validation/retrieval", json={"ids": ids})
    assert response.status_code == 422
    assert message in response.json()["detail"]


def test_check_retrieval_uses_the_same_rule_as_the_official_eval(indexed_pipeline):
    questions = load_validation_questions(DATASET)
    answerable = [q["id"] for q in questions if q["answerable"]]
    rows = check_retrieval(indexed_pipeline, questions, answerable, "recursive", "bm25", 5)
    # Com BM25 e trechos literais, a maioria das 50 perguntas precisa achar o trecho esperado;
    # um valor baixo aqui indica dataset desalinhado com a base
    assert sum(r["hit"] for r in rows) / len(rows) >= 0.6


def test_domain_errors():
    with pytest.raises(NotFoundError):
        document_detail(DOCS_DIR, "inexistente.md", "recursive", 800, 120)
    with pytest.raises(InvalidInputError):
        document_detail(DOCS_DIR, "testes.md", "magica", 800, 120)
    with pytest.raises(NotFoundError):
        load_validation_questions(DOCS_DIR / "nao-existe.json")


def test_openapi_lists_new_endpoints(client):
    paths = client.get("/openapi.json").json()["paths"]
    assert {"/documents", "/documents/{source}", "/validation/questions"} <= set(paths)
    assert "/validation/retrieval" in paths
