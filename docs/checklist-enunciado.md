# Checklist de conformidade com o enunciado (Tema 4)

Este documento confronta cada exigência de `Projetos-IA-Programacao-Enunciados.md` com o que o repositório entrega e diz **como conferir** cada item. A auditoria automática equivalente é o subagente `.claude/agents/auditor-rag-enunciado.md`.

Situação em **15/11/2026**, depois da avaliação oficial com o Ollama real.

| Legenda | Significado |
| --- | --- |
| ✅ Atendido | Pronto e verificável |
| 🟡 Parcial | Implementado; falta uma prova ou uma execução |
| ⏳ Pendente | Exige ação fora do código (gravação, escrita, histórico do Git) |

## 1. Prioridades e plano executado

As decisões de escopo foram validadas com o professor: a base própria de 20 documentos, o grupo de 3 integrantes e o uso do Claude Code. Os itens técnicos foram priorizados pelo peso na rubrica (critérios 2 e 3 valem 40 pontos) e pelo risco.

| # | Prioridade | Item | Situação | Onde está a prova |
| --- | --- | --- | --- | --- |
| P1 | Crítica | Avaliação oficial com geração (respostas fundamentadas e recusas corretas) | ✅ | `evidencias/avaliacao/20261115-172143-principal-recursive-hybrid/` |
| P2 | Crítica | Baseline com geração, para comparação | ✅ | `evidencias/avaliacao/20261115-201630-baseline-fixed-vector/` |
| P3 | Crítica | Conjunto de teste revisado e **congelado** antes da avaliação | ✅ | Versão 2.1.0, `questions_sha256` e teste `test_test_set_is_frozen` |
| P4 | Alta | Casos de falha (3 ou mais) com alucinação real e correção | ✅ | `evidencias/falhas/casos-de-falha.md` (5 casos) |
| P5 | Alta | Logs de uma execução completa | ✅ | `evidencias/logs/execucao-completa.jsonl` (128 perguntas) |
| P6 | Alta | Bug da verificação que descartava respostas "explicação + código" | ✅ | Caso de falha 5, testes de regressão em `test_grounding.py` |
| P7 | Média | Interface em estilo chat, com responsividade | ✅ | Aba Perguntar; `tests/test_ui.py` (17 testes) |
| P8 | Média | Leitura de prints também no caminho Docker | 🟡 | `docker-compose.yml` (Ollama 0.12.6, `PULL_VISION_MODEL`); falta executar o compose |
| P9 | Média | Calibração da verificação no conjunto de desenvolvimento | ✅ | `evidencias/avaliacao/calibracao-verificacao-dev/` |
| P10 | — | Vídeo, capturas, tag `v1.0`, PDF ABNT, commits de todos | ⏳ | Fora do código; ver seção 4 |

## 2. Tema 4: exigências específicas

| Exigência | Situação | Como conferir |
| --- | --- | --- |
| Indexar documentação, buscar, responder com citação, interface web | ✅ | Aba **Perguntar**: cada resposta traz selos `[n]` e "Fontes citadas" |
| Documentação de código aberto (base própria validada com o professor) | ✅ | Aba **Documentos**: 20 arquivos, 94 chunks `fixed` e 136 `recursive` |
| Stack: Qdrant, Ollama, reranker, FastAPI, Streamlit | ✅ | `GET /health` e a barra lateral |
| MVP: responder com citação às 50 perguntas, com a recuperação medida | ✅ | `generation_per_question.csv` da avaliação oficial |
| Comparar estratégias de chunking | ✅ | `retrieval_summary.csv`: `fixed` × `recursive` em 4 modos e k = 1, 3, 5, 10 |
| Busca híbrida e reranking | ✅ | Seção 3: a híbrida é a melhor; o reranker piora (ADR 002) |
| Dizer que não sabe | ✅ | 92,9% de recusas corretas (13/14) |
| 50 perguntas com resposta e trecho-fonte, escritas antes de ajustar | ✅ | Conjunto 2.1.0, congelado por hash antes da avaliação oficial. O histórico da revisão está em `docs/dados-e-modelos.md` |
| Recall@k por estratégia, em tabela comparativa | ✅ | Seção 3 e `retrieval_summary.csv` |
| Taxa de respostas fundamentadas e de recusas corretas | ✅ | Seção 3 e `summary.json` |
| Análise das alucinações e da correção aplicada | ✅ | Casos de falha 3 (alucinação do u07, correção tentada e medida) e 4 (calibração) |

## 3. Resultados oficiais (15/11/2026)

- **Comando:** `python -m eval.run_eval --reindex --generate`, e para o baseline `--generate --strategies fixed --modes vector --gen-strategy fixed --gen-mode vector`.
- **Condições:** Ollama real (`nomic-embed-text` e `qwen2.5:3b`), conjunto de teste 2.1.0 (50 perguntas com resposta e 14 sem), top-5.

**Recuperação (Recall@k, 50 perguntas):**

