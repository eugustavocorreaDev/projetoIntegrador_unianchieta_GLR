# Instalação e execução

Há **dois fluxos independentes**. Escolha um deles e siga só a seção correspondente.

| | Fluxo A: oficial | Fluxo B: desenvolvimento local |
| --- | --- | --- |
| Para quê | Entrega, vídeo, avaliação e correção pelo professor | Programar e testar no Windows sem Docker |
| Sistema | Windows, Linux ou macOS com Docker | Windows com PowerShell |
| Precisa de | Docker Desktop (ou Docker Engine + Compose v2) | Python 3.11+; Ollama recomendado |
| Comando | `docker compose up --build` | `powershell -ExecutionPolicy Bypass -File scripts\run_local.ps1` |
| Banco vetorial | Qdrant em container | Qdrant embutido em disco, na pasta `.qdrant_local/` |
| Modelos | Ollama em container, baixados automaticamente (`qwen2.5:3b` e `nomic-embed-text`) | Ollama instalado no Windows (`llama3.2:3b` ou `qwen2.5:3b`, e `nomic-embed-text`) |
| Sem Ollama | Não se aplica: o Ollama vem no compose | Modo de Visualização (Mock), sem IA generativa |
| Vale para a avaliação | **Sim** | Só com o Ollama ativo; o mock nunca vale |

Nenhum dos dois fluxos usa chave de API ou serviço pago.

---

## Fluxo A: execução oficial (Docker + Ollama)

### Pré-requisitos

| Item | Mínimo | Observação |
| --- | --- | --- |
| Docker com Compose v2 | Docker 24 / Compose 2.20 | Docker Desktop no Windows e no macOS |
| Memória RAM livre | 8 GB | O modelo de 3B usa cerca de 2,5 GB |
| Disco livre | 6 GB | Modelos (~2,3 GB) e imagens |
| Internet | Só na primeira execução | Para baixar imagens, modelos e o reranker |
| GPU | Opcional | Sem GPU, cada resposta leva de 10 s a 60 s |

### Passo a passo

```bash
git clone <url-do-repositorio>
cd <pasta-do-repositorio>
docker compose up --build
```

O que acontece, em ordem:

1. `ollama` e `qdrant` sobem.
2. `ollama-pull` baixa `nomic-embed-text` e `qwen2.5:3b` (só na primeira vez) e termina.
3. `ingest` indexa `data/raw_docs/` nas coleções `techdocs_fixed` e `techdocs_recursive`, baixa o modelo do reranker e termina. Nas execuções seguintes, ele só reindexa se a documentação, o chunking ou o modelo de embeddings mudaram.
4. `api` sobe em <http://localhost:8000>, com a documentação OpenAPI em <http://localhost:8000/docs>.
5. `frontend` sobe em <http://localhost:8501> quando a API responde ao healthcheck.

A primeira execução leva de 5 a 15 minutos; as seguintes, menos de 1 minuto. Para parar: `Ctrl+C` ou `docker compose down`. Para apagar também os modelos e o índice: `docker compose down -v`.

### Reindexar depois de mudar a documentação

```bash
docker compose run --rm ingest
```

### Opções

- **GPU NVIDIA:** descomente o bloco `deploy` do serviço `ollama` no `docker-compose.yml`. É preciso ter o NVIDIA Container Toolkit.
- **Porta 11434 ocupada** (Ollama também instalado na máquina): crie um `.env` com `OLLAMA_PORT=11435`.
- **Hosts Linux:** os containers gravam em `./logs` e `./eval` com o UID 1000. Se o seu usuário tiver outro UID, rode `sudo chown -R 1000:1000 logs eval` uma vez.

---

## Fluxo B: desenvolvimento local no Windows (sem Docker)

### 1. Instale o Python 3.11+

Baixe em <https://www.python.org/downloads/> e marque **"Add python.exe to PATH"** na instalação. Confira com `python --version`.

### 2. (Recomendado) Instale o Ollama e baixe os modelos

Sem este passo, o sistema funciona no **Modo de Visualização (Mock)**: dá para ver a busca, as citações e a recusa, mas as respostas não são geradas por IA.

```powershell
winget install Ollama.Ollama        # ou baixe o instalador em https://ollama.com/download
```

Feche e abra o PowerShell de novo, para o comando `ollama` ficar disponível, e baixe os modelos:

```powershell
ollama pull llama3.2:3b             # geração (~2 GB)
ollama pull nomic-embed-text        # embeddings (~270 MB)
ollama list                         # os dois devem aparecer
```

