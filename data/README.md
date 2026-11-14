# Dados

## `raw_docs/`: base de conhecimento (versionada)

Guia técnico em português do ecossistema **FastAPI + Pydantic + pytest + Docker**, com **20 documentos Markdown** divididos em seções. O **texto é original**, escrito para este projeto com apoio de IA e revisado pelo grupo, e fica sob a licença MIT do repositório. Ele descreve o comportamento público dessas ferramentas, documentado em <https://fastapi.tiangolo.com>, <https://docs.pydantic.dev>, <https://docs.pytest.org> e <https://docs.docker.com>, mas **não é cópia da documentação oficial**.

| Tema | Documentos |
| --- | --- |
| FastAPI: fundamentos | `primeiros-passos.md`, `parametros.md`, `corpo-da-requisicao.md`, `cabecalhos-cookies-formularios.md`, `respostas-personalizadas.md` |
| FastAPI: arquitetura | `aplicacoes-maiores.md` (APIRouter), `dependencias.md`, `async-e-concorrencia.md`, `erros-e-middleware.md`, `tarefas-em-segundo-plano.md` |
| Segurança | `seguranca.md` (OAuth2, JWT, escopos, chave de API) |
| Pydantic | `pydantic-modelos.md`, `pydantic-validacao.md`, `configuracoes.md` (pydantic-settings) |
| Testes | `testes.md` (TestClient e testes assíncronos), `pytest-fundamentos.md`, `pytest-fixtures.md` |
| Docker e implantação | `docker-imagens.md`, `docker-compose.md`, `implantacao.md` |

A base serve para três coisas:

- ser o corpus do assistente: ele **só** responde com base nesses documentos;
- servir de corpus do conjunto de teste `eval/datasets/perguntas_teste.json` (50 perguntas com resposta e 14 sem);
- rodar os testes de integração da CI.

Alguns assuntos ficaram **de fora de propósito**, porque são as perguntas sem resposta do conjunto de teste: upload de arquivos, WebSockets, GraphQL, MongoDB, cache com Redis, limite de requisições, algoritmos de hash de senha, número padrão de workers e geração de clientes a partir do OpenAPI. Não acrescente esses temas sem atualizar o conjunto de teste.

Nenhum dado pessoal real aparece nos documentos. Nomes, e-mails e senhas nos exemplos são fictícios.

## `external/`: documentação oficial do FastAPI (não versionada)

Para testar o sistema numa documentação maior, baixe a documentação oficial do FastAPI (licença MIT) numa versão fixa:

```bash
python scripts/download_fastapi_docs.py --version 0.115.5 --lang en
```

Os arquivos vão para `data/external/fastapi/<lang>/`. Para indexá-los, aponte `DOCS_DIR` para essa pasta (ver [docs/instalacao.md](../docs/instalacao.md#usar-a-documentação-oficial-do-fastapi-opcional)). A pasta está no `.gitignore`: o script, a versão e o idioma bastam para reproduzir o corpus.
