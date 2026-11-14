import pytest

from core.schemas import Document
from ingestion.chunking import (
    FixedSizeChunker,
    RecursiveSectionChunker,
    _split_oversized,
    get_chunker,
)
from ingestion.markdown import split_sections


@pytest.mark.parametrize("size,overlap", [(300, 50), (800, 120)])
def test_fixed_chunks_respect_size_and_overlap(documents, size, overlap):
    chunker = FixedSizeChunker(size, overlap)
    for doc in documents:
        chunks = chunker.split(doc)
        assert chunks
        assert all(len(c.text) <= size for c in chunks)
        for prev, nxt in zip(chunks, chunks[1:], strict=False):
            # O começo do próximo chunk aparece no fim do anterior (sobreposição)
            assert nxt.text[:20] in prev.text


def test_fixed_chunks_cover_every_word(documents):
    chunker = FixedSizeChunker(300, 50)
    for doc in documents:
        joined = " ".join(c.text for c in chunker.split(doc))
        for word in doc.text.split():
            assert word in joined


def test_recursive_chunks_stay_inside_one_section(documents):
    chunker = RecursiveSectionChunker(400)
    for doc in documents:
        bodies = {s.path_str or doc.title: s.body for s in split_sections(doc.text)}
        for chunk in chunker.split(doc):
            assert len(chunk.text) <= 400
            assert chunk.section in bodies
            # Cada chunk é composto de blocos daquela seção
            first_line = chunk.text.splitlines()[0]
            assert first_line in bodies[chunk.section]


def test_recursive_sections_use_heading_paths(documents):
    doc = next(d for d in documents if d.source == "dependencias.md")
    sections = {c.section for c in get_chunker("recursive").split(doc)}
    assert "Dependências > Dependências com yield" in sections
    assert not any("Executado ao final" in s for s in sections)


def test_chunk_ids_are_deterministic_and_unique(documents):
    first = [c.id for d in documents for c in get_chunker("fixed").split(d)]
    second = [c.id for d in documents for c in get_chunker("fixed").split(d)]
    assert first == second
    assert len(set(first)) == len(first)
    recursive = {c.id for d in documents for c in get_chunker("recursive").split(d)}
    assert recursive.isdisjoint(first)


def test_fixed_section_metadata_follows_position():
    text = "# T\n\n" + "alfa " * 100 + "\n\n## Seção B\n\n" + "beta " * 100
    chunks = FixedSizeChunker(200, 20).split(Document("x.md", "T", text))
    assert chunks[0].section == "T"
    assert chunks[-1].section == "T > Seção B"


def test_split_oversized_keeps_punctuation():
    text = "Primeira frase longa aqui. Segunda frase longa aqui. Terceira frase longa aqui."
    pieces = _split_oversized(text, 40, (". ", " "))
    assert all(len(p) <= 40 for p in pieces)
    assert pieces[0].endswith(".")
    assert " ".join(pieces).replace("  ", " ") == text


def test_invalid_configuration():
    with pytest.raises(ValueError):
        get_chunker("semantico")
    with pytest.raises(ValueError):
        FixedSizeChunker(100, 100)
    with pytest.raises(ValueError):
        RecursiveSectionChunker(0)
