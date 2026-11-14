# Configurações com pydantic-settings

Aplicações reais leem endereços de bancos de dados, chaves secretas e parâmetros de ambiente a partir de variáveis de ambiente. O pacote `pydantic-settings` estende o Pydantic para carregar e validar essas configurações. Desde a versão 2 do Pydantic, ele é instalado separadamente, com `pip install pydantic-settings`.

## Declarando as configurações

```python
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_prefix="APP_")

    nome_app: str = "Minha API"
    banco_url: str
    debug: bool = False
    max_itens: int = 50
```

Cada campo é lido de uma variável de ambiente com o mesmo nome, acrescido do prefixo definido em `env_prefix`. Neste exemplo, o campo `banco_url` vem da variável `APP_BANCO_URL`. Por padrão, os nomes das variáveis não diferenciam maiúsculas de minúsculas.

Os valores das variáveis de ambiente são sempre texto, mas o Pydantic os converte para o tipo declarado: `APP_DEBUG=true` vira o booleano `True` e `APP_MAX_ITENS=10` vira o inteiro 10. Se uma variável obrigatória estiver ausente ou inválida, a aplicação falha ao iniciar com uma `ValidationError`, o que evita descobrir o erro só em produção.

## Ordem de prioridade

Quando o mesmo campo é definido em vários lugares, vale a seguinte ordem, da maior para a menor prioridade:

1. argumentos passados ao criar a classe, como `Settings(debug=True)`;
2. variáveis de ambiente;
3. o arquivo `.env` indicado em `env_file`;
4. os valores padrão declarados na classe.

O arquivo `.env` deve ficar fora do controle de versão, listado no `.gitignore`, porque costuma conter segredos.

## Valores secretos

Use o tipo `SecretStr` para senhas e chaves. Ao imprimir as configurações ou registrar um log, o valor aparece mascarado como `**********`. Para obter o conteúdo real, chame explicitamente o método `get_secret_value()`.

```python
from pydantic import SecretStr

class SegredoSettings(BaseSettings):
    chave_jwt: SecretStr

# print(settings.chave_jwt) mostra **********
```

## Usando as configurações no FastAPI

Ler o arquivo `.env` a cada requisição seria desnecessário. O padrão recomendado é criar as configurações uma única vez, com `functools.lru_cache`, e entregá-las às rotas como dependência:

```python
from functools import lru_cache
from typing import Annotated
from fastapi import Depends

@lru_cache
def get_settings() -> Settings:
    return Settings()

@app.get("/info")
async def info(settings: Annotated[Settings, Depends(get_settings)]):
    return {"nome_app": settings.nome_app}
```

Como `get_settings` é uma dependência, os testes podem trocá-la por uma versão com valores de teste, sem alterar variáveis de ambiente da máquina.
