#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

# Kill existing backend/frontend processes if running
pkill -f "uvicorn app.main:app" 2>/dev/null || true
pkill -f "vite" 2>/dev/null || true
sleep 1

# Ensure dev database is running
echo "Starting dev database..."
docker compose -f docker-compose.dev.yml -p flawchess-dev up -d
until docker compose -f docker-compose.dev.yml -p flawchess-dev exec db pg_isready -U postgres -q 2>/dev/null; do
  sleep 1
done

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
[ ! -d node_modules ] && npm install
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
