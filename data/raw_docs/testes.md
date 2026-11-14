# Testes

O FastAPI facilita os testes automatizados com o `TestClient`, que permite chamar a aplicação diretamente, sem subir um servidor.

## TestClient

O `TestClient` é baseado na biblioteca HTTPX e tem a mesma interface de um cliente HTTP comum:

```python
from fastapi.testclient import TestClient
from .main import app

client = TestClient(app)

def test_read_root():
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"message": "Olá, mundo"}
```

As funções de teste são declaradas com `def` comum, e não com `async def`, mesmo que a aplicação use funções assíncronas. Os testes são executados com o pytest, que encontra automaticamente os arquivos cujo nome começa com `test_`.

## Sobrescrevendo dependências

Para trocar uma dependência real por uma versão de teste, por exemplo substituir o banco de produção por um banco em memória, use o dicionário `app.dependency_overrides`:

```python
def override_get_db():
    # Banco de dados temporário só para os testes
    yield TestingSessionLocal()

app.dependency_overrides[get_db] = override_get_db
```

A chave do dicionário é a dependência original e o valor é a função que a substitui. Depois dos testes, limpe as substituições com `app.dependency_overrides = {}` para não afetar outros testes.

## Eventos de inicialização

O código de inicialização e de encerramento definido no `lifespan` da aplicação só é executado nos testes quando o cliente é usado como gerenciador de contexto, com `with TestClient(app) as client:`.

## Testes assíncronos

Quando o próprio teste precisa chamar funções assíncronas, como consultar um banco de dados assíncrono, use um cliente assíncrono do HTTPX com o transporte ASGI e um plugin do pytest que permita testes `async`, como o do AnyIO.

### Exemplo com AsyncClient

```python
import pytest
from httpx import ASGITransport, AsyncClient
from .main import app

@pytest.mark.anyio
async def test_root_assincrono():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/")
    assert response.status_code == 200
```

O marcador `pytest.mark.anyio` vem do plugin do AnyIO, que já é instalado como dependência do FastAPI. O `ASGITransport` envia as requisições diretamente para a aplicação, sem rede. Diferentemente do `TestClient` usado como gerenciador de contexto, o `AsyncClient` não dispara os eventos de `lifespan`; para isso, é preciso usar uma ferramenta própria, como o `LifespanManager` do pacote `asgi-lifespan`.
