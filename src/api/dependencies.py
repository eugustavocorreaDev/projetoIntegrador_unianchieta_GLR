"""Injeção de dependências. Os testes substituem get_pipeline por uma versão com fakes."""

from __future__ import annotations

from functools import lru_cache

from core.config import get_settings
from core.pipeline import RAGPipeline, build_pipeline


@lru_cache
def get_pipeline() -> RAGPipeline:
    return build_pipeline(get_settings())
