#!/bin/bash
set -e

echo "Running Alembic migrations..."
alembic upgrade head

echo "Starting API server (APP_ENV=${APP_ENV:-development})..."
if [ "${APP_ENV}" = "production" ]; then
    exec gunicorn app.main:app \
        --workers 4 \
        --worker-class uvicorn.workers.UvicornWorker \
        --bind 0.0.0.0:8000 \
        --timeout 120 \
        --access-logfile - \
        --error-logfile -
else
    exec uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
fi
