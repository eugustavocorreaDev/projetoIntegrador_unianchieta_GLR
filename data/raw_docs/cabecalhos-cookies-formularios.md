# Cabeçalhos, cookies e formulários

Além do caminho, da consulta e do corpo JSON, uma requisição HTTP pode trazer dados em cabeçalhos, cookies e formulários. O FastAPI lê cada um deles com uma função específica, usada da mesma forma que `Query` e `Path`.

## Cabeçalhos com Header

```python
from typing import Annotated
from fastapi import FastAPI, Header

app = FastAPI()

@app.get("/agente")
async def agente(user_agent: Annotated[str | None, Header()] = None):
    return {"User-Agent": user_agent}
```

Como a maioria dos cabeçalhos usa hífen, como `User-Agent`, e o hífen não é válido em nomes de variáveis Python, o `Header` converte automaticamente os sublinhados do nome do parâmetro em hífens. Para desligar essa conversão, use `Header(convert_underscores=False)`.

Os cabeçalhos HTTP não diferenciam maiúsculas de minúsculas, então o parâmetro `user_agent` recebe o valor de `User-Agent`, `user-agent` ou `USER-AGENT`. Quando o mesmo cabeçalho pode aparecer várias vezes, declare o tipo como `list[str]` para receber todos os valores.

## Cookies com Cookie

```python
from fastapi import Cookie

@app.get("/sessao")
async def sessao(sessao_id: Annotated[str | None, Cookie()] = None):
    return {"sessao_id": sessao_id}
```

Sem o `Cookie()`, o parâmetro seria interpretado como um parâmetro de consulta. O uso de `Annotated` com a função correta é o que informa ao FastAPI de onde o valor deve ser lido.

## Formulários com Form

Formulários HTML enviam os campos codificados como `application/x-www-form-urlencoded`, e não como JSON. Para lê-los, use `Form`:

```python
from fastapi import Form

@app.post("/login/")
async def login(username: Annotated[str, Form()], password: Annotated[str, Form()]):
    # Os campos chegam do formulário, não de um corpo JSON
    return {"username": username}
```

Para trabalhar com formulários é necessário instalar o pacote `python-multipart`, que já vem incluído em `fastapi[standard]`.

Não é possível declarar, na mesma operação de caminho, campos de formulário e um corpo JSON. A limitação vem do próprio protocolo HTTP: o corpo da requisição tem uma única codificação, ou formulário ou JSON.

## Validação e documentação

`Header`, `Cookie` e `Form` aceitam as mesmas validações e metadados de `Query`, como `min_length`, `max_length`, `pattern`, `title`, `description` e `deprecated`. Os parâmetros aparecem na documentação interativa na seção correspondente: cabeçalhos, cookies ou corpo do formulário.
