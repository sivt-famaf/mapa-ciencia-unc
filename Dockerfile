# Pinned by digest: tags move, digests do not. Rebuilds stay byte-identical.
FROM python:3.11-slim@sha256:9534e5a8e315485d4061ed659af0fd78a284c015f9b73661b41d6bab25604534

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    UV_PROJECT_ENVIRONMENT=/app/.venv \
    PATH=/app/.venv/bin:$PATH

WORKDIR /app

# System deps for scientific stack
RUN apt-get update && \
    apt-get install -y --no-install-recommends build-essential && \
    rm -rf /var/lib/apt/lists/*

RUN pip install --upgrade pip && pip install uv

COPY pyproject.toml uv.lock README.md /app/
COPY mapa_ciencia_unc /app/mapa_ciencia_unc

# --frozen: install exactly what uv.lock pins, never re-resolve
RUN uv sync --frozen --no-dev

COPY ./mapa_ciencia_unc /app

EXPOSE 8000

CMD ["uvicorn", "mapa_ciencia_unc.main:app", "--host", "0.0.0.0", "--port", "8000"]
