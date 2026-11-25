import pytest

from core.schemas import Chunk, RetrievedChunk
from generation.grounding import (
    citation_coverage,
    extract_citation_ids,
    ground_answer,
    is_refusal,
    missing_critical_terms,
    statements,
    support_ratio,
)
from generation.prompts import REFUSAL_MESSAGE, SYSTEM_PROMPT, build_user_prompt

TEXTS = [
    "Use Depends para declarar uma dependência; o FastAPI resolve a dependência antes da rota.",
    "Classes também funcionam como dependências: o FastAPI chama o construtor da classe.",
    "A opção --workers do fastapi run inicia vários processos para usar mais núcleos da CPU.",
    "Para devolver uma página HTML, use HTMLResponse como response_class.",
]


def _chunks(
    n: int, text: str | None = None, sources: list[str] | None = None
) -> list[RetrievedChunk]:
    return [
        RetrievedChunk(
            Chunk(
                id=f"id{i}",
                text=text or TEXTS[(i - 1) % len(TEXTS)],
                source=sources[i - 1] if sources else f"doc{i}.md",
                section=f"S{i}",
                chunk_index=i,
                strategy="recursive",
            ),
            score=1.0,
        )
        for i in range(1, n + 1)
    ]


def test_prompt_numbers_context_and_states_rules():
    prompt = build_user_prompt("Pergunta?", _chunks(2))
    assert "[1] fonte: doc1.md › S1" in prompt and "[2] fonte: doc2.md › S2" in prompt
    assert "PERGUNTA: Pergunta?" in prompt
    assert REFUSAL_MESSAGE in SYSTEM_PROMPT
    assert "conhecimento geral" in SYSTEM_PROMPT and "tópicos" in SYSTEM_PROMPT


def test_extract_citation_ids_dedupes_in_order():
    assert extract_citation_ids("A [2]. B [1][2]. C [10].") == [2, 1, 10]


def test_valid_answer_keeps_citations():
    text = "Use Depends para declarar a dependência [1]. Classes também funcionam [2]."
    result = ground_answer(text, _chunks(3))
    assert not result.refused
    assert [c.id for c in result.citations] == [1, 2]
    assert result.citations[0].source == "doc1.md"
    assert result.coverage == 1.0 and result.unsupported == []


def test_invalid_citations_are_removed():
    text = "Use Depends para declarar a dependência [1]. Classes também funcionam [7]."
    result = ground_answer(text, _chunks(2))
    assert not result.refused
    assert "[7]" not in result.answer
    assert result.invalid_citation_ids == [7]


def test_answer_without_citation_is_converted_to_refusal():
    result = ground_answer("O FastAPI suporta GraphQL nativamente.", _chunks(3))
    assert result.refused
    assert result.refusal_reason == "ungrounded_answer"
    assert result.answer == REFUSAL_MESSAGE


def test_answer_citing_only_nonexistent_chunks_is_refused():
    result = ground_answer("Algo [9].", _chunks(2))
    assert result.refused and result.refusal_reason == "ungrounded_answer"


@pytest.mark.parametrize(
    "text",
    [
        REFUSAL_MESSAGE,
        "nao encontrei essa informacao na documentacao indexada",
        "Desculpe, não encontrei informações sobre isso nos trechos.",
    ],
)
def test_refusal_variants_are_detected(text):
    assert is_refusal(text)
    result = ground_answer(text, _chunks(2))
    assert result.refused and result.refusal_reason == "llm_refusal"


def test_refusal_with_citation_is_still_a_refusal():
    """Bug P1 da auditoria: a recusa com [1] passava como resposta fundamentada."""
    result = ground_answer(f"{REFUSAL_MESSAGE} [1]", _chunks(2))
    assert result.refused and result.refusal_reason == "llm_refusal"


def test_external_knowledge_with_fake_citation_is_blocked():
    """Bug P2 da auditoria: uma citação qualquer bastava para passar."""
    result = ground_answer("HTML é uma linguagem de marcação usada na web [4].", _chunks(4))
    assert result.refused and result.refusal_reason == "ungrounded_answer"
    assert result.unsupported


def test_mostly_uncited_answer_is_blocked():
    text = (
        "Use Depends para declarar a dependência [1]. "
        "O FastAPI também tem cache distribuído nativo. Ele integra com Kafka sozinho."
    )
    result = ground_answer(text, _chunks(1))
    assert result.refused and result.refusal_reason == "ungrounded_answer"
    assert result.coverage == pytest.approx(1 / 3)


def test_partial_answer_with_citation_is_kept():
    text = (
        "A opção --workers inicia vários processos [3]. "
        "Não encontrei essa informação sobre o valor padrão."
    )
    result = ground_answer(text, _chunks(3))
    assert not result.refused
    assert result.coverage == 1.0  # a frase de recusa não conta como afirmação sem citação