O Ollama fica rodando em segundo plano em `http://localhost:11434`; o ícone dele aparece na bandeja do Windows. Se preferir o mesmo modelo do Fluxo A, use `ollama pull qwen2.5:3b`: o script detecta qual está instalado.

### 3. Suba o projeto

Na pasta do projeto:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\run_local.ps1
```

O script:

1. cria o `.venv` e instala as dependências, só na primeira vez, e ativa o ambiente;
2. copia `.env.example` para `.env`, se ainda não houver `.env`;
3. procura o Ollama em `localhost:11434`:
   - **com** `nomic-embed-text` e um modelo de geração (`LLM_MODEL` do `.env`, `llama3.2:3b` ou `qwen2.5:3b`): usa a IA real (`LLM_MODE=ollama`, `EMBED_MODE=ollama`);
   - **sem** Ollama ou sem os modelos: usa o Modo de Visualização (`LLM_MODE=mock`, `EMBED_MODE=hash`) e mostra o que falta instalar;
4. indexa `data/raw_docs` no Qdrant em disco (`.qdrant_local/`). Ele **reindexa sozinho** quando a documentação, o chunking ou o modelo mudam, e pula quando nada mudou;
5. abre a API em <http://localhost:8000> numa nova janela, chamada "RAG API", com recarga automática ao salvar arquivos de `src/`;
6. abre a interface em <http://localhost:8501> no navegador.

Opções: `-Mock` força o Modo de Visualização e `-Reindex` recria o índice do zero.

### 4. Parar e reiniciar

- Para parar: `Ctrl+C` na janela da interface e feche a janela "RAG API".
- Para reiniciar, por exemplo depois de instalar o Ollama: rode o mesmo comando do passo 3.

### Cuidados do Fluxo B

- **Um processo por vez** abre `.qdrant_local/`. Com a API no ar, a ingestão e a avaliação pela linha de comando falham, com uma mensagem pedindo para parar a API. Para reindexar sem parar a API, use o endpoint dela:

  ```powershell
  Invoke-RestMethod http://localhost:8000/ingest -Method Post -ContentType "application/json" -Body '{}'
  ```

- O modo `hash` grava em coleções separadas (`techdocs_hash_*`). Trocar de modo nunca mistura índices de dimensões diferentes.
- O **mock não é um LLM**: ele organiza as frases dos trechos mais parecidos com a pergunta, com as citações, ou recusa. A interface avisa, e o relatório de `eval/` marca a execução como inválida para resultados.

### Execução manual, sem o script

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e ".[dev,ui]"
$env:QDRANT_MODE="local"; $env:LLM_MODE="ollama"; $env:EMBED_MODE="ollama"; $env:LLM_MODEL="llama3.2:3b"
python -m ingestion.cli --strategy all --skip-existing
uvicorn api.main:app --app-dir src --reload --reload-dir src --port 8000   # terminal 1
streamlit run src/ui/app.py                                              # terminal 2
```

Sem o Ollama, troque a terceira linha por `$env:QDRANT_MODE="local"; $env:LLM_MODE="mock"; $env:EMBED_MODE="hash"`.

---

## Variáveis de ambiente

Todas têm valor padrão: nada precisa ser configurado para rodar. Para mudar algo, copie `.env.example` para `.env`. No Fluxo A, o `docker compose` lê esse arquivo para os modelos e parâmetros, mas os endereços internos (`OLLAMA_BASE_URL`, `QDRANT_URL`, `API_URL`) são fixados pelo próprio compose. No Fluxo B, o `run_local.ps1` define `QDRANT_MODE`, `LLM_MODE`, `EMBED_MODE` e `LLM_MODEL` conforme o que encontrar.

