# Segurança e autenticação

O FastAPI oferece utilitários no módulo `fastapi.security` para implementar esquemas de autenticação padronizados, que também aparecem na documentação interativa com um botão "Authorize".

## Fluxo de senha com OAuth2 e token Bearer

O esquema `OAuth2PasswordBearer` indica que o cliente deve enviar um token no cabeçalho `Authorization` no formato `Bearer <token>`:

```python
from fastapi.security import OAuth2PasswordBearer

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

@app.get("/users/me")
async def read_me(token: Annotated[str, Depends(oauth2_scheme)]):
    return {"token": token}
```

O argumento `tokenUrl` aponta para a rota onde o cliente troca usuário e senha por um token. Se a requisição chegar sem o cabeçalho, a dependência responde automaticamente com o status 401.

Na rota de login, o formulário com usuário e senha é lido com `OAuth2PasswordRequestForm`. Como esses dados chegam como formulário e não como JSON, é preciso ter o pacote `python-multipart` instalado.

## Erros de autenticação

Quando as credenciais são inválidas, responda com `HTTPException` usando o status 401 e o cabeçalho `WWW-Authenticate` com o valor `Bearer`, como define a especificação do esquema.

## Senhas e tokens JWT

Nunca armazene senhas em texto puro. Guarde apenas o hash da senha, calculado com um algoritmo próprio para senhas, e compare o hash no momento do login.

Depois do login, a aplicação pode emitir um token JWT assinado contendo o identificador do usuário e uma data de expiração. A chave usada para assinar o token deve ficar em uma variável de ambiente, nunca no código-fonte nem no repositório.

## Escopos

O OAuth2 permite definir escopos, que são permissões nomeadas como `items:read` ou `items:write`. Com a classe `Security` e o parâmetro `scopes`, cada rota declara quais escopos o token precisa ter, e o FastAPI rejeita tokens sem as permissões necessárias.

## Chave de API em cabeçalho

Para integrações entre sistemas, um esquema simples é exigir uma chave de API em um cabeçalho. A classe `APIKeyHeader`, de `fastapi.security`, lê o cabeçalho e o documenta no OpenAPI:

```python
from fastapi.security import APIKeyHeader

api_key_header = APIKeyHeader(name="X-API-Key")

async def verificar_chave(chave: Annotated[str, Depends(api_key_header)]):
    # Compare com a chave guardada em uma variável de ambiente
    if chave != settings.api_key:
        raise HTTPException(status_code=401, detail="Chave inválida")
```

Se o cabeçalho não for enviado, a própria dependência rejeita a requisição antes de a rota ser executada.

## Use sempre HTTPS

Tokens, senhas e chaves de API viajam nos cabeçalhos e no corpo das requisições. Em produção, a API deve ser acessada somente por HTTPS, para que essas credenciais não trafeguem em texto aberto pela rede.
