# Respostas personalizadas e códigos de status

Por padrão, o FastAPI converte o retorno de uma operação de caminho para JSON e o envia dentro de um `JSONResponse`. Em vários casos é preciso controlar o tipo de resposta, os cabeçalhos ou o código de status.

## Códigos de status com o módulo status

Em vez de escrever números soltos, use as constantes do módulo `status`, que deixam o código mais legível e evitam erros de digitação:

```python
from fastapi import FastAPI, status

app = FastAPI()

@app.post("/items/", status_code=status.HTTP_201_CREATED)
async def create_item(name: str):
    return {"name": name}
```

A constante `status.HTTP_201_CREATED` vale 201 e indica que um recurso foi criado. Para uma operação que não devolve conteúdo, como uma exclusão bem-sucedida, use `status.HTTP_204_NO_CONTENT` e não retorne corpo.

## Escolhendo a classe de resposta

O argumento `response_class` do decorador define a classe usada para montar a resposta e também o tipo de conteúdo documentado no OpenAPI. As classes ficam em `fastapi.responses`:

| Classe | Uso |
| --- | --- |
| `JSONResponse` | Padrão; serializa o conteúdo como JSON |
| `HTMLResponse` | Devolve uma página HTML |
| `PlainTextResponse` | Devolve texto puro |
| `RedirectResponse` | Redireciona o cliente para outra URL, por padrão com o status 307 |
| `StreamingResponse` | Envia o conteúdo aos poucos, a partir de um iterador |
| `FileResponse` | Envia um arquivo do disco de forma assíncrona |

```python
from fastapi.responses import HTMLResponse

@app.get("/painel", response_class=HTMLResponse)
async def painel():
    return "<h1>Painel</h1>"
```

## Retornando uma resposta diretamente

Uma operação de caminho também pode retornar uma instância de `Response` ou de uma subclasse. Nesse caso, o FastAPI envia a resposta como está: ele não aplica o `response_model` e não faz nenhuma conversão de dados. Por isso, ao retornar uma resposta diretamente, você é responsável por garantir que o conteúdo já esteja no formato correto.

## Streaming de conteúdo

O `StreamingResponse` recebe um gerador, síncrono ou assíncrono, e envia cada parte assim que ela fica pronta. Isso evita carregar todo o conteúdo na memória antes de responder, o que é útil para relatórios grandes ou para transmitir texto gerado aos poucos.

```python
from fastapi.responses import StreamingResponse

async def gerar_linhas():
    for numero in range(3):
        # Cada linha é enviada ao cliente assim que é produzida
        yield f"linha {numero}\n"

@app.get("/relatorio")
async def relatorio():
    return StreamingResponse(gerar_linhas(), media_type="text/plain")
```

## Cabeçalhos e cookies na resposta

Para acrescentar cabeçalhos ou cookies sem abrir mão da conversão automática, declare um parâmetro do tipo `Response` na função e altere-o:

```python
from fastapi import Response

@app.get("/preferencias")
async def preferencias(response: Response):
    response.headers["X-Versao-API"] = "2"
    response.set_cookie(key="tema", value="claro")
    return {"ok": True}
```

O FastAPI usa esse objeto temporário para copiar os cabeçalhos, os cookies e o código de status para a resposta final, enquanto o valor retornado continua sendo convertido normalmente.
