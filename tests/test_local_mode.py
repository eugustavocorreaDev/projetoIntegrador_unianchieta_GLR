"""Modo de desenvolvimento sem Docker nem Ollama: Qdrant em disco, hashing e mock extrativo."""

import json
import threading

from core.factory import build_embedder, build_llm, build_store, collection_prefix
from core.pipeline import build_pipeline
from core.schemas import Chunk, RetrievedChunk
from generation.grounding import ground_answer
from generation.llm import OllamaLLM
from generation.mock_llm import HEADER, ExtractiveMockLLM
from generation.prompts import REFUSAL_MESSAGE, build_user_prompt, parse_user_prompt
from ingestion import cli
from ingestion.embeddings import HashEmbedder, OllamaEmbedder
from retrieval.vector_store import QdrantStore, SerializedClient
from tests.conftest import DATASET, make_pipeline, make_settings


def _chunks(*texts: str) -> list[RetrievedChunk]:
    return [
        RetrievedChunk(Chunk(f"id{i}", t, f"doc{i}.md", f"Seção {i}", i, "recursive"), 1.0)
        for i, t in enumerate(texts, start=1)
    ]


def test_parse_user_prompt_inverts_build_user_prompt():
    chunks = _chunks("Primeiro trecho.\n\nCom parágrafo.", "Segundo trecho [1] com colchetes.")
    question, blocks = parse_user_prompt(build_user_prompt("Qual o trecho?", chunks))
    assert question == "Qual o trecho?"
    assert blocks == [
        (1, "doc1.md › Seção 1", "Primeiro trecho.\n\nCom parágrafo."),
        (2, "doc2.md › Seção 2", "Segundo trecho [1] com colchetes."),
    ]


def test_mock_llm_organizes_cited_topics():
    chunks = _chunks(
        "O CORSMiddleware permite apenas o método GET por padrão. Outra frase qualquer.",
        "Texto sobre tarefas em segundo plano.",
    )
    raw = ExtractiveMockLLM().generate(
        "", build_user_prompt("Quais métodos o CORSMiddleware permite?", chunks)
    )
    assert raw.splitlines()[0] == HEADER
    assert (
        "- **Seção 1**: O CORSMiddleware permite apenas o método GET por padrão. "
        "Outra frase qualquer. [1]"
    ) in raw
    assert "[2]" not in raw  # o trecho sobre tarefas não cobre a pergunta
    assert not ground_answer(raw, chunks).refused


def test_mock_llm_shows_code_from_top_chunk():
    chunks = _chunks(
        "Use o TestClient para testar a API.\n\n```python\nclient = TestClient(app)\n```"
    )
    raw = ExtractiveMockLLM().generate("", build_user_prompt("Como testar com TestClient?", chunks))
    assert "Exemplo de código do trecho [1]:" in raw
    assert "```python\nclient = TestClient(app)\n```" in raw
    assert "- **Seção 1**: Use o TestClient para testar a API. [1]" in raw


def test_mock_llm_refuses_when_no_chunk_covers_the_question():
    chunks = _chunks("O CORSMiddleware permite apenas o método GET por padrão.")
    assert (
        ExtractiveMockLLM().generate(
            "", build_user_prompt("Como uso GraphQL com Strawberry?", chunks)
        )
        == REFUSAL_MESSAGE
    )
    assert ExtractiveMockLLM().generate("", "prompt sem formato") == REFUSAL_MESSAGE


def test_factory_respects_modes(tmp_path):
    official = make_settings()
    assert isinstance(build_embedder(official), OllamaEmbedder)
    assert isinstance(build_llm(official), OllamaLLM)
    assert collection_prefix(official) == "techdocs"

    dev = make_settings(
        llm_mode="mock", embed_mode="hash", qdrant_mode="local", qdrant_path=tmp_path / "q"
    )
    assert isinstance(build_embedder(dev), HashEmbedder)
    assert isinstance(build_llm(dev), ExtractiveMockLLM)
    assert collection_prefix(dev) == "techdocs_hash"
    store = build_store(dev)
    assert isinstance(store.client, SerializedClient) and store.ping()
    store.client.close()


def test_local_disk_mode_end_to_end_and_persists(tmp_path):
    """Indexa em disco, responde com citação, recusa fora do escopo e reabre o índice."""
    settings = make_settings(
        llm_mode="mock",
        embed_mode="hash",
        qdrant_mode="local",
        qdrant_path=tmp_path / "q",
        retrieval_mode="hybrid",
    )
    pipeline = build_pipeline(settings)
    pipeline.ingest()

    answer = pipeline.ask("Como substituo uma dependência real por uma versão de teste?")
    assert not answer.refused
    assert "testes.md" in {c.source for c in answer.citations}

    refusal = pipeline.ask("Qual é a receita de um bolo de cenoura?")
    assert refusal.refused and refusal.answer == REFUSAL_MESSAGE

    health = pipeline.health()
    assert (
        health["status"] == "ok"
        and health["llm_mode"] == "mock"
        and health["qdrant_mode"] == "local"
    )
    chunks = health["collections"]["recursive"]
    pipeline.retriever.store.client.close()

    reopened = build_store(settings)
    assert reopened.count("recursive") == chunks  # sobreviveu ao fechamento
    reopened.client.close()


def test_mock_mode_answers_most_answerable_and_refuses_most_unanswerable():
    """Sanidade do modo de demonstração (não é avaliação): a tela mostra os dois caminhos."""
    pipeline = make_pipeline(llm=ExtractiveMockLLM(), retrieval_mode="hybrid")
    questions = json.loads(DATASET.read_text(encoding="utf-8"))["questions"]
    refused = {q["id"]: pipeline.ask(q["question"]).refused for q in questions}
    answerable = [q["id"] for q in questions if q["answerable"]]
    unanswerable = [q["id"] for q in questions if not q["answerable"]]
    assert sum(not refused[i] for i in answerable) / len(answerable) >= 0.6
    assert sum(refused[i] for i in unanswerable) / len(unanswerable) >= 0.5


def test_serialized_client_runs_one_call_at_a_time():
    active, peak = [0], [0]
    lock = threading.Lock()

    class Slow:
        name = "fake"

        def call(self):
            with lock:
                active[0] += 1
                peak[0] = max(peak[0], active[0])
            threading.Event().wait(0.01)
            with lock:
                active[0] -= 1
            return "ok"

    client = SerializedClient(Slow())
    threads = [threading.Thread(target=client.call) for _ in range(8)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert peak[0] == 1
    assert client.name == "fake"


def test_cli_reports_locked_local_folder(monkeypatch, caplog):
    def locked(settings):
        raise RuntimeError("Storage folder .qdrant_local is already accessed by another instance")

    monkeypatch.setattr(cli, "get_settings", lambda: make_settings())
    monkeypatch.setattr(cli, "setup_logging", lambda *a, **k: None)
    monkeypatch.setattr(cli, "build_store", locked)
    assert cli.main(["--strategy", "fixed"]) == 1
    assert any("Pare a API" in getattr(r, "error", "") for r in caplog.records)


def test_from_path_creates_folder(tmp_path):
    store = QdrantStore.from_path(tmp_path / "novo" / "qdrant", "x")
    assert (tmp_path / "novo" / "qdrant").is_dir()
    store.client.close()
