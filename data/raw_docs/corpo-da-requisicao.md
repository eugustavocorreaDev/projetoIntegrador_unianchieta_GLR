# Corpo da requisição e modelos de resposta

O corpo da requisição é o dado que o cliente envia para a API, normalmente em JSON, em métodos como POST, PUT e PATCH. No FastAPI, o corpo é descrito com modelos Pydantic.

## Declarando um modelo

```python
from pydantic import BaseModel

class Item(BaseModel):
    name: str
    description: str | None = None
    price: float
    tax: float | None = None

@app.post("/items/")
async def create_item(item: Item):
    return item
```

Com essa declaração, o FastAPI lê o corpo como JSON, converte os tipos, valida os campos e entrega à função uma instância de `Item`. Campos com valor padrão, como `description`, são opcionais. Se um campo obrigatório estiver faltando, a resposta é um erro 422 indicando o campo ausente.

Para converter o modelo em dicionário dentro da função, use `item.model_dump()`.

## Como o FastAPI decide a origem de cada parâmetro

É possível misturar parâmetros de caminho, de consulta e de corpo na mesma função. A regra é:

- se o nome aparece no caminho, é um parâmetro de caminho;
- se o tipo é simples, como `int`, `str` ou `bool`, é um parâmetro de consulta;
- se o tipo é um modelo Pydantic, é lido do corpo da requisição.

Quando a função recebe um único modelo, o JSON esperado é o próprio conteúdo do modelo. Para exigir que ele venha dentro de uma chave com o nome do parâmetro, use `Body(embed=True)`.

## Validação dentro do modelo

Use `Field` do Pydantic para validar e documentar cada campo, por exemplo `price: float = Field(gt=0, description="Preço em reais")`. As mesmas validações disponíveis em `Query` e `Path`, como `gt`, `max_length` e `pattern`, funcionam em `Field`.

## Modelo de resposta

O argumento `response_model` do decorador define o formato da resposta. O FastAPI converte o retorno da função para esse modelo e remove qualquer campo que não esteja nele, o que evita vazar dados sensíveis:

```python
class UserIn(BaseModel):
    username: str
    password: str

class UserOut(BaseModel):
    username: str

@app.post("/users/", response_model=UserOut, status_code=201)
async def create_user(user: UserIn):
    # A senha recebida nunca aparece na resposta
    return user
```

Nesse exemplo, a senha é descartada da resposta mesmo que a função devolva o objeto completo. O argumento `status_code=201` muda o código de status da resposta de sucesso, que por padrão é 200.

Para omitir da resposta os campos que não foram definidos explicitamente, use `response_model_exclude_unset=True`.

## Atualizações parciais com PATCH

Em uma atualização parcial, o cliente envia só os campos que quer mudar. Declare um modelo com todos os campos opcionais e use `model_dump(exclude_unset=True)` para obter apenas os campos enviados:

```python
class ItemUpdate(BaseModel):
    name: str | None = None
    price: float | None = None

@app.patch("/items/{item_id}")
async def update_item(item_id: str, changes: ItemUpdate):
    stored = Item(**items[item_id])
    # Só os campos enviados pelo cliente substituem os valores guardados
    updated = stored.model_copy(update=changes.model_dump(exclude_unset=True))
    items[item_id] = updated.model_dump()
    return updated
```

Sem o `exclude_unset=True`, os campos que o cliente não enviou chegariam como `None` e apagariam os valores já guardados.

## Exemplos na documentação

Para mostrar um exemplo de corpo na documentação interativa, use o argumento `examples` de `Field`, como `name: str = Field(examples=["Caneta azul"])`. O exemplo aparece no esquema OpenAPI e já vem preenchido quando alguém testa a rota pelo navegador.
