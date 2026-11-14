"""CLI de ingestão (python -m ingestion.cli) com Qdrant em memória e embeddings falsos."""

import json
import logging

import pytest
from qdrant_client import QdrantClient

from core.errors import RAGError, RerankerError
from ingestion import cli
from ingestion.embeddings import HashEmbedder
from retrieval.vector_store import QdrantStore
from tests.conftest import make_settings


class OfflineEmbedder(HashEmbedder):
    """Simula o Ollama fora do ar."""

    def ping(self) -> bool:
        return False


class FakeReranker:
    instances: list["FakeReranker"] = []

    def __init__(self, model_name: str, cache_dir: str, fail: bool = False) -> None:
        self.model_name = model_name
        self.fail = fail
        self.calls = 0
        FakeReranker.instances.append(self)

    def rerank(self, query, candidates):
        self.calls += 1
        if self.fail:
            raise RerankerError("sem internet para baixar o modelo")
        return candidates


@pytest.fixture
def env(monkeypatch):
    """Troca Qdrant, Ollama, reranker e logs reais por dublês; devolve o store em memória."""
    store = QdrantStore(QdrantClient(location=":memory:"), prefix="cli")
    state = {"store": store, "embedder_cls": HashEmbedder, "reranker_fail": False}

    monkeypatch.setattr(cli, "get_settings", lambda: make_settings())
    monkeypatch.setattr(cli, "setup_logging", lambda *args, **kwargs: None)
    monkeypatch.setattr(cli, "build_store", lambda settings: store)
    monkeypatch.setattr(cli, "build_embedder", lambda settings: state["embedder_cls"]())
    monkeypatch.setattr(
        cli,
        "build_reranker",
        lambda s: FakeReranker(s.reranker_model, s.reranker_cache_dir, fail=state["reranker_fail"]),
    )
    monkeypatch.setattr(cli.time, "sleep", lambda _: None)
    FakeReranker.instances = []
    return state


def _printed_stats(capsys) -> list[dict]:
    return [json.loads(line) for line in capsys.readouterr().out.splitlines() if line.strip()]


def test_main_indexes_all_strategies(env, capsys):
    assert cli.main(["--strategy", "all"]) == 0

    stats = _printed_stats(capsys)
    assert [s["strategy"] for s in stats] == ["fixed", "recursive"]
    assert all(s["chunks"] > 0 and s["documents"] > 0 for s in stats)
    assert env["store"].count("fixed") > 0 and env["store"].count("recursive") > 0
    assert FakeReranker.instances == []  # sem --warmup-reranker não carrega o modelo


def test_main_skip_existing_only_indexes_missing_strategies(env, capsys, caplog):
    assert cli.main(["--strategy", "recursive"]) == 0
    capsys.readouterr()

    with caplog.at_level(logging.INFO, logger="rag.ingestion.cli"):
        assert cli.main(["--strategy", "all", "--skip-existing"]) == 0

    assert [s["strategy"] for s in _printed_stats(capsys)] == ["fixed"]
    skipped = [r for r in caplog.records if r.getMessage() == "index.skipped_existing"]
    assert [r.strategy for r in skipped] == ["recursive"]


def test_skip_existing_reindexes_when_corpus_changes(env, tmp_path, capsys, caplog):
    docs = tmp_path / "docs"
    docs.mkdir()
    (docs / "a.md").write_text("# A\n\nTexto original sobre rotas.", encoding="utf-8")
    assert cli.main(["--strategy", "recursive", "--docs-dir", str(docs)]) == 0
    first = _printed_stats(capsys)[0]["fingerprint"]

    # Mesma base: pula
    assert cli.main(["--strategy", "recursive", "--docs-dir", str(docs), "--skip-existing"]) == 0
    assert _printed_stats(capsys) == []

    # Base alterada: reindexa mesmo com --skip-existing
    (docs / "b.md").write_text("# B\n\nDocumento novo sobre fixtures.", encoding="utf-8")
    with caplog.at_level(logging.INFO, logger="rag.ingestion.cli"):
        assert (
            cli.main(["--strategy", "recursive", "--docs-dir", str(docs), "--skip-existing"]) == 0
        )
    stats = _printed_stats(capsys)
    assert stats and stats[0]["documents"] == 2 and stats[0]["fingerprint"] != first
    assert any(r.getMessage() == "index.outdated_reindexing" for r in caplog.records)
    assert env["store"].stored_fingerprint("recursive") == stats[0]["fingerprint"]


def test_main_returns_1_when_docs_dir_does_not_exist(env, tmp_path, capsys):
    assert cli.main(["--strategy", "fixed", "--docs-dir", str(tmp_path / "nada")]) == 1
    assert capsys.readouterr().out == ""
    assert env["store"].count("fixed") == 0


def test_main_returns_1_when_ollama_does_not_answer(env, caplog):
    env["embedder_cls"] = OfflineEmbedder
    with caplog.at_level(logging.ERROR, logger="rag.ingestion.cli"):
        assert cli.main(["--strategy", "fixed", "--wait=-1"]) == 1
    failed = [r for r in caplog.records if r.getMessage() == "index.failed"]
    assert failed and "Ollama" in failed[0].error


def test_main_warms_up_reranker(env, caplog):
    with caplog.at_level(logging.INFO, logger="rag.ingestion.cli"):
        assert cli.main(["--strategy", "fixed", "--warmup-reranker"]) == 0
    assert len(FakeReranker.instances) == 1 and FakeReranker.instances[0].calls == 1
    assert any(r.getMessage() == "reranker.ready" for r in caplog.records)


def test_reranker_warmup_failure_is_not_fatal(env, caplog):
    env["reranker_fail"] = True
    with caplog.at_level(logging.WARNING, logger="rag.ingestion.cli"):
        assert cli.main(["--strategy", "fixed", "--warmup-reranker"]) == 0
    assert any(r.getMessage() == "reranker.warmup_failed" for r in caplog.records)


def test_wait_for_retries_until_service_answers(monkeypatch):
    monkeypatch.setattr(cli.time, "sleep", lambda _: None)
    answers = iter([False, False, True])
    cli.wait_for(lambda: next(answers), "Qdrant", timeout_s=60)
    assert next(answers, "esgotado") == "esgotado"


def test_wait_for_raises_after_timeout(monkeypatch):
    monkeypatch.setattr(cli.time, "sleep", lambda _: None)
    with pytest.raises(RAGError, match="Qdrant não respondeu"):
        cli.wait_for(lambda: False, "Qdrant", timeout_s=-1)
