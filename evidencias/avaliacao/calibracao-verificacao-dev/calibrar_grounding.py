"""Calibra a verificação de citações no conjunto de DESENVOLVIMENTO (nunca no de teste).

Aplica `ground_answer` às respostas reais gravadas em `dev_respostas.json` (ver
`coletar_dev.py`) com variações dos limites, e a respostas forjadas que precisam ser barradas.
As métricas são as da avaliação oficial: respondida com o trecho-ouro dentro do trecho CITADO.
"""

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]  # raiz do repositório
sys.path.insert(0, str(ROOT / "src"))
from core.schemas import Chunk, RetrievedChunk  # noqa: E402
from core.text import contains_snippet  # noqa: E402
from generation.grounding import ground_answer  # noqa: E402

dev = json.loads(Path(__file__).with_name("dev_respostas.json").read_text(encoding="utf-8"))
by_id = {q["id"]: q for q in dev}


def chunks_of(q):
    return [
        RetrievedChunk(Chunk(c["id"], c["text"], c["source"], c["section"], i, "recursive"), 1.0)
        for i, c in enumerate(q["chunks"], 1)
    ]


# Cada item é (id da pergunta cujos trechos o modelo veria, resposta forjada). Todas devem ser
# recusadas: conhecimento externo, valor/escopo/negação inventados (caso u07), com ou sem [n].
ADVERSARIAL = [
    ("d01", "HTML é uma linguagem de marcação usada para estruturar páginas web [1]."),
    ("d01", "Use o Django REST Framework com serializers [1]. Ele gera a API automaticamente."),
    ("d01", "O FastAPI usa bcrypt com 12 rodadas por padrão [1]. Isso garante senhas seguras."),
    ("d01", "JavaScript é executado no navegador [2]. Ele manipula o DOM da página."),
    ("d01", "HTML é uma linguagem de marcação usada para estruturar páginas web."),
    ("d07", "A opção `pytest -x` para na primeira falha por padrão [1]."),
    ("d07", "A opção `pytest -x` para depois de 3 falhas [1]."),
    ("d07", "Use `pytest --maxfail` para parar na primeira falha [1]."),
    ("d07", "A opção `pytest -x` para na primeira falha por padrão."),
    ("d07", "A opção `pytest -x` para depois de 3 falhas."),
    ("d03", "Todos os modelos Pydantic são imutáveis [2]."),
    ("d03", "O parâmetro `frozen=True` não torna as instâncias imutáveis [2]."),
    ("v11", "O Uvicorn usa por padrão um único processo [1]."),
    ("v11", "O Uvicorn usa 1 worker por padrão [1]."),
    ("v11", "O Uvicorn usa por padrão um único processo."),
]
# (nome, parâmetros de ground_answer). min_attribution > 1 desliga o reparo e a atribuição.
POLICIES = {
    "sem reparo nem atribuição": {"min_attribution": 1.01},
    "atribuição >= 0,50": {"min_attribution": 0.5},
    "atribuição >= 0,60 (adotada)": {"min_attribution": 0.6},
    "atribuição >= 0,70": {"min_attribution": 0.7},
    "atribuição >= 0,80": {"min_attribution": 0.8},
}

results = {}
for name, params in POLICIES.items():
    ok = wrong = refused_ok = resolved = 0
    refused_ids = []
    for q in dev:
        r = ground_answer(q["raw_answer"], chunks_of(q), **params)
        if q["answerable"]:
            cited = [c.excerpt for c in r.citations]
            texts = {c["id"]: c["text"] for c in q["chunks"]}
            cited_text = [texts[c.chunk_id] for c in r.citations]
            hit = (not r.refused) and any(contains_snippet(t, q["expected_snippets"]) for t in cited_text)
            ok += hit
            wrong += (not r.refused) and not hit
            resolved += r.resolved
            if r.refused:
                refused_ids.append(q["id"])
        else:
            refused_ok += r.refused
    leaked = [
        raw
        for qid, raw in ADVERSARIAL
        if not ground_answer(raw, chunks_of(by_id[qid]), **params).refused
    ]
    n_ans = sum(q["answerable"] for q in dev)
    results[name] = {
        "respostas_fundamentadas": f"{ok}/{n_ans}",
        "respondidas_sem_trecho_ouro_citado": wrong,
        "falsas_recusas": refused_ids,
        "citacoes_reparadas_ou_atribuidas": resolved,
        "recusas_corretas": f"{refused_ok}/{len(dev) - n_ans}",
        "forjadas_aceitas": f"{len(leaked)}/{len(ADVERSARIAL)}",
        "forjadas_aceitas_texto": leaked,
    }
    print(
        f"{name:32} fundamentadas={ok}/{n_ans} sem_ouro={wrong} "
        f"recusas={refused_ok}/{len(dev) - n_ans} forjadas_aceitas={len(leaked)}/{len(ADVERSARIAL)}"
    )
Path(__file__).with_name("resultado.json").write_text(
    json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8"
)
