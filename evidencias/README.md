# Índice de evidências

Roteiro de conferência para o professor: cada afirmação do trabalho de pesquisa aponta para uma evidência que pode ser reproduzida.

> **Regra:** toda evidência sai da execução real do projeto na tag `v1.0`, **com o Ollama ativo** (`llm_mode=ollama` e `embed_mode=ollama`). Saídas do Modo de Visualização (mock/hash), inclusive o `logs/app.log` e o `.qdrant_local/` produzidos nele, não valem como evidência. Capturas editadas, números inventados ou resultados copiados de outro lugar são fraude acadêmica. Antes de versionar, confira que nada mostra chaves, senhas ou dados pessoais.

## 1. Evidências exigidas

| # | Evidência | Onde fica | Como gerar | Obrigatória | Status |
| --- | --- | --- | --- | --- | --- |
| 1 | Execução gravada (3 a 5 min, tela inteira, do `docker compose up` ao fluxo principal) | `video/demo-v1.0.mp4` ou link em `video/LINK.md` | Gravar com OBS Studio: `docker compose down -v`, `docker compose up --build`, pergunta respondida, pergunta recusada, troca de estratégia | Sim | Pendente |
| 2 | Integração contínua verde na tag `v1.0` | `ci/LINK.md` (URL da execução) e `ci/ci-v1.0.png` | GitHub → Actions → execução da tag `v1.0` | Sim | Pendente |
| 3 | Resultados da avaliação (tabelas, gráficos, CSV e JSON brutos) | `avaliacao/<AAAAMMDD-HHMMSS>/` | `docker compose run --rm api python -m eval.run_eval --reindex --generate` e, para o baseline, `... --generate --gen-strategy fixed --gen-mode vector`; copiar as duas pastas de `eval/results/` | Sim | **Feito (15/11):** `avaliacao/20261115-172143-principal-recursive-hybrid/` e `avaliacao/20261115-201630-baseline-fixed-vector/`, gerados no caminho Windows com o Ollama real (`QDRANT_MODE=local`), e `avaliacao/calibracao-verificacao-dev/` |
| 4 | Logs de uma execução completa, com data e hora | `logs/execucao-completa.jsonl` | Trecho de `logs/app.log` cobrindo ingestão (`index.completed`) e perguntas (`ask.completed`), coerente com o vídeo | Sim | **Feito (15/11):** 138 eventos das duas avaliações oficiais (128 perguntas). Falta um trecho da sessão do vídeo |
| 5 | Capturas de tela (5 situações ou mais, incluindo uma falha tratada) | `prints/` | Ver a lista em `docs/manual-usuario.md` (01 a 09) | Não | Pendente |
| 6 | Casos de falha (3 ou mais, com análise da causa) | `falhas/casos-de-falha.md` | A partir de `hallucination_candidates` e de `relevant_rank` vazio na avaliação | Sim | **Feito (15/11):** 5 casos, incluindo a alucinação real do u07 e as correções medidas |
| 7 | Histórico do Git (commits de todos e PRs revisados por outro membro) | `git/LINK.md` (links do histórico e dos PRs) | GitHub → Insights → Contributors e lista de PRs fechados | Sim | Pendente |
| 8 | Este índice | `README.md` | Atualizar a cada evidência nova | Sim | Em andamento |

## 2. Afirmações do trabalho de pesquisa → evidência

Preencha uma linha para cada número ou afirmação de funcionamento citado no trabalho em ABNT.

| Afirmação no trabalho (seção) | Evidência | Como reproduzir |
| --- | --- | --- |
| O sistema sobe com um comando, sem serviço pago (3. Metodologia) | 1 (vídeo, 00:00–01:30) | `docker compose up --build` |
| Recall@5 de cada estratégia × modo (4. Resultados, Tabela 1) | 3 (`retrieval_summary.csv`) | `python -m eval.run_eval --reindex` |
| Taxa de respostas fundamentadas e de recusas corretas (4. Resultados, Tabela 2) | 3 (`summary.json` → `generation`) | `python -m eval.run_eval --generate` |
| Respostas sem citação são bloqueadas (4. Resultados) | 4 (eventos `decision: refused:ungrounded_answer`) e testes `test_grounding.py` | Pergunta descrita num dos casos de `falhas/casos-de-falha.md` |
| Análise dos casos de alucinação (4.x) | 6 | Casos descritos em `falhas/casos-de-falha.md` |
| A CI roda lint e testes a cada push (3. Metodologia) | 2 | Abrir a execução da tag `v1.0` |

## 3. Estrutura

```text
evidencias/
├── README.md            este índice
├── video/               evidência 1
├── ci/                  evidência 2
├── avaliacao/           evidência 3
├── logs/                evidência 4
├── prints/              evidência 5
├── falhas/              evidência 6 (casos-de-falha.md)
└── git/                 evidência 7
```
