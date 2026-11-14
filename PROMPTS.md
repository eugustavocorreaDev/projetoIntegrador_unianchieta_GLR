# Registro de uso de IA na programação

Regras do enunciado: pelo menos **10 interações relevantes**, cada uma com o prompt, um resumo da resposta e o que foi **aceito, corrigido ou descartado, com o motivo**. O grupo responde por todo o código, independentemente de quem ou do que o escreveu. Projeto em grupo, com 3 integrantes; cada interação registra quem a conduziu.

## Modelo de registro

```markdown
## Interação N: título curto
- **Data:** AAAA-MM-DD · **Integrante:** nome · **Ferramenta:** nome e modelo/plano
- **Objetivo:** o que se queria obter
- **Prompt:** texto do prompt (literal ou resumido, com o essencial)
- **Resumo da resposta:** o que a IA produziu
- **Aceito:** o que entrou no projeto, e por quê
- **Corrigido:** o que a IA errou e como foi consertado (com teste ou evidência)
- **Descartado:** o que foi jogado fora, e por quê
- **Revisão humana:** integrante que revisou (nunca quem conduziu a interação), PR e resultado da CI
```

---

## Interação 1: estrutura completa e MVP do Tema 4

- **Data:** 2026-11-14 · **Integrante:** Gustavo Correa Lima · **Ferramenta:** Claude Code (Anthropic), modelo Claude Opus 5.5
- **Objetivo:** criar a estrutura do repositório exigida no enunciado e um MVP funcional do RAG, local e a custo zero.
- **Prompt (resumido):** "Atue como engenheiro de software sênior e arquiteto de sistemas de IA. Leia o `Projetos-IA-Programacao-Enunciados.md` (visão geral, regras de IA, itens de envio, evidências, documentação, rubrica e Tema 4). Construa o MVP do Tema 4 com Python 3.11, FastAPI, Streamlit, Qdrant e Ollama (`nomic-embed-text` e um modelo de 3B), 100% local. Requisitos: ingestão com pelo menos duas estratégias de chunking comparáveis; busca vetorial combinada com BM25 ou reranking leve; geração que responda só com base nos trechos, cite arquivo e seção e recuse com 'Não encontrei essa informação na documentação indexada'. Crie README (com Mermaid), PROMPTS.md, LICENSE MIT, docker-compose (api, frontend, qdrant, ollama), CI com lint e pytest, `src/` modular, `tests/` com mocks do LLM, `eval/` com Recall@k, taxa de citação e de recusa e dataset de exemplo, `evidencias/README.md`, `docs/`, `.gitignore` e `.env.example`. Sem placeholders. No final, dê os comandos git."
- **Resumo da resposta:** a IA leu o enunciado, propôs a arquitetura e gerou:
  - `src/` em camadas (`core`, `ingestion`, `retrieval`, `generation`, `api`, `ui`), com chunking `fixed` e `recursive`, BM25 próprio, fusão RRF, reranker FlashRank, prompt com trechos numerados e uma verificação de citações em código que transforma resposta sem citação em recusa;
  - 85 testes iniciais com dublês (embedder por hashing, LLM falso, Qdrant em memória);
  - script de avaliação com Recall@k, MRR, taxas de fundamentação e de recusa e calibração do limite de relevância;
  - corpus de exemplo em português (9 arquivos) e dataset de 40 perguntas (29 com resposta, 11 sem, incluindo armadilhas), depois ampliado na interação 3;
  - compose com download automático dos modelos e ingestão, CI com lint, testes e build das imagens, e documentação.
- **Decisões da IA que diferem do prompt ou o completam:**
  - `qwen2.5:3b` em vez de `llama3.2:3b`, por ser melhor em português (ADR registrada em `docs/arquitetura.md`);
  - BM25 implementado à mão em vez da biblioteca `rank-bm25`, para facilitar a explicação na defesa oral;
  - FlashRank (ONNX) em vez de CrossEncoder do `sentence-transformers`, para não trazer o PyTorch (~2 GB) para a imagem;
  - recusa em três camadas (filtro de relevância, prompt e verificação em código), e não só pelo prompt;
  - critério de relevância do Recall@k por **trecho literal esperado**, para a métrica não depender da estratégia de chunking.
