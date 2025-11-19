FROM python:3.12-slim AS runtime

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    DJANGO_SETTINGS_MODULE=config.settings.production \
    PYTHONPATH=/app \
    PORT=8000 \
    WORKERS=4 \
    THREADS=2 \
    GUNICORN_TIMEOUT=60

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements/ /tmp/requirements/

RUN pip install --upgrade pip \
    && pip install --no-cache-dir -r /tmp/requirements/production.txt

COPY . /app

RUN useradd --create-home appuser \
    && chown -R appuser:appuser /app

USER appuser

EXPOSE 8000

CMD ["sh", "-c", "gunicorn config.wsgi:application --bind 0.0.0.0:${PORT:-8000} --workers ${WORKERS} --threads ${THREADS} --timeout ${GUNICORN_TIMEOUT} --log-file -"]

