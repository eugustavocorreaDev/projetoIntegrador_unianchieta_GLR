import json

import httpx
import pytest

from core.errors import EmbeddingError, LLMError
from generation.llm import OllamaLLM
from ingestion.embeddings import OllamaEmbedder


def test_embedder_applies_prefixes_and_batches():
    seen: list[list[str]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        assert request.url.path == "/api/embed"
        assert body["model"] == "nomic-embed-text"
        seen.append(body["input"])
        return httpx.Response(200, json={"embeddings": [[0.1, 0.2] for _ in body["input"]]})

    embedder = OllamaEmbedder(
        "http://ollama:11434/",
        "nomic-embed-text",
        query_prefix="search_query: ",
        document_prefix="search_document: ",
        batch_size=2,
        transport=httpx.MockTransport(handler),
    )
    assert len(embedder.embed_documents(["a", "b", "c"])) == 3
    assert embedder.embed_query("pergunta") == [0.1, 0.2]
    assert seen == [
        ["search_document: a", "search_document: b"],
        ["search_document: c"],
        ["search_query: pergunta"],
    ]


def test_embedder_missing_model_suggests_pull():
    transport = httpx.MockTransport(
        lambda r: httpx.Response(404, json={"error": "model not found"})
    )
    embedder = OllamaEmbedder("http://x", "nomic-embed-text", transport=transport)
    with pytest.raises(EmbeddingError, match="ollama pull nomic-embed-text"):
        embedder.embed_query("oi")


def test_embedder_connection_error():
    def handler(request):
        raise httpx.ConnectError("recusado", request=request)

    embedder = OllamaEmbedder("http://x", "m", transport=httpx.MockTransport(handler))
    with pytest.raises(EmbeddingError, match="indisponível"):
        embedder.embed_documents(["a"])
    assert embedder.ping() is False


def test_embedder_rejects_wrong_size_response():
    transport = httpx.MockTransport(lambda r: httpx.Response(200, json={"embeddings": []}))
    with pytest.raises(EmbeddingError):
        OllamaEmbedder("http://x", "m", transport=transport).embed_query("a")


def test_llm_sends_deterministic_options_and_returns_content():
    captured = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured.update(json.loads(request.content))
        return httpx.Response(
            200, json={"message": {"role": "assistant", "content": "  Resposta [1]. "}}
        )

    llm = OllamaLLM(
        "http://x", "qwen2.5:3b", seed=42, num_ctx=4096, transport=httpx.MockTransport(handler)
    )
    assert llm.generate("sistema", "usuário") == "Resposta [1]."
    assert captured["stream"] is False
    assert captured["options"] == {
        "temperature": 0.0,
        "num_ctx": 4096,
        "num_predict": 512,
        "seed": 42,
    }
    assert [m["role"] for m in captured["messages"]] == ["system", "user"]


@pytest.mark.parametrize(
    "handler,match",
    [
        (lambda r: httpx.Response(404, json={"error": "not found"}), "ollama pull"),
        (lambda r: httpx.Response(500, text="boom"), "500"),
    ],
)
def test_llm_http_errors(handler, match):
    llm = OllamaLLM("http://x", "qwen2.5:3b", transport=httpx.MockTransport(handler))
    with pytest.raises(LLMError, match=match):
        llm.generate("s", "u")


def test_llm_timeout():
    def handler(request):
        raise httpx.ReadTimeout("lento", request=request)

    llm = OllamaLLM("http://x", "m", transport=httpx.MockTransport(handler))
    with pytest.raises(LLMError, match="tempo limite"):
        llm.generate("s", "u")