- **Erros que a própria IA cometeu e corrigiu durante a geração** (registrados para a análise crítica):
  1. O `.dockerignore` excluía `*.md`, o que tiraria o corpus `data/raw_docs` da imagem. Corrigido antes do primeiro build.
  2. A limpeza de HTML do loader apagaria textos como `Bearer <token>`. Restringida a tags HTML conhecidas e fora de código inline (teste em `test_loader.py`).
  3. O script de download gravava `FONTE.txt` dentro da pasta indexada, e o arquivo seria indexado como documentação. Movido para um nível acima.
  4. **Bug encontrado por teste:** no chunker `fixed`, quando o recuo da sobreposição caía num token longo sem espaços (ex.: `FastAPI(dependencies=[Depends(verify_token)])`), a sobreposição encolhia de 50 para cerca de 17 caracteres. A janela passou a recuar até o espaço anterior, o que garante sobreposição ≥ `CHUNK_OVERLAP`. Quem detectou foi `test_fixed_chunks_respect_size_and_overlap`.
  5. YAML inválido em dois lugares, por causa de `: ` sem aspas (prefixo `search_query: ` no compose e um `name:` da CI). Detectado ao validar os arquivos com um parser de YAML.
  6. O `split` por `". "` no chunker recursivo perdia o ponto final nas fronteiras. Corrigido mantendo o separador grudado em cada parte (teste `test_split_oversized_keeps_punctuation`).
- **Aceito:**
  - arquitetura em camadas com protocolos (`Embedder`, `LLM`, `Reranker`), que permite testar tudo sem modelos;
  - as duas estratégias de chunking com o mesmo `embedding_text`, para a comparação isolar só as fronteiras dos chunks;
  - BM25 implementado à mão, RRF e FlashRank, porque cumprem o desafio do tema sem PyTorch e sem serviço pago;
  - recusa em três camadas, porque o prompt sozinho não é verificável com um modelo de 3B;
  - Recall@k por trecho literal esperado, independente da estratégia de chunking;
  - compose com `ollama-pull` e `ingest` automáticos, para cumprir o "sobe com um comando".
- **Corrigido:**
  - os 6 erros listados acima, todos antes do primeiro commit. O bug de sobreposição do chunker foi pego por teste automatizado, o que mostra o valor da regra "testes primeiro";
  - a tabela de contribuição foi ajustada para os 3 integrantes do grupo (interação 4).
- **Descartado:**
  - `llama3.2:3b` como modelo padrão: fica só como alternativa, porque o Qwen responde melhor em português;
  - `rank-bm25` e `sentence-transformers`: a primeira esconderia a fórmula que precisa ser explicada na defesa, e a segunda colocaria ~2 GB de PyTorch na imagem;
  - confiar só no prompt para recusar.
- **Verificação automática:** lint limpo e 85 testes passando nesta etapa.
- **Revisão humana (outro integrante):** [ ] li os módulos de `src/` · [ ] conferi os fatos do corpus com a documentação do FastAPI · [ ] PR `feat/mvp-rag` → `main` com a CI verde (link: ___)

---

## Interação 2: subagente revisor, ambiente, arquitetura oficial e nova interface

