---
phase: 259-facepalm-first-principles-refit
plan: 11
subsystem: release
tags: [facepalm, readiness-gate, covering-index, refit, calibration, owner-checkpoint, d-15]

requires:
  - phase: 259-06
    provides: "R1 on prod, line pass done, reply pass running"
  - phase: 259-10
    provides: "covering index migration and operator build-and-check script"
provides:
  - "Prod reply pass complete: reply_pending_games=0, reply_residue_losing=0"
  - "Prod index ix_game_flaws_facepalm_inputs built, valid, 224 MB"
  - "reports/maia-flaws-backfill/prod-facepalm-259-readiness.md"
  - "reports/blunder-check/facepalm-fit-2026-11-22.md and the 2026-11-22 features, calibration and spot-check reports"
  - "Owner decision D-15: model confirmed, FACEPALM_SCORE_MIN=0.7, FACEPALM_STATS_MIN=0.7"
affects: [259-12]

actuals:
  tasks: 3
  commits: 2
commits: 2

key-files:
  created:
    - reports/maia-flaws-backfill/prod-facepalm-259-readiness.md
    - reports/blunder-check/facepalm-features-2026-11-22.tsv
    - reports/blunder-check/facepalm-fit-2026-11-22.md
    - reports/blunder-check/blunder-check-calibration-2026-11-22.md
    - reports/blunder-check/spot-check-2026-11-22.md
  modified: []

key-decisions:
  - "D-15 owner decision, 2026-11-22: \"new-cuts: other values\", then \"FACEPALM_SCORE_MIN=0.7, FACEPALM_STATS_MIN=0.7\". The model is confirmed; the drill cut moves from 0.50 to 0.70, the stats cut stays 0.70 (no frontend cutoff change)."
  - "The fresh prod pull is byte-identical to the 2026-11-21 one, so the six constants are the ones plan 09 already put in the code: intercept -1.4308, played -0.6065, loss 0.8379, missed 0.4971, best_prob 2.0786, reply_prob 0.9133."
  - "Owner approved building the covering index and running the pull and calibration beside the Phase 252 feeder (exception to map rule 6)."
---

# Phase 259 Plan 11: Readiness Gate, Covering Index, D-15 Summary

**The prod backfill is complete, the covering index is valid on prod, and the owner confirmed the model with both cuts at 0.70 (drill cut up from 0.50, stats cut unchanged).**

## Performance

- **Executed by:** the orchestrator inline (Task 1 is five dev commands; Tasks 2 and 3 are orchestrator checkpoints)
- **Completed:** 2026-11-22
- **Tasks:** 3/3
- **Commits:** 2 (`e113f0407`, `6e4fbd424`)

## Task 1: dev tracer (nothing committed)

Log: `temp/blunder-check/tracer-259-11.log`.

1. `uv run alembic current`: `e2f6a8b0d259 (head)`.
2. `build_facepalm_inputs_index.py --db dev --check-only`: `maintenance_work_mem: 64MB`, `sessions on this database: 3`, `ix_game_flaws_facepalm_inputs: valid, definition equals the expected text.`, exit 0.
3. `backfill_maia_flaws.py --db dev --status --mode spread --user-id 28`: `spread_stamped_games=5311 spread_pending_games=0 user_blunders_total=10259 user_blunders_with_spread=10259 user_blunders_with_score=10241 user_blunders_qualifying=4307`, exit 0.
4. `fit_facepalm.py ... --check-constants`: `constants match: the app constants are the refit of this features table`, exit 0.
5. `blunder_check_calibration.py --db dev --sample-permille 1000 --limit-games 200`: sampled 200 games, 625 per-user groups, scored 3106 Good moves (0 not scorable), wrote the calibration and spot-check reports (47 windows) to `temp/blunder-check/`, exit 0.

## Task 2: readiness gate and covering index on prod

Full record: `reports/maia-flaws-backfill/prod-facepalm-259-readiness.md`.

- Reply pass: launched 2026-11-21T19:01:25Z, ended 2026-11-22T11:02Z with `EXIT=0`, about 16 hours, no relaunch. `games_selected=1054792 games_scored=1054792 games_stamped=1044652 games_already_stamped=10140 games_write_failed=0 games_score_failed=0 reason_reply_missing=288044`.
- Reply status: `reply_stamped_games=1058523 reply_pending_games=0 blunders_total=4729767 blunders_with_reply_prob=4418658 reply_residue_losing=0 unscored_pure_miss_no_best=8300 blunders_without_material_inputs=296674`.
- Line status for the R1 cutoff: `line_pending_games=0`.
- Coverage, deployed code against switched code: user blunders with a score 2,209,209 to 2,209,608 (+0.02%); opponent blunders with a score 2,195,352 to 2,195,716 (+0.02%). Qualifying at 0.50: 972,755 to 1,050,362 (+8.0%).
- Prod-run worktree `.claude/worktrees/phase-259-prod` removed and pruned.
- Index build: `statement_timeout` 0, `maintenance_work_mem` 512MB, under 50 seconds, `EXIT=0`, valid with the expected definition, 224 MB, `indisvalid` true. S1 before the build: 21 connections, no long transactions.
- Committed as `e113f0407` with the reply-pass shard JSONs.

