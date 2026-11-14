"""Verificação determinística da resposta do LLM (camada anti-alucinação).

O prompt pede citações, mas modelos pequenos nem sempre obedecem. Por isso a saída é
conferida em código, em quatro passos:

1. citações [n] fora do intervalo de trechos enviados são removidas;
2. uma recusa continua sendo recusa mesmo que o modelo tenha acrescentado uma citação;
3. **cobertura:** pelo menos `min_coverage` das afirmações precisa ter citação;
4. **sustentação:** cada afirmação citada precisa compartilhar pelo menos `min_support`
   dos seus termos com os trechos que cita. Uma frase de conhecimento externo com um
   [1] qualquer ("HTML é uma linguagem de marcação [1]") não se sustenta no trecho.

Respostas que falham em 3 ou 4 são descartadas e trocadas pela recusa (`ungrounded_answer`).
A checagem é lexical: ela barra afirmações sem relação com os trechos, mas não garante que
uma paráfrase com os mesmos termos esteja correta (ver docs/seguranca-lgpd.md).
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field

from core.schemas import Citation, RetrievedChunk
from core.text import stems
from generation.prompts import REFUSAL_MESSAGE

_CITATION_RE = re.compile(r"\[(\d{1,3})\]")
# Não separa a citação da frase quando ela vem depois do ponto ("frase. [1]"), mas corta
# depois dela quando outra frase começa ("frase. [1] Outra frase. [2]").
_SENTENCE_SPLIT_RE = re.compile(
    r"(?<=[.!?])\s+(?!\[\d)|(?<=[.!?] \[\d\])\s+|(?<=[.!?] \[\d\d\])\s+|\n+"
)
_CODE_RE = re.compile(r"```.*?```", re.DOTALL)
# Variações que modelos pequenos usam para recusar
_REFUSAL_MARKERS = (
    "nao encontrei essa informacao",
    "nao encontrei esta informacao",
    "nao encontrei informacoes",
    "nao ha informacoes sobre isso",
    "a documentacao indexada nao",
    "nao consta na documentacao",
)


def _normalize(text: str) -> str:
    decomposed = unicodedata.normalize("NFKD", text.lower())
    return " ".join("".join(c for c in decomposed if not unicodedata.combining(c)).split())


def is_refusal(text: str) -> bool:
    normalized = _normalize(text)
    return any(marker in normalized for marker in _REFUSAL_MARKERS)


def extract_citation_ids(text: str) -> list[int]:
    seen: list[int] = []
    for match in _CITATION_RE.finditer(text):
        number = int(match.group(1))
        if number not in seen:
            seen.append(number)
    return seen


def statements(text: str) -> list[str]:
    """Afirmações da resposta: frases e tópicos, sem blocos de código e sem linhas
    introdutórias terminadas em ':' (ex.: "Exemplo de código do trecho [1]:")."""
    prose = _CODE_RE.sub("\n", text)
    result = []
    for part in _SENTENCE_SPLIT_RE.split(prose.strip()):
        part = part.strip()
        content = _CITATION_RE.sub("", part).strip(" -*•\t")
        if len(content) > 3 and not content.endswith(":"):
            result.append(part)
    return result


def citation_coverage(text: str) -> float:
    """Fração das afirmações (exceto frases de recusa) que têm pelo menos uma citação."""
    claims = [s for s in statements(text) if not is_refusal(s)]
    if not claims:
        return 0.0
    return sum(1 for s in claims if _CITATION_RE.search(s)) / len(claims)


def support_ratio(statement: str, cited_texts: list[str]) -> float:
    """Fração dos termos da afirmação que aparecem nos trechos citados por ela."""
    terms = stems(_CITATION_RE.sub("", statement))
    if not terms:
        return 1.0
    pool: set[str] = set()
    for text in cited_texts:
        pool |= stems(text)
    return len(terms & pool) / len(terms)


@dataclass
class GroundingResult:
    answer: str
    refused: bool
    refusal_reason: str | None
    citations: list[Citation] = field(default_factory=list)
    invalid_citation_ids: list[int] = field(default_factory=list)
    coverage: float | None = None
    unsupported: list[str] = field(default_factory=list)


def _chunk_text(item: RetrievedChunk) -> str:
    chunk = item.chunk
    return f"{chunk.source} {chunk.section}\n{chunk.text}"


def ground_answer(
    raw_answer: str,
    chunks: list[RetrievedChunk],
    min_coverage: float = 0.5,
    min_support: float = 0.3,
) -> GroundingResult:
    ids = extract_citation_ids(raw_answer)
    valid = [i for i in ids if 1 <= i <= len(chunks)]
    invalid = [i for i in ids if i not in valid]

    answer = raw_answer
    for number in invalid:
        answer = answer.replace(f"[{number}]", "")
    answer = re.sub(r"[ \t]{2,}", " ", answer).strip()

    def refuse(reason: str, **details) -> GroundingResult:
        return GroundingResult(REFUSAL_MESSAGE, True, reason, [], invalid, **details)

    if not valid:
        return refuse("llm_refusal" if is_refusal(raw_answer) else "ungrounded_answer")

    # Uma recusa com citação ("Não encontrei essa informação [1]") continua sendo recusa,
    # a não ser que exista alguma afirmação além dela (resposta parcial).
    claims = [s for s in statements(answer) if not is_refusal(s)]
    if is_refusal(answer) and not claims:
        return refuse("llm_refusal")

    coverage = citation_coverage(answer)
    if coverage < min_coverage:
        return refuse("ungrounded_answer", coverage=coverage)

    unsupported = []
    cited_claims = 0
    for claim in claims:
        numbers = [n for n in extract_citation_ids(claim) if 1 <= n <= len(chunks)]
        if not numbers:
            continue
        cited_claims += 1
        texts = [_chunk_text(chunks[n - 1]) for n in numbers]
        if support_ratio(claim, texts) < min_support:
            unsupported.append(claim)
    if cited_claims and len(unsupported) * 2 > cited_claims:
        return refuse("ungrounded_answer", coverage=coverage, unsupported=unsupported)

    citations = []
    for number in valid:
        chunk = chunks[number - 1].chunk
        citations.append(
            Citation(
                id=number,
                source=chunk.source,
                section=chunk.section,
                chunk_id=chunk.id,
                excerpt=chunk.text[:400],
            )
        )
    return GroundingResult(answer, False, None, citations, invalid, coverage, unsupported)
