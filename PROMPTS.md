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
- **Pendências apontadas pelo auditor que dependem do grupo:** rodar a avaliação real com o Ollama (Fluxo A) e versionar as saídas; analisar 3 ou mais casos de falha reais; gravar o vídeo; fazer as capturas; criar o repositório com commits de todos e revisão cruzada; preencher os integrantes 2 e 3 (feito na interação 7); confirmar com o professor o grupo de 3 (o enunciado fala em 4) e o uso de uma base própria em vez de uma documentação pública grande (o script da documentação oficial do FastAPI continua disponível); redigir o PDF ABNT; completar 10 ou mais interações neste arquivo.
- **Verificação automática:** `ruff check` e `ruff format --check` limpos; **132 testes passando**; cobertura de 94% de `src/` e `eval/`; reindexação real pela API (20 documentos, 94 e 136 chunks); perguntas reais pela API em modo mock: "O que é HTML?" e "O que é JavaScript?" recusadas, e perguntas sobre fixtures e Compose respondidas com citação.
- **Revisão humana (outro integrante):** [ ] revisou a nova base de conhecimento contra a documentação oficial · [ ] leu as 64 perguntas de teste e as 18 de desenvolvimento · [ ] aprovou o PR

---

## Interação 5: instalação assistida e README simplificado

- **Data:** 2026-11-14 · **Integrante:** Gustavo Correa Lima · **Ferramenta:** Claude Code (Anthropic), modelo Claude Opus 5.5
- **Objetivo:** tornar a instalação compreensível para quem abre o repositório pela primeira vez. O `docker compose up --build` falhou numa máquina sem Docker, e as seções "Fluxo A" e "Fluxo B" do README não deixavam claro se eram etapas ou alternativas.
- **Prompt (resumido):** "Crie um facilitador de instalação: audite e valide o Docker, o Python, todas as dependências e os modelos necessários, mostre um checklist do que está instalado e configurado, abra o Ollama, e reescreva a instalação do README de forma simplificada. Hoje há muita informação e não dá para entender se o Fluxo A e o B são continuação um do outro."
- **Resumo da resposta:**
  - **`scripts/instalar.ps1`:** audita sistema (winget, Git, Python 3.11+), projeto (`.venv`, dependências, `.env`), IA local (Ollama instalado e aberto, `nomic-embed-text` e o modelo de geração, cada um com um teste real), Docker (opcional) e máquina (RAM, disco, portas). Pergunta antes de instalar cada item pelo `winget`, termina com um checklist OK/FALTA/AVISO/OPCIONAL e oferece iniciar o projeto. Opções `-Verificar` (só audita), `-Sim`, `-ComDocker`, `-Modelo` e `-Iniciar`. O teste do modelo de geração usa `keep_alive` de 30 minutos, deixando o modelo aberto no Ollama.
  - **`scripts/verificar_dependencias.py`:** compara cada pacote instalado com a versão fixada no `pyproject.toml` (inclusive os extras `dev` e `ui`) e confere os pacotes de `src/`. Fica em Python para ser testável.
  - **README e `docs/instalacao.md`:** "Fluxo A/B" viraram **Caminho Windows** e **Caminho Docker**, com uma tabela "Você quer... → caminho → comando" e o aviso explícito de que são alternativas. O caminho Windows ficou em três passos: clonar, `instalar.ps1` (uma vez) e `run_local.ps1` (dia a dia).
  - **`run_local.ps1`:** sem `.venv`, pede para rodar o instalador, em vez de criar o ambiente com o primeiro Python do PATH.
  - **Interface:** a faixa do Modo de Visualização aponta para o `instalar.ps1`.