def test_formatted_answer_with_list_and_code_passes():
    text = (
        "Para usar dependências [1]:\n\n"
        "- Use Depends para declarar a dependência [1]\n"
        "- Classes também funcionam como dependências [2]\n\n"
        "Exemplo do trecho [1]:\n\n```python\ncommons = Depends(common_parameters)\n```"
    )
    result = ground_answer(text, _chunks(2))
    assert not result.refused
    # o bloco de código não conta; introduções com ':' contam porque trazem citação
    assert len(statements(text)) == 4


def test_cited_intro_before_code_counts_as_claim():
    # Formato real do qwen2.5:3b (q22): a citação fica na introdução do código, e a linha
    # depois do código vem sem citação. Antes, a introdução era ignorada, a cobertura ia a 0
    # e uma resposta correta era descartada como ungrounded_answer.
    text = (
        "- Para trocar uma dependência por uma versão de teste, use o dicionário "
        "`app.dependency_overrides`:\n\n"
        "[1] Para trocar uma dependência real por uma versão de teste, use o dicionário "
        "`app.dependency_overrides`:\n\n"
        "```python\napp.dependency_overrides[get_db] = override_get_db\n```\n\n"
        "- Limpe as substituições depois dos testes."
    )
    chunk_text = (
        "Para trocar uma dependência real por uma versão de teste, use o dicionário "
        "app.dependency_overrides. Limpe as substituições depois dos testes."
    )
    result = ground_answer(text, _chunks(1, text=chunk_text))
    assert not result.refused, result.refusal_reason
    # a última linha vem sem citação, mas o trecho 1 a sustenta sozinho: ela ganha o [1]
    assert result.resolved == 1 and result.coverage == 1.0
    assert "Limpe as substituições depois dos testes. [1]" in result.answer


def test_bare_intro_without_citation_is_still_ignored():
    assert statements("Veja o exemplo:\n\n```python\nx = 1\n```\n\nUse x [1].") == ["Use x [1]."]


def test_support_ratio():
    assert support_ratio("Use Depends para declarar a dependência [1]", [TEXTS[0]]) == 1.0
    assert support_ratio("HTML é uma linguagem de marcação usada na web [1]", [TEXTS[3]]) < 0.3
    assert support_ratio("[1]", [TEXTS[0]]) == 1.0


def test_thresholds_are_configurable():
    text = "Use Depends para declarar a dependência [1]. Frase sem citação nenhuma aqui."
    assert not ground_answer(text, _chunks(1), min_coverage=0.5).refused
    assert ground_answer(text, _chunks(1), min_coverage=0.9).refused


def test_citation_after_period_stays_with_its_sentence():
    text = "Use Depends para declarar a dependência. [1] Classes também funcionam. [2]"
    assert statements(text) == [
        "Use Depends para declarar a dependência. [1]",
        "Classes também funcionam. [2]",
    ]
    assert citation_coverage(text) == 1.0


def test_citation_coverage():
    assert citation_coverage("Frase um [1]. Frase dois [2].") == 1.0
    assert citation_coverage("Frase um [1]. Frase sem citação.") == 0.5
    assert citation_coverage("Introdução:\n```\ncódigo\n```\nFrase [1].") == 1.0
    assert citation_coverage("") == 0.0


# Caso 3 (u07): o modelo reaproveita as palavras do trecho e inventa o valor padrão
WORKERS_TEXT = (
    "O comando `fastapi run` aceita a opção `--workers` para iniciar vários processos, "
    "por exemplo `fastapi run --workers 4 main.py`. Em um cluster com Kubernetes, o "
    "recomendado é rodar um único processo por container."
)


@pytest.mark.parametrize(
    "answer",
    [
        "O FastAPI run usa por padrão um único processo. [1]",  # qualificador inventado
        "O FastAPI run usa 1 worker. [1]",  # número inventado
        "Use `fastapi run --threads 4` para isso. [1]",  # identificador inventado
    ],
)
def test_invented_value_reusing_chunk_words_is_refused(answer):
    result = ground_answer(answer, _chunks(1, WORKERS_TEXT))
    assert result.refused and result.refusal_reason == "ungrounded_answer"
    assert result.unsupported == [answer]


def test_one_invented_claim_refuses_the_whole_answer():
    """A regra da maioria deixaria passar: 2 frases boas e 1 inventada."""
    text = (
        "A opção `--workers` inicia vários processos [1]. "
        "O exemplo é `fastapi run --workers 4 main.py` [1]. "
        "O valor padrão é 8 workers [1]."
    )
    result = ground_answer(text, _chunks(1, WORKERS_TEXT))
    assert result.refused
    assert result.unsupported == ["O valor padrão é 8 workers [1]."]


def test_faithful_answer_with_numbers_and_code_is_kept():
    text = "Use `fastapi run --workers 4 main.py` para iniciar 4 processos [1]."
    assert not ground_answer(text, _chunks(1, WORKERS_TEXT)).refused