- **Data:** 2026-11-14 · **Integrante:** Gustavo Correa Lima · **Ferramenta:** Claude Code (Anthropic), modelo Claude Opus 5.5, com 1 subagente
- **Objetivo:** auditar o código gerado, deixar o ambiente local verde, oficializar a arquitetura e refinar a interface.
- **Prompt (resumido):** "Sem sobrescrever a lógica de negócio: (1) crie um único subagente de Arquiteto de Software e Revisor de Código que conheça o enunciado do Tema 4, garanta custo zero, exija testes para toda função nova, impeça vazamento de `.env` e valide a estrutura de pastas, e peça a ele que audite os arquivos gerados e corrija imports quebrados ou incompatibilidades entre `src/` e `tests/`; (2) crie o `.venv`, instale as dependências e rode pytest e ruff até ficar 100% verde; (3) crie `docs/arquitetura.md` com diagramas Mermaid (ingestão → chunking → Qdrant → busca híbrida/rerank → Ollama → citação/recusa), padrão de camadas, contratos Pydantic e 3 ADRs; (4) refaça a UI em tema claro e minimalista, com Nexa Sans (fallback Montserrat) nos títulos e Arial no texto, paleta #FFFFFF/#F8FAFC/#E2E8F0/#2563EB, cartões expansíveis para as fontes citadas (arquivo, score e trecho) e um indicador visual claro de recusa anti-alucinação; atualize o PROMPTS.md."
- **Resumo da resposta:**
  - **Subagente** `.claude/agents/arquiteto-revisor.md`, com checklist de custo zero, testes, segredos/LGPD, estrutura do repositório, camadas e reprodutibilidade. Na auditoria, ele:
    - escreveu 13 testes (`test_ingestion_cli.py` e `test_logging_setup.py`), levando a CLI de 0% para 98% de cobertura e os logs de 34% para 100%;
    - acrescentou `--no-access-log` ao Uvicorn, porque o access log gravava o IP do cliente (regra de LGPD do enunciado);
    - fez a CI instalar o extra `ui`, porque os testes de interface seriam pulados sem aviso;
    - passou a repassar `EMBED_BATCH_SIZE` no compose;
    - não encontrou imports quebrados nem violações de camada.
  - **Ambiente:** `.venv` com Python 3.11.16, instalação via `pip install -e ".[dev,ui]"` (com `uv`). Resultado final: `ruff check` e `ruff format --check` limpos, **104 testes passando, cobertura de 92%** (medindo `src/` e `eval/`).
  - **`docs/arquitetura.md`:** diagrama de componentes, fluxos de ingestão e de pergunta, tabela de camadas com regras de import, mapeamento de exceções para HTTP, contratos de domínio e HTTP, e 3 ADRs (Qdrant, busca híbrida com rerank, recusa estrita em três camadas).
  - **Interface:** tema em `.streamlit/config.toml` e CSS em `src/ui/styles.py`; cartão de resposta com selos de citação `[n]`; cartão amarelo "Recusa anti-alucinação acionada" com o motivo explicado; fontes em cartões expansíveis com arquivo, seção, barra de relevância, etapas da busca e trecho exato; chips de latência e modo; histórico da sessão; 6 testes com `streamlit.testing.AppTest`.
- **Corrigido durante a interação:**
  1. **Nexa Sans é fonte comercial (Fontfabric):** não está no Google Fonts nem pode ser redistribuída no repositório. O CSS a usa só se estiver instalada no sistema de quem abre a página e, senão, cai para Montserrat (Google Fonts).
  2. `st.pills` quebrava o `AppTest` do Streamlit 1.40 quando não havia seleção (erro interno do framework). Os exemplos viraram botões com callback, que funcionam igual e são testáveis.
  3. O texto vindo do LLM é escapado antes de virar HTML, para evitar injeção de HTML pela resposta do modelo (teste `test_model_output_is_html_escaped`).
  4. O `ruff` rejeitou o CSS montado com formatação `%`. As cores ficaram como variáveis CSS literais em `:root`.
- **Pendências apontadas pelo subagente:** dataset oficial de 50 perguntas; conferir permissões dos volumes `./logs` e `./eval` em Linux com UID diferente de 1000 (nota acrescentada ao README).
- **Aceito:**
  - o subagente e as quatro correções dele: `--no-access-log` (LGPD), CI com o extra `ui`, `EMBED_BATCH_SIZE` no compose e os testes da CLI e dos logs;
  - `docs/arquitetura.md` como referência oficial, com as regras de import e os 3 ADRs;
  - o tema claro, os selos de citação, o cartão de recusa e os cartões de fonte com barra de relevância.
- **Corrigido:**
  - Nexa Sans → **Plus Jakarta Sans** (fonte livre, OFL) nos títulos, mantendo Arial no corpo (interação 3);
  - `st.pills` → botões de exemplo, por causa do erro interno do `AppTest`;
  - escape do HTML vindo do LLM, para evitar injeção pela resposta.
- **Descartado:**
  - Nexa Sans e o fallback Montserrat: a Nexa é comercial e não pode ser redistribuída;
  - `st.pills`;
  - CSS montado com formatação `%`, rejeitado pelo ruff.
- **Verificação automática:** auditoria do subagente; 104 testes passando (inclusive a interface via `AppTest`), cobertura de 92% e lint limpo.
- **Revisão humana (outro integrante):** [ ] li o relatório do subagente · [ ] conferi a interface no navegador

---

## Interação 3: modo local sem Docker, fonte livre e 50 perguntas

