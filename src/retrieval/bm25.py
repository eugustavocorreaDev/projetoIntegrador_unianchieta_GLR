"""BM25 Okapi implementado do zero, para busca lexical em memória.

Busca lexical complementa a vetorial em documentação técnica: nomes exatos de
funções, parâmetros e comandos (ex.: "dependency_overrides") são termos raros que
embeddings tendem a diluir.
"""

from __future__ import annotations

import math
from collections import Counter

from core.schemas import Chunk, RetrievedChunk
from core.text import STOPWORDS, tokenize

__all__ = ["STOPWORDS", "BM25Index", "tokenize"]


class BM25Index:
    def __init__(self, chunks: list[Chunk], k1: float = 1.5, b: float = 0.75) -> None:
        self.chunks = chunks
        self.k1 = k1
        self.b = b
        self._tfs = [Counter(tokenize(c.embedding_text())) for c in chunks]
        self._lengths = [sum(tf.values()) for tf in self._tfs]
        self._avgdl = (sum(self._lengths) / len(self._lengths)) if self._lengths else 0.0
        df: Counter[str] = Counter()
        for tf in self._tfs:
            df.update(tf.keys())
        n = len(chunks)
        self._idf = {
            term: math.log((n - freq + 0.5) / (freq + 0.5) + 1.0) for term, freq in df.items()
        }

    def __len__(self) -> int:
        return len(self.chunks)

    def scores(self, query: str) -> list[float]:
        terms = tokenize(query)
        results: list[float] = []
        for tf, length in zip(self._tfs, self._lengths, strict=True):
            score = 0.0
            norm = (
                self.k1 * (1 - self.b + self.b * length / self._avgdl) if self._avgdl else self.k1
            )
            for term in terms:
                freq = tf.get(term)
                if freq:
                    score += self._idf[term] * freq * (self.k1 + 1) / (freq + norm)
            results.append(score)
        return results

    def search(self, query: str, limit: int) -> list[RetrievedChunk]:
        scored = [(s, i) for i, s in enumerate(self.scores(query)) if s > 0]
        scored.sort(key=lambda pair: (-pair[0], pair[1]))
        return [
            RetrievedChunk(chunk=self.chunks[i], score=s, bm25_score=s, stages=["bm25"])
            for s, i in scored[:limit]
        ]