def test_numbered_list_markers_are_not_critical_terms():
    claim = "1. Instale o pacote com `fastapi run`"
    assert missing_critical_terms(claim, [WORKERS_TEXT]) == []
    assert missing_critical_terms("3) Use sempre `fastapi run`", [WORKERS_TEXT]) == ["sempre"]


def test_missing_critical_terms_reports_each_kind():
    assert missing_critical_terms("São 7 processos", [WORKERS_TEXT]) == ["7"]
    assert missing_critical_terms("Use `fastapi dev`", [WORKERS_TEXT]) == ["fastapi dev"]
    assert missing_critical_terms("Use --reload sempre", [WORKERS_TEXT]) == ["--reload", "sempre"]
    # com o qualificador no trecho, ele deixa de faltar
    assert missing_critical_terms("É o padrão", ["O valor padrão é 4."]) == []


# --- Falsas recusas: parser, reparo de citação e atribuição ----------------------

FROZEN = "O parâmetro `frozen=True` torna as instâncias imutáveis depois de criadas."
EXTRA = 'O parâmetro `extra="forbid"` rejeita campos que não foram declarados.'


def _pair(first: str, second: str, sources=("a.md", "a.md")) -> list[RetrievedChunk]:
    return [
        RetrievedChunk(Chunk(f"id{n}", text, src, f"S{n}", n, "recursive"), score=1.0)
        for n, (text, src) in enumerate(zip((first, second), sources, strict=True), start=1)
    ]


def test_standalone_citation_line_belongs_to_the_previous_statement():
    """Caso d11: o qwen2.5:3b escreve a frase e põe o [1] sozinho na linha seguinte."""
    text = "- O middleware que comprime é o `GZipMiddleware`.\n\n[1]"
    assert statements(text) == ["- O middleware que comprime é o `GZipMiddleware`. [1]"]
    chunk = "O `GZipMiddleware` comprime as respostas da API com gzip."
    assert not ground_answer(text, _chunks(1, text=chunk)).refused


def test_wrong_citation_number_in_the_same_document_is_repaired():
    """Casos d03 e d07: o fato está no trecho 2 do mesmo arquivo, citado como [1]."""
    text = "Use `frozen=True` para tornar as instâncias imutáveis [1]."
    result = ground_answer(text, _pair(EXTRA, FROZEN))
    assert not result.refused and result.resolved == 1
    assert [c.id for c in result.citations] == [2]
    assert result.answer.endswith("[2]")


def test_citation_is_never_repaired_across_documents():
    """Caso u07: o qualificador existe em outro arquivo, mas isso não sustenta a frase."""
    other = (
        "A porta padrão do servidor é 8000 e o comando fastapi run usa um único processo padrão."
    )
    text = "O comando `fastapi run` usa por padrão um único processo [1]."
    chunks = _pair(WORKERS_TEXT, other, sources=("implantacao.md", "primeiros-passos.md"))
    result = ground_answer(text, chunks)
    assert result.refused and result.resolved == 0


def test_uncited_statement_supported_by_one_chunk_gets_its_citation():
    text = "Use `frozen=True` para tornar as instâncias imutáveis depois de criadas."
    result = ground_answer(text, _pair(EXTRA, FROZEN))
    assert not result.refused and result.resolved == 1
    assert [c.id for c in result.citations] == [2]


def test_uncited_external_knowledge_is_not_attributed():
    text = "HTML é uma linguagem de marcação usada para estruturar páginas web."
    result = ground_answer(text, _chunks(4))
    assert result.refused and result.resolved == 0


def test_uncited_statement_needs_one_chunk_not_the_union_of_the_context():
    """Metade dos termos num trecho e metade em outro não sustenta a frase."""
    text = "O parâmetro extra torna as instâncias imutáveis e rejeita campos."
    result = ground_answer(text, _pair(EXTRA, FROZEN))
    assert result.refused


def test_negation_missing_from_the_chunk_counts_as_invented():
    claim = "O parâmetro `frozen=True` não torna as instâncias imutáveis [1]"
    assert missing_critical_terms(claim, [FROZEN]) == ["não"]
    assert (
        missing_critical_terms(
            "Não use `frozen=True` em modelos mutáveis", ["Não use frozen=True."]
        )
        == []
    )


def test_attributed_statement_does_not_dilute_a_rejected_cited_one():
    """Citada e reprovada + sem citação e atribuída: a resposta continua recusada."""
    text = (
        "Use o Django REST Framework com serializers [1]. "
        "Use `frozen=True` para tornar as instâncias imutáveis depois de criadas."
    )
    result = ground_answer(text, _pair(FROZEN, EXTRA))
    assert result.refused and result.coverage == 1.0  # a 2ª frase ganhou citação
    assert result.unsupported == ["Use o Django REST Framework com serializers [1]."]
