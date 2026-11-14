from pathlib import Path

import pytest

from ingestion.loader import clean_markdown, load_document, load_documents
from ingestion.markdown import find_headings, split_blocks, split_sections
from tests.conftest import DOCS_DIR


def test_load_documents_reads_whole_corpus(documents):
    sources = {d.source for d in documents}
    assert len(documents) == 20
    assert "dependencias.md" in sources
    assert all("/" not in s or not s.startswith("/") for s in sources)


def test_front_matter_becomes_title_and_is_removed():
    doc = load_document(DOCS_DIR / "primeiros-passos.md", DOCS_DIR)
    assert doc.title == "Primeiros passos"
    assert not doc.text.startswith("---")
    assert "title:" not in doc.text


def test_title_falls_back_to_h1():
    doc = load_document(DOCS_DIR / "dependencias.md", DOCS_DIR)
    assert doc.title == "Dependências"


def test_comments_inside_code_blocks_are_not_headings():
    doc = load_document(DOCS_DIR / "primeiros-passos.md", DOCS_DIR)
    titles = [h.title for h in find_headings(doc.text)]
    assert "Instalação" in titles
    assert not any(t.startswith("Crie e ative") for t in titles)
    assert not any("operação de caminho" in t for t in titles)


def test_clean_markdown_removes_noise_but_keeps_code_and_placeholders():
    raw = (
        "<!-- comentário -->\n"
        "Use <abbr title='Interface'>API</abbr> com `Bearer <token>`.\n"
        "{* ../../docs_src/app.py *}\n"
        "/// tip | Dica\n"
        "Texto da dica.\n"
        "///\n"
        "```html\n<div>mantido</div>\n```\n"
    )
    cleaned = clean_markdown(raw)
    assert "comentário" not in cleaned
    assert "Use API com `Bearer <token>`." in cleaned
    assert "docs_src" not in cleaned
    assert "Dica:" in cleaned and "///" not in cleaned
    assert "<div>mantido</div>" in cleaned


def test_split_sections_tracks_heading_path():
    text = (
        "# Guia\n\nIntro.\n\n## Parte A\n\nTexto A.\n\n"
        "### Detalhe\n\nTexto D.\n\n## Parte B\n\nTexto B.\n"
    )
    sections = split_sections(text)
    paths = [s.path_str for s in sections]
    assert paths == ["Guia", "Guia > Parte A", "Guia > Parte A > Detalhe", "Guia > Parte B"]
    assert sections[2].body == "Texto D."


def test_split_blocks_keeps_code_block_with_blank_lines_intact():
    text = "Parágrafo um.\n\n```python\nx = 1\n\ny = 2\n```\n\nParágrafo dois."
    blocks = split_blocks(text)
    assert len(blocks) == 3
    assert blocks[1].startswith("```python") and "y = 2" in blocks[1]


def test_missing_directory_raises(tmp_path: Path):
    with pytest.raises(FileNotFoundError):
        load_documents(tmp_path / "nao-existe")


def test_ignores_unsupported_files(tmp_path: Path):
    (tmp_path / "a.md").write_text("# A\n\nconteúdo", encoding="utf-8")
    (tmp_path / "b.png").write_bytes(b"\x89PNG")
    (tmp_path / "sub").mkdir()
    (tmp_path / "sub" / "c.md").write_text("# C\n\noutro", encoding="utf-8")
    docs = load_documents(tmp_path)
    assert [d.source for d in docs] == ["a.md", "sub/c.md"]
