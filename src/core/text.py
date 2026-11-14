"""Normalização e tokenização de texto compartilhadas (BM25, embeddings por hashing, mock,
validação interativa e avaliação)."""

from __future__ import annotations

import re
import unicodedata
from collections.abc import Iterable, Sequence

_TOKEN_RE = re.compile(r"\w+")

STOPWORDS = frozenset(
    """
    a o as os um uma uns umas de da do das dos em na no nas nos por para pra com sem
    e ou que se ao aos à às é ser são foi como mais mas qual quais quando onde porque
    isso esse essa este esta eu voce você ele ela eles elas seu sua seus suas meu minha
    nao não sim já ja tambem também entre sobre ate até pelo pela pelos pelas lhe
    the an of to in on for with and or is are be by it this that as at from how what
    which do does can i you
    """.split()
)


def _strip_accents(text: str) -> str:
    decomposed = unicodedata.normalize("NFKD", text)
    return "".join(c for c in decomposed if not unicodedata.combining(c))


def tokenize(text: str) -> list[str]:
    """Minúsculas, sem acentos, sem stopwords; identificadores com "_" também viram partes."""
    tokens: list[str] = []
    for token in _TOKEN_RE.findall(_strip_accents(text.lower())):
        candidates = [token]
        if "_" in token:
            candidates.extend(p for p in token.split("_") if p)
        for t in candidates:
            if t not in STOPWORDS and (len(t) > 1 or t.isdigit()):
                tokens.append(t)
    return tokens


STEM_CHARS = 6  # "sobrescrever" e "sobrescrevendo" contam como o mesmo termo


def stems(text: str) -> set[str]:
    """Radicais aproximados (primeiros caracteres de cada token), para comparar termos."""
    return {t[:STEM_CHARS] for t in tokenize(text)}


def normalize(text: str) -> str:
    """Minúsculas, sem acentos, sem crases/asteriscos do Markdown e com espaços colapsados."""
    stripped = _strip_accents(text.lower()).replace("`", "").replace("*", "")
    return " ".join(stripped.split())


def contains_snippet(text: str, snippets: Iterable[str]) -> bool:
    haystack = normalize(text)
    return any(normalize(s) in haystack for s in snippets)


def first_relevant_rank(texts: Sequence[str], snippets: Sequence[str]) -> int | None:
    """Posição (começando em 1) do primeiro texto que contém um trecho esperado."""
    for rank, text in enumerate(texts, start=1):
        if contains_snippet(text, snippets):
            return rank
    return None
