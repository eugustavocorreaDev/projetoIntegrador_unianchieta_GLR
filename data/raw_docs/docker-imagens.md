# Docker: construindo imagens

Uma imagem Docker é um pacote imutável com o sistema de arquivos, as dependências e o comando necessários para executar uma aplicação. Ela é descrita em um arquivo `Dockerfile` e construída com `docker build`. Um container é uma instância em execução de uma imagem.

## Instruções principais do Dockerfile

| Instrução | Função |
| --- | --- |
| `FROM` | Define a imagem base, como `python:3.11-slim` |
| `WORKDIR` | Define o diretório de trabalho das instruções seguintes |
| `COPY` | Copia arquivos do contexto de construção para a imagem |
| `RUN` | Executa um comando durante a construção, como instalar pacotes |
| `ENV` | Define variáveis de ambiente da imagem |
| `EXPOSE` | Documenta a porta em que a aplicação escuta |
| `USER` | Define o usuário que executa os comandos seguintes e o container |
| `CMD` | Define o comando padrão ao iniciar o container |

A instrução `EXPOSE` apenas documenta a porta: ela não publica a porta no computador hospedeiro. Para acessar o container, a porta precisa ser publicada ao executá-lo, com `docker run -p 8000:80`, em que o primeiro número é a porta do hospedeiro e o segundo, a do container.

## Construindo e executando

```bash
# Constrói a imagem a partir do Dockerfile da pasta atual
docker build -t minha-api:1.0 .

# Executa em segundo plano, publicando a porta 8000
docker run -d --name api -p 8000:80 minha-api:1.0
```

O ponto final em `docker build` é o contexto de construção: a pasta cujos arquivos ficam disponíveis para as instruções `COPY`.

## O arquivo .dockerignore

O arquivo `.dockerignore` lista o que não deve ser enviado no contexto de construção, como `.git`, ambientes virtuais, caches e arquivos `.env`. Ele deixa a construção mais rápida e evita copiar segredos para dentro da imagem.

## CMD e ENTRYPOINT

O `CMD` define o comando padrão, que pode ser substituído por argumentos passados ao `docker run`. O `ENTRYPOINT` define um executável fixo, e os argumentos do `docker run` passam a ser acrescentados a ele. Uma combinação comum é usar o `ENTRYPOINT` para o programa e o `CMD` para os argumentos padrão.

## Imagens menores e mais seguras

- Prefira imagens `slim`, que têm só o essencial do sistema. Imagens `alpine` são ainda menores, mas usam outra biblioteca C, o que pode obrigar a compilar pacotes Python que normalmente chegariam prontos.
- Use `pip install --no-cache-dir` para não guardar o cache do pip dentro da imagem.
- Crie um usuário sem privilégios e ative-o com `USER`, para que a aplicação não rode como root dentro do container.

## Construção em múltiplos estágios

Um Dockerfile pode ter vários estágios, cada um iniciado por um `FROM`. O primeiro estágio instala ferramentas de compilação e gera os artefatos; o estágio final copia só o resultado com `COPY --from=<estágio>`:

```dockerfile
FROM python:3.11 AS construcao
WORKDIR /build
COPY requirements.txt .
RUN pip wheel --no-cache-dir -r requirements.txt -w /wheels

FROM python:3.11-slim
COPY --from=construcao /wheels /wheels
RUN pip install --no-cache-dir /wheels/*
```

Assim, compiladores e arquivos temporários ficam fora da imagem final, que fica menor e com menos pacotes que possam ter vulnerabilidades.

## Verificação de saúde

A instrução `HEALTHCHECK` define um comando que o Docker executa periodicamente para saber se a aplicação está respondendo. O container passa a ter o estado `healthy` ou `unhealthy`, que outras ferramentas, como o Docker Compose, podem usar para decidir a ordem de inicialização.
