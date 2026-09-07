#!/bin/sh
set -e

if [ "$POSTGRES_DB" ]; then
    echo "==> Waiting for PostgreSQL at ${POSTGRES_HOST:-db}:${POSTGRES_PORT:-5432}..."
    while ! nc -z "${POSTGRES_HOST:-db}" "${POSTGRES_PORT:-5432}"; do
      sleep 0.5
    done
    echo "==> PostgreSQL is ready!"
fi

echo "==> Running Django collectstatic..."
python manage.py collectstatic --noinput

echo "==> Running Django migrate..."
python manage.py migrate --noinput

echo "==> Starting Gunicorn server on 0.0.0.0:8000..."
exec gunicorn card_project.wsgi:application \
    --bind 0.0.0.0:8000 \
    --workers ${GUNICORN_WORKERS:-3} \
    --threads 2 \
    --timeout ${GUNICORN_TIMEOUT:-60} \
    --access-logfile - \
    --error-logfile -