- **Erros e ajustes encontrados ao testar:**
  - o `.venv` desta máquina, criado com `uv`, não tinha `pip`, e a instalação das dependências falharia. O instalador usa o `uv` quando ele existe e, senão, roda `ensurepip` antes do `pip`;
  - o `python` do PATH era o 3.13, mas o projeto é testado no 3.11 (Docker e CI). O instalador procura `py -3.11` e `py -3.12` antes, e marca 3.13+ como AVISO;
  - o checklist repetia a mesma dica de instalação do Ollama em dois itens. As dicas passaram a ser únicas;
  - o instalador tentaria `ollama pull` com o Ollama respondendo na porta 11434 mas não instalado no Windows (caso do container do compose). O download passou a exigir o executável.
- **Aceito:** o instalador com confirmação item a item, o verificador de dependências, a reorganização em dois caminhos e um só modelo padrão (`qwen2.5:3b`) nos dois caminhos.
- **Corrigido:** os 4 itens acima, antes do commit.
- **Descartado:**
  - instalar tudo sem perguntar: o script mexe no sistema (Python, Ollama, Docker), então cada instalação é confirmada, a não ser com `-Sim`;
  - instalar o Docker por padrão: ele exige reiniciar o Windows e só é necessário no caminho Docker, então só entra com `-ComDocker` ou confirmação explícita;
  - manter `llama3.2:3b` como modelo padrão do caminho Windows: dois modelos diferentes por caminho complicavam a explicação. Ele continua aceito com `-Modelo llama3.2:3b`.
- **Limitação:** nesta máquina, foram validados de verdade só o modo `-Verificar` e a detecção de Python, `.venv`, dependências, Ollama ausente e Docker ausente. Os ramos que instalam e abrem o Ollama e o Docker ainda não rodaram e precisam ser testados pelo grupo.
- **Verificação automática:** `ruff check` e `ruff format --check` limpos; **141 testes passando** (9 novos em `tests/test_scripts.py`: versões fixadas, problemas de dependência, códigos de saída e BOM UTF-8 dos `.ps1`); sintaxe dos dois `.ps1` validada pelo parser do PowerShell; `instalar.ps1 -Verificar` executado nesta máquina.
- **Revisão humana (outro integrante):** [ ] rodou `scripts\instalar.ps1` numa máquina limpa · [ ] seguiu o README do zero sem ajuda · [ ] aprovou o PR

---

## Interação 6: origem das instalações, validação de ponta a ponta e compatibilidade

- **Data:** 2026-11-14 · **Integrante:** Gustavo Correa Lima · **Ferramenta:** Claude Code (Anthropic), modelo Claude Opus 5.5
- **Objetivo:** garantir que o instalador instale (e não só avise), diga de onde instala, valide tudo e suba o projeto, e deixar claro em quais máquinas o projeto funciona.
- **Prompt (resumido):** "O script só avisa o que falta ou também instala, dos lugares corretos, perguntando antes? No final, ele precisa validar a instalação e rodar o projeto. O projeto vai funcionar na máquina de qualquer usuário? Isso está no README?"
- **Resumo da resposta:**
  - o script já instalava com confirmação. Agora cada pergunta mostra a **origem**: `winget` com o instalador oficial (python.org, ollama.com, git-scm.com, docker.com), PyPI para os pacotes e a biblioteca oficial do Ollama para os modelos. Sem o `winget`, ele mostra o link oficial;
  - **validação de ponta a ponta:** nova opção `run_local.ps1 -Testar`, que o instalador usa ao iniciar o projeto. Com a API no ar, ela faz uma pergunta coberta pela documentação (precisa responder com citação) e "O que é HTML?" (precisa recusar);
  - **README:** nova seção "Em que máquina funciona" (Windows 10 1809+/11 nos dois caminhos; Linux/macOS só pelo Docker; RAM, disco, internet, permissão de administrador e GPU) e a opção de baixar o ZIP sem Git.
