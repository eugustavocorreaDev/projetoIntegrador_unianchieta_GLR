# Checklist de conformidade com o enunciado (Tema 4)

Confronta cada exigência de `Projetos-IA-Programacao-Enunciados.md` com o que o repositório entrega e diz **como conferir**. Revise antes de cada marco e antes da tag `v1.0`. O subagente `.claude/agents/auditor-rag-enunciado.md` faz esta auditoria de forma automática.

**Situação em 14/11/2026.**

| Legenda | Significado |
| --- | --- |
| ✅ Atendido | Pronto e verificável |
| 🟡 Parcial | Implementado, mas falta prova ou execução oficial |
| ⏳ Pendente | Depende do grupo (execução, gravação, escrita) |

## 1. Tema 4: exigências específicas

| Exigência do enunciado | Situação | Onde está | Como conferir |
| --- | --- | --- | --- |
| Indexar uma documentação, buscar, responder com citações e ter interface web | ✅ | `src/`, interface em <http://localhost:8501> | Aba **Perguntar**: toda resposta traz selos `[n]` e "Fontes citadas" |
| Documentação "de código aberto, grande" | 🟡 | `data/raw_docs/` (20 documentos sobre FastAPI, Pydantic, pytest e Docker, escritos para o projeto) | Aba **Documentos**. Confirmar com o professor se a base própria vale. A documentação oficial do FastAPI pode ser usada com `scripts/download_fastapi_docs.py` |
| Stack: Qdrant, Ollama, reranker, FastAPI, Streamlit | ✅ | `docker-compose.yml`, `src/` | `GET /health` e a barra lateral da interface |
| MVP até 14/11: responder com citação a 50 perguntas, com a recuperação medida | 🟡 | `eval/datasets/perguntas_teste.json`, aba **Validação** | A recuperação foi medida ao vivo (seção 4). Falta rodar a parte 2 da aba Validação, ou `eval/run_eval.py --generate`, nas 50 perguntas |
| Comparar estratégias de chunking | ✅ | `src/ingestion/chunking.py` (`fixed` × `recursive`) | Aba **Documentos** → **Chunks** (troque a estratégia na barra lateral) e aba **Validação** |
| Busca híbrida e reranking | ✅ | `src/retrieval/` | Seção 4: a comparação mostrou que o reranker piora a busca, e o padrão virou `hybrid` (ADR 002) |
| Dizer que não sabe quando a resposta não está na documentação | ✅ | `src/generation/grounding.py`, `prompts.py`, `core/pipeline.py` | Pergunte "O que é HTML?" ou "Como faz um ovo frito?" e veja o cartão amarelo de recusa |
| 50 perguntas com resposta e trecho-fonte esperados, **escritas antes de ajustar o sistema** | 🟡 | `perguntas_teste.json` (50 com resposta e 14 sem) | Um teste automatizado confere que todo trecho esperado existe na base. A anterioridade só fica provada pelo histórico do Git, e o dataset foi refeito quando a base foi ampliada: declarem isso no trabalho |
| Recall@k por estratégia, em tabela comparativa | 🟡 | `eval/run_eval.py`, aba **Validação** | Os números ao vivo estão na seção 4. Falta salvar a saída oficial em `evidencias/avaliacao/` |
| Taxa de respostas fundamentadas e de recusas corretas | ⏳ | Aba **Validação**, parte 2, e `eval/run_eval.py --generate` | Rodar com o Ollama ativo e salvar o CSV |
| Análise dos casos de alucinação e da correção aplicada | 🟡 | `evidencias/falhas/casos-de-falha.md` | 2 casos reais registrados (reranker e recusa indevida). Faltam 1 ou mais, de preferência uma alucinação |

## 2. Rubrica (critérios 1 a 7)

