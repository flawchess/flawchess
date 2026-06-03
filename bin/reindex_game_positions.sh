#!/usr/bin/env bash
set -euo pipefail

# =============================================================================
# reindex_game_positions.sh — PROD-ONLY, HUMAN-run index-bloat reclaim (SEED-035)
# =============================================================================
#
# MANUAL ops step. NEVER run by automation, CI, the GSD executor, or
# deploy/entrypoint.sh. A human with a privileged DB role runs it at deploy time.
#
# WHY THIS IS AN OPS SCRIPT, NOT AN ALEMBIC MIGRATION:
#   REINDEX is a maintenance operation, not a schema change. Alembic migrations
#   run automatically on every backend container start (deploy/entrypoint.sh) and
#   against the dev/test DB on every test run, where a REINDEX would be pure
#   wasted work (those tables are tiny and carry no bloat). Keeping this as a
#   standalone bin/ script, alongside the other prod-ops scripts
#   (prod_db_tunnel.sh, benchmark_db.sh, deploy.sh), matches the repo convention
#   and keeps it firmly human-gated.
#
# SCOPE — exactly TWO indexes (and the reasoning):
#   SEED-035's "Separate, lower-risk quick win" listed four bloated indexes, but
#   the SEED-035 migration (f4d88c3659c6) drops or rebuilds two of them, so they
#   need NO reindex:
#     - game_positions_pkey   -> re-created fresh by the migration's CONCURRENTLY
#                                unique-index build => not bloated => EXCLUDED.
#     - ix_gp_user_game_ply   -> dropped entirely by the migration => EXCLUDED.
#   The two the migration leaves UNTOUCHED, and that therefore still carry the
#   bloat accrued since the 2026-05-31 hash-only reindex, are:
#     - ix_gp_user_endgame_game   (~622 MB, never touched by the migration)
#     - ix_game_positions_game_id (~452 MB, explicitly KEPT-not-rebuilt; backs the
#                                  ON DELETE CASCADE FK)
#   This script reindexes precisely these two and nothing else.
#
# EXPECTED RECLAIM:
#   Combined with the migration's PK shrink (~1.45 GB), this reindex pass should
#   reclaim on the order of ~1 GB more from the game_positions index set.
#
# REQUIREMENTS:
#   1. The prod SSH tunnel must already be open:
#        bin/prod_db_tunnel.sh        (forwards localhost:15432 -> prod DB 5432)
#      This script checks the tunnel is up and tells you to start it if not.
#   2. A DB role with MAINTENANCE privileges on game_positions (table owner /
#      admin). The READ-ONLY MCP prod user / read-only role CANNOT run REINDEX —
#      it will fail with "must be owner". Supply a privileged connection via the
#      environment (see below). NO password is hard-coded or committed here.
#
# CONNECTION (no committed secrets — follows the project's placeholder convention):
#   Provide ONE of:
#     - REINDEX_DB_URL  : a full libpq URL for a privileged role, e.g.
#                         postgresql://flawchess:<PASSWORD>@localhost:15432/flawchess
#     - PGUSER + PGPASSWORD (+ optional PGDATABASE), used against localhost:15432.
#   Never paste the password on the command line in a way that lands in shell
#   history; prefer exporting it for the single invocation.
#
# ONLINE / NON-BLOCKING:
#   REINDEX INDEX CONCURRENTLY runs ONLINE — no table lock-out, no maintenance
#   window needed. It rebuilds one index at a time. It is still a real prod
#   maintenance op (extra I/O + a transient duplicate index), so it is gated
#   behind an explicit confirmation prompt.
#
# TRANSACTION CONSTRAINT:
#   REINDEX ... CONCURRENTLY CANNOT run inside a transaction block. Each REINDEX
#   is issued as its own top-level psql statement (psql is autocommit by default
#   for top-level statements). Do NOT wrap in BEGIN/COMMIT and do NOT pass
#   -1 / --single-transaction.
#
# SEQUENCING:
#   This pass is INDEPENDENT of the migration and may run any time. Prefer running
#   it POST-deploy: right after the SEED-035 migration ships, only these two
#   indexes remain bloated (the PK and ix_gp_user_game_ply are already handled),
#   which is exactly the set this script targets. If run BEFORE the migration it
#   would still reindex these two correctly, just leave the soon-to-be-dropped
#   indexes alone — harmless but wasteful.
#
# USAGE:
#   bin/reindex_game_positions.sh [--dry-run] [--verify]
#     (default mode, no flag) : prompt for confirmation, then REINDEX both indexes
#     --dry-run               : PRINT the exact psql commands without connecting
#                               or executing anything (the verifiable, DB-free path)
#     --verify                : run READ-ONLY pg_relation_size() queries for both
#                               indexes (before/after size comparison)
# =============================================================================

LOCAL_PORT=15432
DB_HOST=localhost