| Variável | Padrão | Função |
| --- | --- | --- |
| `LLM_MODE` | `ollama` | `ollama` ou `mock` (Modo de Visualização, só desenvolvimento) |
| `EMBED_MODE` | `ollama` | `ollama` ou `hash` (embeddings por hashing, só desenvolvimento) |
| `QDRANT_MODE` / `QDRANT_PATH` | `server` / `.qdrant_local` | `local` usa o Qdrant embutido em disco, sem servidor |
| `OLLAMA_BASE_URL` | `http://localhost:11434` | Endereço do Ollama |
| `EMBED_MODEL` | `nomic-embed-text` | Modelo de embeddings |
| `EMBED_QUERY_PREFIX` / `EMBED_DOCUMENT_PREFIX` | `search_query: ` / `search_document: ` | Prefixos exigidos pelo nomic; deixe vazio para outros modelos |
| `LLM_MODEL` | `qwen2.5:3b` | Modelo de geração |
| `LLM_TEMPERATURE` / `LLM_SEED` | `0.0` / `42` | Geração determinística, para reprodutibilidade |
| `LLM_NUM_CTX` / `LLM_MAX_TOKENS` | `4096` / `512` | Janela de contexto e tamanho máximo da resposta |
| `REQUEST_TIMEOUT_S` | `180` | Tempo limite das chamadas ao Ollama |
| `QDRANT_URL` | `http://localhost:6333` | Endereço do Qdrant servidor |
| `QDRANT_COLLECTION_PREFIX` | `techdocs` | Prefixo das coleções (`<prefixo>_<estratégia>`) |
| `DOCS_DIR` | `data/raw_docs` | Pasta com os Markdown a indexar |
| `CHUNK_STRATEGY` | `recursive` | Estratégia padrão: `fixed` ou `recursive` |
| `CHUNK_SIZE` / `CHUNK_OVERLAP` | `800` / `120` | Tamanho máximo do chunk e sobreposição (caracteres) |
| `RETRIEVAL_MODE` | `hybrid_rerank` | `vector`, `bm25`, `hybrid` ou `hybrid_rerank` |
| `TOP_K` / `CANDIDATES_K` / `RRF_K` | `5` / `20` / `60` | Trechos enviados ao LLM, candidatos por busca, constante do RRF |
| `RERANKER_MODEL` | `ms-marco-MultiBERT-L-12` | Modelo FlashRank |
| `MIN_VECTOR_SCORE` | `0.0` | Limite de cosseno para chamar o LLM (0 desativa) |
| `MIN_CITATION_COVERAGE` | `0.5` | Fração mínima das afirmações da resposta com citação |
| `MIN_SUPPORT_RATIO` | `0.3` | Fração mínima dos termos de cada afirmação presentes no trecho citado |
| `ENABLE_INGEST_ENDPOINT` | `true` | Habilita o `POST /ingest` |
| `LOG_LEVEL` / `LOG_DIR` | `INFO` / `logs` | Nível e pasta dos logs JSON |
| `API_URL` | `http://localhost:8000` | Endereço da API usado pela interface |
| `OLLAMA_PORT` | `11434` | Porta do Ollama publicada no host (Fluxo A) |

---

## Usar a documentação oficial do FastAPI (opcional)

```bash
python scripts/download_fastapi_docs.py --version 0.115.5 --lang en
```

Depois, aponte `DOCS_DIR=data/external/fastapi/en` no `.env` e reindexe: no Fluxo A com `docker compose run --rm ingest`, no Fluxo B rodando o `run_local.ps1` de novo. O conjunto de teste de `eval/` foi escrito para a base de `data/raw_docs`; para avaliar a documentação oficial, é preciso um conjunto próprio.

---

## Problemas comuns

| Sintoma | Causa provável | Solução |
| --- | --- | --- |
| `docker: CommandNotFoundException` | Docker não instalado | Instale o Docker Desktop (Fluxo A) ou use o Fluxo B |
| `ollama: comando não encontrado` logo após instalar | O PowerShell foi aberto antes da instalação | Feche e abra o PowerShell de novo |
| Faixa "Modo de Visualização (Mock)" na interface | Ollama ausente ou sem os modelos | Fluxo B, passo 2; depois feche a janela "RAG API" e rode o script de novo |
| `409 Coleção ... não indexada` | A ingestão falhou ou não rodou | Fluxo A: `docker compose logs ingest`. Fluxo B: rode o script de novo |
| `503 Modelo ... não encontrado` | Modelo não baixado | `ollama pull <modelo>` (Fluxo B) ou `docker compose run --rm ollama-pull` (Fluxo A) |
| `503 O LLM excedeu o tempo limite` | CPU lenta ou primeira carga do modelo | Aumente `REQUEST_TIMEOUT_S` ou reduza `TOP_K` |
| Ingestão: "Pare a API e rode de novo" | A API está com `.qdrant_local/` aberta | Feche a janela "RAG API" ou use o `POST /ingest` |
| A interface diz "a resposta usou a busca híbrida" | O modelo do reranker não baixou | Verifique a internet. O sistema tenta de novo depois de 5 minutos |
