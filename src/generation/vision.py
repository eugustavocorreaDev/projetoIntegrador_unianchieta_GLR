"""Leitura de imagens (prints) enviadas junto com a pergunta.

Um modelo de visão do Ollama transcreve o texto e o código da imagem. A transcrição entra
na pergunta (busca e prompt), mas nunca vira fonte: a resposta continua precisando citar os
trechos da documentação e passa pela mesma verificação de citações.
"""

from __future__ import annotations

import base64
import binascii
from typing import Protocol

import httpx

from core.errors import InvalidInputError, LLMError

VISION_PROMPT = (
    "Transcreva fielmente todo o texto e todo o código visíveis nesta imagem, na ordem em que "
    "aparecem, sem traduzir e sem comentar. Se não houver texto, descreva em uma frase, em "
    "português, o que a imagem mostra. Não responda perguntas nem dê explicações."
)

# Assinaturas dos formatos aceitos (os que o modelo de visão lê)
_SIGNATURES = {
    "png": (b"\x89PNG\r\n\x1a\n",),
    "jpeg": (b"\xff\xd8\xff",),
}


class ImageReader(Protocol):
    def read(self, image_b64: str) -> str: ...


def decode_image(image_b64: str, max_bytes: int) -> tuple[str, str]:
    """Valida a imagem em base64 e devolve (base64 limpo, formato).

    Aceita o prefixo "data:image/...;base64," que navegadores costumam incluir.
    """
    data = image_b64.strip()
    if data.startswith("data:") and "," in data:
        data = data.split(",", 1)[1]
    try:
        raw = base64.b64decode(data, validate=True)
    except (binascii.Error, ValueError) as exc:
        raise InvalidInputError("A imagem enviada não está em base64 válido.") from exc
    if not raw:
        raise InvalidInputError("A imagem enviada está vazia.")
    if len(raw) > max_bytes:
        limit_mb = max_bytes / (1024 * 1024)
        raise InvalidInputError(f"A imagem passa do limite de {limit_mb:.0f} MB.")
    if raw[:12].startswith(b"RIFF") and raw[8:12] == b"WEBP":
        return data, "webp"
    for fmt, signatures in _SIGNATURES.items():
        if raw.startswith(signatures):
            return data, fmt
    raise InvalidInputError("Formato de imagem não suportado. Envie PNG, JPG ou WEBP.")


class OllamaImageReader:
    def __init__(
        self,
        base_url: str,
        model: str,
        *,
        max_tokens: int = 600,
        timeout_s: float = 180.0,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        self.model = model
        self.options = {"temperature": 0.0, "num_predict": max_tokens}
        self._client = httpx.Client(
            base_url=base_url.rstrip("/"), timeout=timeout_s, transport=transport
        )

    def read(self, image_b64: str) -> str:
        payload = {
            "model": self.model,
            "stream": False,
            "options": self.options,
            "messages": [{"role": "user", "content": VISION_PROMPT, "images": [image_b64]}],
        }
        try:
            response = self._client.post("/api/chat", json=payload)
        except httpx.TimeoutException as exc:
            raise LLMError(f"O modelo de visão excedeu o tempo limite: {exc}") from exc
        except httpx.HTTPError as exc:
            raise LLMError(f"Ollama indisponível para ler a imagem: {exc}") from exc
        if response.status_code == 404:
            raise LLMError(
                f"Modelo de visão '{self.model}' não encontrado. Rode: ollama pull {self.model}"
            )
        if response.status_code >= 400:
            raise LLMError(
                f"Erro do Ollama ao ler a imagem ({response.status_code}): "
                f"{response.text[:300]}"
            )
        return response.json().get("message", {}).get("content", "").strip()
