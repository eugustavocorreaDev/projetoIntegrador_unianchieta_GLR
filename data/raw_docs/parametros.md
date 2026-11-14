# Parâmetros de caminho e de consulta

As funções de uma operação de caminho recebem dados da URL de duas formas: parâmetros de caminho, que fazem parte do próprio caminho, e parâmetros de consulta, que vêm depois do `?` na URL.

## Parâmetros de caminho

Um parâmetro de caminho é declarado com chaves no caminho e com um argumento de mesmo nome na função:

```python
@app.get("/items/{item_id}")
async def read_item(item_id: int):
    return {"item_id": item_id}
```

Como `item_id` foi anotado como `int`, o FastAPI converte o texto da URL para inteiro. Se o cliente enviar um valor que não é número, como `/items/abc`, a API responde com o status 422 e uma mensagem explicando qual parâmetro é inválido.

### A ordem das rotas importa

As operações de caminho são avaliadas na ordem em que foram declaradas. Se existir uma rota fixa `/users/me` e uma rota com parâmetro `/users/{user_id}`, declare `/users/me` primeiro. Caso contrário, a rota com parâmetro captura a requisição e trata "me" como se fosse um `user_id`.

### Valores predefinidos com Enum

Para limitar os valores aceitos em um parâmetro de caminho, use uma classe que herda de `str` e de `Enum`. A documentação interativa passa a mostrar a lista de valores válidos, e qualquer outro valor é rejeitado com erro de validação.

## Parâmetros de consulta

Os argumentos da função que não aparecem no caminho são interpretados como parâmetros de consulta:

```python
@app.get("/items/")
async def list_items(skip: int = 0, limit: int = 10):
    # GET /items/?skip=20&limit=5
    return fake_db[skip : skip + limit]
```

Um parâmetro de consulta com valor padrão é opcional. Para torná-lo obrigatório, basta não definir valor padrão. Usar `None` como padrão indica um parâmetro opcional sem valor definido.

Parâmetros do tipo `bool` aceitam os valores `1`, `true`, `on` e `yes` como verdadeiro, sem diferenciar maiúsculas e minúsculas.

## Validações adicionais

Para validar o conteúdo de um parâmetro de consulta, combine `Annotated` com `Query`:

```python
from typing import Annotated
from fastapi import Query

@app.get("/search/")
async def search(q: Annotated[str | None, Query(min_length=3, max_length=50)] = None):
    return {"q": q}
```

Além de `min_length` e `max_length`, é possível exigir um formato com `pattern`, que recebe uma expressão regular. Para receber uma lista de valores, como em `?tag=a&tag=b`, declare o tipo como `list[str]` e use `Query()` explicitamente.

Para parâmetros de caminho numéricos, use `Path` com as validações `gt` (maior que), `ge` (maior ou igual), `lt` (menor que) e `le` (menor ou igual). Por exemplo, `Path(ge=1)` rejeita identificadores menores que 1.

## Alias, parâmetros descontinuados e ocultos

Quando o nome do parâmetro na URL não é um nome válido em Python, como `item-query`, use um alias: `q: Annotated[str | None, Query(alias="item-query")] = None`. O cliente envia `?item-query=...` e a função recebe o valor em `q`.

Para avisar que um parâmetro será removido no futuro, declare `Query(deprecated=True)`. Ele continua aceito, mas a documentação o mostra como descontinuado. Para esconder um parâmetro do esquema OpenAPI, use `Query(include_in_schema=False)`.

Os argumentos `title` e `description` acrescentam explicações que aparecem na documentação interativa, ao lado do campo do parâmetro.
