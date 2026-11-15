# Instalação e execução

Há **dois caminhos para rodar o mesmo sistema**. Eles não são etapas um do outro: escolha um e siga só a seção dele.

| | Caminho Windows | Caminho Docker |
| --- | --- | --- |
| Para quem | Integrantes do grupo, no dia a dia | Professor, vídeo da entrega, avaliação oficial, Linux/macOS |
| Instala | `scripts\instalar.ps1`, uma vez | Docker Desktop, uma vez |
| Sobe | `scripts\run_local.ps1` | `docker compose up --build` |
| Python e Ollama | Instalados no Windows (o instalador cuida disso) | Dentro dos containers; nada a instalar |
| Banco vetorial | Qdrant embutido em disco (`.qdrant_local/`) | Qdrant em container |
| Modelos | `qwen2.5:3b` e `nomic-embed-text` no Ollama do Windows | Os mesmos, baixados pelo compose |
| Sem Ollama | Modo de Visualização (Mock), sem IA generativa | Não se aplica: o Ollama vem no compose |
| Vale para a avaliação | Só com o Ollama ativo; o mock nunca vale | **Sim** |

Nenhum dos dois caminhos usa chave de API ou serviço pago.

---

## Caminho Windows

### 1. Instalação assistida (`scripts\instalar.ps1`)

```powershell
git clone https://github.com/eugustavocorreaDev/projetoIntegrador_unianchieta_GLR.git
cd projetoIntegrador_unianchieta_GLR
powershell -ExecutionPolicy Bypass -File scripts\instalar.ps1
```

O script confere tudo o que o projeto precisa e, para cada coisa que falta, **mostra de onde vai instalar e pergunta antes**:
- **programas:** pelo `winget`, com o instalador oficial do fabricante;
- **pacotes Python:** do PyPI;
- **modelos:** da biblioteca oficial do Ollama.

Sem o `winget`, o script mostra o link oficial para instalar à mão. No final, ele mostra um checklist. Pode ser rodado quantas vezes quiser: o que já estiver certo é só conferido.

| Grupo | Item | Como é conferido | Se faltar |
| --- | --- | --- | --- |
| Sistema | `winget` | Comando disponível | Avisa: instale o "App Installer" pela Microsoft Store |
| Sistema | Git | `git --version` | Oferece `winget install Git.Git` |
| Sistema | Python 3.11+ | Procura `py -3.11`, `py -3.12` e o `python` do PATH, nessa ordem | Oferece `winget install Python.Python.3.11` |
| Projeto | `.venv` | Existe e usa Python 3.11+ | Cria (com o `uv`, se houver; senão, com o Python encontrado) |
| Projeto | Dependências | `scripts/verificar_dependencias.py` compara cada pacote instalado com a versão fixada no `pyproject.toml` e confere os pacotes de `src/` | Roda `pip install -e ".[dev,ui]"` |
| Projeto | `.env` | Existe | Copia do `.env.example` |
| IA local | Ollama instalado | Comando `ollama` ou a pasta padrão do instalador | Oferece `winget install Ollama.Ollama` |
| IA local | Ollama em execução | Responde em `http://localhost:11434` | Abre o Ollama e espera até 30 s |
| IA local | `nomic-embed-text` | Baixado e gerando um vetor de teste | `ollama pull nomic-embed-text` (~270 MB) |
| IA local | Modelo de geração | `LLM_MODEL` do `.env` (padrão `qwen2.5:3b`) baixado e respondendo a um prompt de teste | `ollama pull qwen2.5:3b` (~2 GB) |
| Docker | Desktop, Engine e Compose v2 | `docker info` e `docker compose version` | Opcional neste caminho: só oferece instalar ou abrir |
| Máquina | RAM, disco, portas 8000 e 8501 | 8 GB de RAM, 6 GB livres em disco, portas livres | Avisa |

O teste do modelo de geração usa `keep_alive` de 30 minutos: o modelo fica **aberto na memória do Ollama**, e a primeira pergunta no sistema já sai rápida.

Os status do checklist significam:

