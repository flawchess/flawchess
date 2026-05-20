---
status: partial
phase: 90-import-pipeline-memory-leak-fix-resilience
source: [90-VERIFICATION.md]
started: 2026-05-20T16:30:00Z
updated: 2026-05-20T16:30:00Z
---

## Current Test

[awaiting human testing]

## Tests

### 1. RSS-flat import behavior (primary leak prevention goal)
expected: RSS stays within +/-15% of baseline across the full import; does not climb linearly with batch count (pre-fix behavior was ~0.48 MB/game growth)
how: Start `bin/run_local.sh`, import a real ~5k+ game chess.com or lichess account. Sample RSS every 5s with `ps -o rss= -p $(pgrep -f uvicorn)` or `docker stats flawchess-dev-backend`. A flat or gently oscillating profile across the full import constitutes passing.
result: [pending]

### 2. Reaper fires after a Postgres-only restart (backend stays up)
expected: A stranded in_progress job transitions to 'failed' within 5 minutes of the next reaper tick; the reaper does NOT kill a <3h-old job in normal operation.
how: Start an import; pause backend; restart Postgres only (`docker compose -f docker-compose.dev.yml restart db`); resume backend. Watch logs for reaper tick + observe the orphaned job transition to `failed` in the DB.
result: [pending]

### 3. Production Sentry FLAWCHESS-56 / FLAWCHESS-3Q do not recur
expected: After deploy to production, no recurrence of the OOM-kill / Postgres-recovery error signatures from the 2026-05-16 incident over a 48h monitoring window.
how: Deploy via `bin/deploy.sh`. Monitor Sentry issues FLAWCHESS-56 and FLAWCHESS-3Q for 48h. If quiet, mark passed; if recurrence, gap-close.
result: [pending]

## Summary

total: 3
passed: 0
issues: 0
pending: 3
skipped: 0
blocked: 0

## Gaps
