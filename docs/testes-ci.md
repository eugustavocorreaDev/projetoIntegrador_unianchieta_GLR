# Testes e integração contínua

## Como executar

```bash
pip install -e ".[dev,ui]"
ruff check . && ruff format --check .
pytest --cov --cov-report=term-missing
```

Os testes **não precisam de Ollama, Qdrant em rede nem internet**. Eles usam dublês definidos em `tests/conftest.py`:

| Dublê | Substitui | Como funciona |
| --- | --- | --- |
| `HashEmbedder` (de `ingestion/embeddings.py`) | Ollama `/api/embed` | Vetor de 512 dimensões com contagem de tokens via MD5 (determinístico) |
| `FakeLLM` | Ollama `/api/chat` | Função Python que devolve uma resposta controlada pelo teste |
| `OverlapReranker` | FlashRank | Pontua pelo número de termos da pergunta presentes no trecho |
| `QdrantClient(":memory:")` | Servidor Qdrant | Modo local do próprio `qdrant-client`, com a mesma API |
| `httpx.MockTransport` | Rede HTTP | Testa os clientes reais do Ollama com respostas simuladas |
| `streamlit.testing.v1.AppTest` + `monkeypatch` | Navegador e API | Executa a interface de verdade com a API simulada |

## O que é testado

| Arquivo | Cobre |
| --- | --- |
| `test_loader.py` | Front matter, título, limpeza de HTML e diretivas, `#` dentro de código não vira título, seções e blocos |
| `test_chunking.py` | Tamanho e sobreposição do `fixed`, cobertura do texto, chunks do `recursive` dentro de uma única seção, IDs determinísticos, pontuação preservada |
| `test_retrieval.py` | Tokenização, BM25, RRF, os 4 modos × 2 estratégias, queda para `hybrid` quando o reranker falha, coleção ausente, wrapper do FlashRank |
| `test_grounding.py` | Prompt, extração de citações, remoção de citações inválidas, resposta sem citação vira recusa, variações de recusa, recusa com citação continua recusa, conhecimento externo com citação falsa é bloqueado, cobertura mínima de citações, sustentação lexical, termos críticos (número, identificador e qualificador inventados), citação depois do ponto, respostas em tópicos e com código |
| `test_ollama_clients.py` | Prefixos e lotes de embeddings, opções determinísticas do LLM, erros 404, 500, conexão e tempo limite |
| `test_pipeline_integration.py` | Ingestão das duas estratégias, reindexação sem duplicar, resposta com citação real, filtro de relevância sem chamar o LLM, falhas do LLM |
| `test_api.py` | Endpoints, validação (422), 409, 503, 403 do `/ingest`, ausência de segredos no `/config`, OpenAPI |
| `test_eval.py` | Métricas (Recall@k, MRR, Wilson), integridade dos conjuntos de teste e de desenvolvimento, separação entre os dois (sem vazamento), calibração e o script de avaliação ponta a ponta com dublês |
| `test_ui.py` | Enter no campo de chat envia a pergunta, selos de citação, recusa com "trechos mais próximos", erro de API, botões de exemplo, "só recuperar", escape de HTML, texto lido do print, aviso do modo demonstração, abas Documentos e Validação (Recall@k, respostas fundamentadas, recusas corretas), só fontes livres |
| `test_vision.py` | Perguntas com print: formatos aceitos (PNG/JPG/WEBP), base64 inválido, limite de tamanho, cliente do modelo de visão (payload, 404, 500, tempo limite), texto do print na busca e no prompt, 422 e 503 na API |
| `test_validation.py` | Endpoints das abas Documentos e Validação: chunks mostrados = chunks indexados, caminho do arquivo, 404 para arquivos fora da base (inclusive `../../.env`), conjunto de teste e conferência de recuperação com a mesma regra da avaliação |
| `test_scripts.py` | Verificador de dependências, BOM UTF-8 e funções coladas a argumentos nos `.ps1` |
| `test_local_mode.py` | Parser do prompt, respondedor extrativo (mock), fábrica por modo, Qdrant em disco ponta a ponta e persistindo, cliente serializado, pasta travada |
| `test_ingestion_cli.py` | CLI de ingestão: duas estratégias, `--skip-existing`, pasta inexistente, Ollama fora do ar, aquecimento do reranker com sucesso e falha, espera pelos serviços |
| `test_logging_setup.py` | Logs JSON (ts, level, event, campos extra, exceções), gravação em arquivo, idempotência, truncamento |

Cobertura em 15/11/2026: **94%** de `src/` e `eval/` (190 testes). Para conferir: `pytest --cov --cov-report=term-missing`. A configuração de cobertura fica em `pyproject.toml`.

## Integração contínua

O arquivo `.github/workflows/ci.yml` roda a cada push e pull request:

1. **Lint e testes:** confere que nenhum `.env` foi versionado, instala `.[dev,ui]`, roda `ruff check`, `ruff format --check` e `pytest` com cobertura, e publica `coverage.xml` e `pytest-report.xml` como artefatos.
2. **Build das imagens:** valida o `docker-compose.yml` e constrói as imagens da API e da interface.

## Regras do grupo

1. Todos os integrantes escrevem código e fazem commits distribuídos no repositório.
2. **Revisão cruzada obrigatória:** nenhum integrante aprova o próprio pull request. Todo PR é revisado por outro membro do grupo.
3. Código gerado por IA só entra na `main` por pull request, com teste automatizado passando na CI.
4. Configure em *Settings → Branches* do GitHub a proteção da `main`: exigir PR, 1 aprovação e o status `Lint e testes` verde.