- **Erro encontrado ao revisar:** uma edição anterior colou o nome da função à pergunta (`Confirm-Step"Baixar..."`). O parser do PowerShell aceita, mas a execução falharia ao baixar o modelo de embeddings. Foi corrigido, e um teste novo (`test_powershell_functions_are_not_glued_to_arguments`) passou a barrar esse tipo de erro nos dois `.ps1`.
- **Aceito:** a origem explícita, a validação de ponta a ponta e a seção de compatibilidade.
- **Corrigido:** o erro acima.
- **Descartado:** baixar instaladores diretamente por URL quando falta o `winget`: duplicaria o que o `winget` já faz com verificação de hash, para um caso raro (Windows 10 anterior a 1809).
- **Limitação:** a validação de ponta a ponta foi executada contra a API real, mas no modo mock. Os ramos que instalam o Python, o Ollama e o Docker, e o caminho Docker como um todo, ainda não foram executados em nenhuma máquina.
- **Verificação automática:** `ruff` limpo; testes passando; sintaxe dos `.ps1` validada; bloco `-Testar` executado contra a API: a pergunta sobre fixtures foi respondida citando `pytest-fixtures.md`, e "O que é HTML?" foi recusada.
- **Revisão humana (outro integrante):** [ ] rodou o instalador do zero numa máquina sem Ollama · [ ] testou o caminho Docker · [ ] aprovou o PR

---

## Interação 7: validação interativa, perguntas com print, Enter para enviar e auditoria ao vivo

- **Data:** 2026-11-14 · **Integrante:** Gustavo Correa Lima · **Ferramenta:** Claude Code (Anthropic), modelo Claude Opus 5.5
- **Objetivo:** responder "como eu sei que o sistema atende ao enunciado?" com uma forma interativa de conferir a base e as métricas, aceitar perguntas com print, enviar com Enter e preencher os integrantes 2 e 3.
- **Prompt (resumido):** "Que documentos ele está usando para responder, e onde estão? Quero um checklist de validação do enunciado e uma página interativa para validar os documentos. Quero mandar um print e ele detectar e responder, enviar com Enter, mais testes automatizados e uma auditoria dinâmica da interface. Adicione os RAs: Larissa Paula de Almeida Campos (2506209) e Rafael Dourado Coimbra (2414807)."
- **Resumo da resposta:**
  - **Integrantes:** Larissa como integrante 2 e Rafael como integrante 3, na ordem enviada e nos papéis que já estavam na tabela.
  - **API:** `GET /documents`, `GET /documents/{arquivo}`, `GET /validation/questions` e `POST /validation/retrieval` (`core/validation.py`, com a mesma regra de acerto da avaliação). A comparação de trechos passou para `core/text.py` e é compartilhada com `eval/metrics.py`.
  - **Interface:** três abas.
    - **Perguntar:** `st.chat_input`, que envia com Enter; upload de print; "Você perguntou"; na recusa, os trechos aparecem como "mais próximos encontrados", com a explicação.
    - **Documentos:** totais, tabela filtrável, texto, chunks por estratégia e perguntas de teste de cada arquivo.
    - **Validação:** Recall@k ao vivo, respostas fundamentadas, recusas corretas e CSV.
  - **Prints:** `generation/vision.py` com o `qwen2.5vl:3b` do Ollama. A transcrição entra na pergunta, mas nunca vira fonte: a resposta continua sujeita à verificação de citações. Há validação de formato e tamanho (422) e um 503 claro sem o modelo ou no modo mock. O modelo também foi incluído no `instalar.ps1` como item opcional.
  - **Documentação:** `docs/checklist-enunciado.md` (Tema 4, rubrica, evidências, resultados preliminares e roteiro de validação), além de `docs/api.md`, do manual (seções 6 e 7) e do README.
