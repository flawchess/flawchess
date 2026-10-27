#!/usr/bin/env bash
# Read-only production health snapshot for the morning health check
# (bin/morning_health_check.sh). Prints labelled sections; never changes
# anything on the server. Each probe is independent: one failing probe
# prints its error and the rest still run (no `set -e` on purpose).
#
# Usage: bin/health_check.sh

set -uo pipefail

SITE="https://flawchess.com"
ANALYTICS="https://analytics.flawchess.com"
SSH_HOST="flawchess"
REPO="flawchess/flawchess"
SECURITY_HEADERS="strict-transport-security x-content-type-options referrer-policy permissions-policy content-security-policy-report-only"
CURL_TIMEOUT_S=15
LONG_QUERY_MIN=5
STUCK_IMPORT_HOURS=2

cd "$(dirname "$0")/.."

section() { printf '\n## %s\n' "$1"; }

section "Check time"
date -u +"%Y-%m-%dT%H:%M:%SZ (UTC)"

section "Public endpoints"
for url in "$SITE/" "$SITE/api/health" "$ANALYTICS/script.js"; do
  printf '%s -> %s\n' "$url" \
    "$(curl -s -o /dev/null -m "$CURL_TIMEOUT_S" -w 'HTTP %{http_code}, %{time_total}s' "$url" || echo 'curl failed')"
done
printf 'health body: %s\n' "$(curl -s -m "$CURL_TIMEOUT_S" "$SITE/api/health" | head -c 300)"

section "Security headers"
headers=$(curl -sI -m "$CURL_TIMEOUT_S" "$SITE/" | tr 'A-Z' 'a-z')
for h in $SECURITY_HEADERS; do
  if grep -q "^$h:" <<<"$headers"; then echo "PASS $h"; else echo "MISSING $h"; fi
done

