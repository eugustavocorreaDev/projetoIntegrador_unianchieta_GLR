"""Coleta respostas brutas reais do LLM no conjunto de DESENVOLVIMENTO (para calibrar a
verificação sem olhar o conjunto de teste). Mesma configuração da avaliação principal."""

import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]  # raiz do repositório
os.chdir(ROOT)
os.environ.update(QDRANT_MODE="local", QDRANT_PATH=".qdrant_local", LLM_MODE="ollama",
                  EMBED_MODE="ollama", LOG_DIR="")
sys.path[:0] = [str(ROOT / "src"), str(ROOT)]
from core.config import Settings  # noqa: E402
from core.pipeline import build_pipeline  # noqa: E402
from generation.prompts import SYSTEM_PROMPT, build_user_prompt  # noqa: E402

pipeline = build_pipeline(Settings(log_dir=None))
dev = json.loads((ROOT / "eval/datasets/perguntas_dev.json").read_text(encoding="utf-8"))
dev = dev["questions"] if isinstance(dev, dict) else dev
out = []
for q in dev:
    chunks, _ = pipeline.retriever.retrieve(q["question"], "recursive", "hybrid", 5)
    raw = pipeline.llm.generate(SYSTEM_PROMPT, build_user_prompt(q["question"], chunks))
    out.append({**q, "raw_answer": raw,
                "chunks": [{"id": c.chunk.id, "source": c.chunk.source,
                            "section": c.chunk.section, "text": c.chunk.text} for c in chunks]})
    print(q["id"], len(raw), flush=True)
dest = Path(__file__).with_name("dev_respostas.json")
dest.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
print("ok", len(out), dest)