- **OK:** o item está certo.
- **FALTA:** impede o uso com IA real. O script mostra o comando que resolve.
- **AVISO:** funciona, mas vale corrigir.
- **OPCIONAL:** só é necessário no outro caminho.

O script termina com código 0 quando nada está em FALTA.

| Opção | Efeito |
| --- | --- |
| `-Verificar` | Só audita e mostra o checklist, sem instalar nem alterar nada |
| `-Sim` | Responde "sim" a todas as perguntas (o Docker só é instalado junto com `-ComDocker`) |
| `-ComDocker` | Trata o Docker como obrigatório e oferece instalá-lo |
| `-Modelo llama3.2:3b` | Usa outro modelo de geração de 3B |
| `-Iniciar` | No final, sobe e valida o projeto (`run_local.ps1 -Testar`) sem perguntar |

### 2. Subir o sistema (`scripts\run_local.ps1`)

```powershell
powershell -ExecutionPolicy Bypass -File scripts\run_local.ps1
```

O script:

1. ativa o `.venv` (se ele não existir, pede para rodar o `instalar.ps1` antes);
2. procura o Ollama em `localhost:11434`:
   - **com** `nomic-embed-text` e um modelo de geração (`LLM_MODEL` do `.env`, `llama3.2:3b` ou `qwen2.5:3b`), usa a IA real (`LLM_MODE=ollama`, `EMBED_MODE=ollama`);
   - **sem** Ollama ou sem os modelos, usa o Modo de Visualização (`LLM_MODE=mock`, `EMBED_MODE=hash`) e diz o que falta;
3. indexa `data/raw_docs` no Qdrant em disco (`.qdrant_local/`). Ele **reindexa sozinho** quando a documentação, o chunking ou o modelo mudam, e pula quando nada mudou;
4. abre a API em <http://localhost:8000> numa nova janela, chamada "RAG API", com recarga automática ao salvar arquivos de `src/`;
5. abre a interface em <http://localhost:8501> no navegador.

Opções:
- `-Mock` força o Modo de Visualização;
- `-Reindex` recria o índice do zero;
- `-Testar` valida a instalação de ponta a ponta antes de abrir a interface. Ele faz duas perguntas à API: uma coberta pela documentação, que precisa ser respondida com citação, e "O que é HTML?", que precisa ser recusada. O `instalar.ps1` usa esta opção quando você aceita iniciar o projeto no final.

Para parar, use `Ctrl+C` na janela da interface e feche a janela "RAG API". Para reiniciar, por exemplo depois de instalar o Ollama, rode o mesmo comando de novo.

### Cuidados do caminho Windows

- **Um processo por vez** abre `.qdrant_local/`. Com a API no ar, a ingestão e a avaliação pela linha de comando falham, com uma mensagem pedindo para parar a API. Para reindexar sem parar a API, use o endpoint dela:

  ```powershell
  Invoke-RestMethod http://localhost:8000/ingest -Method Post -ContentType "application/json" -Body '{}'
  ```

- O modo `hash` grava em coleções separadas (`techdocs_hash_*`). Trocar de modo nunca mistura índices de dimensões diferentes.
- O **mock não é um LLM**: ele organiza as frases dos trechos mais parecidos com a pergunta, com as citações, ou recusa. A interface avisa, e o relatório de `eval/` marca a execução como inválida para resultados.