- **Data:** 2026-11-14 · **Integrante:** Gustavo Correa Lima · **Ferramenta:** Claude Code (Anthropic), modelo Claude Opus 5.5
- **Objetivo:** rodar e testar a interface e o backend na máquina local, sem Docker Desktop, sem alterar o `docker-compose.yml` da entrega, e fechar os ajustes de entrega.
- **Prompt (resumido):** "Recebi `CommandNotFoundException` no `docker compose up` porque não tenho Docker Desktop. Quero rodar agora, localmente, mantendo o compose intacto. (1) Adicione `QDRANT_MODE=local`/`QDRANT_PATH` para o `qdrant-client` gravar em disco, e `.qdrant_local/` no `.gitignore`. Verifique se o Ollama está instalado; se não estiver, crie `LLM_MODE=mock` só para desenvolvimento, com `ollama` como padrão oficial. Crie `scripts/run_local.ps1`, que ativa o `.venv`, indexa se necessário, sobe o uvicorn com `--reload` na porta 8000 em outra janela e o Streamlit na 8501 abrindo o navegador. (2) Troque Nexa Sans por Plus Jakarta Sans nos títulos e Arial no corpo; documente no README o modo oficial e o local, o desenvolvimento individual autorizado pelo professor (pedido **revertido na interação 4**: o projeto é em grupo) e o uso de ferramentas gratuitas; complete o dataset até as 50 perguntas e preencha os campos de revisão no PROMPTS.md. (3) Rode ruff e pytest e me dê os comandos para rodar o script e fazer o push."
- **Resumo da resposta:**
  - **Diagnóstico:** o Ollama não está instalado (`ollama` ausente e porta 11434 sem resposta). Então o mock precisa cobrir também os **embeddings**, e não só o LLM.
  - **Modos novos** em `core/config.py`, decididos num só lugar (`core/factory.py`):
    - `QDRANT_MODE=local`: Qdrant embutido em disco, com um cliente serializado por lock, porque o FastAPI atende em várias threads;
    - `EMBED_MODE=hash`: o `HashEmbedder` saiu dos testes e foi para `ingestion/embeddings.py`. Essas coleções ganham o sufixo `_hash`, para não se misturarem com as de 768 dimensões do Ollama;
    - `LLM_MODE=mock`: `generation/mock_llm.py`, um respondedor extrativo que lê o mesmo prompt do LLM, copia a frase mais relevante, cita `[n]` ou recusa.
  - **Sinalização do mock:** a interface mostra a faixa "Modo demonstração (sem Ollama)", o `/health` informa os modos e o relatório de `eval/` marca como inválida qualquer execução em mock ou hash.
  - **`scripts/run_local.ps1`:** detecta o Ollama, cria o `.env`, indexa, abre a API numa nova janela, espera o `/health` e sobe o Streamlit em modo headless. O navegador abre quando a interface responde, o que evita a pergunta de e-mail que o Streamlit faz no terminal na primeira vez.
  - **Fonte:** Plus Jakarta Sans (Google Fonts, OFL) nos títulos e Arial no corpo, com um teste que garante a ausência de fontes comerciais.
  - **Dataset:** `eval/datasets/perguntas_teste.json` com **50 perguntas com resposta e trecho-fonte esperados e 12 sem resposta**. Os 62 trechos esperados são verificados automaticamente contra o corpus e contra os chunks das duas estratégias.
  - **README e documentação:** os dois modos de execução. A autoria individual escrita nesta interação foi **revertida na interação 4**, junto com a volta da revisão cruzada entre integrantes.
  - **Teste real do modo local** (ingestão + API + `/ask`): resposta citando `testes.md` e recusa para GraphQL.
- **Corrigido durante a interação** (problemas reais encontrados ao testar):
  1. **Download do reranker interrompido** (`IncompleteRead`, 9 MB de 103 MB). A queda para a busca híbrida funcionou, mas cada pergunta tentaria baixar o modelo de novo, o que custaria minutos por requisição. O reranker agora lembra a falha e só tenta de novo depois de 5 minutos (teste `test_flashrank_load_failure_is_remembered`).
  2. **Pasta do Qdrant local travada** quando a API já está no ar: a CLI agora devolve uma mensagem clara ("Pare a API e rode de novo") em vez de um traceback.
  3. **Codificação do `.ps1`:** o Windows PowerShell 5.1 lê scripts sem BOM como ANSI, o que embaralharia os acentos. O script foi gravado em UTF-8 com BOM.
  4. **Cache do Streamlit entre testes:** o `st.cache_data` do `/health` vazava de um teste para outro. Agora ele é limpo na fixture.
- **Aceito:** o modo local completo (Qdrant em disco, hash e mock), o script, a fonte livre e o dataset (refeito na interação 4).
- **Corrigido:** os 4 problemas acima, antes do commit.
- **Descartado:**
  - configurar o `.env` para o Ollama local: não se aplica, porque o Ollama não está instalado. O script detecta o Ollama quando ele for instalado;
  - criar uma imitação de LLM que "gere" texto: o mock é deliberadamente extrativo e sinalizado, para não passar por resultado real;
  - qualquer mudança no `docker-compose.yml`, que continua sendo o caminho oficial.
