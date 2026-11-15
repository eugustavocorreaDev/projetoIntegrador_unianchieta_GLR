"""Calibra a regra de verificação no conjunto de DESENVOLVIMENTO (nunca no de teste)."""

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]  # raiz do repositório
sys.path.insert(0, str(ROOT / "src"))
from generation.grounding import (  # noqa: E402
    extract_citation_ids,
    is_refusal,
    statements,
    support_ratio,
)


def decide(raw, chunk_texts, min_cov, check_uncited, min_support=0.3):
    """Devolve (respondeu, fontes citadas) para uma variação da regra."""
    n = len(chunk_texts)
    valid = [i for i in extract_citation_ids(raw) if 1 <= i <= n]
    if not valid:
        return False, []
    claims = [s for s in statements(raw) if not is_refusal(s)]
    if is_refusal(raw) and not claims:
        return False, []
    cited = [c for c in claims if any(1 <= i <= n for i in extract_citation_ids(c))]
    coverage = len(cited) / len(claims) if claims else 0.0
    if coverage < min_cov:
        return False, []
    checked = unsupported = 0
    for claim in claims:
        nums = [i for i in extract_citation_ids(claim) if 1 <= i <= n]
        if nums:
            texts = [chunk_texts[i - 1] for i in nums]
        elif check_uncited:
            texts = chunk_texts
        else:
            continue
        checked += 1
        unsupported += support_ratio(claim, texts) < min_support
    if checked and unsupported * 2 > checked:
        return False, []
    return True, valid


dev = json.loads(Path(__file__).with_name("dev_respostas.json").read_text(encoding="utf-8"))
ADVERSARIAL = [  # conhecimento externo com citação "de fachada": tem de ser barrado sempre
    "HTML é uma linguagem de marcação usada para estruturar páginas web [1].",
    "Use o Django REST Framework com serializers [1]. Ele gera a API automaticamente.",
    "O FastAPI usa bcrypt com 12 rodadas por padrão [1]. Isso garante senhas seguras.",
    "JavaScript é executado no navegador [2]. Ele manipula o DOM da página.",
]
POLICIES = [(0.5, False), (0.25, False), (0.0, False), (0.5, True), (0.25, True), (0.0, True)]
results = {}
for min_cov, check_uncited in POLICIES:
    ok_ans = ok_un = wrong_src = 0
    for q in dev:
        texts = [f"{c['source']} {c['section']}\n{c['text']}" for c in q["chunks"]]
        answered, ids = decide(q["raw_answer"], texts, min_cov, check_uncited)
        sources = {q["chunks"][i - 1]["source"] for i in ids}
        if q["answerable"]:
            ok_ans += answered and q["expected_source"] in sources
            wrong_src += answered and q["expected_source"] not in sources
        else:
            ok_un += not answered
    texts0 = [f"{c['source']} {c['section']}\n{c['text']}" for c in dev[0]["chunks"]]
    leaked = sum(decide(a, texts0, min_cov, check_uncited)[0] for a in ADVERSARIAL)
    n_ans = sum(q["answerable"] for q in dev)
    key = f"cobertura>={min_cov:.2f} {'+ confere frases sem citação' if check_uncited else '(atual)' if min_cov == 0.5 else ''}"
    results[key] = {
        "respostas_fundamentadas": f"{ok_ans}/{n_ans}",
        "fonte_errada": wrong_src,
        "recusas_corretas": f"{ok_un}/{len(dev) - n_ans}",
        "falsas_aceitas_adversariais": f"{leaked}/{len(ADVERSARIAL)}",
    }
    print(f"{key:55} fundamentadas={ok_ans}/{n_ans} fonte_errada={wrong_src} "
          f"recusas={ok_un}/{len(dev) - n_ans} adversariais_aceitas={leaked}/{len(ADVERSARIAL)}")
Path(__file__).with_name("resultado.json").write_text(
    json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8"
)