### Execução manual, sem os scripts

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e ".[dev,ui]"
$env:QDRANT_MODE="local"; $env:LLM_MODE="ollama"; $env:EMBED_MODE="ollama"
python -m ingestion.cli --strategy all --skip-existing
uvicorn api.main:app --app-dir src --reload --reload-dir src --port 8000   # terminal 1
streamlit run src/ui/app.py                                              # terminal 2
```

Sem o Ollama, troque a quarta linha por `$env:QDRANT_MODE="local"; $env:LLM_MODE="mock"; $env:EMBED_MODE="hash"`.

---

## Caminho Docker

### Pré-requisitos

| Item | Mínimo | Observação |
| --- | --- | --- |
| Docker com Compose v2 | Docker 24 / Compose 2.20 | Docker Desktop no Windows e no macOS. No Windows: `winget install -e --id Docker.DockerDesktop` ou `scripts\instalar.ps1 -ComDocker`, e depois reiniciar |
| Memória RAM livre | 8 GB | O modelo de 3B usa cerca de 2,5 GB |
| Disco livre | 6 GB | Modelos (~2,3 GB) e imagens |
| Internet | Só na primeira execução | Para baixar imagens, modelos e o reranker |
| GPU | Opcional | Sem GPU, cada resposta leva de 10 s a 60 s |

### Passo a passo

```bash
git clone https://github.com/eugustavocorreaDev/projetoIntegrador_unianchieta_GLR.git
cd projetoIntegrador_unianchieta_GLR
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
- **Perguntas com print:** crie um `.env` com `PULL_VISION_MODEL=true` antes do `docker compose up`. O `ollama-pull` baixa então também o `qwen2.5vl:3b` (~3,2 GB). Sem isso, as perguntas com imagem respondem 503 com a instrução de instalar o modelo. O compose usa o `ollama/ollama:0.12.6`, porque a 0.5.4 não roda esse modelo.
- **Porta 11434 ocupada** (Ollama também instalado no Windows, pelo caminho Windows): crie um `.env` com `OLLAMA_PORT=11435`, ou feche o Ollama do Windows antes.
- **Hosts Linux:** os containers gravam em `./logs` e `./eval` com o UID 1000. Se o seu usuário tiver outro UID, rode `sudo chown -R 1000:1000 logs eval` uma vez.

---

## Variáveis de ambiente

Todas têm valor padrão: nada precisa ser configurado para rodar. Para mudar algo, edite o `.env` (o `instalar.ps1` o cria a partir do `.env.example`).

- **Caminho Docker:** o `docker compose` lê esse arquivo para os modelos e parâmetros, mas os endereços internos (`OLLAMA_BASE_URL`, `QDRANT_URL`, `API_URL`) são fixados pelo próprio compose.
- **Caminho Windows:** o `run_local.ps1` define `QDRANT_MODE`, `LLM_MODE`, `EMBED_MODE` e `LLM_MODEL` conforme o que encontrar.

| Variável | Padrão | Função |
| --- | --- | --- |
| `LLM_MODE` | `ollama` | `ollama` ou `mock` (Modo de Visualização, só desenvolvimento) |
| `EMBED_MODE` | `ollama` | `ollama` ou `hash` (embeddings por hashing, só desenvolvimento) |
| `QDRANT_MODE` / `QDRANT_PATH` | `server` / `.qdrant_local` | `local` usa o Qdrant embutido em disco, sem servidor |
| `OLLAMA_BASE_URL` | `http://localhost:11434` | Endereço do Ollama |
| `EMBED_MODEL` | `nomic-embed-text` | Modelo de embeddings |
| `EMBED_QUERY_PREFIX` / `EMBED_DOCUMENT_PREFIX` | `search_query: ` / `search_document: ` | Prefixos exigidos pelo nomic; deixe vazio para outros modelos |
| `LLM_MODEL` | `qwen2.5:3b` | Modelo de geração (é o que o `instalar.ps1` baixa) |
| `LLM_TEMPERATURE` / `LLM_SEED` | `0.0` / `42` | Geração determinística, para reprodutibilidade |
| `LLM_NUM_CTX` / `LLM_MAX_TOKENS` | `4096` / `512` | Janela de contexto e tamanho máximo da resposta |
| `REQUEST_TIMEOUT_S` | `180` | Tempo limite das chamadas ao Ollama |
| `QDRANT_URL` | `http://localhost:6333` | Endereço do Qdrant servidor |
| `QDRANT_COLLECTION_PREFIX` | `techdocs` | Prefixo das coleções (`<prefixo>_<estratégia>`) |
| `DOCS_DIR` | `data/raw_docs` | Pasta com os Markdown a indexar |
| `CHUNK_STRATEGY` | `recursive` | Estratégia padrão: `fixed` ou `recursive` |
| `CHUNK_SIZE` / `CHUNK_OVERLAP` | `800` / `120` | Tamanho máximo do chunk e sobreposição (caracteres) |
| `RETRIEVAL_MODE` | `hybrid` | `vector`, `bm25`, `hybrid` ou `hybrid_rerank` (ver ADR 002) |
| `VISION_MODEL` / `MAX_IMAGE_MB` | `qwen2.5vl:3b` / `5` | Modelo que lê os prints enviados com a pergunta (opcional) e tamanho máximo da imagem |
| `EVAL_DATASET` | `eval/datasets/perguntas_teste.json` | Conjunto de teste usado pela aba Validação |
| `TOP_K` / `CANDIDATES_K` / `RRF_K` | `5` / `20` / `60` | Trechos enviados ao LLM, candidatos por busca, constante do RRF |
| `RERANKER_MODEL` | `ms-marco-MultiBERT-L-12` | Modelo FlashRank |
| `MIN_VECTOR_SCORE` | `0.0` | Limite de cosseno para chamar o LLM (0 desativa) |
| `MIN_CITATION_COVERAGE` | `0.5` | Fração mínima das afirmações da resposta com citação |
| `MIN_SUPPORT_RATIO` | `0.3` | Fração mínima dos termos de cada afirmação presentes no trecho citado |
| `ENABLE_INGEST_ENDPOINT` | `true` | Habilita o `POST /ingest` |
| `LOG_LEVEL` / `LOG_DIR` | `INFO` / `logs` | Nível e pasta dos logs JSON |
| `API_URL` | `http://localhost:8000` | Endereço da API usado pela interface |
| `OLLAMA_PORT` | `11434` | Porta do Ollama publicada no host (caminho Docker) |

