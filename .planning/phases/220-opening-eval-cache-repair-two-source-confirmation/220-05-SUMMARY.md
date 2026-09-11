---
phase: 220-opening-eval-cache-repair-two-source-confirmation
plan: 05
subsystem: database
tags: [opening-cache-repair, dev-smoke, release, deploy, stockfish, alembic]

# Dependency graph
requires:
  - phase: 220-01
    provides: audit tables, stage state machine, seed/calibrate/screen/orphans
  - phase: 220-02
    provides: remote-worker submit lane writes the opening cache (CACHEFIX-12)
  - phase: 220-03
    provides: confirm/propagate/rederive
  - phase: 220-04
    provides: report/legacy-sample
provides:
  - "Dev smoke of the full pipeline with two injected poisoned rows, four literal SIGTERM resumes and an exact row-count reconciliation"
  - "Release 1 squash-merged into main (b75c17172) and deployed to production (2ad90ce97): four audit tables live on prod at Alembic head a1c2e3f40001, cache untouched"
  - "Three pipeline defects found by the smoke and fixed before the release (pool size ignored, short-game terminal carriers unscreenable, propagate never set status repaired)"
affects: [220-06, 220-07, 220-08]

# Actuals (#2632)
actuals:
  tokens: 0
  tasks: 3
  commits: 10

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Operator stages run from the orchestrator session as detached processes (setsid nohup) with a low-noise Monitor; SIGTERM goes to the venv python3 PID, never the uv wrapper"
    - "_carrier_targets(): one replay helper for every hash-asserted stage, including the terminal position of a game that ended inside DEDUP_MAX_PLY plies, with the terminal target's full_hash taken from its stored row"

key-files:
  created:
    - reports/opening-cache-repair/opening-cache-repair-2026-09-10.md
  modified:
    - CHANGELOG.md
    - scripts/opening_cache_repair.py
    - app/services/engine.py
    - tests/scripts/test_opening_cache_repair.py

key-decisions:
  - "The dev smoke was run from the orchestrator session, not a human terminal: the plan's 'must not be backgrounded by an agent' caveat targets subagents (whose children die with them); a setsid-detached process owned by the session survives across turns and can be SIGTERMed from a second shell call"
  - "Two poisoned hashes instead of one, and their carrier game_positions rows poisoned as well, so propagate had real rows to rewrite and rederive had a game with blobbed surviving flaws (201805) to prove blob preservation"
  - "Screen resumed at pool size 8 (not the plan's 4) once the pool-size fix landed; pool size changes throughput only, never per-eval budgets, and the calibration floors were measured before the change"
  - "The 295 already-propagated dev rows were moved confirmed_bad -> repaired with a one-off UPDATE after the status-transition fix, mirroring exactly what the fixed propagate now writes; prod never runs the unfixed code"

patterns-established:
  - "Stage throughput on dev: screen ~430 rows/min at pool 1, ~1,500 rows/min at pool 8 (DB-bound overhead limits scaling); confirm 1,551 rows at 1M nodes in ~5 min at pool 8; a pending-only re-walk of 670k game ids takes ~12 min"

requirements-completed: []
# CACHEFIX-02 is shared with 220-01/03/04 (all summarized) and CACHEFIX-11 with
# 220-06/220-08; the shared-ID gate marks them when the last declaring plan
# finishes. REQUIREMENTS.md does not exist in this project, so mark-complete is a no-op.

coverage:
  - id: D1
    description: "Full pipeline end to end on dev with kill-and-resume on screen (x2), confirm, rederive; propagate finished in 1 s so its kill could not land mid-run (in-process CancelledError test covers it)"
    requirement: CACHEFIX-02
    verification:
      - kind: other
        ref: "smoke transcript below; opening_cache_repair_progress has all eight *_finished_at stamps; pending = 0; cache 106,615 -> 82,586 = snapshot minus the 24,029 orphans"
        status: pass
    human_judgment: false
  - id: D2
    description: "Release 1 merged with a green full gate and deployed; audit tables exist on prod with 0 rows, cache row count within 1% of baseline"
    requirement: CACHEFIX-11
    verification:
      - kind: other
        ref: "origin/production = 2ad90ce97; prod query: four to_regclass non-NULL, opening_cache_audit = 0, opening_position_eval = 2,567,921 (baseline 2,567,473), alembic_version = a1c2e3f40001"
        status: pass
    human_judgment: false

# Metrics
duration: ~5h40m (04:39Z - 10:32Z, of which ~1h40m screen walk and ~20 min production CI+deploy)
completed: 2026-09-10
status: complete
---

