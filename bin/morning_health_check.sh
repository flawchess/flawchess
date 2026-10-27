#!/usr/bin/env bash
# Morning production health check: headless Claude runs bin/health_check.sh,
# applies whitelisted fixes via bin/health_fix.sh, logs a row in the
# "FlawChess Health" Claude Doc, and prints HEALTH_STATUS: OK|WARN|FAIL.
# Reports land in temp/health/ (gitignored); WARN/FAIL or a broken run pops a
# desktop notification. Runs from a systemd user timer on the owner's PC.
#
# Usage: bin/morning_health_check.sh            run the check now
#        bin/morning_health_check.sh install    install + enable the timer (05:00 Europe/Zurich)

set -uo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
REPORT_DIR="$ROOT/temp/health"
PROMPT_FILE="$ROOT/bin/morning_health_check.prompt.md"
MODEL="claude-sonnet-5-5"
CLAUDE_BIN="${CLAUDE_BIN:-$HOME/.local/bin/claude}"
TIMER_SCHEDULE="*-*-* 05:00 Europe/Zurich"
NETWORK_WAIT_S=300
UNIT="flawchess-health-check"

# Only these tools exist for the agent; everything else is denied (dontAsk).
ALLOWED_TOOLS=(
  "Bash(bin/health_check.sh)"
  "Bash(bin/health_fix.sh:*)"
  "Read"
  "ToolSearch"
  "mcp__plugin_sentry_sentry__search_issues"
  "mcp__plugin_sentry_sentry__search_errors"
  "mcp__plugin_sentry_sentry__get_sentry_resource"
  "mcp__plugin_sentry_sentry__find_organizations"
  "mcp__claude_ai_Claude_Docs__guide"
  "mcp__claude_ai_Claude_Docs__read"
  "mcp__claude_ai_Claude_Docs__update"
)

notify() {
  # The timer runs outside the desktop session's environment; point at its bus.
  DBUS_SESSION_BUS_ADDRESS="${DBUS_SESSION_BUS_ADDRESS:-unix:path=/run/user/$(id -u)/bus}" \
    notify-send --urgency="$1" --app-name="FlawChess" "$2" "$3" 2>/dev/null || true
}

install_timer() {
  local dir="$HOME/.config/systemd/user"
  mkdir -p "$dir"
  cat >"$dir/$UNIT.service" <<EOF
[Unit]
Description=FlawChess morning production health check

[Service]
Type=oneshot
WorkingDirectory=$ROOT
ExecStart=$ROOT/bin/morning_health_check.sh
TimeoutStartSec=30min
EOF
  cat >"$dir/$UNIT.timer" <<EOF
[Unit]
Description=FlawChess morning production health check (05:00 Zurich)

[Timer]
OnCalendar=$TIMER_SCHEDULE
# PC off or asleep at 05:00 -> run once as soon as it is back.
Persistent=true

[Install]
WantedBy=timers.target
EOF
  systemctl --user daemon-reload
  systemctl --user enable --now "$UNIT.timer"
  systemctl --user list-timers "$UNIT.timer" --no-pager
}

run_check() {
  mkdir -p "$REPORT_DIR"
  local today report status
  today=$(date +%F)
  report="$REPORT_DIR/$today.md"

  # After a boot or resume the network can lag; Persistent=true fires right away.
  local waited=0
  until curl -s -o /dev/null -m 5 https://github.com; do
    if [ "$waited" -ge "$NETWORK_WAIT_S" ]; then
      notify critical "FlawChess health check did not run" "No network after ${NETWORK_WAIT_S}s."
      exit 1
    fi
    sleep 10
    waited=$((waited + 10))
  done

  cd "$ROOT" || exit 1
  "$CLAUDE_BIN" -p "$(cat "$PROMPT_FILE")" \
    --model "$MODEL" \
    --permission-mode dontAsk \
    --allowedTools "${ALLOWED_TOOLS[@]}" \
    --no-session-persistence \
    >"$report" 2>&1
  local rc=$?

  status=$(grep -oE '^HEALTH_STATUS: (OK|WARN|FAIL)' "$report" | tail -1 | cut -d' ' -f2)
  case "$status" in
    OK) ;;
    WARN) notify normal "FlawChess health: WARN" "Details in the FlawChess Health doc and $report" ;;
    FAIL) notify critical "FlawChess health: FAIL" "Details in the FlawChess Health doc and $report" ;;
    *) notify critical "FlawChess health check broke" "claude exit $rc, no status line. See $report" ;;
  esac
  echo "status=${status:-none} claude_exit=$rc report=$report"
}

case "${1:-run}" in
  install) install_timer ;;
  run) run_check ;;
  *) echo "Usage: $0 [run|install]" >&2; exit 2 ;;
esac
