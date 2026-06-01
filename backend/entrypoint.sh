#!/bin/sh
set -e

export PYTHONPATH=/app

echo "Running database migrations..."
python /app/scripts/bootstrap_migrations.py

PORT="${PORT:-8000}"
exec uvicorn app.main:app --host 0.0.0.0 --port "$PORT"
