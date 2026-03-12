#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

DB_NAME="chessalytics"
DB_USER="postgres"

echo "Dropping database '$DB_NAME'..."
dropdb --if-exists -h localhost -U "$DB_USER" "$DB_NAME"

echo "Creating database '$DB_NAME'..."
createdb -h localhost -U "$DB_USER" "$DB_NAME"

echo "Running Alembic migrations..."
uv run alembic upgrade head

echo "Done. Database '$DB_NAME' has been reset."
