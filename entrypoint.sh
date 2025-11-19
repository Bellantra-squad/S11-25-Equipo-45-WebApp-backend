#!/usr/bin/env bash
set -euo pipefail

# Optional delay to give the database time to accept connections.
DB_WAIT_SECONDS="${DB_WAIT_SECONDS:-5}"
if [ "${DB_WAIT_SECONDS}" -gt 0 ]; then
  echo "Waiting for database for ${DB_WAIT_SECONDS}s..."
  sleep "${DB_WAIT_SECONDS}"
fi

if [ "${RUN_MIGRATIONS:-1}" = "1" ]; then
  echo "Applying database migrations..."
  python manage.py migrate --noinput
else
  echo "Skipping migrations because RUN_MIGRATIONS=${RUN_MIGRATIONS:-0}"
fi

if [ "${SKIP_COLLECTSTATIC:-0}" = "0" ]; then
  echo "Collecting static files..."
  python manage.py collectstatic --noinput
else
  echo "Skipping collectstatic because SKIP_COLLECTSTATIC=${SKIP_COLLECTSTATIC}"
fi

DEFAULT_CMD=(
  gunicorn config.asgi:application
  -k uvicorn.workers.UvicornWorker
  --bind "0.0.0.0:${PORT:-8000}"
  --workers "${WORKERS:-4}"
  --threads "${THREADS:-2}"
  --timeout "${GUNICORN_TIMEOUT:-60}"
  --log-file -
)

if [ "$#" -gt 0 ]; then
  echo "Starting application with custom command: $*"
  exec "$@"
else
  echo "Starting application with default command: ${DEFAULT_CMD[*]}"
  exec "${DEFAULT_CMD[@]}"
fi