section "TLS certificates (days left)"
origin_ip=$(ssh -G "$SSH_HOST" 2>/dev/null | awk '/^hostname /{print $2}')
for target in "edge:flawchess.com" "origin:$origin_ip"; do
  label=${target%%:*}
  host=${target#*:}
  end=$(echo | timeout "$CURL_TIMEOUT_S" openssl s_client -servername flawchess.com -connect "$host:443" 2>/dev/null \
    | openssl x509 -noout -enddate 2>/dev/null | cut -d= -f2)
  if [ -n "$end" ]; then
    echo "$label ($host): expires $end, $(( ($(date -d "$end" +%s) - $(date +%s)) / 86400 )) days left"
  else
    echo "$label ($host): could not read certificate"
  fi
done

section "Deployed commit"
expected=$(git ls-remote origin refs/heads/production 2>/dev/null | cut -c1-12)
deployed=$(ssh -T -o ConnectTimeout=10 "$SSH_HOST" 'git -C /opt/flawchess rev-parse HEAD' 2>&1 | cut -c1-12)
echo "origin/production: $expected"
echo "server HEAD:       $deployed"

section "GitHub"
echo "Latest CI runs on main:"
gh run list -R "$REPO" --workflow=ci.yml --branch main --limit 3 \
  --json conclusion,status,event,createdAt,headSha \
  --jq '.[] | "  \(.createdAt) \(.event) \(.headSha[:9]) \(.status) \(.conclusion)"' 2>&1
echo "Open Renovate PRs:"
gh pr list -R "$REPO" --author "app/renovate" --state open \
  --json number,title,createdAt,autoMergeRequest,statusCheckRollup \
  --jq '.[] | "  #\(.number) opened \(.createdAt[:10]) automerge=\(.autoMergeRequest != null) checks=\([.statusCheckRollup[]? | .conclusion // .status] | unique | join(",")) | \(.title)"' 2>&1

section "Server (via ssh)"
# Everything below runs on the server and only reads. sudo is needed for the
# unattended-upgrades log, the kernel journal and dpkg --audit.
ssh -T -o ConnectTimeout=10 "$SSH_HOST" \
  "LONG_QUERY_MIN=$LONG_QUERY_MIN STUCK_IMPORT_HOURS=$STUCK_IMPORT_HOURS bash -s" <<'REMOTE'
set -uo pipefail
cd /opt/flawchess
sub() { printf '\n### %s\n' "$1"; }

sub "Boot and load"
echo "booted: $(uptime -s) UTC ($(uptime -p))"
uptime | sed 's/.*load average/load average/'
if [ -f /var/run/reboot-required ]; then
  echo "REBOOT REQUIRED since $(stat -c %y /var/run/reboot-required | cut -d. -f1) for: $(sort -u /var/run/reboot-required.pkgs 2>/dev/null | tr '\n' ' ')"
else
  echo "no reboot pending"
fi

sub "Unattended upgrades (last 2 days)"
log=/var/log/unattended-upgrades/unattended-upgrades.log
sudo grep -E "^($(date -u +%F)|$(date -u -d yesterday +%F))" "$log" \
  | grep -E " (INFO|WARNING|ERROR|CRITICAL) " \
  | grep -vE "Initial (blacklist|whitelist)|Allowed origins|dry-run|Starting unattended" | tail -15
echo "dpkg --audit: $(sudo dpkg --audit 2>&1 | head -5 | tr '\n' ' ')"
echo "pending upgradable packages: $(apt list --upgradable 2>/dev/null | tail -n +2 | wc -l)"

sub "systemd failed units"
systemctl --failed --no-legend --plain || true

sub "Disk, memory"
df -h / | tail -1
free -m | sed -n '1,3p'

sub "Kernel OOM kills (24h)"
sudo journalctl -k --since "-24h" --no-pager 2>/dev/null | grep -iE "out of memory|oom-kill|killed process" | tail -5 || true
echo "(end)"

sub "Containers"
docker compose ps -a --format '{{.Service}}\t{{.State}}\t{{.Status}}'
for c in $(docker compose ps -aq); do
  docker inspect --format '{{.Name}} restarts={{.RestartCount}} oom_killed={{.State.OOMKilled}} started={{.State.StartedAt}}' "$c"
done
echo "docker live-restore: $(docker info --format '{{.LiveRestoreEnabled}}')"

sub "Backend log warnings/errors (docker keeps only ~1h; Sentry is the source of truth)"
docker compose logs --since 24h --no-color backend 2>&1 | grep -E "WARNING|ERROR|CRITICAL|Traceback" | tail -10
echo "(end)"

sub "Database (read-only)"
docker compose exec -T db sh -c 'PGOPTIONS="-c default_transaction_read_only=on" psql -X -q -U "$POSTGRES_USER" -d "$POSTGRES_DB" -A -F " | " -P footer=off' <<SQL
\echo [size]
SELECT pg_size_pretty(pg_database_size(current_database()));
\echo [connections by state]
SELECT coalesce(state, 'background') AS state, count(*) FROM pg_stat_activity WHERE datname = current_database() GROUP BY 1 ORDER BY 2 DESC;
\echo [queries running > ${LONG_QUERY_MIN} min]
SELECT pid, date_trunc('second', now() - query_start) AS running, state, left(regexp_replace(query, '\s+', ' ', 'g'), 120)
FROM pg_stat_activity
WHERE backend_type = 'client backend' AND state <> 'idle' AND now() - query_start > interval '${LONG_QUERY_MIN} minutes';
\echo [imports stuck > ${STUCK_IMPORT_HOURS} h]
SELECT platform, status, count(*) FROM import_jobs
WHERE status IN ('pending', 'in_progress') AND started_at < now() - interval '${STUCK_IMPORT_HOURS} hours' GROUP BY 1, 2;
\echo [imports last 24h by status]
SELECT platform, status, count(*) FROM import_jobs WHERE started_at > now() - interval '24 hours' GROUP BY 1, 2 ORDER BY 1, 2;
\echo [failed import messages last 24h]
SELECT left(error_message, 150), count(*) FROM import_jobs
WHERE status = 'failed' AND started_at > now() - interval '24 hours' GROUP BY 1 ORDER BY 2 DESC LIMIT 5;
\echo [remote workers seen in the last 7 days]
SELECT worker_id, last_ip, date_trunc('minute', now() - last_seen) AS last_seen_ago FROM worker_heartbeats
WHERE last_seen > now() - interval '7 days' ORDER BY last_seen DESC;
SQL
REMOTE
echo "(ssh exit $?)"
