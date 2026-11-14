"""Logs estruturados: formato JSON, gravação em arquivo, idempotência e truncamento (LGPD)."""

import json
import logging
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path

import pytest

from core.logging_setup import JsonFormatter, setup_logging, truncate

NOISY = ("httpx", "httpcore", "urllib3")


def _record(msg: str = "index.completed", **extra) -> logging.LogRecord:
    return logging.getLogger("rag.test").makeRecord(
        "rag.test", logging.INFO, __file__, 10, msg, (), None, extra=extra
    )


@pytest.fixture
def clean_root():
    """setup_logging é idempotente via flag no root logger: salva e restaura o estado global."""
    root = logging.getLogger()
    handlers, level = list(root.handlers), root.level
    had_flag = hasattr(root, "_rag_configured")
    flag = getattr(root, "_rag_configured", None)
    noisy_levels = {name: logging.getLogger(name).level for name in NOISY}
    if had_flag:
        del root._rag_configured
    yield root
    for handler in root.handlers:
        if handler not in handlers:
            handler.close()
    root.handlers[:] = handlers
    root.setLevel(level)
    if had_flag:
        root._rag_configured = flag
    elif hasattr(root, "_rag_configured"):
        del root._rag_configured
    for name, noisy_level in noisy_levels.items():
        logging.getLogger(name).setLevel(noisy_level)


# --- JsonFormatter -------------------------------------------------------------


def test_json_formatter_has_timestamp_level_event_and_extras():
    entry = json.loads(
        JsonFormatter().format(_record(strategy="fixed", chunks=12, docs_dir=Path("data")))
    )
    assert entry["level"] == "INFO"
    assert entry["logger"] == "rag.test"
    assert entry["event"] == "index.completed"
    assert entry["ts"][:4].isdigit() and "T" in entry["ts"]  # ISO 8601 com fuso
    assert entry["strategy"] == "fixed" and entry["chunks"] == 12
    assert entry["docs_dir"] == "data"  # valores não serializáveis viram str
    # Atributos internos do LogRecord não vazam para o JSON
    assert not {"msg", "args", "pathname", "lineno", "levelno"} & set(entry)


def test_json_formatter_keeps_accents_and_includes_exception():
    try:
        raise ValueError("falhou")
    except ValueError:
        record = logging.getLogger("rag.test").makeRecord(
            "rag.test", logging.ERROR, __file__, 10, "ação inválida", (), sys.exc_info()
        )
    line = JsonFormatter().format(record)
    assert "ação inválida" in line  # ensure_ascii=False
    entry = json.loads(line)
    assert entry["level"] == "ERROR"
    assert "ValueError: falhou" in entry["exception"]


# --- setup_logging -------------------------------------------------------------


def test_setup_logging_writes_json_lines_to_file(clean_root, tmp_path):
    log_dir = tmp_path / "logs"
    before = len(clean_root.handlers)

    setup_logging("debug", log_dir)

    assert clean_root.level == logging.DEBUG
    added = clean_root.handlers[before:]
    assert len(added) == 2
    assert all(isinstance(h.formatter, JsonFormatter) for h in added)
    file_handlers = [h for h in added if isinstance(h, RotatingFileHandler)]
    assert len(file_handlers) == 1
    assert logging.getLogger("httpx").level == logging.WARNING

    logging.getLogger("rag.test").info("ask.completed", extra={"question": "Como usar CORS?"})
    file_handlers[0].flush()
    lines = (log_dir / "app.log").read_text(encoding="utf-8").strip().splitlines()
    entry = json.loads(lines[-1])
    assert entry["event"] == "ask.completed"
    assert entry["question"] == "Como usar CORS?"


def test_setup_logging_is_idempotent_and_file_is_optional(clean_root):
    before = len(clean_root.handlers)
    setup_logging("WARNING", None)
    setup_logging("DEBUG", None)  # ignorada: já configurado

    added = clean_root.handlers[before:]
    assert len(added) == 1 and not isinstance(added[0], RotatingFileHandler)
    assert clean_root.level == logging.WARNING


# --- truncate ------------------------------------------------------------------


def test_truncate_limits_text_size():
    assert truncate("curta") == "curta"
    text = "x" * 300
    result = truncate(text, limit=50)
    assert len(result) == 50 and result.endswith("…")
    assert truncate("a" * 200) == "a" * 200