- **Achado mais importante, com dados reais:** a validação ao vivo, com o Ollama e as 50 perguntas, mostrou que o modo **padrão** `hybrid_rerank` tinha Recall@5 de 58–60%, contra 96–98% do `hybrid` sem reranking. A hipótese de truncamento do FlashRank (128, 256 e 512 tokens) foi testada e descartada. O padrão passou a ser `hybrid` em `config.py`, no `docker-compose.yml`, no `.env.example` e na barra lateral, e a ADR 002 foi revisada com a tabela. Antes disso, todas as perguntas feitas na interface usavam a pior configuração.
- **Teste real da leitura de print:** o modelo de visão transcreveu sem erros um print com `RuntimeError: Form data requires "python-multipart"`, e a busca trouxe o trecho certo em 1º lugar. Mesmo assim, o LLM de 3B recusou (`llm_refusal`). Ficou registrado como o caso de falha 2 em `evidencias/falhas/`, com correção proposta.
- **Auditoria dinâmica da interface** (a interface real contra a API real, via `AppTest`): abre sem erros; a aba Documentos mostra 20 documentos e 94/136 chunks, iguais ao índice; o Enter envia e a resposta cita `pytest-fixtures.md` (45 s); "Como faz um ovo frito?" é recusada (21 s); a aba Validação mede Recall@5 = 96% (48/50, MRR 0,86) em 15 s.
- **Aceito:** as três abas, os endpoints de validação, a leitura de prints, o novo padrão `hybrid`, o checklist e os casos de falha.
- **Corrigido durante a interação:** um erro no próprio script de auditoria (ele lia a caixa de seleção errada), confirmado pelo rótulo antes de concluir.
- **Descartado:**
  - **OCR clássico (RapidOCR/Tesseract):** traria o OpenCV e as bibliotecas de sistema do Docker. O modelo de visão já faz parte da stack Ollama;
  - **atualizar o Streamlit para anexar a imagem no próprio campo de chat:** trocar uma versão fixada sem necessidade arriscaria os testes;
  - **trocar o modelo do reranker agora:** fica como trabalho futuro, medido na aba Validação.
- **Limitações:**
  - o `ollama/ollama:0.5.4` do compose não roda o `qwen2.5vl`. No caminho Docker, a leitura de prints só funciona atualizando a imagem do Ollama, o que não foi testado;
  - os números da seção 4 do checklist são preliminares, porque saíram da API e não do `eval/run_eval.py`.
- **Verificação automática:** `ruff` limpo; **185 testes passando** (eram 143), com 94% de cobertura; validação ao vivo das 50 perguntas em 4 modos × 2 estratégias.
- **Revisão humana (outro integrante):** [ ] Larissa conferiu o conjunto de teste pela aba Documentos · [ ] Rafael revisou a interface e o manual · [ ] PR aprovado por alguém que não conduziu a interação

---

## Interação 8: execução do checklist de conformidade (avaliação oficial, conjunto congelado, verificação e interface de chat)

- **Data:** 2026-11-15 · **Integrante:** Gustavo Correa Lima · **Ferramenta:** Claude Code (Anthropic), modelo Claude Opus 5.5
- **Objetivo:** fechar os itens técnicos do checklist de conformidade com o Tema 4, priorizados pelo peso na rubrica (critérios 2 e 3), e produzir as evidências 3, 4 e 6.
- **Prompt (resumido):** "Melhore o checklist geral, pontue os pontos principais, faça um plano de implementação e execute-o. As dúvidas com o professor e com o grupo já foram resolvidas: siga com o desenvolvimento, rode os testes e o que for preciso no terminal e registre a interação em formato técnico."

### Plano executado

