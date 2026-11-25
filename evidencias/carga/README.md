# Teste de carga

`python scripts/load_test.py --endpoint search|ask --concurrency 1,4,16 --requests 100 --out ...`
Usa as 42 perguntas do conjunto de **desenvolvimento**. Executado em 24/11/2026, na máquina de
desenvolvimento: WSL2, 6 núcleos, 15 GB de RAM, **sem GPU**, stack no Podman (Ollama `qwen2.5:3b` e
`nomic-embed-text`, Qdrant, API com 1 worker `uvicorn`).

## `/search` (recuperação híbrida, sem LLM): 100 requisições por degrau, 0 erros

| Concorrência | req/s | p50 | p95 | p99 |
| --- | --- | --- | --- | --- |
| 1 | 12,1 | 78 ms | 124 ms | 193 ms |
| 4 | 12,0 | 321 ms | 498 ms | 537 ms |
| 8 | 12,5 | 642 ms | 707 ms | 713 ms |
| 16 | 11,6 | 1.310 ms | 1.603 ms | 1.615 ms |
| 32 | 10,8 | 2.878 ms | 3.175 ms | 3.201 ms |

A vazão satura em ~12 req/s desde a concorrência 1 e a latência cresce linearmente: há um gargalo
serial (hipótese: o embedding de cada consulta no Ollama; **não foi isolado**). Sem erros até 32.

## `/ask` (fluxo completo com LLM em CPU): 6 requisições por degrau, 0 erros

| Concorrência | req/s | p50 | p95 (= máximo, n=6) |
| --- | --- | --- | --- |
| 1 | 0,051 | 22,3 s | 31,4 s |
| 2 | 0,104 | 13,8 s | 33,1 s |
| 4 | 0,117 | 15,8 s | 41,2 s |

Com n=6 os percentis são frágeis; o resultado mostra a ordem de grandeza (dezenas de segundos por
resposta em CPU) e que a vazão cresce pouco com a concorrência.

## Limites deste teste

- Um único cliente numa máquina que também roda o Ollama: a carga e o servidor disputam CPU e RAM.
- Não há GPU, então os números de `/ask` não representam o ambiente de produção.
- Sem limitação de taxa na API: acima da capacidade, as requisições enfileiram em vez de serem recusadas.
