#!/usr/bin/env bash
set -e

# Only one process should race to run migrations against the same
# database on startup. docker-compose has the `backend` service do it
# (SKIP_MIGRATIONS unset there); the `worker`/`beat` Celery services set
# SKIP_MIGRATIONS=true and simply wait for the schema to already be
# current rather than also calling `alembic upgrade head` concurrently.
if [ "${SKIP_MIGRATIONS:-false}" != "true" ]; then
    echo "Running database migrations..."
    alembic upgrade head
fi

if [ "$#" -eq 0 ]; then
    echo "Starting API server on port ${PORT:-8000}..."
    exec uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-8000}"
fi

# docker-compose overrides `command:` for the worker/beat services (Celery)
# — run whatever was passed instead of always starting the API server, so
# migrations still run once before either process starts (both need the
# schema to exist, and this keeps that logic in one place).
echo "Starting: $*"
exec "$@"
