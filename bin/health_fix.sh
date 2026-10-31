#!/usr/bin/env bash
# The only production fixes the unattended morning health check may apply
# (bin/morning_health_check.sh allows this script and nothing else that
# writes). Each action checks its own precondition and refuses otherwise, so
# a confused agent cannot turn it into a general remote shell.
#
# Usage: bin/health_fix.sh up
#        bin/health_fix.sh restart backend|caddy|umami
#        bin/health_fix.sh prune-builder
#        bin/health_fix.sh dpkg-configure

set -euo pipefail

SSH_HOST="flawchess"
RESTARTABLE="backend caddy umami"   # never db: a Postgres restart is the owner's call
PRUNE_MIN_DISK_PCT=85
PRUNE_KEEP_CACHE="1gb"

remote() { ssh -T -o ConnectTimeout=10 "$SSH_HOST" "$@"; }
log() { echo "[$(date -u +%H:%M:%SZ)] $*"; }

action="${1:-}"
case "$action" in
  up)
    # Starts stopped/missing services from images already on the server; no build, no pull.
    log "docker compose up -d --no-build"
    remote 'cd /opt/flawchess && docker compose up -d --no-build && docker compose ps -a --format "{{.Service}}\t{{.State}}\t{{.Status}}"'
    ;;
  restart)
    svc="${2:-}"
    if ! grep -qw -- "$svc" <<<"$RESTARTABLE" || [ -z "$svc" ]; then
      echo "REFUSED: restart only accepts one of: $RESTARTABLE" >&2
      exit 2
    fi
    log "docker compose restart $svc"
    remote "cd /opt/flawchess && docker compose restart $svc && docker compose ps -a --format '{{.Service}}\t{{.State}}\t{{.Status}}'"
    ;;
  prune-builder)
    pct=$(remote "df --output=pcent / | tail -1 | tr -dc 0-9")
    if [ "$pct" -lt "$PRUNE_MIN_DISK_PCT" ]; then
      echo "REFUSED: disk is ${pct}% full, prune only runs at >= ${PRUNE_MIN_DISK_PCT}%" >&2
      exit 2
    fi
    log "disk ${pct}%: pruning build cache (keep ${PRUNE_KEEP_CACHE}) and dangling images"
    remote "docker builder prune -f --reserved-space=$PRUNE_KEEP_CACHE >/dev/null && docker image prune -f && df -h / | tail -1"
    ;;
  dpkg-configure)
    audit=$(remote "sudo dpkg --audit 2>&1")
    if [ -z "$audit" ]; then
      echo "REFUSED: dpkg --audit reports nothing to finish" >&2
      exit 2
    fi
    log "finishing interrupted package configuration"
    remote "sudo dpkg --configure -a && sudo dpkg --audit && echo 'dpkg clean'"
    ;;
  *)
    echo "Usage: $0 up | restart backend|caddy|umami | prune-builder | dpkg-configure" >&2
    exit 2
    ;;
esac
