#!/bin/sh
set -e

export PYTHONPATH=/app

echo "Running database migrations..."
python /app/scripts/bootstrap_migrations.py

if [ -n "${SEED_USER_EMAIL:-}" ] && [ -n "${SEED_USER_PASSWORD:-}" ]; then
  echo "Seeding login user (if not already present)..."
  python /app/scripts/create_user.py \
    --name "${SEED_USER_NAME:-Demo User}" \
    --email "$SEED_USER_EMAIL" \
    --password "$SEED_USER_PASSWORD" \
    --skip-if-exists
fi

PORT="${PORT:-8000}"
exec uvicorn app.main:app --host 0.0.0.0 --port "$PORT"
