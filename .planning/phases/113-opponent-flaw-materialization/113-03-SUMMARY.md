---
phase: 113-opponent-flaw-materialization
plan: 03
subsystem: database
tags: [flaws, backfill, data-migration, game-flaws, opponent, benchmark]

# Dependency graph
requires:
  - phase: 113-01
    provides: classify_game_flaws both-sides kernel + is_opponent_expr helper
  - phase: 113-02
    provides: player_only_gate on all 5 library_repository read sites (R1-R5)
provides:
  - dev game_flaws repopulated with both sides for users 28 & 44 (idempotent wipe+recompute)
  - end-to-end no-regression proof: gated player-only reads unchanged, ungated doubled
  - benchmark-cohort backfill instructions (HUMAN-UAT, phase-114 hand-off)
affects: [114-benchmark-delta-zones, 115-comparison-endpoint]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "backfill_flaws.py --db dev --user-id <N>: idempotent wipe+recompute via delete_flaws_for_game + bulk_insert_game_flaws, no code change beyond Plan-01 kernel (D-09)"
    - "Idempotency gate: re-running produces identical row counts (delete+reinsert is deterministic)"

key-files:
  created:
    - ".planning/phases/113-opponent-flaw-materialization/113-03-SUMMARY.md"
  modified: []

key-decisions:
  - "D-09 confirmed: backfill_flaws.py needed zero code changes — the D-10 single-classify-path propagated both-sides behavior automatically via classify_game_flaws kernel change in Plan-01"
  - "Benchmark cohort backfill is HUMAN-UAT phase-114 hand-off — does NOT gate phase completion per D-09"
  - "Post-backfill gated reads confirm exact 1620-row baseline preserved for both users — no-regression proven on real dev data"

patterns-established:
  - "Post-backfill verification: ungated ~2x baseline, gated == pre-phase baseline — proven via direct SQL against dev DB"

requirements-completed: [FLAWX-04]

# Metrics
duration: 10min
completed: 2026-06-10
---

# Phase 113 Plan 03: Dev Backfill + No-Regression Verification Summary

**Dev users 28 & 44 game_flaws repopulated with both sides (1620 → 3310 rows each, 2.04x) via zero-code-change idempotent backfill; gated player-only reads confirm exact 1620-row baseline preserved end-to-end**

## Performance

- **Duration:** ~10 min
- **Started:** 2026-06-10T06:03:00Z
- **Completed:** 2026-06-10T06:13:00Z
- **Tasks:** 1 (autonomous); 1 checkpoint (HUMAN-UAT — not executed)
- **Files modified:** 0 (execution-only plan — no code changes)

## Accomplishments

- Captured pre-backfill baseline: users 28 & 44 each had 1,620 `game_flaws` rows (player-only, 476 games)
- Dry-run for user 28 confirmed both-sides recompute would produce 3,310 rows (5,122 games iterated, 4,560 skipped/no-eval, 562 analyzed)
- Ran `backfill_flaws.py --db dev --user-id 28` and `--user-id 44` — both produced 3,310 rows (2.04x baseline), 0 errors
- Idempotency confirmed: re-running `--user-id 28` produced identical 3,310 count
- No-regression invariant proven via direct SQL: gated player-only reads (ply parity + game.user_color join) returned exactly 1,620 for both users, matching the pre-phase baseline
- `backfill_flaws.py` required zero code changes (D-09) — the D-10 single classify path propagated both-sides behavior from the Plan-01 kernel change automatically
- All 26 `tests/test_flaws_materialization.py` tests pass; full suite 2491 passed

## Backfill Numbers

| User | Pre-Backfill (player-only) | Post-Backfill (both sides) | Ratio | Gated Post-Backfill |
|------|---------------------------|---------------------------|-------|---------------------|
| 28   | 1,620 rows                | 3,310 rows                | 2.04x | 1,620 (= baseline)  |
| 44   | 1,620 rows                | 3,310 rows                | 2.04x | 1,620 (= baseline)  |

User 28: 5,122 total games, 4,560 skipped (no Stockfish analysis), 562 analyzed games.
User 44: 769 total games, 207 skipped, 562 analyzed games.

## No-Regression Proof

