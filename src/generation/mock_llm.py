"""Respondedor extrativo para desenvolvimento sem Ollama (LLM_MODE=mock).

Não é um modelo de linguagem e não deve aparecer em resultados de avaliação. Ele lê o
mesmo prompt que o LLM receberia, escolhe os trechos que cobrem a maior parte dos termos
da pergunta e organiza o que eles dizem em tópicos legíveis, com a citação [n] de cada
um e o exemplo de código do trecho principal, quando houver. Se nenhum trecho cobre a
pergunta, devolve a frase de recusa. Com isso dá para ver, numa máquina sem Ollama, o
fluxo inteiro funcionando: recuperação, citações, verificação e recusa.
"""

from __future__ import annotations

import re

from core.text import stems as _stems
from generation.prompts import REFUSAL_MESSAGE, parse_user_prompt

_SENTENCE_RE = re.compile(r"(?<=[.!?])\s+|\n+")
_CODE_RE = re.compile(r"```[\w-]*\n.*?```", re.DOTALL)
_MAX_CODE_CHARS = 700
HEADER = "Trechos da documentação que respondem à pergunta:"


def _section_title(origin: str) -> str:
    """'testes.md › Testes > Sobrescrevendo dependências' -> 'Sobrescrevendo dependências'."""
    section = origin.split(" › ", 1)[-1]
    return section.rsplit(" > ", 1)[-1].strip()


class ExtractiveMockLLM:
    def __init__(self, min_overlap: float = 0.5, max_blocks: int = 3) -> None:
        self.min_overlap = min_overlap
        self.max_blocks = max_blocks

    def _sentences(self, text: str) -> list[str]:
        prose = _CODE_RE.sub("\n", text)
        return [s.strip() for s in _SENTENCE_RE.split(prose) if len(s.strip()) > 2]

    def _summary(self, terms: set[str], text: str) -> str:
        """A frase mais relevante do trecho, mais a seguinte quando a primeira é curta."""
        sentences = self._sentences(text)
        if not sentences:
            return text.strip()[:300]
        best = max(range(len(sentences)), key=lambda i: (len(terms & _stems(sentences[i])), -i))
        chosen = sentences[best]
        if len(chosen) < 120 and best + 1 < len(sentences):
            chosen = f"{chosen} {sentences[best + 1]}"
        return chosen[:500].rstrip()

    def generate(self, system: str, user: str) -> str:
        question, blocks = parse_user_prompt(user)
        terms = _stems(question)
        if not terms or not blocks:
            return REFUSAL_MESSAGE
        scored = sorted(
            (
                (len(terms & _stems(f"{origin}\n{text}")) / len(terms), number, origin, text)
                for number, origin, text in blocks
            ),
            key=lambda item: (-item[0], item[1]),
        )
        selected = [item for item in scored if item[0] >= self.min_overlap][: self.max_blocks]
        if not selected:
            return REFUSAL_MESSAGE

        lines = [HEADER, ""]
        for _, number, origin, text in selected:
            lines.append(f"- **{_section_title(origin)}**: {self._summary(terms, text)} [{number}]")
        _, top_number, _, top_text = selected[0]
        code = _CODE_RE.search(top_text)
        if code and len(code.group(0)) <= _MAX_CODE_CHARS:
            lines += ["", f"Exemplo de código do trecho [{top_number}]:", "", code.group(0)]
        return "\n".join(lines)

    def ping(self) -> bool:
        return True
