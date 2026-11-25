"""Verificação determinística da resposta do LLM (camada anti-alucinação).

O prompt pede citações, mas modelos pequenos nem sempre obedecem. Por isso a saída é
conferida em código, em quatro passos:

1. citações [n] fora do intervalo de trechos enviados são removidas;
2. uma recusa continua sendo recusa mesmo que o modelo tenha acrescentado uma citação;
3. **cobertura:** pelo menos `min_coverage` das afirmações precisa ter citação;
4. **sustentação:** cada afirmação citada precisa compartilhar pelo menos `min_support`
   dos seus termos com os trechos que cita. Uma frase de conhecimento externo com um
   [1] qualquer ("HTML é uma linguagem de marcação [1]") não se sustenta no trecho;
5. **termos críticos:** a média do passo 4 deixa passar a frase que reaproveita as palavras
   do trecho e inventa só o que importa ("usa por padrão 1 worker"). Por isso números,
   identificadores de código e qualificadores de escopo ("padrão", "sempre", "apenas"...)
   da afirmação precisam aparecer no trecho citado. Um só que falte reprova a resposta.

Antes dos passos 3 a 5, cada afirmação tem a citação conferida e, se preciso, resolvida
(`_resolve`), porque modelos pequenos erram a atribuição mais do que o conteúdo:
- citação com o número errado: se outro trecho **do mesmo documento** sustenta a afirmação
  sozinho, a citação é trocada por ele. Entre documentos diferentes nunca, senão uma
  alucinação como "usa por padrão um único processo" se apoiaria em outro arquivo;
- afirmação sem citação: só é aceita se um único trecho a sustentar com pelo menos
  `min_attribution` dos termos e sem termo crítico faltando, e então ganha a citação dele.
  O pool de todo o contexto não serve: palavras do domínio aparecem em qualquer trecho.

Respostas que falham em 3, 4 ou 5 são descartadas e trocadas pela recusa (`ungrounded_answer`).
A checagem é lexical: ela barra afirmações sem relação com os trechos e valores ou escopos
inventados, mas não garante que uma paráfrase com os mesmos termos esteja correta (ver
docs/seguranca-lgpd.md).
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
_INLINE_CODE_RE = re.compile(r"`([^`\n]+)`")
_LIST_MARKER_RE = re.compile(r"^\s*(?:\d{1,2}[.)]|[-*•])\s+")
_NUMBER_RE = re.compile(r"\b\d+\b")
_FLAG_RE = re.compile(r"(?<![\w-])--?[a-z][\w-]*", re.IGNORECASE)
# Palavras que transformam um caso específico em regra geral. Se a afirmação usa uma delas,
# o trecho citado precisa usar a mesma (comparação por radical, como em `stems`).
_NEGATIONS = frozenset({"nao", "nunca", "sem", "nenhum", "nenhuma"})
_SCOPE_QUALIFIERS = frozenset(
    stems(
        "padrão default sempre nunca todos todas apenas somente obrigatório obrigatória "
        "automaticamente"
    )
)
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
    """Afirmações da resposta: frases e tópicos, sem blocos de código.

    Linhas introdutórias terminadas em ':' só contam quando trazem citação: "Use o
    dicionário X [1]:" seguido de código afirma algo e cita a fonte, enquanto "Veja o
    exemplo:" não afirma nada. Se só houver introduções sem citação, elas contam assim
    mesmo, para que a resposta tenha o que verificar (e seja recusada por falta de citação).
    """
    prose = _CODE_RE.sub("\n", text)
    result, bare_intros = [], []
    for part in _SENTENCE_SPLIT_RE.split(prose.strip()):
        part = part.strip()
        content = _CITATION_RE.sub("", part).strip(" -*•\t")
        if len(content) <= 3:
            if result and _CITATION_RE.search(part):  # "[1]" sozinho cita a frase anterior
                result[-1] = f"{result[-1]} {part}"
            continue
        if content.endswith(":") and not _CITATION_RE.search(part):
            bare_intros.append(part)
        else:
            result.append(part)
    return result or bare_intros


def citation_coverage(text: str) -> float:
    """Fração das afirmações (exceto frases de recusa) que têm pelo menos uma citação."""
    claims = [s for s in statements(text) if not is_refusal(s)]
    if not claims:
        return 0.0
    return sum(1 for s in claims if _CITATION_RE.search(s)) / len(claims)


def _pool(cited_texts: list[str]) -> set[str]:
    pool: set[str] = set()
    for text in cited_texts:
        pool |= stems(text)
    return pool


def support_ratio(statement: str, cited_texts: list[str]) -> float:
    """Fração dos termos da afirmação que aparecem nos trechos citados por ela."""
    terms = stems(_CITATION_RE.sub("", statement))
    if not terms:
        return 1.0
    return len(terms & _pool(cited_texts)) / len(terms)


def missing_critical_terms(statement: str, cited_texts: list[str]) -> list[str]:
    """Números, identificadores de código e qualificadores de escopo ausentes dos trechos.

    São os termos que carregam o fato: a média de `support_ratio` os dilui entre palavras
    que vieram da própria pergunta ("fastapi", "run").
    """
    text = _LIST_MARKER_RE.sub("", _CITATION_RE.sub("", statement))
    haystack = _normalize(" ".join(cited_texts))
    pool = _pool(cited_texts)
    missing = [n for n in _NUMBER_RE.findall(text) if n not in pool]
    for code in _INLINE_CODE_RE.findall(text):
        if _normalize(code) not in haystack:
            missing.append(code)
    flags = _FLAG_RE.findall(_INLINE_CODE_RE.sub("", text))
    missing += [f for f in flags if f.lower() not in haystack]
    missing += sorted(stems(text) & _SCOPE_QUALIFIERS - pool)
    # afirmação negativa sobre trecho que não nega nada inverte o sentido
    if _NEGATIONS & set(_normalize(text).split()) and not _NEGATIONS & set(haystack.split()):
        missing.append("não")
    return list(dict.fromkeys(missing))


@dataclass
class GroundingResult:
    answer: str
    refused: bool
    refusal_reason: str | None
    citations: list[Citation] = field(default_factory=list)
    invalid_citation_ids: list[int] = field(default_factory=list)
    coverage: float | None = None
    unsupported: list[str] = field(default_factory=list)
    resolved: int = 0  # afirmações cuja citação foi trocada ou atribuída por verificação


def _chunk_text(item: RetrievedChunk) -> str:
    chunk = item.chunk
    return f"{chunk.source} {chunk.section}\n{chunk.text}"


def _verdict(claim: str, texts: list[str], min_support: float) -> str | None:
    if missing_critical_terms(claim, texts):
        return "invented"
    return "weak" if support_ratio(claim, texts) < min_support else None


def _resolve(
    claim: str, cited: list[int], chunks: list[RetrievedChunk], min_support: float, min_attr: float
) -> tuple[list[int], str | None, bool]:
    """Confere a citação da afirmação. Devolve (citações, veredito, citação foi trocada)."""
    verdict = _verdict(claim, [_chunk_text(chunks[n - 1]) for n in cited], min_support)
    if cited and verdict is None:
        return cited, None, False
    if cited:
        sources = {chunks[n - 1].chunk.source for n in cited}
        candidates = [
            n
            for n in range(1, len(chunks) + 1)
            if n not in cited and chunks[n - 1].chunk.source in sources
        ]
    else:
        has_terms = len(stems(claim)) >= 2
        candidates = list(range(1, len(chunks) + 1)) if has_terms else []
    best, best_ratio = None, 0.0
    for n in candidates:
        texts = [_chunk_text(chunks[n - 1])]
        ratio = support_ratio(claim, texts)
        if _verdict(claim, texts, min_attr) is None and ratio > best_ratio:
            best, best_ratio = n, ratio
    if best is not None:
        return [best], None, True
    return cited, verdict if cited else None, False


def ground_answer(
    raw_answer: str,
    chunks: list[RetrievedChunk],
    min_coverage: float = 0.5,
    min_support: float = 0.3,
    min_attribution: float = 0.6,
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

    if not valid and is_refusal(raw_answer):
        return refuse("llm_refusal")

    # Uma recusa com citação ("Não encontrei essa informação [1]") continua sendo recusa,
    # a não ser que exista alguma afirmação além dela (resposta parcial).
    claims = [s for s in statements(answer) if not is_refusal(s)]
    if is_refusal(answer) and not claims:
        return refuse("llm_refusal")

    invented, weak, cited_claims, resolved = [], [], 0, 0
    for claim in claims:
        cited = [n for n in extract_citation_ids(claim) if 1 <= n <= len(chunks)]
        ids, verdict, changed = _resolve(claim, cited, chunks, min_support, min_attribution)
        if changed:
            fixed = re.sub(r"\s{2,}", " ", _CITATION_RE.sub("", claim)).rstrip()
            answer = answer.replace(claim, f"{fixed} [{ids[0]}]", 1)
            resolved += 1
        # só as citações do próprio modelo entram na maioria: uma frase atribuída por nós já
        # passou na checagem estrita e não pode diluir a reprovação de uma frase citada
        cited_claims += bool(cited)
        {"invented": invented, "weak": weak}.get(verdict, []).append(claim)

    coverage = citation_coverage(answer)
    unsupported = invented + weak
    if (
        invented
        or coverage < min_coverage
        or (cited_claims and len(unsupported) * 2 > cited_claims)
    ):
        return refuse("ungrounded_answer", coverage=coverage, unsupported=unsupported)

    citations = []
    for number in extract_citation_ids(answer):
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
    return GroundingResult(answer, False, None, citations, invalid, coverage, unsupported, resolved)
