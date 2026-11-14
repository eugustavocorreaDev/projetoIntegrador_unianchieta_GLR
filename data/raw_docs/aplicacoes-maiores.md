# Aplicações maiores com APIRouter

Quando a aplicação cresce, manter todas as rotas em um único arquivo `main.py` fica difícil de ler e de testar. O FastAPI oferece a classe `APIRouter` para dividir as operações de caminho em módulos, mantendo a mesma documentação automática e o mesmo sistema de dependências.

## Estrutura de pastas sugerida

Uma organização comum separa rotas, modelos e dependências em pacotes Python:

```text
app/
├── __init__.py
├── main.py            # cria o FastAPI e inclui os roteadores
├── dependencies.py    # dependências compartilhadas
└── routers/
    ├── __init__.py
    ├── items.py
    └── users.py
```

Cada pasta com um arquivo `__init__.py` vira um pacote, o que permite importações como `from app.routers import items`. A aplicação é executada a partir da pasta acima de `app`, por exemplo com `fastapi run app/main.py`.

## Criando um roteador

Um `APIRouter` funciona como uma pequena aplicação: ele aceita os mesmos decoradores `get`, `post`, `put`, `patch` e `delete`.

```python
from fastapi import APIRouter

router = APIRouter(prefix="/items", tags=["items"])

# O caminho final desta rota será /items/
@router.get("/")
async def list_items():
    return [{"name": "Caneta"}, {"name": "Caderno"}]

@router.get("/{item_id}")
async def read_item(item_id: int):
    return {"item_id": item_id}
```

O argumento `prefix` é adicionado ao início de todos os caminhos do roteador e não pode terminar com barra. O argumento `tags` agrupa as rotas na documentação interativa, o que facilita a navegação quando há muitos endpoints.

## Incluindo o roteador na aplicação

No arquivo principal, importe o módulo e registre o roteador com `include_router`:

```python
from fastapi import FastAPI
from app.routers import items, users

app = FastAPI()
app.include_router(items.router)
app.include_router(users.router)
```

O método `include_router` também aceita `prefix`, `tags`, `dependencies` e `responses`. Isso é útil para incluir um roteador de terceiros, que você não pode editar, aplicando um prefixo como `/admin` e uma dependência de autenticação só àquele grupo de rotas.

## Dependências por roteador

O parâmetro `dependencies` do `APIRouter` aplica uma lista de dependências a todas as rotas do roteador, por exemplo para exigir um token em todo o módulo de administração. As dependências do roteador são executadas antes das dependências declaradas em cada rota.

## Respostas documentadas por roteador

O parâmetro `responses` recebe um dicionário com códigos de status e descrições adicionais, como `{404: {"description": "Não encontrado"}}`. Essas respostas aparecem na documentação OpenAPI de todas as rotas do roteador, sem alterar o comportamento delas.

## Boas práticas

- Mantenha um roteador por domínio do negócio, como itens, usuários e pedidos.
- Deixe a criação do objeto `FastAPI` e a inclusão dos roteadores apenas no `main.py`.
- Coloque dependências reutilizadas em um módulo próprio, para evitar importações circulares entre roteadores.
