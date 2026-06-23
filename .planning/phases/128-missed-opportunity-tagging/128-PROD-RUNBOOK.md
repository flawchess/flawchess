# Phase 128 — Folded Prod Re-Backfill Runbook (DEFERRED)

**Status:** DEFERRED — executed OUTSIDE the phase 128 gate (D-12, mirroring Phase 127 D-13).
This runbook documents the prod procedure; it is **not** run during the phase.

## What this does

Re-runs `classify_game_flaws` over prod's existing `game_flaws` rows in a **single pass**,
folding the Phase 127 deferred backfill and the Phase 128 missed-opportunity fill together
(D-12 efficiency note):

1. **Phase 127 fixes** — `allowed_tactic_depth` populated (non-NULL) on re-backfilled tagged
   rows; fork false positives pruned by the D-01 relevance gate; min-depth dispatcher
   re-resolves motif ties.

2. **Phase 128 additions** — `missed_tactic_motif / missed_tactic_piece /
   missed_tactic_confidence / missed_tactic_depth` populated from the `flaw_ply` PV
   (the SEED-054 "instead-of" line). Rows whose `flaw_ply` PV is absent (lichess coverage
   still filling) stay `NULL` — honest, per D-13. No fabrication.

Both fills live inside the same `classify_game_flaws` call path, so a single sweep over
`game_flaws` populates all eight orientation columns in one commit.

## Pre-conditions

- SEED-054 `flaw_ply` PV prod backfill **must be complete** before running this runbook.
  Confirm: `SELECT COUNT(*) FROM game_positions WHERE pv IS NOT NULL` is non-zero and the
  backfill script (`scripts/backfill_best_move_pv.py`) reports 0 remaining rows.
  (D-12: the planner assumed this — rows without a PV simply yield NULL `missed_*`, but
  running before the SEED-054 backfill completes means more NULL rows initially; the
  runbook is safe to re-run once coverage improves.)
- The `production` branch carries the Phase 128 migration (`b6e2978df54f` — four renames
  `tactic_* → allowed_*` + four new `missed_*` columns) and the Phase 127 detection fixes.

## Command

The script is **unmodified** — the same `scripts/backfill_flaws.py` used for dev/benchmark.

```bash
# 1. Open the prod DB tunnel (forwards localhost:15432 -> prod Postgres).
bin/prod_db_tunnel.sh

# 2. Capture a pre-run baseline (all motif counts).
uv run python -c "
import asyncio, asyncpg, os
async def _():
    conn = await asyncpg.connect(os.environ['DATABASE_URL_PROD'])
    rows = await conn.fetch('''
        SELECT
            COUNT(*) FILTER (WHERE allowed_tactic_motif IS NOT NULL) AS allowed_tagged,
            COUNT(*) FILTER (WHERE allowed_tactic_motif IS NOT NULL
                               AND allowed_tactic_depth IS NOT NULL) AS allowed_with_depth,
            COUNT(*) FILTER (WHERE missed_tactic_motif IS NOT NULL)  AS missed_tagged
        FROM game_flaws
    ''')
    print(dict(rows[0]))
    await conn.close()
asyncio.run(_())
"

# 3. Dry-run to confirm game count without writing.
uv run python scripts/backfill_flaws.py --db prod --full-evald-only --dry-run

# 4. Real run (writes). --full-evald-only scopes to the flaw-eligible set.
uv run python scripts/backfill_flaws.py --db prod --full-evald-only

# 5. Close the tunnel when done.
bin/prod_db_tunnel.sh stop
```

Optional: scope to a single user with `--user-id <id>` for a staged rollout.

## Idempotency & batch size

- **Idempotent:** per game, a delete-then-insert inside a transaction produces the same
  end state on re-run. Re-running after SEED-054 coverage improves fills previously-NULL
  `missed_*` rows without corrupting `allowed_*` (T-128-07).
- **Batch size:** 100 games per commit (`BACKFILL_GAMES_PER_BATCH`). Proven at this batch
  size on prod in Phase 125 and Phase 127; within the prod `mem_limit` budget.

## Expected effect on prod

- `allowed_tactic_depth`: NULL → non-NULL on every re-backfilled tagged row (Phase 127 fill).
- `missed_tactic_motif / piece / confidence / depth`: NULL → populated where `pv[flaw_ply]`
  exists (SEED-054 coverage). Rows without a PV remain NULL (honest, D-13).
- **fork** (`allowed_tactic_motif` = FORK int): count drops due to Phase 127 relevance gate.
  Direction matches dev (−7.6% on dev in 127-04); exact prod magnitude depends on game mix.
- Other `allowed_*` motifs redistribute slightly as min-depth re-resolves.

## Verification after a prod run

```sql
-- Orientation coverage: allowed depth + missed fill
SELECT
    COUNT(*) FILTER (WHERE allowed_tactic_motif IS NOT NULL)                AS allowed_tagged,
    COUNT(*) FILTER (WHERE allowed_tactic_motif IS NOT NULL
                       AND allowed_tactic_depth IS NOT NULL)                AS allowed_with_depth,
    COUNT(*) FILTER (WHERE missed_tactic_motif IS NOT NULL)                 AS missed_tagged,
    COUNT(*) FILTER (WHERE missed_tactic_motif IS NOT NULL
                       AND allowed_tactic_motif IS NULL)                    AS missed_only,
    COUNT(*) FILTER (WHERE missed_tactic_motif IS NOT NULL
                       AND allowed_tactic_motif IS NOT NULL)                AS both_orientations,
    COUNT(*) FILTER (WHERE missed_tactic_motif IS NULL
                       AND allowed_tactic_motif IS NULL)                    AS neither
FROM game_flaws;

-- Motif distribution (allowed orientation)
SELECT allowed_tactic_motif, COUNT(*)
FROM game_flaws
WHERE allowed_tactic_motif IS NOT NULL
GROUP BY allowed_tactic_motif
ORDER BY count DESC;

-- Motif distribution (missed orientation)
SELECT missed_tactic_motif, COUNT(*)
FROM game_flaws
WHERE missed_tactic_motif IS NOT NULL
GROUP BY missed_tactic_motif
ORDER BY count DESC;
```

Confirm:
- `allowed_with_depth` == `allowed_tagged` (no depth-NULL on tagged rows after backfill).
- `missed_tagged` > 0.
- `missed_only` > 0 (flaws the mover missed but didn't get punished for — proves the two
  passes are independent).
- Fork (`allowed_tactic_motif` = 1 or relevant int) dropped vs pre-run baseline.
- No motif collapsed to near-zero.

## Coverage note (drains auto-pick-up)

Running tier-1/2 drain workers call the same `classify_game_flaws` path, so **newly drained
games already pick up `missed_*` tagging automatically** once Phase 128 deploys. This runbook
back-corrects the historical rows imported before Phase 128 deployed. Without it, organic drain
refill gradually corrects the historical set over time.
