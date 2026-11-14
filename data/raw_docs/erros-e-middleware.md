# Tratamento de erros, middleware e CORS

## Levantando erros HTTP

Para devolver um erro ao cliente, levante uma `HTTPException` com o código de status e uma mensagem:

```python
from fastapi import HTTPException

@app.get("/items/{item_id}")
async def read_item(item_id: str):
    if item_id not in items:
        raise HTTPException(status_code=404, detail="Item não encontrado")
    return items[item_id]
```

A exceção interrompe a execução e a resposta é um JSON no formato `{"detail": "Item não encontrado"}`. O argumento `detail` aceita qualquer valor que possa ser convertido em JSON, como um dicionário ou uma lista. Também é possível enviar cabeçalhos adicionais com o argumento `headers`.

## Manipuladores de exceção personalizados

Para tratar uma exceção própria da aplicação, registre um manipulador com o decorador `@app.exception_handler(MinhaExcecao)`. A função recebe a requisição e a exceção e devolve a resposta, por exemplo um `JSONResponse` com o status 418.

Os erros de validação de dados geram uma `RequestValidationError`, que por padrão vira uma resposta 422 com a lista de problemas encontrados. Registrar um manipulador para essa exceção permite mudar o formato dessa resposta.

## Middleware

Um middleware é uma função executada em toda requisição, antes de ela chegar à rota, e em toda resposta, antes de ela voltar ao cliente:

```python
import time

@app.middleware("http")
async def add_process_time_header(request, call_next):
    start = time.perf_counter()
    response = await call_next(request)
    # Mede quanto tempo a rota levou para responder
    response.headers["X-Process-Time"] = str(time.perf_counter() - start)
    return response
```

A função `call_next` repassa a requisição para a rota correspondente e devolve a resposta gerada.

## CORS

CORS (Cross-Origin Resource Sharing) controla quais origens, como um frontend em outro domínio ou porta, podem chamar a API pelo navegador. Configure com o `CORSMiddleware`:

```python
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

Por padrão, o `CORSMiddleware` permite apenas o método GET, por isso é comum liberar outros métodos com `allow_methods`. Quando `allow_credentials` é verdadeiro, a lista de origens não pode ser o curinga `["*"]`: as origens precisam ser listadas explicitamente.

## Outros middlewares prontos

O FastAPI reexporta middlewares do Starlette para necessidades comuns:

- `GZipMiddleware` comprime as respostas para clientes que aceitam gzip. O argumento `minimum_size` evita comprimir respostas pequenas.
- `TrustedHostMiddleware` recusa requisições cujo cabeçalho `Host` não esteja na lista `allowed_hosts`, o que protege contra ataques de cabeçalho Host.
- `HTTPSRedirectMiddleware` redireciona toda requisição HTTP para o endereço HTTPS equivalente.

```python
from fastapi.middleware.gzip import GZipMiddleware

app.add_middleware(GZipMiddleware, minimum_size=1000)
```
