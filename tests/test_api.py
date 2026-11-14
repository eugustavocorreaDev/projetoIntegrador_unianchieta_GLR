import pytest
from fastapi.testclient import TestClient

from api.dependencies import get_pipeline
from api.main import app
from core.config import get_settings
from core.errors import LLMError
from generation.prompts import REFUSAL_MESSAGE
from tests.conftest import FakeLLM, make_pipeline


@pytest.fixture
def client_factory():
    def factory(pipeline):
        app.dependency_overrides[get_pipeline] = lambda: pipeline
        return TestClient(app)

    yield factory
    app.dependency_overrides = {}
    get_settings.cache_clear()


def test_health(client_factory, indexed_pipeline):
    response = client_factory(indexed_pipeline).get("/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok" and body["qdrant"] and body["ollama"]


def test_ask_returns_answer_with_citations(client_factory, indexed_pipeline):
    response = client_factory(indexed_pipeline).post(
        "/ask",
        json={"question": "Como configurar o CORSMiddleware?", "strategy": "fixed", "top_k": 3},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["refused"] is False
    assert body["citations"][0]["id"] == 1
    assert body["strategy"] == "fixed" and body["mode"] == "hybrid"
    assert len(body["retrieved"]) == 3 and body["retrieved"][0]["rank"] == 1


def test_ask_refusal(client_factory):
    pipeline = make_pipeline(llm=FakeLLM(lambda s, u: REFUSAL_MESSAGE))
    body = client_factory(pipeline).post("/ask", json={"question": "Como usar WebSockets?"}).json()
    assert body["refused"] is True
    assert body["refusal_reason"] == "llm_refusal"
    assert body["citations"] == []


def test_search_does_not_call_llm(client_factory):
    llm = FakeLLM()
    pipeline = make_pipeline(llm=llm)
    response = client_factory(pipeline).post(
        "/search", json={"question": "BackgroundTasks add_task", "mode": "bm25"}
    )
    assert response.status_code == 200
    assert response.json()["retrieved"][0]["source"] == "tarefas-em-segundo-plano.md"
    assert llm.calls == []


@pytest.mark.parametrize(
    "payload",
    [
        {"question": "oi"},
        {"question": "pergunta válida", "mode": "magico"},
        {"question": "válida", "top_k": 50},
    ],
)
def test_validation_errors(client_factory, indexed_pipeline, payload):
    assert client_factory(indexed_pipeline).post("/ask", json=payload).status_code == 422


def test_llm_unavailable_returns_503(client_factory):
    def broken(system, user):
        raise LLMError("Ollama fora do ar")

    response = client_factory(make_pipeline(llm=FakeLLM(broken))).post(
        "/ask", json={"question": "Como usar CORS?"}
    )
    assert response.status_code == 503
    assert "Ollama" in response.json()["detail"]


def test_missing_collection_returns_409(client_factory):
    response = client_factory(make_pipeline(ingest=False)).post(
        "/ask", json={"question": "Como usar CORS?"}
    )
    assert response.status_code == 409
    assert "ingestion.cli" in response.json()["detail"]


def test_ingest_endpoint(client_factory):
    pipeline = make_pipeline(ingest=False)
    response = client_factory(pipeline).post("/ingest", json={"strategies": ["recursive"]})
    assert response.status_code == 200
    assert response.json()["results"][0]["strategy"] == "recursive"


def test_ingest_endpoint_can_be_disabled(client_factory, monkeypatch):
    monkeypatch.setenv("ENABLE_INGEST_ENDPOINT", "false")
    get_settings.cache_clear()
    response = client_factory(make_pipeline(ingest=False)).post("/ingest", json={})
    assert response.status_code == 403


def test_config_has_no_secrets(client_factory, indexed_pipeline):
    body = client_factory(indexed_pipeline).get("/config").json()
    assert "llm_model" in body
    assert not any("key" in k.lower() or "password" in k.lower() for k in body)


def test_openapi_documents_endpoints(client_factory, indexed_pipeline):
    paths = client_factory(indexed_pipeline).get("/openapi.json").json()["paths"]
    assert {"/ask", "/search", "/health", "/ingest", "/config"} <= set(paths)
