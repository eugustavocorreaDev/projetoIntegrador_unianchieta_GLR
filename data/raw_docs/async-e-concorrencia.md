# Concorrência: async def ou def

O FastAPI aceita operações de caminho e dependências declaradas tanto com `async def` quanto com `def` comum. A escolha afeta como o servidor executa o código e, se for feita errada, pode travar o atendimento de todas as requisições.

## Como cada forma é executada

- Funções declaradas com `async def` rodam diretamente no laço de eventos (event loop). Enquanto esperam uma operação com `await`, como uma consulta a outro serviço, o laço atende outras requisições.
- Funções declaradas com `def` comum são executadas em um pool de threads externo, e o FastAPI aguarda o resultado. Assim, uma função síncrona que demora não bloqueia o laço de eventos.

A mesma regra vale para as dependências: uma dependência com `def` roda no pool de threads, e uma com `async def`, no laço de eventos.

## A regra prática

1. Se a biblioteca que você usa oferece funções assíncronas, que devem ser chamadas com `await`, declare a rota com `async def`.
2. Se a biblioteca é síncrona, como a maioria dos drivers de banco de dados tradicionais, declare a rota com `def` comum.
3. Se a rota não faz nenhuma espera de entrada e saída, as duas formas funcionam; `async def` evita o pequeno custo de usar uma thread.

```python
import time
import httpx

@app.get("/lento-errado")
async def lento_errado():
    # Erro: time.sleep bloqueia o laço de eventos e trava todas as requisições
    time.sleep(5)
    return {"ok": True}

@app.get("/externo")
async def externo():
    async with httpx.AsyncClient() as cliente:
        resposta = await cliente.get("https://example.com")
    return {"status": resposta.status_code}
```

## O erro mais comum

Chamar uma função bloqueante, como `time.sleep`, uma leitura síncrona de arquivo grande ou um driver de banco síncrono, dentro de uma rota `async def` bloqueia o laço de eventos. Durante esse tempo, nenhuma outra requisição é atendida pelo processo. A correção é usar a versão assíncrona da biblioteca ou declarar a rota com `def` comum.

## await só dentro de async def

A palavra `await` só pode ser usada dentro de funções declaradas com `async def`. Usá-la em uma função comum é um erro de sintaxe.

## Concorrência não é paralelismo

O modelo assíncrono é eficiente para cargas com muita espera de rede ou disco, típicas de APIs web. Para trabalho pesado de CPU, como processar imagens ou treinar modelos, o ganho vem do paralelismo: usar vários processos, por exemplo com a opção `--workers` do servidor, ou enviar o trabalho para uma fila de tarefas separada.