- **Pontos de atenção:**
  - as perguntas do dataset foram redigidas com IA. O grupo deve lê-las antes do commit, já que a rubrica pede que sejam escritas antes de ajustar o sistema;
  - o README deixa em aberto o plano do Claude Code, para o grupo declarar como ele atende à regra de custo zero.
- **Verificação automática:** teste real do modo local (ingestão, API e `/ask` com resposta citada e recusa); lint limpo e suíte completa verde.
- **Revisão humana (outro integrante):** [ ] rodei `scripts/run_local.ps1` e testei perguntas com e sem resposta · [ ] li as perguntas do dataset · [ ] declarei o plano do Claude Code no README

---

## Interação 4: grupo de 3 integrantes, auditor de conformidade, base ampliada e verificação reforçada

- **Data:** 2026-11-14 · **Integrante:** Gustavo Correa Lima · **Ferramenta:** Claude Code (Anthropic), modelo Claude Opus 5.5, com 1 subagente novo (`auditor-rag-enunciado`)
- **Objetivo:** corrigir a autoria, enriquecer a base de conhecimento, melhorar o estilo das respostas e auditar a conformidade com o enunciado antes do primeiro commit.
- **Prompt (resumido):** "(1) Remova toda menção a projeto individual: o projeto é em grupo, com 3 integrantes (Gustavo Correa Lima, RA 2530185: backend, arquitetura, pipeline RAG e infraestrutura; integrante 2: dados, dataset e testes; integrante 3: interface, documentação e pesquisa ABNT), e restaure as regras de commits de todos e de revisão cruzada. (2) Crie só mais um subagente, `auditor-rag-enunciado`, que confronta o projeto com a rubrica e o Tema 4. (3) Explique por que a base gerou 46 chunks e por que 'O que é HTML?' foi recusado; amplie a base para 15 a 20 documentos densos sobre FastAPI, Pydantic, pytest e Docker; alinhe as 50 perguntas; reindexe o `.qdrant_local`; melhore o prompt do Ollama (didático, em tópicos, com citações) e a formatação do mock, com um aviso discreto; reescreva a instalação em Fluxo A (Docker) e Fluxo B (Windows sem Docker, com `ollama pull llama3.2:3b`). (4) Entregue uma tabela de conformidade, rode ruff e pytest e registre a interação."
- **Resumo da resposta:**
  - **Autoria:** README com a tabela de 3 integrantes e as regras do grupo (commits de todos, revisão cruzada, CI verde). `docs/arquitetura.md`, `docs/testes-ci.md`, `data/README.md`, `docs/dados-e-modelos.md` e este arquivo foram corrigidos. As menções às interações anteriores ficaram marcadas como revertidas, para não reescrever o histórico.
  - **Base:** de 9 para **20 documentos** (cerca de 58 mil caracteres e 131 seções). Os 9 originais foram ampliados sem alterar o texto existente, e entraram 11 novos (APIRouter, respostas, cabeçalhos e formulários, Pydantic, pydantic-settings, pytest, fixtures, imagens Docker, Compose e async). Chunks: 31 → **94** (`fixed`) e 46 → **136** (`recursive`).
  - **Dataset:** versão 2.0.0, com **50 perguntas com resposta cobrindo os 20 documentos** e 14 sem resposta, incluindo "O que é HTML?" e "O que é JavaScript?". Novo **conjunto de desenvolvimento** (`perguntas_dev.json`, 12 + 6), disjunto do de teste, verificado por teste automatizado.
  - **Prompt:** resposta direta primeiro, depois tópicos ou passos e código copiado do trecho, com citação em cada afirmação e proibição explícita de conhecimento geral.
  - **Mock:** tópicos com o título da seção, uma ou duas frases citadas por trecho e o código do trecho principal. Na UI, o cartão "Trechos organizados · modo de visualização" e uma faixa discreta explicando como ativar o Ollama. A UI também passou a renderizar listas, passos numerados e negrito.
  - **Reindexação automática:** cada ponto guarda uma impressão digital da base, do chunking e do modelo de embeddings. O `--skip-existing` (Fluxo A e Fluxo B) agora reindexa sozinho quando algo muda; antes, a base nova nunca substituiria o índice antigo. A reindexação desta interação foi feita pelo `POST /ingest` da API que estava no ar, sem derrubá-la.
  - **Fluxo B:** o `run_local.ps1` usa o modelo instalado (`LLM_MODEL` do `.env`, `llama3.2:3b` ou `qwen2.5:3b`) e só cai para o mock se faltar o modelo de geração ou o de embeddings, dizendo o que instalar.
