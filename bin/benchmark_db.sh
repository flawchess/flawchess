#!/usr/bin/env bash
# Lifecycle script for the isolated flawchess-benchmark PostgreSQL instance (Phase 69 INFRA-01).
# Usage:
#   bin/benchmark_db.sh start   — bring container up, wait for health, run Alembic migrations
#   bin/benchmark_db.sh stop    — bring container down, preserve data volume
#   bin/benchmark_db.sh reset   — destroy data volume, recreate, re-migrate
set -euo pipefail

cd "$(dirname "$0")/.."

PROJECT="flawchess-benchmark"
COMPOSE_FILE="docker-compose.benchmark.yml"
BENCHMARK_DB_URL="postgresql+asyncpg://flawchess_benchmark:flawchess_benchmark@localhost:5433/flawchess_benchmark"

wait_healthy() {
  echo "Waiting for benchmark database to be healthy..."
  until docker compose -f "$COMPOSE_FILE" -p "$PROJECT" exec db pg_isready -U postgres -q 2>/dev/null; do
    sleep 1
  done
}

run_migrations() {
  echo "Running Alembic migrations against benchmark DB on port 5433..."
  DATABASE_URL="$BENCHMARK_DB_URL" uv run alembic upgrade head
}

case "${1:-start}" in
  start)
    echo "Starting benchmark database (project=$PROJECT, port=5433)..."
    docker compose -f "$COMPOSE_FILE" -p "$PROJECT" up -d
    wait_healthy
    run_migrations
    echo "Done. Benchmark database is ready on localhost:5433."
    ;;
  stop)
    echo "Stopping benchmark database (data volume preserved)..."
    docker compose -f "$COMPOSE_FILE" -p "$PROJECT" down
    ;;
  reset)
    echo "Resetting benchmark database (ALL DATA WILL BE LOST)..."
    docker compose -f "$COMPOSE_FILE" -p "$PROJECT" down -v
    docker compose -f "$COMPOSE_FILE" -p "$PROJECT" up -d
    wait_healthy
    run_migrations
    echo "Done. Benchmark database reset."
    ;;
  *)
    echo "Usage: $0 [start|stop|reset]"
    exit 1
    ;;
esac
