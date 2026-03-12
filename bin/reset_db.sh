#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

DB_NAME="chessalytics"

echo "Dropping database '$DB_NAME'..."
dropdb --if-exists "$DB_NAME"

echo "Creating database '$DB_NAME'..."
createdb "$DB_NAME"

echo "Running Alembic migrations..."
uv run alembic upgrade head

echo "Done. Database '$DB_NAME' has been reset."
