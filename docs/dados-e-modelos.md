# Dados e modelos

## Conjuntos de dados

### Ficha: base de conhecimento (`data/raw_docs/`)

| Campo | Valor |
| --- | --- |
| Conteúdo | Guia em português do ecossistema FastAPI + Pydantic + pytest + Docker, com 20 documentos Markdown (~58 mil caracteres, 131 seções): rotas, parâmetros, corpo, respostas, cabeçalhos e formulários, APIRouter, dependências, async, erros e middleware, tarefas em segundo plano, segurança, modelos e validação Pydantic, pydantic-settings, TestClient e testes assíncronos, pytest e fixtures, imagens Docker, Docker Compose e implantação |
| Origem | Texto original escrito para o projeto com apoio de IA e revisado pelo grupo. Descreve comportamento público do FastAPI, mas não copia a documentação oficial |
| Licença | MIT (a do repositório) |
| Dados pessoais | Nenhum. E-mails e nomes nos exemplos de código são fictícios |
| Tratamento | O loader remove front matter, comentários e tags HTML conhecidas, diretivas de inclusão e marcadores de admonição. Blocos de código são preservados |
| Uso | Testes da CI, demonstração imediata e conjunto de teste oficial |

### Ficha: documentação oficial do FastAPI (`data/external/`, não versionada)

| Campo | Valor |
| --- | --- |
| Origem | <https://github.com/fastapi/fastapi>, tag fixa (padrão `0.115.5`), pasta `docs/<idioma>/docs/` |
| Licença | MIT |
| Obtenção | `python scripts/download_fastapi_docs.py --version 0.115.5 --lang en` |
| Limitação conhecida | Os exemplos de código entram por diretivas `{* ../../docs_src/... *}`, que o loader remove: os trechos indexados ficam sem esses exemplos |

### Ficha: conjunto de teste oficial (`eval/datasets/perguntas_teste.json`)

| Campo | Valor |
| --- | --- |
| Tamanho | 64 perguntas: **50 com resposta e trecho-fonte esperados**, cobrindo os 20 documentos, e 14 sem resposta (assuntos ausentes, 5 armadilhas próximas ao corpus e 2 de conhecimento geral, como "O que é HTML?") |
| Campos | `id`, `question`, `answerable`, `expected_answer`, `expected_source`, `expected_section`, `expected_snippets` |
| Critério de relevância | Um chunk é relevante se contém um dos `expected_snippets` (sem acentos, sem crases, sem diferenciar maiúsculas). Assim o Recall@k independe da estratégia de chunking |
| Validação automática | `tests/test_eval.py` confere que todo trecho esperado existe no arquivo-fonte e cabe inteiro em algum chunk das duas estratégias |
| Conjunto de desenvolvimento | `eval/datasets/perguntas_dev.json`: 12 perguntas com resposta e 6 sem, sobre fatos que o conjunto de teste não usa. Serve só para calibrar `MIN_VECTOR_SCORE` |
| Ordem de escrita | Escrito e versionado antes de qualquer ajuste do sistema (versão 2.0.0, junto com a ampliação da base). Não deve ser usado para calibrar parâmetros |
| Autoria | Perguntas redigidas com apoio de IA e revisadas pelo grupo contra o corpus; registro no `PROMPTS.md` (interações 3 e 4) |

## Modelos

| Função | Modelo | Execução | Licença | Por que |
| --- | --- | --- | --- | --- |
| Embeddings | `nomic-embed-text` (v1.5, 768 dimensões) | Ollama | Apache 2.0 | Bom desempenho em recuperação, leve (~270 MB). Usa os prefixos `search_query:` e `search_document:` |
| Geração | `qwen2.5:3b` | Ollama | Qwen Research License (uso acadêmico e não comercial; conferir o texto da licença) | Melhor em português que modelos de tamanho parecido e roda em CPU |
| Reranking | FlashRank `ms-marco-MultiBERT-L-12` | ONNX em CPU | Biblioteca FlashRank: Apache 2.0. Conferir a ficha do modelo em <https://huggingface.co/prithivida/flashrank> | Cross-encoder multilíngue, sem PyTorch |

Só no desenvolvimento sem Ollama (`scripts/run_local.ps1`): `EMBED_MODE=hash` (embeddings por hashing, sem semântica) e `LLM_MODE=mock` (respondedor extrativo em `generation/mock_llm.py`, que copia frases dos trechos e **não é um modelo de linguagem**). Nenhum dos dois entra em resultados.

Alternativa de geração: `llama3.2:3b` (Llama 3.2 Community License). Basta `LLM_MODEL=llama3.2:3b` e rodar a avaliação de novo.

### Ficha resumida do uso do LLM

- **Uso pretendido:** responder perguntas sobre a documentação indexada, só com base nos trechos recuperados.
- **Fora do escopo:** conhecimento geral, aconselhamento, geração de código que não esteja na documentação.
- **Parâmetros:** `temperature=0`, `seed=42`, `num_ctx=4096`, `num_predict=512`.
- **Riscos conhecidos:** omitir citações (tratado pela verificação de citações), citar o trecho errado (medido por `grounded_rate_snippet`) e parafrasear de forma imprecisa (não detectado automaticamente; analisar nos casos de falha).