| # | Item | Resultado |
| --- | --- | --- |
| P1 | Avaliação oficial com geração (`recursive + hybrid`) | ✅ `evidencias/avaliacao/20261115-172143-principal-recursive-hybrid/` |
| P2 | Baseline com geração (`fixed + vector`) | ✅ `evidencias/avaliacao/20261115-201630-baseline-fixed-vector/` |
| P3 | Revisão e congelamento do conjunto de teste | ✅ v2.1.0, `questions_sha256` e `test_test_set_is_frozen` |
| P4 | Casos de falha com alucinação real | ✅ casos 3, 4 e 5 em `evidencias/falhas/casos-de-falha.md` |
| P5 | Log de execução completa | ✅ `evidencias/logs/execucao-completa.jsonl` (138 eventos, 128 perguntas) |
| P6 | Bug da verificação de citações | ✅ `generation/grounding.py` e testes de regressão |
| P7 | Interface em estilo chat e responsiva | ✅ `src/ui/app.py`, `src/ui/styles.py`, `tests/test_ui.py` |
| P8 | Leitura de prints no caminho Docker | 🟡 compose atualizado (Ollama 0.12.6 e `PULL_VISION_MODEL`); `docker compose up` não executado |
| P9 | Calibração da verificação no conjunto de desenvolvimento | ✅ `evidencias/avaliacao/calibracao-verificacao-dev/` |

### Alterações por arquivo

- **`eval/datasets/perguntas_teste.json` (v2.1.0):** 14 perguntas reescritas em linguagem de usuário: q16, q18, q19, q23, q27, q28, q30, q31, q32, q34, q40, q46, q48 e q50. Antes, 17 das 50 perguntas continham o identificador de código esperado, e q40, q46 e q50 tinham de 88% a 100% dos termos do trecho esperado. Os trechos esperados não mudaram. Novo campo `questions_sha256`.
- **`tests/test_eval.py`:** `test_test_set_is_frozen` (hash SHA-256 canônico das perguntas). O teste offline passou a localizar a q27 pelo id.
- **`src/generation/grounding.py`:** `statements()` conta as linhas de introdução terminadas em ":" quando elas trazem citação; as sem citação continuam ignoradas. Testes: `test_cited_intro_before_code_counts_as_claim` e `test_bare_intro_without_citation_is_still_ignored`.
- **`src/ui/app.py` e `styles.py`:**
  - aba Perguntar em formato de conversa (`st.chat_message`), com o histórico de até 20 trocas;
  - a lista completa de trechos aparece só na última resposta (`render_result(show_all=...)`);
  - botão "Nova conversa", anexo num expansível 📎 e exemplos só com a conversa vazia;
  - aviso de que cada pergunta é respondida de forma independente;
  - regras `@media` para 900 px e 640 px;
  - testes `test_conversation_keeps_history_like_a_chat` e `test_new_chat_clears_the_conversation`.
- **`docker-compose.yml`:**
  - `ollama/ollama:0.5.4` → `0.12.6`, porque a 0.5.4 não roda o `qwen2.5vl`; a existência da tag foi conferida na API do Docker Hub;
  - `VISION_MODEL` no ambiente da API;
  - `ollama-pull` baixa o modelo de visão só com `PULL_VISION_MODEL=true`;
  - a ausência de chaves duplicadas foi validada com um loader YAML estrito.
- **Documentação:**
  - `docs/checklist-enunciado.md`, reescrito com prioridades, resultados oficiais e roteiro de validação;
  - README, com a nova seção "Resultados";
  - ADR 002, com a confirmação oficial;
  - `docs/avaliacao.md`, com o comando no Windows, o congelamento e a regra de calibração;
  - `docs/dados-e-modelos.md`, `docs/manual-usuario.md`, `docs/instalacao.md`, `docs/testes-ci.md`, `.env.example` e `evidencias/README.md`.

### Experimentos (hipótese → método → resultado → decisão)

1. **Prompt contra a alucinação do u07 e a recusa do caso 2.**
   - *Hipótese:* duas regras novas no prompt (valor padrão só se estiver explícito; mensagem de erro em inglês faz parte da pergunta) corrigem os dois casos.
   - *Método:* A/B ao vivo com 9 perguntas: o caso 2, as armadilhas u04, u07, u09, u10, u12 e u13, e os controles q22 e q45.
   - *Resultado:* 6/9 antes e 6/9 depois. O modelo de 3B manteve a alucinação do u07 e a recusa do caso 2.
   - *Decisão:* regras **retiradas**, para não alterar o prompt sem ganho medido antes da avaliação oficial.
