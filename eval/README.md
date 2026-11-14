# Avaliação experimental

- `metrics.py`: Recall@k, MRR, calibração do limite de relevância e métricas de geração (testadas na CI).
- `run_eval.py`: executa os experimentos e grava os resultados.
- `datasets/perguntas_teste.json`: conjunto de teste oficial, com 50 perguntas com resposta e trecho-fonte esperados (cobrindo os 20 documentos de `data/raw_docs/`) e 14 sem resposta.
- `results/`: saídas de cada execução (fora do Git; copie para `evidencias/avaliacao/` o que virar evidência).

Comando:

```bash
docker compose run --rm api python -m eval.run_eval --reindex --generate
```

Guia completo, definição de cada métrica e protocolo do conjunto oficial de 50 perguntas: [docs/avaliacao.md](../docs/avaliacao.md).