# The two (and only two) indexes this script reindexes. See SCOPE above.
INDEXES=(
  "ix_gp_user_endgame_game"
  "ix_game_positions_game_id"
)

mode="run"
case "${1:-}" in
  --dry-run) mode="dry-run" ;;
  --verify) mode="verify" ;;
  "") mode="run" ;;
  *)
    echo "Usage: $0 [--dry-run | --verify]" >&2
    exit 1
    ;;
esac

# Build the psql base command from the privileged connection the operator supplies.
# Kept as an array so the dry-run path can print it without executing.
psql_base() {
  if [ -n "${REINDEX_DB_URL:-}" ]; then
    printf 'psql %q' "$REINDEX_DB_URL"
  else
    printf 'psql -h %q -p %q' "$DB_HOST" "$LOCAL_PORT"
  fi
}

# --- Dry-run: print exactly what would run, touch no DB ----------------------
if [ "$mode" = "dry-run" ]; then
  echo "--dry-run: the following commands WOULD run (no DB connection made):"
  echo
  for idx in "${INDEXES[@]}"; do
    echo "  $(psql_base) -c \"REINDEX INDEX CONCURRENTLY ${idx};\""
  done
  echo
  echo "Run without --dry-run to execute (requires the prod tunnel + a privileged role)."
  exit 0
fi

# --- Connection / tunnel preconditions (run + verify modes) ------------------
if ! lsof -ti :"$LOCAL_PORT" &>/dev/null; then
  echo "ERROR: no prod tunnel detected on localhost:${LOCAL_PORT}." >&2
  echo "Start it first:  bin/prod_db_tunnel.sh" >&2
  exit 1
fi

if [ -z "${REINDEX_DB_URL:-}" ] && [ -z "${PGUSER:-}" ]; then
  echo "ERROR: no privileged connection provided." >&2
  echo "Set REINDEX_DB_URL (privileged libpq URL) or PGUSER + PGPASSWORD." >&2
  echo "The read-only prod role CANNOT run REINDEX — use the table owner/admin." >&2
  exit 1
fi

# Assemble the psql invocation as an array so each REINDEX is its own top-level
# (autocommit) statement — REINDEX ... CONCURRENTLY cannot run in a transaction.
PSQL=(psql)
if [ -n "${REINDEX_DB_URL:-}" ]; then
  PSQL+=("$REINDEX_DB_URL")
else
  PSQL+=(-h "$DB_HOST" -p "$LOCAL_PORT")
fi

index_size_sql() {
  # Read-only size lookup; pg_relation_size needs only SELECT-level access.
  local idx="$1"
  echo "SELECT '${idx}' AS index, pg_size_pretty(pg_relation_size('${idx}'::regclass)) AS size;"
}

# --- Verify: read-only size report, no rebuild -------------------------------
if [ "$mode" = "verify" ]; then
  echo "Index sizes for game_positions (prod, via tunnel localhost:${LOCAL_PORT}):"
  for idx in "${INDEXES[@]}"; do
    "${PSQL[@]}" -X -A -t -c "$(index_size_sql "$idx")"
  done
  echo
  echo "Compare these before vs after a reindex run to confirm the reclaim."
  echo "You can also cross-check against the db-report skill (reports/db-stats/)."
  exit 0
fi

# --- Run mode: confirm, then REINDEX each index one at a time ----------------
cat <<BANNER
=============================================================================
 PROD MAINTENANCE: REINDEX game_positions indexes
   Target : production DB via SSH tunnel (localhost:${LOCAL_PORT})
   Indexes: ${INDEXES[*]}
   Mode   : REINDEX INDEX CONCURRENTLY (ONLINE, non-blocking, one at a time)
 This is online and does NOT lock the table, but it is still a real prod
 maintenance op (extra I/O + a transient duplicate index per rebuild).
=============================================================================
BANNER

read -r -p "Type REINDEX to proceed (anything else aborts): " confirm
if [ "$confirm" != "REINDEX" ]; then
  echo "Aborted — no changes made."
  exit 1
fi

for idx in "${INDEXES[@]}"; do
  echo
  echo ">>> Reindexing ${idx} (CONCURRENTLY)..."
  # Each statement is its own top-level (autocommit) psql -c invocation: REINDEX
  # ... CONCURRENTLY cannot run inside a transaction block, so do NOT batch these.
  "${PSQL[@]}" -X -v ON_ERROR_STOP=1 -c "REINDEX INDEX CONCURRENTLY ${idx};"
  echo ">>> Done: ${idx}"
done

echo
echo "All reindexes complete. Verify the reclaim with:"
echo "  bin/reindex_game_positions.sh --verify"
echo "Expected: combined with the SEED-035 PK shrink (~1.45 GB), the"
echo "game_positions index set reclaims on the order of ~1 GB from this pass."
