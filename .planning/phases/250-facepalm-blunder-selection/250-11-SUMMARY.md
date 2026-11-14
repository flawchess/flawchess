---
phase: 250-facepalm-blunder-selection
plan: 11
subsystem: database
tags: [maia, game-flaws, migration, column-drop, d-11]

requires:
  - phase: 250-facepalm-blunder-selection
    provides: "owner verdict accept, d11_go: yes (plan 09)"
provides:
  - "Migration f9c4d7e3a250: nine Maia columns dropped from game_flaws, games.maia_refutation_completed_at dropped"
  - "The hook computes only maia_played_prob, the reply spread, the line facts and facepalm_score"
  - "scripts/backfill_maia_flaws.py modes: full, spread, line (refutation removed)"
affects: [250-10]

key-files:
  created:
    - alembic/versions/20261114_120000_f9c4d7e3a250_phase_250_drop_maia_columns.py
  modified:
    - app/models/game_flaw.py
    - app/models/game.py
    - app/repositories/game_flaws_repository.py
    - app/services/maia_flaw_stats.py
    - app/services/maia_flaw_scoring.py
    - scripts/backfill_maia_flaws.py
    - scripts/blunder_check/oddness.py
    - docs/dev-tooling.md

key-decisions:
  - "Owner: drop-now (2026-11-14), with the Phase 252 repair on the other machine pulled and restarted by the owner after the deploy"
  - "The game fingerprint is now (ply, fen, severity, ply+1 line); best_move is no longer fingerprinted"

requirements-completed: [D-11]
---

# Phase 250 Plan 11: Drop the nine unused Maia columns

**The nine Maia columns and the refutation stamp are dropped on prod; one prod check (live hook) is still open.**

## Tasks

- **Task 1 (tracer):** the hook writes only the kept values and the drop migration round-trips on dev (upgrade, downgrade, upgrade; `alembic check` clean).
- **Task 2:** remaining readers removed. `grep -rnE 'maia_(played_rank|best_(prob|rank)|second_|top_prob|effective_moves|refutation_)' app scripts tests` is empty (308 lines before). Full pre-merge gate green: 6,306 backend tests (parallel and serial), 6,246 frontend tests, ruff, ty, function-size, knip.
- **Task 3 (decision):** owner chose **drop-now** on 2026-11-14. SEED-261110-cqk makes no claim on the dropped columns; the only planning docs naming them are the Phase 247 to 250 seeds and ROADMAP history.
- **Task 4 (deploy):** squash-merge `d00cb7e27` on main, PR #477 squash-merged to production as `86d9b0a86`, deployed 2026-11-14T11:32Z through `bin/deploy.sh`, server SHA verified. No operator script was running.

## Dropped and kept

- Dropped from `game_flaws`: `maia_played_rank`, `maia_best_prob`, `maia_best_rank`, `maia_second_prob`, `maia_second_rank`, `maia_top_prob`, `maia_effective_moves`, `maia_refutation_prob`, `maia_refutation_rank`.
- Dropped from `games`: `maia_refutation_completed_at`.
- Kept on `game_flaws`: `maia_played_prob`, `maia_reply_spread`, `line_loss_1/3/5/7/9`, `line_mate_ply`, `facepalm_score`. Kept on `games`: `maia_flaws_completed_at`, `facepalm_spread_completed_at`, `facepalm_line_completed_at`.

## Prod verification

- alembic head `f9c4d7e3a250`.
- `maia_*` columns on `game_flaws`: exactly `maia_played_prob`, `maia_reply_spread`.
- `games.maia_refutation_completed_at`: gone.
- Sentry, hour after the deploy: only the known "Stale frontend build" notice (2 events); nothing from the Maia hook.
- **Open: live hook check (O3).** No game finished full evaluation after the deploy, so the hook had nothing to score: the last completion was 10:56:45 UTC, when the only active remote worker (`amalie-pc`) stopped, 35 minutes before the deploy. The check has to be repeated once a worker runs again:
  `SELECT count(*), count(*) FILTER (WHERE facepalm_spread_completed_at IS NOT NULL) FROM games WHERE maia_flaws_completed_at >= '2026-11-14T11:32:00Z'` (both counts equal and above 0).

## Deviations from Plan

- A reader outside the plan's file list: `scripts/blunder_check/oddness.py` passed `best_uci` / `second_uci`; fixed.
- `docs/dev-tooling.md` still described `--mode refutation`; updated.
- Tests that changed `best_move` to alter the fingerprint now change a severity.
- Follow-up candidate, not done: the tier-4 blob-submit lane still re-scores a game through the hook, which no longer changes any stored value now that the second-pair columns are gone.

## Next Phase Readiness

Plan 250-10 (D-18 refit and prod line pass) is the only plan left; it waits on the Phase 252 prod line repair.

## Self-Check: PASSED (code and schema); live hook check open
