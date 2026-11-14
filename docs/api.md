# Referência da API e da interface

A documentação interativa (OpenAPI/Swagger) é gerada pelo FastAPI em <http://localhost:8000/docs>, e o esquema fica em `/openapi.json`. Os contratos completos estão em [arquitetura.md, seção 3](arquitetura.md#3-contratos-de-entrada-e-saída).

## Endpoints

| Método | Caminho | Descrição | Erros |
| --- | --- | --- | --- |
| `GET` | `/health` | Estado do Qdrant e do Ollama e número de chunks por coleção. `status` = `ok` ou `degraded` | — |
| `GET` | `/config` | Configuração em uso, sem segredos | — |
| `POST` | `/ask` | Pergunta → resposta com citações ou recusa. Aceita um print opcional em `image_base64` | 422, 409, 503 |
| `POST` | `/search` | Só a recuperação, sem chamar o LLM (também aceita `image_base64`) | 422, 409, 503 |
| `POST` | `/ingest` | Reindexa `DOCS_DIR` (recria as coleções) | 403 se `ENABLE_INGEST_ENDPOINT=false` |
| `GET` | `/documents` | Arquivos da base, com título, tamanho, seções e chunks por estratégia | — |
| `GET` | `/documents/{arquivo}?strategy=` | Texto, caminho, seções e chunks de um arquivo da base | 404 fora da base, 422 |
| `GET` | `/validation/questions` | Perguntas do conjunto de teste, com fonte e trechos esperados | 404 |
| `POST` | `/validation/retrieval` | Confere, pergunta a pergunta, se o trecho esperado veio entre os top-k (mesma regra de `eval/run_eval.py`) | 422 |

### Perguntas com print

Envie a imagem em base64 (PNG, JPG ou WEBP, até `MAX_IMAGE_MB`, padrão 5 MB) no campo `image_base64`. A pergunta pode ficar vazia quando houver imagem.

1. O modelo de visão (`VISION_MODEL`, padrão `qwen2.5vl:3b`) transcreve o texto e o código do print.
2. A transcrição volta no campo `image_text` e é anexada à pergunta, tanto na busca quanto no prompt.
3. A imagem **nunca é fonte**: a resposta precisa citar trechos da documentação e passa pela mesma verificação de citações.

Os erros possíveis são:
- **422:** imagem inválida, grande demais ou em formato não aceito;
- **503:** modelo de visão ausente (`ollama pull qwen2.5vl:3b`) ou Modo de Visualização ativo.

A imagem não é gravada; o log registra só o começo do texto lido.

### Exemplos

```bash
curl -s http://localhost:8000/ask -H "Content-Type: application/json" \
  -d '{"question": "Como sobrescrever uma dependência nos testes?"}'

curl -s http://localhost:8000/search -H "Content-Type: application/json" \
  -d '{"question": "dependency_overrides", "strategy": "fixed", "mode": "bm25", "top_k": 3}'

curl -s -X POST http://localhost:8000/ingest -H "Content-Type: application/json" \
  -d '{"strategies": ["recursive"]}'
```

No PowerShell, use `Invoke-RestMethod`:

```powershell
Invoke-RestMethod -Uri http://localhost:8000/ask -Method Post -ContentType "application/json" `
  -Body '{"question": "Como sobrescrever uma dependência nos testes?"}'
```

### Motivos de recusa (`refusal_reason`)

| Valor | Significado | O LLM foi chamado? |
| --- | --- | --- |
| `no_context` | Nenhum trecho recuperado | Não |
| `low_relevance` | Melhor cosseno abaixo de `MIN_VECTOR_SCORE` | Não |
| `llm_refusal` | O modelo respondeu com a frase de recusa | Sim |
| `ungrounded_answer` | O modelo respondeu sem citação válida; resposta descartada | Sim |

## Linha de comando

| Comando | Função |
| --- | --- |
| `python -m ingestion.cli --strategy all\|fixed\|recursive [--docs-dir PASTA] [--skip-existing] [--warmup-reranker]` | Indexa a documentação |
| `python -m eval.run_eval [--reindex] [--generate] [--strategies ...] [--modes ...] [--k 1 3 5 10] [--dataset ARQ]` | Avaliação experimental (ver [avaliacao.md](avaliacao.md)) |
| `python scripts/download_fastapi_docs.py --version 0.115.5 --lang en` | Baixa a documentação oficial do FastAPI |

## Interface web

Em <http://localhost:8501>, com três abas:

- **Perguntar:** o Enter envia, e é possível anexar um print;
- **Documentos:** a base indexada, arquivo por arquivo;
- **Validação:** o conjunto de teste rodado ao vivo.

Passo a passo em [manual-usuario.md](manual-usuario.md).
