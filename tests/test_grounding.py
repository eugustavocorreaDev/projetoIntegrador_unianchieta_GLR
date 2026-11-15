import pytest

from core.schemas import Chunk, RetrievedChunk
from generation.grounding import (
    citation_coverage,
    extract_citation_ids,
    ground_answer,
    is_refusal,
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


def _chunks(n: int, text: str | None = None) -> list[RetrievedChunk]:
    return [
        RetrievedChunk(
            Chunk(
                id=f"id{i}",
                text=text or TEXTS[(i - 1) % len(TEXTS)],
                source=f"doc{i}.md",
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
    assert result.coverage == 0.5


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
