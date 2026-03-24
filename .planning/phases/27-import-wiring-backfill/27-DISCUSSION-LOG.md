# Phase 27: Import Wiring & Backfill - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-03-24
**Phase:** 27-import-wiring-backfill
**Areas discussed:** Backfill strategy, Production deployment, Error handling

---

## Backfill Strategy

### Position Replay Method

| Option | Description | Selected |
|--------|-------------|----------|
| Re-parse PGN | Re-parse stored PGN, replay moves through chess.Board, call classify_position at each ply. Mirrors hashes_for_game pattern. | ✓ |
| Board from FEN + hashes | Reconstruct board from stored data without PGN. Not feasible since game_positions only stores hashes. | |

**User's choice:** Re-parse PGN (after initial consideration of delete-and-reimport approach)
**Notes:** User initially suggested deleting all games and re-importing through the updated pipeline, noting this could combine with Phase 29's engine analysis import. After discussion of trade-offs (API rate limiting, backfill simplicity), agreed that backfill from stored PGN is the better approach since it's purely local.

### Resumability

| Option | Description | Selected |
|--------|-------------|----------|
| NULL game_phase query | Find games with NULL game_phase positions on each run. Self-healing. | ✓ |
| Last processed game_id | Track last completed game_id, resume from there. Requires manual tracking. | |
| Marker table | Dedicated backfill_progress table. Robust but overkill for one-time operation. | |

**User's choice:** NULL game_phase query (Recommended)

### Script Location

| Option | Description | Selected |
|--------|-------------|----------|
| scripts/ directory | Standalone script at scripts/backfill_positions.py | ✓ |
| App CLI command | Management command with click/typer | |

**User's choice:** scripts/ directory (Recommended)

---

## Production Deployment

### Downtime

| Option | Description | Selected |
|--------|-------------|----------|
| Live | Run while app serves traffic. Metadata columns not queried yet. | ✓ |
| Brief maintenance | Stop app, run backfill, restart. | |

**User's choice:** Live (Recommended)

### VACUUM Strategy

| Option | Description | Selected |
|--------|-------------|----------|
| Script runs VACUUM | Automated VACUUM ANALYZE after completion | ✓ |
| Manual VACUUM | Operator runs manually via psql | |
| Periodic auto-vacuum | Rely on PostgreSQL's autovacuum | |

**User's choice:** Script runs VACUUM (Recommended)

---

## Error Handling

### Per-Game Failures

| Option | Description | Selected |
|--------|-------------|----------|
| Skip and log | Log game_id and error, skip to next game, continue | |
| Halt the batch | Stop processing on first failure | |
| Skip, log, and collect | Skip and log plus write failures to file | |
| Skip and Sentry | Skip game, log via sentry_sdk.capture_exception() | ✓ |

**User's choice:** Sentry error logging (user-suggested alternative)
**Notes:** User suggested using Sentry for classification failures since it's already set up on the backend. Provides centralized tracking and alerting without halting the backfill.

### Reporting

| Option | Description | Selected |
|--------|-------------|----------|
| Stdout summary | Progress every N games, final summary to stdout | ✓ |
| Log file | Detailed log to scripts/backfill.log | |

**User's choice:** Stdout summary (Recommended)

---

## Claude's Discretion

- Import wiring approach (how to integrate classify_position into the import loop)
- Backfill UPDATE strategy (per-game vs batch)
- Progress reporting frequency
- Test structure and coverage

## Deferred Ideas

- Delete-and-reimport approach for combining backfill with Phase 29 engine analysis import — deferred to Phase 29 planning