- **Achados do subagente auditor corrigidos nesta interação:**
  1. **P1, bug:** uma recusa com citação ("Não encontrei essa informação... [1]") passava como resposta fundamentada. Corrigido e testado.
  2. **P2, bug:** conhecimento externo com uma citação qualquer ("HTML é uma linguagem de marcação [1]") passava, porque a verificação só conferia o formato. Agora há cobertura mínima de citações (`MIN_CITATION_COVERAGE`) e sustentação lexical de cada afirmação no trecho citado (`MIN_SUPPORT_RATIO`).
  3. **P3:** o limite `MIN_VECTOR_SCORE` era calibrado no próprio conjunto de teste. Agora usa o conjunto de desenvolvimento, e o script se recusa a calibrar com o de teste.
  4. **P4:** a calibração usava o top-1 do modo vetorial, e a produção, o maior cosseno entre os trechos enviados ao LLM. As duas passaram a usar a mesma função (`relevance_signal`).
  5. **P5, P7, P8, P9 e P12:** novas colunas `grounded_among_answered`, `avg_chunk_chars`, `hits@5` e intervalo de Wilson. Os modos (`llm_mode`, `embed_mode`) aparecem nos CSVs, no resumo e no log `ask.completed`. O reranker é aquecido antes de medir as latências.
- **Corrigido durante a interação** (erros encontrados ao testar):
  - o divisor de frases separava a citação quando ela vinha depois do ponto ("frase. [1]"), e a cobertura caía para 0;
  - o `FakeLLM` padrão dos testes respondia uma frase sem sustentação no trecho e passou a citar o trecho de verdade;
  - o hook do shell corrompeu barras invertidas em duas edições (`\n` virou quebra de linha, `\1` virou caractere de controle, `\r` em `scripts\run_local.ps1`), detectadas pelo ruff e por verificação de caracteres de controle. As edições seguintes passaram a ser feitas por scripts gravados pelo editor;
  - o README tinha o comando `scripts\run_local.ps1` quebrado em duas linhas por esse mesmo problema;
  - um erro de digitação no caminho do enunciado dentro do arquivo do subagente.
- **Aceito:** a autoria em grupo, o subagente auditor, a base de 20 documentos, o dataset 2.0, o conjunto de desenvolvimento, as correções P1 a P12 aplicáveis, o novo prompt, o mock formatado e os Fluxos A e B.
- **Corrigido:** os itens acima, antes do commit.
- **Descartado:**
  - apagar do histórico do `PROMPTS.md` o pedido de autoria individual da interação 3: ele foi mantido e marcado como revertido, porque o registro de uso de IA precisa ser fiel;
  - trocar o modelo padrão do Docker para `llama3.2:3b`: o Fluxo A continua com `qwen2.5:3b` (ADR e avaliação) e o Fluxo B aceita os dois;
  - usar um LLM como juiz da fundamentação: dobraria a latência em CPU e fica como trabalho futuro.
- **Pendências apontadas pelo auditor que dependem do grupo:** rodar a avaliação real com o Ollama (Fluxo A) e versionar as saídas; analisar 3 ou mais casos de falha reais; gravar o vídeo; fazer as capturas; criar o repositório com commits de todos e revisão cruzada; preencher os integrantes 2 e 3; confirmar com o professor o grupo de 3 (o enunciado fala em 4) e o uso de uma base própria em vez de uma documentação pública grande (o script da documentação oficial do FastAPI continua disponível); redigir o PDF ABNT; completar 10 ou mais interações neste arquivo.
- **Verificação automática:** `ruff check` e `ruff format --check` limpos; **132 testes passando**; cobertura de 94% de `src/` e `eval/`; reindexação real pela API (20 documentos, 94 e 136 chunks); perguntas reais pela API em modo mock: "O que é HTML?" e "O que é JavaScript?" recusadas, e perguntas sobre fixtures e Compose respondidas com citação.
- **Revisão humana (outro integrante):** [ ] revisou a nova base de conhecimento contra a documentação oficial · [ ] leu as 64 perguntas de teste e as 18 de desenvolvimento · [ ] aprovou o PR

---

<!-- Próximas interações: 3 a 10+. Registre também usos menores mas relevantes (ex.: depurar um erro, ajustar um prompt após a avaliação). -->
