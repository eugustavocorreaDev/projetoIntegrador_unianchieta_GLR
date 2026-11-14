# Imagem da interface Streamlit (só precisa de streamlit + httpx)
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

COPY pyproject.toml ./
RUN python -c "import tomllib; print('\n'.join(tomllib.load(open('pyproject.toml','rb'))['project']['optional-dependencies']['ui']))" > /tmp/requirements.txt \
    && pip install -r /tmp/requirements.txt

COPY .streamlit ./.streamlit
COPY src/ui ./src/ui

RUN useradd --create-home --uid 1000 app && chown -R app:app /app
USER app

EXPOSE 8501
CMD ["streamlit", "run", "src/ui/app.py", "--server.address=0.0.0.0", "--server.port=8501", "--browser.gatherUsageStats=false"]
