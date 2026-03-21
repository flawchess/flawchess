#!/bin/sh
set -e

echo "Running Alembic migrations..."
alembic upgrade head

echo "Starting Uvicorn..."
# --proxy-headers: trust X-Forwarded-Proto/Host from Caddy reverse proxy
# --forwarded-allow-ips='*': accept forwarded headers from any Docker network IP
exec uvicorn app.main:app --host 0.0.0.0 --port 8000 --proxy-headers --forwarded-allow-ips='*'
