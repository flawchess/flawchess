#!/usr/bin/env bash
set -euo pipefail

# Open an SSH tunnel to the production PostgreSQL database.
# Forwards local port 15432 to the remote DB on port 5432.
# Usage: bin/prod_db_tunnel.sh        (start tunnel)
#        bin/prod_db_tunnel.sh stop    (stop tunnel)

LOCAL_PORT=15432
REMOTE_HOST=127.0.0.1
REMOTE_PORT=5432
SSH_HOST=flawchess

if [ "${1:-}" = "stop" ]; then
  if pids=$(lsof -ti :$LOCAL_PORT 2>/dev/null); then
    echo "$pids" | xargs kill 2>/dev/null
    echo "Tunnel stopped."
  else
    echo "No tunnel running on port $LOCAL_PORT."
  fi
  exit 0
fi

# Check if tunnel is already running
if lsof -ti :$LOCAL_PORT &>/dev/null; then
  echo "Tunnel already running on port $LOCAL_PORT."
  exit 0
fi

echo "Opening SSH tunnel to production DB..."
ssh -fN -L $LOCAL_PORT:$REMOTE_HOST:$REMOTE_PORT $SSH_HOST

echo "Tunnel open: localhost:$LOCAL_PORT -> production DB"
echo "Stop with: bin/prod_db_tunnel.sh stop"
