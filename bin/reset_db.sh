#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

PROJECT="flawchess-dev"
COMPOSE_FILE="docker-compose.dev.yml"

echo "Stopping and removing dev database (including data)..."
docker compose -f "$COMPOSE_FILE" -p "$PROJECT" down -v

echo "Starting fresh dev database..."
docker compose -f "$COMPOSE_FILE" -p "$PROJECT" up -d

echo "Waiting for database to be healthy..."
until docker compose -f "$COMPOSE_FILE" -p "$PROJECT" exec db pg_isready -U postgres -q 2>/dev/null; do
  sleep 1
done

echo "Running Alembic migrations..."
uv run alembic upgrade head

echo "Seeding openings table..."
uv run python -m scripts.seed_openings

echo "Done. Dev database has been reset."