# Phase 220 Plan 05: Dev smoke, Release 1 merge and production deploy

## Performance

- Wall clock: ~5h40m including a ~1h40m screen walk (pool 1 for the first 15 min, pool 8 afterwards), the pending-only re-walk after the terminal-carrier fix (~12 min), and production CI + deploy (~20 min).
- Commits: 10 on the phase branch (3 fixes, 1 feature, 1 report, 1 changelog, 1 style, plus this summary's docs commits), squashed into `b75c17172` on `main`.

## Accomplishments

- Ran the 14-step dev smoke end to end against the real dev database with `--db dev`, never `bin/reset_db.sh`, never a cache truncate.
- Injected two synthetic poisoned rows (cache and carrier `game_positions` rows set to 305) and watched both travel `pending -> flagged -> confirmed_bad -> repaired` with the cache and carrier rows restored to the 1M-node values.
- Four literal `kill -TERM` resumes (screen x2, confirm, rederive) with no row screened twice, no duplicate repair-row key, `last_game_id_walked` never moving backwards.
- Found and fixed three real defects the unit tests could not see (below), each with a mutation-proven regression test.
- Release 1 shipped: changelog bullet, full pre-merge gate green, squash-merge into `main`, PR #356 to `production`, `bin/deploy.sh`, forward-port, post-deploy verification.

## Dev-smoke transcript (times UTC, 2026-09-10)

| Step | Command / action | Result |
|---|---|---|
| 1-2 | `alembic upgrade head`; `\copy opening_position_eval to stdout csv > /tmp/opening_cache_dev_backup.csv` | 106,615 rows snapshotted |
| 3 | Poison A: hash `8173389654679153058` (true -14 / c6a5, 6 carriers, min game 157920) -> `eval_cp = 305`; carrier row game 157920 ply 12 -> 305 | audit row re-seeded with `old_cp = 305` |
| 3b | Poison B (added 04:50Z while screen was at cursor 161112): hash `4873260489425083776` (true 84 / f6d5, 4 carriers, min game 201805 which has 7 blobbed flaws) -> 305; carrier row game 201805 ply 6 -> 305 | audit row re-seeded with `old_cp = 305` |
| 4 | `seed --db dev` (04:40:57Z) | inserted 106,615; re-run inserted 0 / skipped 106,615 |
| 5 | `calibrate --db dev --n 50` (1m13s) | `screen_floor = 0.0323`, `confirm_floor = 0.0189`, `engine_version = Stockfish 18` |
| 6 | `screen --db dev` run 1 (04:41:15Z, pool 1) | 04:46:53Z `kill -TERM` at cursor 159112: "signal 15 received, stopping after this batch. processed 2757 row(s); cursor at game_id 159312", exit 0, counts flagged 31 / pending 103,858 / clean 2,726 = 106,615 |
| 6 | screen run 2 (04:47:34Z, `STOCKFISH_POOL_SIZE=8` ignored -> still pool 1, ~430 rows/min) | 04:56:05Z `kill -TERM` at cursor 162312 -> "processed 3849 row(s); cursor at game_id 162512", exit 0; cursor moved forward only |
| fix | `2b21a6232` stages size their EnginePool from `STOCKFISH_POOL_SIZE`; `3e415b809` `--pool-size N` override | |
| 6 | screen run 3 (04:56:28Z, pool 8, ~1,500 rows/min) | 05:38:14Z walk exhausted, `screen_finished_at` set: clean 80,945 / flagged 1,550 / pending 24,120 |
| 7 | `orphans --db dev --dry-run` | 24,029 orphans (exactly the RESEARCH baseline) plus **91 still-pending rows WITH a carrier** -> investigated: all 103 carrier rows are the final position of a game that ended by resignation/timeout/abandon inside 20 plies (`include_terminal=False` never yields that board) |
| fix | `290997dc6` `_carrier_targets()` includes short-game terminal positions | |
| 6 | cursor reset (`last_game_id_walked = 0`, screen stamps NULL), screen run 4 (05:47:56Z, pending-only) | 06:00:19Z "processed 91 row(s)"; clean 81,035 / flagged 1,551 / pending 24,029 |
| 7 | `orphans --db dev` | deleted 24,029; cache 82,586 rows |
| 8 | `confirm --db dev --pool-size 8` run 1 | 06:02:39Z `kill -TERM` -> "stopping after this batch. processed 500 row(s)", exit 0: bad 112 / clean 388 / flagged 1,051, `confirm_finished_at` NULL |
| 8 | confirm run 2 (3m15s) | processed 1,051: bad 295 / clean 1,256; both poisons `confirmed_bad`; cache A -> 6 / c6a5 (20 cp from the recorded -14, engine nondeterminism), cache B -> 84 / f6d5 (exact) |
| 9 | `propagate --db dev` x3 | run 1 finished in ~1 s (295 rows, 267 carrier rewrites, 527 games queued) before the SIGTERM could land; runs 2 and 3 rewrote 0; 267 repair rows, 267 distinct keys; game 157920 ply 12: 305 -> 6, game 201805 ply 6: 305 -> 84 |
| fix | `0d0854104` propagate transitions status to `repaired` (only `repaired_at` was stamped; Release 2's migration trusts `repaired` only); dev's 295 rows aligned with a one-off UPDATE | |
| 10 | `rederive --db dev` | 06:08:20Z `kill -TERM` after 382 games -> exit 0, resume processed 145; final 279 reclassified / 248 failed (`GameNotAnalyzed: insufficient eval coverage`, all never-evaluated carrier games); herring_pool 30 -> 30, drill_solves 168 -> 168, drill_items 31 -> 31, game_flaws 70,933 -> 70,918; game 201805: 7 flaws with byte-identical blobs, oracle counts and accuracy unchanged, `blobs_completed_at` re-stamped (not cleared, no new flaw); game 157920: 0 flaws, accuracy 89.4 -> 90.5 / 91.6 -> 93.2 from the restored ply-12 eval |
| 11 | `report --db dev` | `reports/opening-cache-repair/opening-cache-repair-2026-09-10.md` (committed `49c85b7b4`) |
| 12 | `legacy-sample --db dev --append-report --pool-size 8` (3m48s) | legacy 200 games, 7,901 rows ply>20, 14.33% disagree; control 7 games, 259 rows, 12.74%; `LEGACY-COHORT-DECISION: NO BUILD` |
| 14 | reconcile | cache 82,586 = 106,615 - 24,029; pending 0; 82,586 screened rows each with one `screened_at`; all eight `*_finished_at` set |

Kill points landed: screen (x2), confirm, rederive. Not landed: propagate (stage completes in ~1 s at dev scale).

## Release 1

- Full pre-merge gate: `ruff format` reformatted two pre-existing files (`26096d87a`), `ruff check`, `ty` (app/tests/scripts and analysis), function-size gate, `pytest -n auto -x` 4,595 passed / 19 skipped, frontend lint clean, vitest 259 files / 4,022 tests passed.
- Squash commit `b75c17172` on `main`, pushed, `main...origin/main = 0 0`; phase branch re-created from `main`.
- PR #356 `main -> production`, CI green first try (test 9m8s), squash `2ad90ce97`; `bin/deploy.sh` exit 0, production CI 34465632480 (test 8m59s, deploy 1m6s), server verified at `2ad90ce9`, forward-port `3c471a54b` pushed.
- Post-deploy: HTTP 200 in 0.08 s; backend/caddy up; prod `alembic_version = a1c2e3f40001`; four audit tables present, `opening_cache_audit = 0`; `opening_position_eval = 2,567,921` (baseline 2,567,473, +0.02%).
- No benchmark re-clone or `gen_benchmarks` run anywhere in the phase.

## Task Commits

1. Task 1 (dev smoke): `2b21a6232` pool size honoured; `3e415b809` `--pool-size`; `290997dc6` terminal carriers; `0d0854104` status repaired; `49c85b7b4` dev report.
2. Task 2: `e3c3e2780` changelog bullet; `26096d87a` style drift; squash `b75c17172` on `main`.
3. Task 3: `2ad90ce97` on `production`; `3c471a54b` forward-port on `main`.

## Files Created/Modified

- `scripts/opening_cache_repair.py`: `_pool_from_env(pool_size)`, `--pool-size` on calibrate/screen/confirm/legacy-sample, `build_parser()`, `_carrier_targets()`, `audit.status = "repaired"` in propagate, `_CONFIRMED_BAD_STATUSES` for the report.
- `app/services/engine.py`: `read_pool_size()` made public.
- `tests/scripts/test_opening_cache_repair.py`: `TestPoolFromEnv` (4), `test_screen_reaches_terminal_position_of_short_game`, `test_propagate_transitions_status_to_repaired`.
- `CHANGELOG.md`: one bullet under `## [Unreleased]` -> `### Fixed`.
- `reports/opening-cache-repair/opening-cache-repair-2026-09-10.md`.

## Decisions Made

See frontmatter `key-decisions`.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Every engine stage hardcoded `EnginePool(1)`**
- Found during: Task 1 step 6 (one Stockfish child under the python process despite `STOCKFISH_POOL_SIZE=8`; throughput unchanged).
- Fix: `read_pool_size()` public in `engine.py`, `_pool_from_env()` in the script; `--pool-size N` CLI override added at the user's request (prod box has 32 threads).
- Verification: `TestPoolFromEnv`; screen throughput 430 -> ~1,500 rows/min.
- Committed in: `2b21a6232`, `3e415b809`.

**2. [Rule 1 - Bug] Cache rows carried only by a short game's final position were unscreenable**
- Found during: Task 1 step 7 (`orphans --dry-run` reported 91 still-pending rows WITH a carrier after a finished walk).
- Diagnosis: 103/103 carrier rows are the last `game_positions` row of a game ending by resignation/timeout/abandon within 20 plies; `_collect_full_ply_targets(include_terminal=False)` never yields that board.
- Fix: `_carrier_targets()` replays with `include_terminal=True`, gives the terminal target its stored row hash, and replaces the four opening-carrier call sites (legacy-sample's whole-game replay left unchanged so D-07's measurement is byte-identical).
- Verification: `test_screen_reaches_terminal_position_of_short_game` (fails on the old path); re-walk screened exactly the 91 rows.
- Committed in: `290997dc6`.

**3. [Rule 1 - Bug] `propagate` never transitioned the audit row to `repaired`**
- Found during: Task 1 step 14 (both poisons ended `confirmed_bad` with `repaired_at` set; the report's `repaired` row read 0).
- Impact if unfixed: Release 2's migration (CACHEFIX-08, plan 07) marks `confirmed=true` only for `screened_clean`/`confirmed_clean`/`repaired`, so every repaired prod row would have re-entered as an untrusted candidate.
- Fix: `audit.status = "repaired"` next to the `repaired_at` stamp; report sections count `confirmed_bad` and `repaired`.
- Verification: `test_propagate_transitions_status_to_repaired` (fails with the line removed).
- Committed in: `0d0854104`.

### Process deviations (documented, not Rule 1-4)

- The smoke ran from the orchestrator session instead of a human terminal (user: "Do this yourself"); the deploy was still gated on an explicit go.
- Two poisoned hashes with poisoned carrier rows instead of one cache-only poison, so propagate/rederive had real work.
- Screen resumed at pool 8 after the fix; calibration was measured before at pool 1 (floors are budget-based, not pool-based).
- Dev cursor reset by hand to re-walk after fix 2; dev statuses aligned by a one-off UPDATE after fix 3.
- Step-10 sub-assertions "blobs_completed_at cleared on a new flaw" and "drill_items pruned where a flaw is gone" were not exercisable live (no game gained or lost a flaw among the two injected carriers); both are covered by `TestRederive`.

## Issues Encountered

- 248 of 527 repair games end `failed` with `GameNotAnalyzed: insufficient eval coverage`: never-evaluated carrier games with nothing to rederive. Honest, but the label will read badly in the prod report; consider a distinct `skipped_unanalyzed` status in a follow-up.
- Dev `confirm` marked 22% of flagged rows bad against an n=50 floor of 0.019 expected-score (deltas mostly 25-50 cp: legacy lower-budget values). Prod calibrates with n=500; the report's histogram-vs-control block is the acceptance signal, not this rate.
- `seed`/`propagate` re-stamp their `*_finished_at` on every re-run (harmless, noted for the timings section).

## User Setup Required

None beyond the already-open prod DB tunnel (`bin/prod_db_tunnel.sh`) for plan 06.

## Next Phase Readiness

Plan 06 (prod run) can start: audit tables live on prod, cache untouched, `--pool-size` available for the 32-thread box. Live prod sizing (2026-09-10): 2,567,921 cache rows, 575,318 fully evaluated engine games; 1% hash-residue sample shows 82% of cache rows have a carrier, median 1 / p90 3 / max 2,258 carriers, and the 0.4% of rows with >50 carriers hold 36% of all carrier positions. Expected repair blast radius: ~9k cache rows (0.35%), ~20-25k carrier positions, ~15-25k games reclassified (hard lower bound 4,361 from the seed), <1% of flaw rows. Expected screen time at pool 28: ~10-12 h if dev scaling holds.

## Self-Check: PASSED

- `reports/opening-cache-repair/opening-cache-repair-2026-09-10.md` exists and is committed.
- `git log origin/production --oneline -1` = `2ad90ce97 Release: opening eval cache repair pipeline (Phase 220 Release 1) (#356)`.
- Prod: four `to_regclass` non-NULL, `opening_cache_audit` 0 rows, cache 2,567,921 rows.
