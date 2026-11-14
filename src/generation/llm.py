"""Cliente de chat do Ollama (endpoint /api/chat, sem streaming)."""

from __future__ import annotations

from typing import Protocol

import httpx

from core.errors import LLMError


class LLM(Protocol):
    def generate(self, system: str, user: str) -> str: ...


class OllamaLLM:
    def __init__(
        self,
        base_url: str,
        model: str,
        *,
        temperature: float = 0.0,
        num_ctx: int = 4096,
        max_tokens: int = 512,
        seed: int | None = 42,
        timeout_s: float = 180.0,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        self.model = model
        self.options = {"temperature": temperature, "num_ctx": num_ctx, "num_predict": max_tokens}
        if seed is not None:
            self.options["seed"] = seed
        self._client = httpx.Client(
            base_url=base_url.rstrip("/"), timeout=timeout_s, transport=transport
        )

    def generate(self, system: str, user: str) -> str:
        payload = {
            "model": self.model,
            "stream": False,
            "options": self.options,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        }
        try:
            response = self._client.post("/api/chat", json=payload)
        except httpx.TimeoutException as exc:
            raise LLMError(f"O LLM excedeu o tempo limite: {exc}") from exc
        except httpx.HTTPError as exc:
            raise LLMError(f"Ollama indisponível para geração: {exc}") from exc
        if response.status_code == 404:
            raise LLMError(f"Modelo '{self.model}' não encontrado. Rode: ollama pull {self.model}")
        if response.status_code >= 400:
            raise LLMError(f"Erro do Ollama ({response.status_code}): {response.text[:300]}")
        content = response.json().get("message", {}).get("content", "")
        return content.strip()

    def ping(self) -> bool:
        try:
            return self._client.get("/api/tags", timeout=5).status_code == 200
        except httpx.HTTPError:
            return False
