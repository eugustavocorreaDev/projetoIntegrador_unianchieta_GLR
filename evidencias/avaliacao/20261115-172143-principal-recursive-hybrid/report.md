# Relatório de avaliação — 20261115-172143

- Conjunto de teste: `eval\datasets\perguntas_teste.json` (64 perguntas)
- Corpus: `data\raw_docs` · embeddings `nomic-embed-text` · LLM `qwen2.5:3b` · reranker `ms-marco-MultiBERT-L-12`
- chunk_size=800 · chunk_overlap=120 · candidates_k=20
- Comando: `python -m eval.run_eval --reindex --generate`
- Modos: llm_mode=ollama · embed_mode=ollama · qdrant_mode=local

## Recuperação

Baseline: chunking `fixed` + busca `vector`. Um trecho é relevante quando contém o trecho-fonte esperado. `avg_chunk_chars` mostra o tamanho médio dos chunks de cada estratégia: com o mesmo k, chunks menores entregam menos texto ao LLM. O intervalo de 95% (Wilson) indica a incerteza com o número de perguntas usado.

| strategy | mode | mode_effective | baseline | n | avg_chunk_chars | recall@1 | recall@3 | recall@5 | recall@10 | hits@5 | recall@5_ci95 | mrr | mean_latency_ms |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| fixed | vector | vector | True | 50 | 717.9 | 0.38 | 0.7 | 0.8 | 0.9 | 40 | [0.67, 0.89] | 0.5549 | 49.6 |
| fixed | bm25 | bm25 | False | 50 | 717.9 | 0.66 | 0.88 | 0.92 | 0.98 | 46 | [0.81, 0.97] | 0.7741 | 0.1 |
| fixed | hybrid | hybrid | False | 50 | 717.9 | 0.54 | 0.84 | 0.92 | 0.98 | 46 | [0.81, 0.97] | 0.7068 | 46.7 |
| fixed | hybrid_rerank | hybrid_rerank | False | 50 | 717.9 | 0.16 | 0.48 | 0.58 | 0.8 | 29 | [0.44, 0.71] | 0.3653 | 2838.0 |
| recursive | vector | vector | False | 50 | 399.2 | 0.58 | 0.76 | 0.82 | 0.88 | 41 | [0.69, 0.90] | 0.6922 | 49.7 |
| recursive | bm25 | bm25 | False | 50 | 399.2 | 0.7 | 0.86 | 0.9 | 0.96 | 45 | [0.79, 0.96] | 0.7907 | 0.1 |
| recursive | hybrid | hybrid | False | 50 | 399.2 | 0.72 | 0.82 | 0.92 | 0.96 | 46 | [0.81, 0.97] | 0.7877 | 43.4 |
| recursive | hybrid_rerank | hybrid_rerank | False | 50 | 399.2 | 0.28 | 0.48 | 0.56 | 0.82 | 28 | [0.42, 0.69] | 0.4179 | 2302.1 |

## Calibração do limite de relevância (conjunto de desenvolvimento `eval\datasets\perguntas_dev.json`)

| strategy | mode | n_answerable | n_unanswerable | mean_signal_answerable | mean_signal_unanswerable | best_threshold | accuracy |
| --- | --- | --- | --- | --- | --- | --- | --- |
| fixed | hybrid | 12 | 6 | 0.7613 | 0.704 | 0.7071 | 0.8333 |
| recursive | hybrid | 12 | 6 | 0.7603 | 0.7047 | 0.724 | 0.8889 |

Calibrado fora do conjunto de teste. Use `best_threshold` como `MIN_VECTOR_SCORE` e rode a avaliação do conjunto de teste uma única vez com esse valor.

## Geração (recursive + hybrid, top_k=5)

| questions | answer_rate | grounded_rate_snippet | grounded_among_answered | grounded_rate_source | correct_refusal_rate | false_refusal_rate | ungrounded_blocked_rate | mean_citation_coverage |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 64 | 0.62 | 0.58 | 0.9355 | 0.62 | 0.9286 | 0.38 | 0.25 | 0.8333 |

### Candidatos a alucinação (analisar manualmente)

| id | answerable | question | answer | cited_sources |
| --- | --- | --- | --- | --- |
| u07 | False | Quantos workers o fastapi run usa por padrão? | O FastAPI run usa por padrão um único processo. [1] | implantacao.md |
