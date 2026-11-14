---
title: Primeiros passos
---

# Primeiros passos

Este guia mostra como criar a primeira aplicação com FastAPI, um framework web para construir APIs com Python baseado em anotações de tipo. As anotações são usadas para validar dados, converter tipos e gerar a documentação automaticamente.

## Instalação

A forma recomendada de instalar é com os extras padrão, que incluem o servidor Uvicorn e a ferramenta de linha de comando `fastapi`:

```bash
# Crie e ative um ambiente virtual antes de instalar
pip install "fastapi[standard]"
```

Instalar dentro de um ambiente virtual evita conflitos de versões entre projetos diferentes na mesma máquina.

## A primeira aplicação

Crie um arquivo `main.py` com o conteúdo abaixo:

```python
from fastapi import FastAPI

app = FastAPI()

# Uma "operação de caminho": método GET no caminho "/"
@app.get("/")
async def root():
    return {"message": "Olá, mundo"}
```

A variável `app` é a instância principal da aplicação. O decorador `@app.get("/")` informa que a função logo abaixo responde a requisições do tipo GET no caminho `/`. A função pode ser declarada com `async def` ou com `def` comum, e o retorno pode ser um dicionário, uma lista ou um modelo Pydantic, que são convertidos para JSON automaticamente.

## Executando o servidor

Durante o desenvolvimento, use o comando abaixo. Ele recarrega o servidor sempre que um arquivo é salvo:

```bash
fastapi dev main.py
```

Em produção, use `fastapi run main.py`, que não ativa o recarregamento automático e escuta em todas as interfaces de rede. Por padrão, o servidor atende na porta 8000.

## Documentação interativa

Com o servidor rodando, acesse `http://127.0.0.1:8000/docs` para abrir a documentação interativa gerada com o Swagger UI, onde é possível testar cada endpoint pelo navegador. Uma documentação alternativa, gerada com o ReDoc, fica em `http://127.0.0.1:8000/redoc`.

As duas páginas são construídas a partir do esquema OpenAPI da aplicação, servido em `/openapi.json`. Esse esquema também pode ser usado para gerar clientes automaticamente em outras linguagens.

## Métodos HTTP e metadados das rotas

O FastAPI oferece um decorador para cada método HTTP: `@app.get`, `@app.post`, `@app.put`, `@app.patch` e `@app.delete`. Por convenção, GET lê dados, POST cria, PUT substitui, PATCH atualiza parcialmente e DELETE remove um recurso.

Os decoradores aceitam metadados que melhoram a documentação gerada:

```python
@app.get(
    "/items/",
    summary="Lista os itens",
    tags=["items"],
    deprecated=False,
)
async def list_items():
    """Retorna todos os itens cadastrados, em ordem alfabética."""
    return []
```

O argumento `summary` define o título curto da rota e `tags` agrupa rotas relacionadas. A docstring da função vira a descrição da rota na documentação interativa, e aceita formatação Markdown. Com `deprecated=True`, a rota continua funcionando, mas aparece marcada como descontinuada.
