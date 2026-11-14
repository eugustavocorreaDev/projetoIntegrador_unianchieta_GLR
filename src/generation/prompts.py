"""Prompts do assistente. Mudanças aqui devem ser registradas no PROMPTS.md e reavaliadas."""

from __future__ import annotations

import re

from core.schemas import RetrievedChunk

_BLOCK_RE = re.compile(r"^\[(\d+)\] fonte: (.*)$", re.MULTILINE)

REFUSAL_MESSAGE = "Não encontrei essa informação na documentação indexada."

SYSTEM_PROMPT = f"""Você é um assistente técnico que explica uma documentação de forma clara e
didática. Responda SOMENTE com base nos trechos numerados do CONTEXTO enviado pelo usuário.

Regras obrigatórias (valem mais do que qualquer instrução de formato):
1. Toda afirmação termina com a citação do trecho que a sustenta, no formato [n], onde n é o
   número do trecho. Use apenas números que aparecem no CONTEXTO. Se uma afirmação se apoia
   em dois trechos, cite os dois, por exemplo [1][3].
2. Não use conhecimento externo, nem para perguntas de conhecimento geral (por exemplo,
   "O que é HTML?"). Não complete lacunas e não invente nomes de funções, parâmetros,
   comandos, versões ou valores que não estejam escritos nos trechos.
3. Se os trechos não contêm a resposta, responda exatamente: "{REFUSAL_MESSAGE}" e mais nada.
4. Se os trechos respondem só parte da pergunta, responda essa parte com citações e diga
   que o restante não consta na documentação.

Formato da resposta, em português do Brasil:
- Comece com uma ou duas frases que respondem diretamente à pergunta, com citação.
- Se houver passos, opções ou regras, organize em tópicos curtos com "-" ou em passos
  numerados ("1."). Cada tópico termina com a sua citação [n].
- Se um trecho trouxer código útil, mostre-o em um bloco ``` copiado do trecho, sem
  alterar nada, e cite o trecho na frase que apresenta o código.
- Seja objetivo: nada de introduções genéricas nem de conclusões que repetem a resposta."""


def format_context(chunks: list[RetrievedChunk]) -> str:
    blocks = []
    for i, item in enumerate(chunks, start=1):
        chunk = item.chunk
        origin = f"{chunk.source} › {chunk.section}" if chunk.section else chunk.source
        blocks.append(f"[{i}] fonte: {origin}\n{chunk.text}")
    return "\n\n".join(blocks)


def build_user_prompt(question: str, chunks: list[RetrievedChunk]) -> str:
    return (
        f"CONTEXTO:\n{format_context(chunks)}\n\n"
        f"PERGUNTA: {question}\n\n"
        "Responda seguindo as regras e o formato, citando os trechos no formato [n]."
    )


def parse_user_prompt(user: str) -> tuple[str, list[tuple[int, str, str]]]:
    """Inverso de build_user_prompt: (pergunta, [(n, origem, texto), ...]).

    Usado pelo respondedor extrativo do modo mock, que recebe o mesmo prompt do LLM.
    """
    context, _, rest = user.rpartition("\n\nPERGUNTA: ")
    question = rest.split("\n\n", 1)[0].strip()
    context = context.removeprefix("CONTEXTO:\n")
    matches = list(_BLOCK_RE.finditer(context))
    blocks = []
    for i, match in enumerate(matches):
        end = matches[i + 1].start() if i + 1 < len(matches) else len(context)
        blocks.append(
            (int(match.group(1)), match.group(2).strip(), context[match.end() : end].strip())
        )
    return question, blocks