---

## Usar a documentação oficial do FastAPI (opcional)

```bash
python scripts/download_fastapi_docs.py --version 0.115.5 --lang en
```

Depois, aponte `DOCS_DIR=data/external/fastapi/en` no `.env` e reindexe:

- **caminho Docker:** `docker compose run --rm ingest`;
- **caminho Windows:** rode o `run_local.ps1` de novo.

O conjunto de teste de `eval/` foi escrito para a base de `data/raw_docs`. Para avaliar a documentação oficial, é preciso um conjunto próprio.

---

## Problemas comuns

O primeiro passo para quase todos eles, no Windows, é rodar `scripts\instalar.ps1 -Verificar`. Ele mostra exatamente o que está faltando.

| Sintoma | Causa provável | Solução |
| --- | --- | --- |
| `docker: CommandNotFoundException` | Docker não instalado | Use o caminho Windows, ou instale o Docker (`scripts\instalar.ps1 -ComDocker`) e reinicie |
| `running scripts is disabled on this system` | Política de execução do PowerShell | Rode os scripts com `powershell -ExecutionPolicy Bypass -File ...`, como nos exemplos |
| `ollama: comando não encontrado` logo após instalar | O PowerShell foi aberto antes da instalação | Feche e abra o PowerShell; o `instalar.ps1` já recarrega o PATH sozinho |
| Faixa "Modo de Visualização (Mock)" na interface | Ollama fechado ou sem os modelos | Rode `scripts\instalar.ps1`; depois feche a janela "RAG API" e rode o `run_local.ps1` de novo |
| `run_local.ps1`: "Ambiente ainda não instalado" | Falta o `.venv` | Rode `scripts\instalar.ps1` |
| `409 Coleção ... não indexada` | A ingestão falhou ou não rodou | Docker: `docker compose logs ingest`. Windows: rode o `run_local.ps1` de novo |
| `503 Modelo ... não encontrado` | Modelo não baixado | Windows: `scripts\instalar.ps1`. Docker: `docker compose run --rm ollama-pull` |
| `503 O LLM excedeu o tempo limite` | CPU lenta ou primeira carga do modelo | Aumente `REQUEST_TIMEOUT_S` ou reduza `TOP_K` |
| Ingestão: "Pare a API e rode de novo" | A API está com `.qdrant_local/` aberta | Feche a janela "RAG API" ou use o `POST /ingest` |
| A interface diz "a resposta usou a busca híbrida" | O modelo do reranker não baixou | Verifique a internet. O sistema tenta de novo depois de 5 minutos |
