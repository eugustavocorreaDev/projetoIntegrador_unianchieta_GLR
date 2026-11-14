import pytest

from core.errors import CollectionNotFoundError, RerankerError
from core.schemas import Chunk, RetrievedChunk
from retrieval.bm25 import BM25Index, tokenize
from retrieval.fusion import reciprocal_rank_fusion
from retrieval.reranker import FlashRankReranker
from tests.conftest import OverlapReranker, make_pipeline


def _chunk(cid: str, text: str, source: str = "x.md") -> Chunk:
    return Chunk(id=cid, text=text, source=source, section="", chunk_index=0, strategy="t")


def test_tokenize_normalizes_accents_stopwords_and_identifiers():
    tokens = tokenize("Como usar a Dependência dependency_overrides?")
    assert "dependencia" in tokens
    assert "dependency_overrides" in tokens and "overrides" in tokens
    assert "como" not in tokens and "a" not in tokens


def test_bm25_prefers_documents_with_rare_terms():
    chunks = [
        _chunk("1", "rotas e parâmetros de caminho"),
        _chunk("2", "use dependency_overrides para trocar dependências nos testes"),
        _chunk("3", "rotas rotas rotas"),
    ]
    index = BM25Index(chunks)
    results = index.search("dependency_overrides testes", limit=3)
    assert results[0].chunk.id == "2"
    assert all(r.bm25_score > 0 for r in results)
    assert index.search("palavrainexistente", limit=3) == []


def test_rrf_rewards_items_present_in_both_lists():
    a, b, c = _chunk("a", "a"), _chunk("b", "b"), _chunk("c", "c")
    vector = [RetrievedChunk(a, 0.9, vector_score=0.9), RetrievedChunk(b, 0.8, vector_score=0.8)]
    lexical = [RetrievedChunk(c, 5.0, bm25_score=5.0), RetrievedChunk(b, 4.0, bm25_score=4.0)]
    fused = reciprocal_rank_fusion([vector, lexical], k=60)
    assert fused[0].chunk.id == "b"
    assert fused[0].vector_score == 0.8 and fused[0].bm25_score == 4.0
    assert {r.chunk.id for r in fused} == {"a", "b", "c"}
    assert len(reciprocal_rank_fusion([vector, lexical], limit=2)) == 2


@pytest.mark.parametrize("mode", ["vector", "bm25", "hybrid", "hybrid_rerank"])
@pytest.mark.parametrize("strategy", ["fixed", "recursive"])
def test_all_modes_find_the_expected_document(indexed_pipeline, strategy, mode):
    chunks, _, effective, _ = indexed_pipeline.search(
        "Como usar app.dependency_overrides para trocar uma dependência nos testes?",
        strategy,
        mode,
        5,
    )
    assert effective == mode
    assert 1 <= len(chunks) <= 5
    assert "testes.md" in [c.chunk.source for c in chunks[:3]]


def test_hybrid_rerank_falls_back_to_hybrid_when_reranker_fails():
    class BrokenReranker:
        def rerank(self, query, candidates):
            raise RerankerError("modelo indisponível")

    pipeline = make_pipeline(reranker=BrokenReranker())
    chunks, _, effective, _ = pipeline.search(
        "dependências com yield", "recursive", "hybrid_rerank", 3
    )
    assert effective == "hybrid"
    assert chunks


def test_hybrid_rerank_without_reranker_falls_back():
    pipeline = make_pipeline(reranker=None)
    _, _, effective, _ = pipeline.search("CORS", "recursive", "hybrid_rerank", 3)
    assert effective == "hybrid"


def test_missing_collection_raises_clear_error():
    pipeline = make_pipeline(ingest=False)
    with pytest.raises(CollectionNotFoundError):
        pipeline.search("qualquer coisa", "recursive", "bm25", 3)
    with pytest.raises(CollectionNotFoundError):
        pipeline.search("qualquer coisa", "recursive", "vector", 3)


def test_flashrank_wrapper_maps_scores_and_wraps_errors():
    class FakeRanker:
        def rerank(self, request):
            # Inverte a ordem e devolve pontuações decrescentes
            n = len(request.passages)
            return [{"id": p["id"], "score": float(i)} for i, p in enumerate(request.passages)][
                ::-1
            ][:n]

    candidates = [RetrievedChunk(_chunk(str(i), f"texto {i}"), 0.0) for i in range(3)]
    reranked = FlashRankReranker("m", "/tmp", ranker=FakeRanker()).rerank("q", candidates)
    assert [r.chunk.id for r in reranked] == ["2", "1", "0"]
    assert reranked[0].rerank_score == 2.0 and "rerank" in reranked[0].stages

    class Exploding:
        def rerank(self, request):
            raise RuntimeError("onnx")

    with pytest.raises(RerankerError):
        FlashRankReranker("m", "/tmp", ranker=Exploding()).rerank("q", candidates)
    assert FlashRankReranker("m", "/tmp", ranker=Exploding()).rerank("q", []) == []


def test_overlap_reranker_reorders(indexed_pipeline):
    chunks, _, _, _ = indexed_pipeline.search(
        "CORSMiddleware allow_credentials", "recursive", "hybrid", 10
    )
    reranked = OverlapReranker().rerank("CORSMiddleware allow_credentials", chunks)
    assert reranked[0].chunk.source == "erros-e-middleware.md"


def test_flashrank_load_failure_is_remembered(monkeypatch):
    """Um download que falhou não é repetido a cada pergunta, só depois do intervalo."""
    import sys
    import types

    attempts = []

    class BrokenRanker:
        def __init__(self, **kwargs):
            attempts.append(kwargs)
            raise ConnectionError("IncompleteRead")

    monkeypatch.setitem(sys.modules, "flashrank", types.SimpleNamespace(Ranker=BrokenRanker))
    clock = [1000.0]
    monkeypatch.setattr("retrieval.reranker.time.monotonic", lambda: clock[0])
    candidates = [RetrievedChunk(_chunk("1", "texto"), 0.0)]
    reranker = FlashRankReranker("m", "/tmp")

    for _ in range(3):
        with pytest.raises(RerankerError):
            reranker.rerank("q", candidates)
    assert len(attempts) == 1

    clock[0] += FlashRankReranker.retry_after_s + 1
    with pytest.raises(RerankerError, match="Falha ao carregar"):
        reranker.rerank("q", candidates)
    assert len(attempts) == 2
