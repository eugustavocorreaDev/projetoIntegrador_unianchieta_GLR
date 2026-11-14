"""Perguntas com print: validação da imagem, cliente do modelo de visão, pipeline e API."""

import base64
import json

import httpx
import pytest
from fastapi.testclient import TestClient

from api.dependencies import get_pipeline
from api.main import app
from core.config import get_settings
from core.errors import InvalidInputError, LLMError, ServiceUnavailableError
from core.factory import build_image_reader
from core.pipeline import compose_query
from generation.vision import VISION_PROMPT, OllamaImageReader, decode_image
from tests.conftest import FakeImageReader, FakeLLM, make_pipeline, make_settings

PNG = base64.b64encode(b"\x89PNG\r\n\x1a\n" + b"\x00" * 32).decode()
JPEG = base64.b64encode(b"\xff\xd8\xff\xe0" + b"\x00" * 32).decode()
WEBP = base64.b64encode(b"RIFF\x00\x00\x00\x00WEBPVP8 " + b"\x00" * 16).decode()
GIF = base64.b64encode(b"GIF89a" + b"\x00" * 32).decode()
MB = 1024 * 1024


@pytest.mark.parametrize(("data", "fmt"), [(PNG, "png"), (JPEG, "jpeg"), (WEBP, "webp")])
def test_decode_image_accepts_supported_formats(data, fmt):
    assert decode_image(data, MB) == (data, fmt)


def test_decode_image_strips_data_url_prefix():
    assert decode_image(f"data:image/png;base64,{PNG}", MB) == (PNG, "png")


@pytest.mark.parametrize(
    ("data", "message"),
    [
        ("isto não é base64!", "base64"),
        ("", "vazia"),
        (GIF, "não suportado"),
        (base64.b64encode(b"\x89PNG\r\n\x1a\n" + b"\x00" * 2048).decode(), "limite"),
    ],
)
def test_decode_image_rejects_bad_input(data, message):
    with pytest.raises(InvalidInputError, match=message):
        decode_image(data, max_bytes=1024)


def test_ollama_image_reader_sends_image_and_prompt():
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen.update(json.loads(request.content))
        return httpx.Response(200, json={"message": {"content": "  erro 422  "}})

    reader = OllamaImageReader(
        "http://ollama", "qwen2.5vl:3b", transport=httpx.MockTransport(handler)
    )
    assert reader.read(PNG) == "erro 422"
    assert seen["model"] == "qwen2.5vl:3b"
    assert seen["messages"][0]["images"] == [PNG]
    assert seen["messages"][0]["content"] == VISION_PROMPT
    assert seen["options"]["temperature"] == 0.0


@pytest.mark.parametrize(
    ("handler", "message"),
    [
        (lambda r: httpx.Response(404, json={"error": "not found"}), "ollama pull qwen2.5vl:3b"),
        (lambda r: httpx.Response(500, text="falhou"), "500"),
    ],
)
def test_ollama_image_reader_errors(handler, message):
    reader = OllamaImageReader("http://o", "qwen2.5vl:3b", transport=httpx.MockTransport(handler))
    with pytest.raises(LLMError, match=message):
        reader.read(PNG)


def test_ollama_image_reader_timeout():
    def handler(request):
        raise httpx.ReadTimeout("lento", request=request)

    reader = OllamaImageReader("http://o", "m", transport=httpx.MockTransport(handler))
    with pytest.raises(LLMError, match="tempo limite"):
        reader.read(PNG)


def test_factory_disables_vision_in_mock_mode():
    assert build_image_reader(make_settings(llm_mode="mock")) is None
    reader = build_image_reader(make_settings(vision_model="granite3.2-vision"))
    assert isinstance(reader, OllamaImageReader) and reader.model == "granite3.2-vision"


def test_compose_query():
    assert compose_query("  Pergunta?  ", None) == "Pergunta?"
    composed = compose_query("O que é isto?", "ImportError")
    assert composed.startswith("O que é isto?") and composed.endswith("ImportError")
    assert compose_query("", "ImportError").startswith("O que a documentação diz")


def test_pipeline_puts_image_text_in_retrieval_and_prompt():
    llm, reader = FakeLLM(), FakeImageReader("app.dependency_overrides")
    result = make_pipeline(llm=llm, image_reader=reader).ask("Como uso isto?", image_b64=PNG)
    assert reader.calls == [PNG]
    assert result.image_text == "app.dependency_overrides"
    assert "image" in result.timings_ms
    assert "Texto lido da imagem enviada:\napp.dependency_overrides" in llm.calls[0][1]
    assert result.retrieved[0].chunk.source == "testes.md"  # o texto do print guiou a busca


def test_pipeline_without_vision_reader_is_unavailable():
    with pytest.raises(ServiceUnavailableError, match="Modo de Visualização"):
        make_pipeline(ingest=False).read_image(PNG)


def test_pipeline_rejects_unreadable_image():
    pipeline = make_pipeline(ingest=False, image_reader=FakeImageReader(""))
    with pytest.raises(InvalidInputError, match="não conseguiu ler"):
        pipeline.read_image(PNG)


@pytest.fixture
def client_factory():
    def factory(pipeline):
        app.dependency_overrides[get_pipeline] = lambda: pipeline
        return TestClient(app)

    yield factory
    app.dependency_overrides = {}
    get_settings.cache_clear()


def test_api_ask_with_image_only(client_factory):
    pipeline = make_pipeline(image_reader=FakeImageReader())
    response = client_factory(pipeline).post("/ask", json={"image_base64": PNG})
    assert response.status_code == 200
    assert response.json()["image_text"] == "app.dependency_overrides"


def test_api_search_with_image(client_factory):
    pipeline = make_pipeline(image_reader=FakeImageReader())
    body = client_factory(pipeline).post(
        "/search", json={"question": "o que é isto?", "image_base64": PNG}
    )
    assert body.status_code == 200
    assert body.json()["image_text"] == "app.dependency_overrides"


@pytest.mark.parametrize(
    ("payload", "status"),
    [
        ({"question": ""}, 422),  # sem pergunta e sem imagem
        ({"image_base64": GIF}, 422),  # formato não suportado
        ({"image_base64": "não é base64"}, 422),
    ],
)
def test_api_rejects_invalid_image_requests(client_factory, payload, status):
    pipeline = make_pipeline(ingest=False, image_reader=FakeImageReader())
    assert client_factory(pipeline).post("/ask", json=payload).status_code == status


def test_api_image_without_vision_model_returns_503(client_factory):
    response = client_factory(make_pipeline(ingest=False)).post(
        "/ask", json={"question": "o que é?", "image_base64": PNG}
    )
    assert response.status_code == 503
    assert "modelo de visão" in response.json()["detail"]
