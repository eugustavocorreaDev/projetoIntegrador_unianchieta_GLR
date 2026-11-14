# Dependências

O sistema de injeção de dependências do FastAPI permite declarar o que uma operação de caminho precisa para funcionar, como uma conexão com o banco de dados, o usuário autenticado ou parâmetros comuns a várias rotas. O FastAPI resolve essas dependências antes de chamar a função.

## Criando uma dependência

Uma dependência é uma função comum que recebe os mesmos tipos de parâmetro que uma operação de caminho:

```python
from typing import Annotated
from fastapi import Depends

async def common_parameters(q: str | None = None, skip: int = 0, limit: int = 100):
    return {"q": q, "skip": skip, "limit": limit}

@app.get("/items/")
async def read_items(commons: Annotated[dict, Depends(common_parameters)]):
    return commons
```

O resultado da função `common_parameters` é entregue no parâmetro `commons`. Os parâmetros da dependência também aparecem na documentação interativa, como se tivessem sido declarados na própria rota.

## Classes como dependências

Qualquer objeto que pode ser chamado serve como dependência, inclusive uma classe. Nesse caso, o FastAPI chama o construtor da classe e entrega a instância criada, o que ajuda o editor a oferecer autocompletar nos atributos.

## Subdependências

Uma dependência pode depender de outra, formando uma árvore. O FastAPI resolve a árvore inteira na ordem correta. Se a mesma dependência aparece mais de uma vez na mesma requisição, ela é executada só uma vez e o resultado fica em cache durante aquela requisição. Para forçar uma nova execução a cada uso, declare `Depends(dependencia, use_cache=False)`.

## Dependências com yield

Uma dependência pode usar `yield` em vez de `return` para executar código de limpeza depois que a rota termina, como fechar uma sessão de banco de dados:

```python
async def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        # Executado ao final, mesmo que a rota levante uma exceção
        db.close()
```

O valor entregue pelo `yield` é injetado na rota. O bloco `finally` garante que o recurso seja liberado mesmo quando ocorre um erro.

## Dependências globais e em decoradores

Quando o valor retornado pela dependência não é necessário, mas ela precisa ser executada, por exemplo para verificar um cabeçalho, declare-a na lista `dependencies` do decorador: `@app.get("/items/", dependencies=[Depends(verify_token)])`.

Para aplicar uma dependência a todas as rotas da aplicação, passe a lista na criação: `app = FastAPI(dependencies=[Depends(verify_token)])`. O mesmo vale para um `APIRouter`, aplicando a dependência só às rotas daquele roteador.

## Exceções em dependências com yield

Se a rota levantar uma exceção enquanto uma dependência com `yield` está ativa, a exceção é relançada no ponto do `yield`. Por isso, o padrão é envolver o `yield` em `try` e `finally`: o bloco `finally` libera o recurso em qualquer caso. Se a dependência capturar a exceção com `except`, ela deve relançá-la com `raise`, para que o FastAPI continue tratando o erro e a resposta de erro chegue ao cliente.

## Quando usar dependências

- Para compartilhar lógica entre rotas, como paginação e filtros comuns.
- Para recursos que precisam ser abertos e fechados a cada requisição, como sessões de banco de dados.
- Para segurança, como ler e validar o token do usuário.
- Para facilitar os testes, porque qualquer dependência pode ser substituída por uma versão falsa.
