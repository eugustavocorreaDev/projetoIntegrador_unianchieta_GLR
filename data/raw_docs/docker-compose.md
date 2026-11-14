# Docker Compose: vários serviços

O Docker Compose descreve, em um único arquivo YAML, todos os containers de uma aplicação, como a API e o banco de dados, com suas portas, variáveis, volumes e dependências. Com um comando, todos os serviços sobem juntos.

## Um arquivo compose típico

```yaml
services:
  api:
    build: .
    ports:
      - "8000:80"
    environment:
      BANCO_URL: postgresql://app:senha@db:5432/app
    depends_on:
      db:
        condition: service_healthy

  db:
    image: postgres:16
    environment:
      POSTGRES_USER: app
      POSTGRES_PASSWORD: senha
    volumes:
      - dados_db:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD", "pg_isready", "-U", "app"]
      interval: 5s
      retries: 10

volumes:
  dados_db:
```

Cada entrada em `services` vira um container. A chave `build` constrói a imagem a partir de um Dockerfile, e a chave `image` usa uma imagem pronta de um registro.

## Rede entre os serviços

O Compose cria uma rede padrão para a aplicação, e cada serviço pode alcançar os outros usando o nome do serviço como endereço. No exemplo, a API se conecta ao banco pelo host `db`, e não por `localhost`, porque `localhost` dentro de um container aponta para o próprio container.

## Ordem de inicialização

A chave `depends_on` define a ordem de inicialização. Na forma simples, ela só garante que o outro container foi iniciado, não que a aplicação dentro dele está pronta. Com `condition: service_healthy`, o Compose espera o `healthcheck` do serviço passar antes de iniciar o dependente. Com `condition: service_completed_successfully`, espera um serviço terminar com sucesso, o que é útil para tarefas de preparação, como migrações de banco de dados.

## Volumes

- **Volume nomeado**, como `dados_db:/var/lib/postgresql/data`: o Docker gerencia o armazenamento, e os dados sobrevivem quando o container é recriado.
- **Montagem de pasta**, como `./data:/app/data:ro`: liga uma pasta do computador hospedeiro ao container. O sufixo `:ro` monta a pasta só para leitura.

## Variáveis de ambiente

As variáveis podem ser definidas em `environment` ou carregadas de um arquivo com `env_file`. O Compose também lê automaticamente um arquivo `.env` na pasta do projeto para substituir expressões como `${PORTA:-8000}` dentro do próprio arquivo compose, em que o valor após `:-` é o padrão usado quando a variável não existe.

## Comandos do dia a dia

| Comando | Efeito |
| --- | --- |
| `docker compose up --build` | Constrói as imagens e sobe todos os serviços |
| `docker compose up -d` | Sobe em segundo plano |
| `docker compose logs -f api` | Acompanha os logs do serviço `api` |
| `docker compose ps` | Lista os serviços e seus estados |
| `docker compose exec api sh` | Abre um terminal dentro do container em execução |
| `docker compose run --rm api pytest` | Executa um comando avulso em um container novo e o remove ao final |
| `docker compose down` | Para e remove os containers e a rede |
| `docker compose down -v` | Faz o mesmo e também apaga os volumes nomeados |

## Política de reinício

A chave `restart` define o que fazer quando um container para: `no` (padrão) não reinicia, `always` sempre reinicia, `on-failure` reinicia só em caso de erro e `unless-stopped` reinicia sempre, exceto quando o container foi parado manualmente.
