# Implantação

Implantar uma aplicação significa deixá-la disponível para os usuários em um servidor. Esta seção resume os conceitos principais para rodar o FastAPI em produção.

## Docker

Uma forma comum de implantar é criar uma imagem Docker a partir de uma imagem oficial do Python:

```dockerfile
FROM python:3.11
WORKDIR /code
COPY ./requirements.txt /code/requirements.txt
RUN pip install --no-cache-dir -r /code/requirements.txt
COPY ./app /code/app
CMD ["fastapi", "run", "app/main.py", "--port", "80"]
```

Copiar o arquivo `requirements.txt` e instalar as dependências antes de copiar o código aproveita o cache de camadas do Docker. Assim, alterar só o código não reinstala todas as bibliotecas a cada construção da imagem.

Use a forma de lista (exec) no `CMD`, como no exemplo, para que o processo receba corretamente os sinais de encerramento do container.

## Proxy reverso e HTTPS

Em produção, o HTTPS normalmente fica a cargo de um proxy de terminação TLS, como Traefik ou Caddy, que recebe as conexões seguras e repassa as requisições para a aplicação. Quando a aplicação roda atrás desse proxy, adicione a opção `--proxy-headers` ao comando `fastapi run`, para que ela confie nos cabeçalhos encaminhados pelo proxy.

## Processos e workers

O comando `fastapi run` aceita a opção `--workers` para iniciar vários processos e usar mais núcleos da CPU, por exemplo `fastapi run --workers 4 main.py`.

Em um cluster com Kubernetes, o recomendado é rodar um único processo por container e deixar a replicação a cargo do próprio cluster, que cria mais containers conforme a demanda.

## Variáveis de ambiente

Configurações que mudam entre ambientes, como endereços de banco de dados e chaves secretas, devem ser lidas de variáveis de ambiente. A classe `BaseSettings`, do pacote `pydantic-settings`, lê essas variáveis e valida os tipos automaticamente.

## Rota de verificação de saúde

Orquestradores como o Docker Compose e o Kubernetes precisam saber se a aplicação está pronta. Uma rota simples, como `GET /health` devolvendo `{"status": "ok"}`, pode ser usada pela instrução `HEALTHCHECK` do Dockerfile ou pelas sondas do Kubernetes. Uma verificação mais completa também confere se os serviços de que a aplicação depende, como o banco de dados, estão respondendo.
