# Tarefas em segundo plano

Tarefas em segundo plano são funções executadas depois que a resposta já foi enviada ao cliente. Elas servem para trabalhos que o cliente não precisa esperar, como enviar um e-mail de confirmação ou gravar um registro de auditoria.

## Usando BackgroundTasks

Declare um parâmetro do tipo `BackgroundTasks` na função da rota e adicione tarefas com o método `add_task`:

```python
from fastapi import BackgroundTasks

def write_notification(email: str, message: str = ""):
    with open("log.txt", mode="a") as log:
        log.write(f"notificação para {email}: {message}\n")

@app.post("/send-notification/{email}")
async def send_notification(email: str, background_tasks: BackgroundTasks):
    background_tasks.add_task(write_notification, email, message="bem-vindo")
    return {"message": "Notificação enviada em segundo plano"}
```

O primeiro argumento de `add_task` é a função a executar. Os argumentos seguintes, posicionais ou nomeados, são repassados para ela. A função pode ser declarada com `def` comum ou com `async def`.

## Em dependências

Um parâmetro `BackgroundTasks` também pode ser declarado dentro de uma dependência. O FastAPI usa o mesmo objeto em toda a requisição, então as tarefas adicionadas na dependência e na rota são executadas juntas depois da resposta.

## Quando usar outra ferramenta

As tarefas em segundo plano rodam no mesmo processo da aplicação. Para cálculos pesados ou trabalhos que precisam sobreviver a uma reinicialização do servidor, prefira uma fila de tarefas dedicada, como o Celery com um broker como RabbitMQ ou Redis, que distribui o trabalho entre processos ou máquinas diferentes.