## Task 3: D-15 refit, prod calibration, owner decision

- Features pull: `rows 291; pv_source: db 280, db_none 11; cache mismatches 0; rows with a NULL score input 11; rows with a NULL best line 5`, `missing: 10`. The file is byte-identical to `facepalm-features-2026-11-21.tsv`.
- Fit (`reports/blunder-check/facepalm-fit-2026-11-22.md`): 268 usable rows (139 fair, 129 unfair). CV AUC 0.909, mean 0.908 over 5 seeds with spread 0.006; in-sample 0.919. Shipped baseline on today's lines 0.897; the difference 0.012 is within the 0.02 range. Set 8 hold-out AUC 0.838.
- Constants: unchanged from the code, so nothing was pasted; `git diff --quiet -- app/services/blunder_check_rules.py` exits 0.
- Fair / unfair among label passers: 0.50 118 / 25; 0.55 116 / 21; 0.60 109 / 18; 0.65 105 / 17; 0.70 98 / 11.
- Prod calibration (`--sample-permille 25`, 27,313 game ids, 59,482 user blunders, 9000 Good moves scored): 93.4% of user blunders scored; pass of all at 0.50 44.7%, 0.60 38.9%, 0.70 32.9%, 0.80 26.6%. Median usable windows per user 562.7 / 489.8 / 413.9 / 331.7 at those cuts; p25 152.5 / 133.4 / 112.9 / 89.8. At 0.50, 68 of 601 users are under 50 windows.
- Fixture scores under the confirmed constants: D-13 row (game 2883555 ply 47) 0.825; Window 14 (game 2099808 ply 23) 0.091; owner fixtures 817357 ply 24 0.0654 and 820181 ply 65 0.1389.
- Reports committed as `6e4fbd424`.

### Owner decision

- **Option, verbatim:** "new-cuts: other values", followed by "FACEPALM_SCORE_MIN=0.7, FACEPALM_STATS_MIN=0.7".
- **Date:** 2026-11-22.
- **Values:** `FACEPALM_SCORE_MIN = 0.7` (was 0.5), `FACEPALM_STATS_MIN = 0.7` (unchanged).
- **Consequences for plan 12:** paste nothing new for the six coefficients (already in the code); change `FACEPALM_SCORE_MIN` to 0.7 and re-pin every test and copy that names the drill cut; `FACEPALM_HIGH_CUTOFF` stays 70. At 0.70 the label passers are 98 fair / 11 unfair (90% fair), the prod drill pool is about 33% of user blunders (median 414 windows per user), and more users fall under 50 own windows than the 68 of 601 measured at 0.50 (not re-rendered at 0.70). Window 14 and both owner fixtures stay below the cut; the D-13 row stays above it.

## Task Commits

1. **Task 2: readiness report and reply shard reports** - `e113f0407` (docs)
2. **Task 3: refit and prod calibration reports** - `6e4fbd424` (docs)

## Deviations from Plan

- **Feeder running.** Map rule 6 wants no other operator job during the index build, the pull and the calibration. The Phase 252 feeder was running; the owner approved proceeding beside it.
- **No paste and restore.** The fit reproduced the constants already in the code, so step 3's working-tree paste and `git restore` were not needed.
- **Fixture scoring.** The D-13 row and Window 14 scores are read from the fit report's extra rows; the owner fixtures were scored through `facepalm_score` from `tests/services/facepalm_owner_fixtures.py`.
- Task 1 ran inline in the orchestrator rather than in an executor.

## Issues Encountered

- The reply pass log showed stamped counts falling behind processed counts by about 0.9%. The totals line explains it: `games_already_stamped=10140`, games the live hook or the feeder had stamped first. No pending games remain.

## Known Stubs

None.

## Threat Flags

None. T-259-26: gate held before any switch. T-259-27: build ran with one session, 21 connections, no long transactions, beside one feeder with owner approval. T-259-28: `blunder_check_rules.py` was never modified.

## Next Phase Readiness

Plan 12 can ship the switch: prod holds every input and the index, and the cuts are decided.

## Self-Check: PASSED
