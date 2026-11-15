# Relatório de avaliação — 20261115-201630

- Conjunto de teste: `eval\datasets\perguntas_teste.json` (64 perguntas)
- Corpus: `data\raw_docs` · embeddings `nomic-embed-text` · LLM `qwen2.5:3b` · reranker `ms-marco-MultiBERT-L-12`
- chunk_size=800 · chunk_overlap=120 · candidates_k=20
- Comando: `python -m eval.run_eval --generate --strategies fixed --modes vector --gen-strategy fixed --gen-mode vector`
- Modos: llm_mode=ollama · embed_mode=ollama · qdrant_mode=local

## Recuperação

Baseline: chunking `fixed` + busca `vector`. Um trecho é relevante quando contém o trecho-fonte esperado. `avg_chunk_chars` mostra o tamanho médio dos chunks de cada estratégia: com o mesmo k, chunks menores entregam menos texto ao LLM. O intervalo de 95% (Wilson) indica a incerteza com o número de perguntas usado.

| strategy | mode | mode_effective | baseline | n | avg_chunk_chars | recall@1 | recall@3 | recall@5 | recall@10 | hits@5 | recall@5_ci95 | mrr | mean_latency_ms |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| fixed | vector | vector | True | 50 | 717.9 | 0.38 | 0.7 | 0.8 | 0.9 | 40 | [0.67, 0.89] | 0.5549 | 46.1 |

## Calibração do limite de relevância (conjunto de desenvolvimento `eval\datasets\perguntas_dev.json`)

| strategy | mode | n_answerable | n_unanswerable | mean_signal_answerable | mean_signal_unanswerable | best_threshold | accuracy |
| --- | --- | --- | --- | --- | --- | --- | --- |
| fixed | hybrid | 12 | 6 | 0.7613 | 0.704 | 0.7071 | 0.8333 |

Calibrado fora do conjunto de teste. Use `best_threshold` como `MIN_VECTOR_SCORE` e rode a avaliação do conjunto de teste uma única vez com esse valor.

## Geração (fixed + vector, top_k=5)

| questions | answer_rate | grounded_rate_snippet | grounded_among_answered | grounded_rate_source | correct_refusal_rate | false_refusal_rate | ungrounded_blocked_rate | mean_citation_coverage |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 64 | 0.52 | 0.42 | 0.8077 | 0.5 | 0.9286 | 0.48 | 0.2188 | 0.7901 |

### Candidatos a alucinação (analisar manualmente)

| id | answerable | question | answer | cited_sources |
| --- | --- | --- | --- | --- |
| q36 | True | O que o Pydantic faz quando recebe o texto "19.90" em um campo float? | O Pydantic, ao receber o texto "19.90" em um campo float, realiza uma conversão automática para o número 19.9, seguindo a configuração de modo flexível. [1] | configuracoes.md |
| u07 | False | Quantos workers o fastapi run usa por padrão? | O FastAPI run usa por padrão 1 worker. [3] | implantacao.md |