| # | Critério (peso) | Situação | O que existe | O que falta |
| --- | --- | --- | --- | --- |
| 1 | Problema, arquitetura e planejamento (10) | 🟡 | README com problema e métricas; `docs/arquitetura.md` com diagramas, camadas e 3 ADRs | Provar os marcos: o Marco 1 (24/10, repositório e CI) é anterior ao primeiro commit |
| 2 | Funcionamento do MVP e desafio do tema (20) | 🟡 | Fluxo de ponta a ponta validado com o Ollama real (instalador `-Testar`, abas da interface) | Vídeo e evidências salvas |
| 3 | Avaliação experimental (20) | 🟡 | Conjunto de teste separado do de calibração, baseline `fixed + vector`, medição real da recuperação | Rodar `eval/run_eval.py` completo, com `--generate`, e versionar as saídas |
| 4 | Qualidade de engenharia (15) | 🟡 | 185 testes automatizados, 94% de cobertura, CI configurada, Docker, erros tratados (422/404/409/503), sem segredos, custo zero | CI verde no GitHub (ainda sem push) e o caminho Docker nunca executado |
| 5 | Uso crítico da IA (10) | 🟡 | `PROMPTS.md` com 7 interações, erros da IA e descartes | Chegar a 10 ou mais interações, de todos os integrantes |
| 6 | Documentação ABNT e técnica, e demonstração (15) | 🟡 | `docs/` completo, README com instalação assistida | PDF ABNT e vídeo |
| 7 | Contribuição individual e defesa oral (10) | ⏳ | Papéis definidos no README | Commits e PRs de **todos** os integrantes, revisão cruzada e preparo para a defesa |

## 3. Evidências obrigatórias (`evidencias/`)

| # | Evidência | Situação | Como gerar |
| --- | --- | --- | --- |
| 1 | Vídeo de 3 a 5 min, do `docker compose up` ao fluxo principal | ⏳ | Precisa do Docker Desktop: `scripts\instalar.ps1 -ComDocker` |
| 2 | CI verde na tag `v1.0` | ⏳ | Push para o GitHub e a tag `v1.0` |
| 3 | Resultados da avaliação (tabelas, CSV, JSON) | 🟡 | `python -m eval.run_eval --reindex --generate`; enquanto isso, o "Baixar CSV" da aba Validação |
| 4 | Logs de uma execução completa | ⏳ | Copiar trechos de `logs/app.log` de uma sessão com o Ollama ativo |
| 5 | Capturas de tela (5 ou mais, com uma falha tratada) | ⏳ | Lista em `docs/manual-usuario.md` (01 a 09) |
| 6 | Casos de falha (3 ou mais) | 🟡 | 2 registrados em `evidencias/falhas/casos-de-falha.md` |
| 7 | Histórico do Git com commits de todos e PRs revisados | ⏳ | Cada integrante abre PRs revisados por outro |

## 4. Resultados medidos até agora (preliminares)

Medidos em 14/11/2026 com a API real (embeddings `nomic-embed-text` via Ollama), as 50 perguntas com resposta e top-5, pela aba Validação (`POST /validation/retrieval`). A regra de acerto é a mesma de `eval/run_eval.py`. Para virar resultado oficial, a avaliação precisa ser reexecutada pelo script e salva em `evidencias/avaliacao/`.

| Modo de recuperação | Recall@5 `fixed` | MRR `fixed` | Recall@5 `recursive` | MRR `recursive` |
| --- | --- | --- | --- | --- |
| `vector` (baseline) | 90% | 0,64 | 90% | 0,80 |
| `bm25` | 98% | 0,83 | 92% | 0,84 |
| `hybrid` (**padrão**) | **98%** | 0,78 | **96%** | **0,86** |
| `hybrid_rerank` | 58% | 0,35 | 60% | 0,41 |

**Leitura:**
- A busca híbrida supera a vetorial pura nas duas estratégias.
- O reranker `ms-marco-MultiBERT-L-12` piora a ordem, e a causa foi investigada (ADR 002, caso de falha 1).
- Os trechos esperados são literais, o que favorece o BM25. Isso é uma limitação a discutir no trabalho.

## 5. Como validar você mesmo, em 5 minutos

1. Suba o projeto: `powershell -ExecutionPolicy Bypass -File scripts\instalar.ps1`. No final, ele faz duas perguntas de teste.
2. **Aba Documentos:** confira os 20 arquivos e os chunks de cada um. É só isto que o assistente sabe.
3. **Aba Perguntar:** pergunte algo coberto ("Como compartilho fixtures entre arquivos de teste?") e algo fora da base ("O que é HTML?"). A primeira precisa citar `pytest-fixtures.md`, e a segunda precisa ser recusada.
4. **Aba Validação, parte 1:** clique em "Rodar as 50 perguntas com resposta". O Recall@5 deve ficar próximo da seção 4.
5. **Aba Validação, parte 2:** rode as 14 perguntas sem resposta e algumas com resposta, e baixe o CSV para `evidencias/avaliacao/`.
6. **Testes automatizados:** `.\.venv\Scripts\python.exe -m pytest`.