2. **Bug da verificação no q22.**
   - *Hipótese:* a resposta correta era descartada porque a citação estava numa linha terminada em ":".
   - *Método:* reprodução fora da API com a resposta bruta completa, mais teste de regressão.
   - *Resultado:* com a correção, o q22 é respondido citando `testes.md` na medição ao vivo (7/9 no A/B).
   - *Decisão:* correção **mantida**.
3. **Falsas recusas por cobertura (avaliação oficial).**
   - *Observação:* 16 das 19 falsas recusas são `ungrounded_answer` com cobertura de 0% a 33% e nenhuma frase sem sustentação.
   - *Método:* seis variações da regra reaplicadas às respostas reais do **conjunto de desenvolvimento** (12 com resposta e 6 sem), mais 4 respostas forjadas de controle. O conjunto de teste não participou.
   - *Resultado:*
     - afrouxar a cobertura ganha no máximo 1 de 12 perguntas;
     - conferir as frases sem citação contra todo o contexto aceita 3 de 4 respostas forjadas, contra 1 de 4 hoje;
     - a forjada aceita pela regra atual é "O FastAPI usa bcrypt com 12 rodadas por padrão [1]".
   - *Decisão:* regra **mantida**. A troca entre precisão e cobertura fica documentada no caso 4.
4. **Interface de chat no AppTest.**
   - *Observação:* depois do `st.rerun()`, a resposta antiga ainda mostrava todos os trechos.
   - *Hipótese:* resíduo do AppTest, que não descarta os elementos da execução interrompida.
   - *Método:* nova execução, sem entrada.
   - *Resultado:* só a última resposta mostra todos os trechos.
   - *Decisão:* o teste faz um `at.run()` extra, comentado.

### Métricas oficiais

Ollama real, conjunto 2.1.0, top-5.

| Métrica | Baseline `fixed + vector` | Padrão `recursive + hybrid` |
| --- | --- | --- |
| Recall@5 | 80% | 92% |
| Fundamentadas entre as respondidas | 80,8% | 93,5% |
| Fundamentadas no total | 42% | 58% |
| Recusas corretas | 92,9% | 92,9% |
| Falsas recusas | 48% | 38% |
| Candidatas a alucinação | q36, u07 | u07 |

O `hybrid_rerank` teve Recall@5 de 58% (`fixed`) e 56% (`recursive`), o que confirma a ADR 002.

### Decisão

- **Aceito:**
  - o plano P1–P9;
  - a correção da verificação;
  - o conjunto 2.1.0 congelado;
  - a interface de chat;
  - o compose com o Ollama 0.12.6;
  - as evidências 3, 4 e 6.
- **Corrigido:**
  - o teste offline que dependia do texto antigo da q27;
  - o script de evidências, que passou a ignorar a execução interrompida por uma queda de internet (pasta sem `summary.json`).
- **Descartado:**
  - as duas regras novas de prompt, sem efeito medido;
  - afrouxar a cobertura de citações, sem ganho no conjunto de desenvolvimento e com risco nas respostas forjadas;
  - calibrar qualquer regra olhando o conjunto de teste.

### Limitações registradas

- A verificação é lexical: a alucinação do u07 e a resposta forjada do bcrypt passam por ela.
- O `docker compose up` com o Ollama 0.12.6 ainda não foi executado. A CI só faz o build das imagens.
- A avaliação oficial rodou no caminho Windows (`QDRANT_MODE=local`), não no Docker.

### Verificação

- `ruff check` e `ruff format --check` limpos.
- **190 testes passando** (eram 185), com 94% de cobertura.
- Auditoria ao vivo da interface de chat contra a API real: 9 de 9 itens.
- CI verde no GitHub nos 3 pushes anteriores, inclusive o job de build das imagens.

---

<!-- Próximas interações: 3 a 10+. Registre também usos menores mas relevantes (ex.: depurar um erro, ajustar um prompt após a avaliação). -->
