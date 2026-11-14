---
phase: 250-facepalm-blunder-selection
plan: 09
subsystem: release
tags: [blunder-check, facepalm-score, release, prod-backfill, calibration, spot-check]

requires:
  - phase: 250-facepalm-blunder-selection
    provides: "facepalm scorer and selection (plans 01-06), backfill modes (plan 07), calibration tooling and green gate (plan 08)"
provides:
  - "Phase 250 released to prod with Phase 249 (PR #475), migration e8b3c6d2f250 applied"
  - "Prod spread backfill: 99.948% of 2,318,467 user blunders carry a reply spread, 79.651% a facepalm score, 616,310 qualify at 0.7"
  - "Prod calibration and spot-check with the facepalm selection, committed"
  - "Session-start fix for the own-game pick (PR #476)"
  - "Owner verdict: accept (D-11 gate open)"
affects: [250-10, 250-11]

d11_go: yes

key-files:
  created:
    - reports/maia-flaws-backfill/prod-facepalm-spread-coverage.md
    - reports/blunder-check/blunder-check-calibration-2026-11-14.md
    - reports/blunder-check/spot-check-2026-11-14.md
  modified:
    - app/repositories/blunder_check_repository.py
    - uv.lock

key-decisions:
  - "Phase 250 shipped together with Phase 249 in one release (owner: Ship)"
  - "12 spread shards instead of the planned 6 to 8, because the Phase 252 repair moved off this machine (owner asked for the faster run)"
  - "Window 14 style blunders with a stored line shorter than 3 plies stay unscored until the D-18 refit (owner: ship-as-fitted)"
  - "The own-game pick pins game_flaws.user_id to the game owner; no new index"

requirements-completed: [D-08, D-09, D-10]
---

# Phase 250 Plan 09: Release, prod spread backfill, prod calibration, owner verdict

**The facepalm selection is live on prod, the existing blunders are backfilled, and the owner accepted it.**

d11_go: yes

## Task 1: Dev rehearsal

The operator command chain ran end to end on dev for user 28.

- Spread run total: games_selected=2660, spreads_scored=4986, scores_set=4328, scores_null=658, no write or score failures.
- O1 on dev (user 28): 5,396 user blunders, 100% with spread, 84.451% with score, 1,228 qualifying, null_no_line 151, null_short_line 688, in_unstamped_games 0.
- Dev calibration rendered both `## Facepalm score` and `## Supply by origin`. Its numbers were zero because the sampled dev games were not spread-backfilled; only the structure was checked. It took 12 minutes and was run from the orchestrator in the background.

## Task 2: Release and prod backfill

- **Release:** squash-merge `b805f979c` on main, PR #475 squash-merged to production as `cd9450066`, deployed 2026-11-13T22:38:21Z through `bin/deploy.sh`, server SHA verified, alembic head `e8b3c6d2f250`. CI first failed on pip-audit (dnspython, opentelemetry-api); fixed in `29ad9b0d9`.
- **Slice:** 50 games, 103 spreads, 101 scores, 0 failures; O2 spread_rows 103, out_of_scope_rows 0.
- **Hook check:** 12 games scored by the live hook 33 minutes after the deploy, all 12 with the facepalm stamp.
- **Full pass:** two legs of 12 shards with `--throttle-ms 50`. Leg 1 (2026-11-13 22:40 to 2026-11-14 02:15 UTC) stamped 431,892 games and was cut by a scheduled prod reboot (exit 4, 3,000 unwritten games, no data loss). Leg 2 (02:17 to 07:30 UTC) stamped the remaining 603,154 games with 0 failures, exit 0. About 32 games per second overall; prod connections 28 of 50.
- **Catch-up:** `--mode full` 1,060 games (1,041 stamped), then `--mode spread` 6 games.
- **Coverage (O1):** 2,318,467 user blunders; with_spread 2,317,270 (99.948%, bar 99.0); with_score 1,846,677 (79.651%); qualifying 616,310; null_no_line 152,567; null_short_line_or_no_played_prob 318,026; null_no_spread 1,197; in_unstamped_games 0.
- **Calibration (25 permille, 58,404 user blunders):** pass share at 0.7 is 33.4% of scored blunders, 33 to 35% up to 2399 and 23.6% at 2400+. Median user has about 343 usable own windows; 95 of 583 users are under 50. Foreign supply within +-150 Elo is thinnest at the 2600 level (about 9,200 usable) and the 800 level (about 16,200).

## Task 3: Owner verdict

**accept** (2026-11-14). The owner played prod beta sessions and reviewed the reports.

The first two session starts took 5 to 10 seconds. Cause: the own-game pick's EXISTS had no selective predicate on `game_flaws`, so prod hashed a sequential scan of the 12 GB table (17.8 s measured). Fix `0a250a3dd` pins `game_flaws.user_id` to the game owner (0.4 s on prod, same 1,967 games). Released as PR #476 (`55e6ecc30`), deployed 2026-11-14. The owner confirmed the session start is fast and accepted.

## Task Commits

- `b805f979c` feat(250): facepalm-blunder selection for the blunder check
- `29ad9b0d9` fix(deps): bump dnspython and opentelemetry-api
- `c7dcb9a70` docs(250-09): prod facepalm spread backfill and coverage
- `bfee46d06` docs(250-09): prod calibration and spot-check with the facepalm selection
- `0a250a3dd` fix(250): own-game pick no longer scans all of game_flaws at session start

## Deviations from Plan

- 12 shards instead of 6 to 8 (owner request; the 252 repair no longer ran on this machine).
- The full pass ran in two legs because of the scheduled prod reboot at 02:15 UTC.
- Release #475 also carried Phase 249; release #476 also carried two Renovate updates already on main.
- An unplanned defect fix and second release (#476) were needed before the verdict. The plan's under-one-second session start was only measured on dev, where the table is too small to show the bad plan.

## Next Phase Readiness

- 250-10 (D-18 refit) waits on the Phase 252 line repair finishing on prod; about 20% of user blunders are unscored until then.
- 250-11 (drop the nine Maia columns) is unblocked by `d11_go: yes` but depends on 250-10.

## Self-Check: PASSED
