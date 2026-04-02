#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

# Kill existing backend/frontend processes if running.
# Use fuser to kill anything on the ports directly — pkill -f can miss
# orphaned uvicorn child processes (--reload spawns a watcher + worker).
pkill -f "uvicorn app.main:app" 2>/dev/null || true
pkill -f "vite" 2>/dev/null || true
fuser -k 8000/tcp 2>/dev/null || true
fuser -k 5173/tcp 2>/dev/null || true
sleep 1

# Fail fast if a local postgres process is already holding port 5432.
# Docker's port-forward shows up as "com.docke", not "postgres", so this
# correctly distinguishes a conflicting system Postgres from Docker itself.
if lsof -ti :5432 2>/dev/null | xargs -I{} ps -p {} -o comm= 2>/dev/null | grep -qi "postgres"; then
  echo "Error: a local PostgreSQL process is already listening on port 5432."
  echo "Stop your local PostgreSQL service before running this script."
  exit 1
fi

# Ensure dev database is running
echo "Starting dev database..."
docker compose -f docker-compose.dev.yml -p flawchess-dev up -d
until docker compose -f docker-compose.dev.yml -p flawchess-dev exec db pg_isready -U postgres -q 2>/dev/null; do
  sleep 1
done

# Install backend dependencies
echo "Installing backend dependencies..."
uv sync

# Run database migrations
echo "Running migrations..."
uv run alembic upgrade head

# Start backend
echo "Starting backend..."
uv run uvicorn app.main:app --reload --port 8000 &
BACKEND_PID=$!

# Start frontend
echo "Starting frontend..."
cd frontend
npm install
npm run dev:mobile &
FRONTEND_PID=$!
cd ..

echo ""
echo "Backend:  http://localhost:8000"
echo "Frontend: http://localhost:5173"
echo ""
echo "PIDs: backend=$BACKEND_PID frontend=$FRONTEND_PID"
echo "Press Ctrl+C to stop both."

trap "kill $BACKEND_PID $FRONTEND_PID 2>/dev/null; exit" INT TERM
wait