| Modo | `fixed` R@1 | `fixed` R@5 | `fixed` R@10 | `recursive` R@1 | `recursive` R@5 | `recursive` R@10 | MRR `recursive` |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `vector` (baseline) | 38% | 80% | 90% | 58% | 82% | 88% | 0,69 |
| `bm25` | 66% | 92% | 98% | 70% | 90% | 96% | 0,79 |
| **`hybrid` (padrão)** | 54% | **92%** | 98% | **72%** | **92%** | 96% | **0,79** |
| `hybrid_rerank` | 16% | 58% | 80% | 28% | 56% | 82% | 0,42 |

O intervalo de confiança de 95% (Wilson) do Recall@5 da híbrida é [0,81; 0,97]; o do baseline, [0,67; 0,89].

**Geração (64 perguntas):**

| Métrica | Baseline `fixed + vector` | **Padrão `recursive + hybrid`** |
| --- | --- | --- |
| Perguntas respondidas | 52% | **62%** |
| Respostas fundamentadas (no total) | 42% | **58%** |
| Fundamentadas, entre as respondidas | 80,8% | **93,5%** |
| Recusas corretas | 92,9% | 92,9% |
| Falsas recusas | 48% | **38%** |
| Candidatas a alucinação | 2 (q36, u07) | **1** (u07) |

**Leitura:**
- A recuperação híbrida com chunking recursivo supera o baseline em todas as métricas de geração, menos nas recusas, onde empata.
- O reranker `ms-marco-MultiBERT-L-12` piora a recuperação (ADR 002, caso 1).
- O ponto fraco são as **falsas recusas**: a verificação de citações descarta respostas corretas em que o modelo de 3B cita poucas frases (caso 4). A calibração no conjunto de desenvolvimento mostrou que afrouxar a regra deixaria passar respostas forjadas, por isso ela foi mantida.
- A única alucinação que passou (u07) mostra o limite da verificação lexical (caso 3).

## 4. Rubrica (critérios 1 a 7)

| # | Critério (peso) | Situação | O que existe | O que falta |
| --- | --- | --- | --- | --- |
| 1 | Problema, arquitetura e planejamento (10) | ✅ | README com problema e métricas; `docs/arquitetura.md` com diagramas, camadas e 3 ADRs (a ADR 002 foi revisada com dados) | — |
| 2 | Funcionamento do MVP e desafio do tema (20) | 🟡 | Fluxo de ponta a ponta com o Ollama real, avaliação oficial, auditoria ao vivo da interface | Vídeo |
| 3 | Avaliação experimental (20) | ✅ | Conjunto de teste congelado e separado do de calibração, baseline, 2 estratégias × 4 modos, análise de erros e resultados reproduzíveis | — |
| 4 | Qualidade de engenharia (15) | 🟡 | 190 testes, 94% de cobertura, CI verde nos 3 pushes (inclusive o build das imagens), erros tratados, sem segredos, custo zero | Executar `docker compose up` de ponta a ponta |
| 5 | Uso crítico da IA (10) | 🟡 | `PROMPTS.md` com 8 interações, erros da IA, correções medidas e descartes | Chegar a 10 ou mais |
| 6 | Documentação ABNT e técnica, e demonstração (15) | 🟡 | `docs/` completo e instalação assistida | PDF ABNT e vídeo |
| 7 | Contribuição individual e defesa oral (10) | ⏳ | Papéis no README | Commits e PRs de todos os integrantes |

## 5. Evidências obrigatórias (`evidencias/`)

| # | Evidência | Situação |
| --- | --- | --- |
| 1 | Vídeo de 3 a 5 min, do `docker compose up` ao fluxo principal | ⏳ |
| 2 | CI verde na tag `v1.0` | 🟡 A CI está verde no `main`; falta a tag |
| 3 | Resultados da avaliação | ✅ |
| 4 | Logs de uma execução completa | ✅ |
| 5 | Capturas de tela (5 ou mais, com uma falha tratada) | ⏳ |
| 6 | Casos de falha (3 ou mais) | ✅ (5 casos) |
| 7 | Histórico do Git com commits de todos e PRs revisados | ⏳ |

## 6. Como validar você mesmo

1. **Subir o sistema:** `powershell -ExecutionPolicy Bypass -File scripts\instalar.ps1`. No final, ele valida o sistema com duas perguntas.
2. **Aba Documentos:** os 20 arquivos e os chunks de cada um.
3. **Aba Perguntar:**
   - "Como compartilho fixtures entre arquivos de teste?" precisa citar `pytest-fixtures.md`;
   - "O que é HTML?" precisa ser recusada;
   - "Quantos workers o fastapi run usa por padrão?" reproduz a alucinação do caso 3.
4. **Aba Validação:** a parte 1 reproduz o Recall@5 de cerca de 92%, e a parte 2 reproduz as taxas de geração.
5. **Avaliação oficial:** `python -m eval.run_eval --reindex --generate` (cerca de 30 min em CPU). No Windows sem Docker, use `QDRANT_MODE=local` e um `QDRANT_PATH` próprio, para não disputar a trava do índice com a API.
6. **Testes:** `.\.venv\Scripts\python.exe -m pytest` deve terminar com `190 passed`.