Gated player-only reads (reproducing the Plan-02 `player_only_gate` parity logic in SQL):
- Even ply + `user_color='white'` = player row; odd ply + `user_color='black'` = player row
- Post-backfill SQL: `SELECT count(*) FROM game_flaws gf JOIN games g ON g.id = gf.game_id WHERE gf.user_id = 28 AND ((ply%2=0 AND user_color='white') OR (ply%2=1 AND user_color='black'))` → **1,620**
- Same query for user 44 → **1,620**

Both match the pre-phase baseline exactly. Ungated total = 3,310 (strictly > 1,620). No-regression invariant confirmed on real dev data.

## D-09 Confirmation

`scripts/backfill_flaws.py` was executed but NOT modified. The `--db dev --user-id <N>` CLI arguments functioned as documented. The D-10 single-classify-path invariant means the Plan-01 kernel change (`classify_game_flaws` dropping the `mover != user_color` filter) propagated automatically to `backfill_flaws.py` without any script edit.

## Task Commits

Task 1 had no file changes (execution-only — dev DB modified, no source files). No per-task commit was generated; the plan metadata commit carries the SUMMARY.

**Plan metadata:** (see final commit hash below)

## Files Created/Modified

- No source files modified (execution-only plan).
- Dev `game_flaws` table updated for users 28 & 44 (DB-only, not tracked in git).

## Decisions Made

- D-09 confirmed correct: zero code changes to backfill_flaws.py were needed. The D-10 single classify path works as designed.
- Benchmark cohort backfill left as HUMAN-UAT (phase-114 hand-off) per D-09 — long run, does not gate phase completion.

## Deviations from Plan

None — plan executed exactly as written. No script edits required. No code changes. Dry-run confirmed plan before write execution.

## Issues Encountered

None — backfill ran cleanly, 0 errors for both users.

## Benchmark Cohort Backfill (HUMAN-UAT — Phase-114 Hand-off)

Task 2 is a `checkpoint:human-verify (gate=blocking)` — see Checkpoint section at end of this summary. The benchmark backfill is a longer unattended run and does NOT gate phase completion per D-09.

**Commands when ready:**
```bash
# 1. Ensure benchmark DB is running
bin/benchmark_db.sh start

# 2. Optional dry-run to estimate scope
uv run python scripts/backfill_flaws.py --db benchmark --dry-run

# 3. Run the benchmark backfill (long run — can take minutes)
uv run python scripts/backfill_flaws.py --db benchmark
```

**Spot-check after run:**
- Pick a known game_id from the benchmark DB
- Query `SELECT ply, severity FROM game_flaws WHERE game_id = <id> AND user_id = <uid> ORDER BY ply LIMIT 20`
- Confirm rows at both even and odd plies (both sides)
- Confirm row volume roughly doubled vs pre-backfill (~2-10 rows/game vs ~1-5)
- Confirm prod `game_flaws` was NOT touched (prod ships empty per FLAWX-04)

## Known Stubs

None — execution-only plan; no UI-facing data changes.

## Threat Flags

None — no new endpoints, no new user input, no prod backfill. T-113-06 (OOM-safe batching) and T-113-07 (idempotent wipe+recompute) both confirmed by zero-error backfill run.

## Next Phase Readiness

- Phase 113 is complete (all 3 plans done). Benchmark backfill is a hand-off for phase 114 to verify before consuming the benchmark `game_flaws`.
- Phase 114 (benchmark delta-zone computation) can begin; `is_opponent_expr`, gated readers, and dev both-sides data are all ready.
- Phase 115 (comparison endpoint + bullet-grid UI) unblocked by the full phase-113 data foundation.

---
*Phase: 113-opponent-flaw-materialization*
*Completed: 2026-06-10*

## Self-Check: PASSED

- FOUND: `.planning/phases/113-opponent-flaw-materialization/113-03-SUMMARY.md`
- CONFIRMED: dev `game_flaws` user 28: 3,310 rows (2.04x baseline 1,620); gated = 1,620
- CONFIRMED: dev `game_flaws` user 44: 3,310 rows (2.04x baseline 1,620); gated = 1,620
- CONFIRMED: backfill_flaws.py had zero code changes (D-09)
- CONFIRMED: idempotency — re-run for user 28 yields identical 3,310
- CONFIRMED: 2491 tests passed (full suite)
