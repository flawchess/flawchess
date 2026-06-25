# Phase 127 — Prod Re-Backfill Runbook (DEFERRED)

**Status:** DEFERRED — executed OUTSIDE the phase 127 gate (D-13, mirroring Phase 125 D-01).
This runbook documents the prod procedure; it is **not** run during the phase.

## What this does

Re-runs the hardened tactic detector (Phase 127-01) over prod's existing tagged
`game_flaws` so that:

- `tactic_depth` is populated (non-NULL) on re-backfilled tagged rows (currently NULL in prod).
- Fork false positives drop (the D-01 relevance gate prunes incidental / deep-scan hits).
- The min-depth dispatcher re-resolves which motif wins per position.

The dev re-backfill (Plan 127-04, Task 1) already proved this against real data: on dev,
`tactic_depth` went 0 → 32,518 tagged rows, fork dropped −7.6% (10,083 → 9,314), and 0 errors
across 10,405 games. See `127-04-SUMMARY.md` for the full before/after table.

## Command

The script is **unmodified** — the same `scripts/backfill_flaws.py` used for dev/benchmark.

```bash
# 1. Open the prod DB tunnel (forwards localhost:15432 -> prod Postgres).
bin/prod_db_tunnel.sh

# 2. Dry-run first to confirm counts without writing.
uv run python scripts/backfill_flaws.py --db prod --full-evald-only --dry-run

# 3. Real run (writes). --full-evald-only scopes to the flaw-eligible set
#    (games with full_evals_completed_at set), avoiding loading positions for
#    the ~95% of games that lack full-game evals.
uv run python scripts/backfill_flaws.py --db prod --full-evald-only

# 4. Close the tunnel when done.
bin/prod_db_tunnel.sh stop
```

Optionally scope to a single user with `--user-id <id>` for a staged rollout.

## Idempotency & batch size

- The backfill is **idempotent**: per game it does a delete-then-insert of that game's
  `game_flaws` rows inside a transaction. Re-running produces the same end state.
- Batch size is **100 games per commit** (`BACKFILL_GAMES_PER_BATCH`). Each batch commits
  before the next loads, bounding the transaction/memory footprint.
- This batched script has run on prod before (Phase 125 backfill); the batch-100 footprint
  is within the prod `mem_limit` budget (T-127-08: DoS risk accepted — batched, proven).

## Expected effect on prod

- `tactic_depth`: NULL → non-NULL on every re-backfilled tagged row.
- **fork**: count drops (false positives removed by the relevance gate). Direction matches
  dev (−7.6%); exact magnitude depends on prod's game mix.
- **pin**: roughly flat on dev (the replacement guard is conservative — pin precision did
  not improve in the 127-03 fixture measurement). Do not expect a large pin drop.
- Other motifs redistribute slightly as the min-depth dispatcher re-resolves ties.

## Coverage note (drains auto-pick-up)

This re-backfill is **not** strictly required to roll the fix forward: the running tier-1/2
eval+tag drain workers call the same `classify_game_flaws` path, so **newly drained games pick
up the corrected detector + `tactic_depth` automatically**. The prod re-backfill only
back-corrects the *already-tagged historical* rows; without it, lichess-only / older coverage
refills with corrected tags over time as games are re-processed. Run the re-backfill when a
clean historical correction is wanted sooner than organic drain refill.

## Verification after a prod run

```sql
-- tactic_depth populated on tagged rows
SELECT COUNT(*) FILTER (WHERE tactic_motif IS NOT NULL)            AS tagged,
       COUNT(*) FILTER (WHERE tactic_motif IS NOT NULL
                          AND tactic_depth IS NOT NULL)            AS tagged_with_depth
FROM game_flaws;

-- fork (motif=1) / pin (motif=3) counts vs the pre-run baseline you captured
SELECT tactic_motif, COUNT(*) FROM game_flaws
WHERE tactic_motif IN (1, 3) GROUP BY tactic_motif;
```

Confirm `tagged_with_depth` == `tagged` for the re-backfilled set, fork dropped vs baseline,
and no motif collapsed to near-zero.
