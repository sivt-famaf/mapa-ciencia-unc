FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# System deps for scientific stack
RUN apt-get update && \
    apt-get install -y --no-install-recommends build-essential && \
    rm -rf /var/lib/apt/lists/*

COPY pyproject.toml README.md /app/
COPY mapa_ciencia_unc /app/mapa_ciencia_unc

RUN pip install --upgrade pip && pip install .

COPY . /app

EXPOSE 8000

CMD ["uvicorn", "mapa_ciencia_unc.main:app", "--host", "0.0.0.0", "--port", "8000"]
