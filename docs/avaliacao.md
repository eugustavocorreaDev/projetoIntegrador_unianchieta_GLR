# Guia de avaliação

## O que é medido

| Métrica | Definição | Critério da rubrica |
| --- | --- | --- |
| `recall@k` | Fração das perguntas com resposta em que algum dos k primeiros trechos contém o trecho-fonte esperado | Recall@k por estratégia, em tabela comparativa |
| `hits@5`, `recall@5_ci95` | Contagem de acertos e intervalo de confiança de 95% (Wilson) do Recall@5 | Mostra se a diferença entre estratégias supera a incerteza de 50 perguntas |
| `avg_chunk_chars` | Tamanho médio dos chunks da estratégia | Com o mesmo k, chunks menores entregam menos texto: leia o Recall@k junto com ele |
| `mrr` | Média de 1/posição do primeiro trecho relevante | Complementar |
| `grounded_rate_snippet` | Perguntas com resposta respondidas citando um trecho que contém o trecho-fonte esperado | Respostas fundamentadas na fonte citada |
| `grounded_among_answered` | Fundamentação só entre as perguntas que o sistema respondeu | Separa "respondeu sem fundamento" de "recusou indevidamente" |
| `grounded_rate_source` | Idem, considerando só o arquivo citado | Complementar, menos estrita |
| `correct_refusal_rate` | Perguntas sem resposta que o sistema recusou | Recusas corretas |
| `false_refusal_rate` | Perguntas com resposta que o sistema recusou | Custo da recusa estrita |
| `ungrounded_blocked_rate` | Respostas do LLM descartadas por não citarem fonte | Mostra quantas alucinações em potencial a verificação barrou |
| `mean_citation_coverage` | Fração das frases da resposta que têm citação | Qualidade das citações |
| `hallucination_candidates` | IDs respondidos que não deveriam ter sido (sem resposta ou sem fonte correta) | Ponto de partida da análise de alucinações |

**Baseline:** chunking `fixed` + busca `vector`, tanto na recuperação quanto na geração (`--gen-strategy fixed --gen-mode vector`). **Comparações:** 2 estratégias de chunking × 4 modos de recuperação.

**Conjuntos:** `perguntas_teste.json` (50 com resposta e 14 sem; só para o resultado) e `perguntas_dev.json` (12 com resposta e 6 sem; só para calibrar). Um teste automatizado garante que os dois não compartilham perguntas nem trechos esperados.

## Como reproduzir (um comando)

> Rode sempre no **modo oficial** (`LLM_MODE=ollama`, `EMBED_MODE=ollama`). O relatório registra os modos e marca como inválida qualquer execução em `mock`/`hash`.

Com o projeto no ar (`docker compose up`):

```bash
docker compose run --rm api python -m eval.run_eval --reindex --generate
```

Ou fora do Docker, com o `.venv` ativo e Ollama e Qdrant acessíveis:

```bash
python -m eval.run_eval --reindex --generate
```

No caminho Windows, sem Docker, use um índice próprio, para não disputar a trava do `.qdrant_local/` com a API. Foi assim que a avaliação oficial de 15/11/2026 foi gerada:

```powershell
$env:QDRANT_MODE="local"; $env:QDRANT_PATH=".cache/qdrant_eval"; $env:LLM_MODE="ollama"; $env:EMBED_MODE="ollama"
.\.venv\Scripts\python.exe -m eval.run_eval --reindex --generate
.\.venv\Scripts\python.exe -m eval.run_eval --generate --strategies fixed --modes vector --gen-strategy fixed --gen-mode vector
```

A execução principal leva cerca de 30 min em CPU, e o baseline mais 30 min.

Opções úteis:

```bash
python -m eval.run_eval --strategies recursive --modes hybrid hybrid_rerank --k 1 3 5
python -m eval.run_eval --dataset eval/datasets/perguntas_teste.json --generate --gen-mode hybrid_rerank
```

## Saídas

Em `eval/results/<AAAAMMDD-HHMMSS>/`:

| Arquivo | Conteúdo |
| --- | --- |
| `retrieval_summary.csv` | Uma linha por estratégia × modo, com recall@k, MRR e latência média |
| `retrieval_per_question.csv` | Posição do primeiro trecho relevante por pergunta, usada na análise de erros |
| `generation_per_question.csv` | Resposta, resposta bruta do LLM, citações e decisão por pergunta |
| `summary.json` | Tudo acima, mais a configuração completa (modelos, chunk_size etc.) e o comando usado |
| `report.md` | Tabelas prontas para o trabalho de pesquisa |

Os resultados ficam fora do Git por padrão. Para virar evidência, copie a pasta da execução escolhida para `evidencias/avaliacao/` e cite o comando no `evidencias/README.md`.

## Calibração do limite de relevância

A avaliação também calcula, no **conjunto de desenvolvimento** e com o modo de recuperação configurado, a mesma estatística que o filtro usa em produção (`relevance_signal`: maior cosseno entre os trechos enviados ao LLM), e sugere `best_threshold`, o limite que melhor separa as perguntas com e sem resposta. O script se recusa a calibrar com o conjunto de teste. Para usar:

1. Rode a avaliação com um **conjunto de desenvolvimento** (`--dataset`), nunca com o oficial.
2. Defina `MIN_VECTOR_SCORE=<best_threshold>` no `.env`.
3. Rode de novo e compare `correct_refusal_rate` e `false_refusal_rate`.

## Protocolo para o resultado oficial

1. O conjunto oficial `eval/datasets/perguntas_teste.json` (50 perguntas com resposta e trecho-fonte esperados, cobrindo os 20 documentos, e 14 sem resposta) está **congelado** desde a versão 2.1.0: o campo `questions_sha256` é conferido pelo teste `test_test_set_is_frozen`, e qualquer mudança exige subir a versão, o que fica explícito no histórico do Git. A revisão 2.1.0 (14 perguntas reescritas para reduzir o viés lexical) foi feita **antes** da avaliação oficial e não mexeu nos trechos esperados.
2. Ajustes de parâmetros (ex.: `MIN_VECTOR_SCORE`) usam perguntas novas de desenvolvimento, nunca as do conjunto oficial. Se o conjunto oficial for usado para calibrar, isso precisa ser declarado como limitação no trabalho de pesquisa.
3. Na avaliação final, roda-se uma vez sobre o conjunto oficial, com o comando registrado em `summary.json`.
4. Os casos em `hallucination_candidates` e as perguntas com `relevant_rank` vazio entram na análise de erros (`evidencias/falhas/`).
5. Uma regra da verificação de citações só muda se a mudança for calibrada no conjunto de desenvolvimento e testada contra respostas forjadas (`evidencias/avaliacao/calibracao-verificacao-dev/`). Foi assim que a regra de cobertura foi avaliada e mantida em 15/11/2026.

## Resultado oficial (15/11/2026)

Os números estão no [checklist, seção 3](checklist-enunciado.md#3-resultados-oficiais-15112026), e as saídas brutas em `evidencias/avaliacao/`.
