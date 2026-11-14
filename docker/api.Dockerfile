# Imagem da API (também usada pelo serviço "ingest" e para rodar eval/)
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PYTHONPATH=/app/src:/app

WORKDIR /app

# Instala as dependências antes de copiar o código, para aproveitar o cache de camadas
COPY pyproject.toml ./
RUN python -c "import tomllib; print('\n'.join(tomllib.load(open('pyproject.toml','rb'))['project']['dependencies']))" > /tmp/requirements.txt \
    && pip install -r /tmp/requirements.txt

COPY src ./src
COPY data ./data
COPY eval ./eval
COPY scripts ./scripts

# Usuário sem privilégios
RUN useradd --create-home --uid 1000 app \
    && mkdir -p logs .cache eval/results \
    && chown -R app:app /app
USER app

EXPOSE 8000
HEALTHCHECK --interval=15s --timeout=5s --start-period=20s --retries=5 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health', timeout=4)"

# --no-access-log: o access log do uvicorn grava o IP do cliente (LGPD); o pipeline já
# registra cada pergunta em JSON, com a pergunta truncada
CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000", "--no-access-log"]
