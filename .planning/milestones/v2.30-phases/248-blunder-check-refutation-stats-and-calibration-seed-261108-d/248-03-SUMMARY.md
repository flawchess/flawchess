---
phase: 248-blunder-check-refutation-stats-and-calibration-seed-261108-d
plan: 03
subsystem: database
tags: [maia, backfill, game_flaws, refutation, sharding]
status: complete

requires:
  - phase: 248-01
    provides: refutation scorer, GameMaiaScore.user_blunders/refutations_from_pv, both stamps, repository helpers
provides:
  - "scripts/backfill_maia_flaws.py --mode {full,refutation}: the only catch-up path for the refutation pair"
  - "ScoringMode, score_game(inputs, boards, mode), mode-aware write_game_maia_scores"
  - "fetch_status(..., mode) refutation counts; per-mode shard reports with refutation counters"
affects: [248-07 prod backfill, 248 ship docs (docs/dev-tooling.md, plan 06)]

actuals:
  tokens: 40000
  tasks: 2
  commits: 2
plan_head_before: 59a25bbe8
plan_head_after: 9759a5c87

tech-stack:
  added: []
  patterns:
    - "Mode selects one of two constant selector predicates (no user input in SQL)"
    - "Refutation-mode rows carry only PK + the two refutation keys, so the base values are left untouched by omission"
    - "Shared _flaw_context guard (ply_beyond_mainline / fen_mismatch / no_rating) feeds both modes"

key-files:
  created: []
  modified:
    - app/services/maia_flaw_scoring.py
    - scripts/backfill_maia_flaws.py
    - tests/scripts/test_backfill_maia_flaws.py
    - tests/services/test_maia_flaw_scoring.py

key-decisions:
  - "GameMaiaScore.mode (default full) rides on the score; write_game_maia_scores derives stamp column, stamps and key set from it and raises ValueError on a mixed batch"
  - "Full mode keeps the 247 status line unchanged (monitor depends on it); refutation status is opt-in via --status --mode refutation"
  - "Added refutations_per_s to the shard report and refutations/s to the progress line (pace input for plan 07)"

requirements-completed: [D-03, D-05, D-09, D-10, D-22]

coverage:
  - id: D1
    description: "--mode refutation selects base-stamped, refutation-unstamped games with flaws (md5-residue sharded); full mode keeps the 247 selector"
    requirement: "D-10"
    verification:
      - kind: unit
        ref: "tests/scripts/test_backfill_maia_flaws.py#test_refutation_mode_selector_needs_base_stamp_and_no_refutation_stamp"
        status: pass
      - kind: unit
        ref: "tests/scripts/test_backfill_maia_flaws.py#test_refutation_mode_shard_partition_disjoint_exhaustive"
        status: pass
    human_judgment: false
  - id: D2
    description: "Refutation mode writes only the pair on user-side blunders plus the refutation stamp; base values, out-of-scope rows and the base stamp untouched"
    requirement: "D-10"
    verification:
      - kind: unit
        ref: "tests/scripts/test_backfill_maia_flaws.py#test_refutation_mode_scores_and_stamps_only_the_pair"
        status: pass
    human_judgment: false
  - id: D3
    description: "A game with flaws but no user-side blunder is stamped with no replay and no inference; rerun selects zero; replay covers only blunder plies"
    requirement: "D-09"
    verification:
      - kind: unit
        ref: "tests/scripts/test_backfill_maia_flaws.py#test_refutation_mode_game_without_user_blunder_stamped_without_replay_or_inference"
        status: pass
      - kind: unit
        ref: "tests/scripts/test_backfill_maia_flaws.py#test_refutation_mode_rerun_selects_nothing_and_changes_nothing"
        status: pass
      - kind: unit
        ref: "tests/scripts/test_backfill_maia_flaws.py#test_refutation_mode_replays_only_blunder_plies"
        status: pass
    human_judgment: false
  - id: D4
    description: "require_unstamped checks the mode's own stamp; mixed-mode batch rejected; full mode default writes pair and both stamps"
    requirement: "D-10"
    verification:
      - kind: unit
        ref: "tests/scripts/test_backfill_maia_flaws.py#test_refutation_mode_skips_game_refutation_stamped_mid_run"
        status: pass
      - kind: unit
        ref: "tests/services/test_maia_flaw_scoring.py#test_write_rejects_batch_mixing_full_and_refutation_scores"
        status: pass
      - kind: unit
        ref: "tests/scripts/test_backfill_maia_flaws.py#test_full_mode_default_writes_pair_and_both_stamps"
        status: pass
    human_judgment: false
  - id: D5
    description: "--status --mode refutation prints the four refutation counts from SELECT-only queries using is_opponent_expr"
    requirement: "D-03"
    verification:
      - kind: unit
        ref: "tests/scripts/test_backfill_maia_flaws.py#test_refutation_status_counts"
        status: pass
      - kind: integration
        ref: "dev smoke: scripts/backfill_maia_flaws.py --db dev --status --mode refutation --user-id 28"
        status: pass
    human_judgment: false
---

# Phase 248 Plan 03: Refutation-only backfill mode Summary

**`scripts/backfill_maia_flaws.py --mode refutation` scores only user-side blunders of base-stamped games (about one inference each) and writes the refutation pair plus its own stamp; the 247 full mode now writes all ten values and both stamps.**

## Accomplishments

- Scorer: `ScoringMode`, `GameMaiaScore.mode`, `score_game(inputs, boards, mode)`. Refutation mode filters to user-side blunders, replays only those plies (D-05), emits rows with PK plus the two refutation keys only, and does no replay or inference when the game has none (D-09). A shared `_flaw_context` carries the board/fen/rating guards for both modes.
- Write: `write_game_maia_scores` reads the mode from the scores (ValueError on a mixed batch), checks `maia_refutation_completed_at` for `require_unstamped` in refutation mode, and stamps only the refutation column there (both in full mode).
- Backfill script: `BackfillMode`, `BACKFILL_MODE_CHOICES`, `DEFAULT_MODE`, `--mode`; selector predicate swapped via two module constants; mode threaded through `select_shard_game_ids`, `run_shard`, `_process_batch`, `_score_batch`; `ShardReport` gained `mode`, `refutations_scored/_null/_from_pv`, `refutations_per_s`; reports named `{db}-{mode}-{run_stamp}-shard{n}.json` (writer and reader); the total line sums the new counters.
- Status: `fetch_status(..., mode)`; refutation mode returns `refutation_stamped_games`, `refutation_unstamped_games_with_flaws`, `user_blunders_with_refutation`, `user_blunders_total` (Core selects with `not_(is_opponent_expr(...))`, no inline parity). Without `--mode` the 247 line is unchanged.

## Task Commits

1. **Task 1 (tracer): scorer mode, selector, write, report** - `934952a2e`
2. **Task 2: selector/idempotence/race/no-blunder/status tests + mixed-mode write test** - `9759a5c87`

The tracer feedback gate (auto-verified, automated-only verify): `pytest -k refutation_mode` green and the full 247 backfill suite green before the second task.

## Mutation Proofs (each reverted; files equal the commit afterwards)

- (a) Dropped `maia_flaws_completed_at IS NOT NULL` from the refutation selector: `test_refutation_mode_selector_needs_base_stamp_and_no_refutation_stamp` and `test_refutation_status_counts` failed.
- (b) `require_unstamped` stamp read always the base stamp: `test_refutation_mode_skips_game_refutation_stamped_mid_run` failed (plus `..._scores_and_stamps_only_the_pair`, `..._rerun_selects_nothing...`, `..._without_user_blunder_stamped...`, `test_refutation_status_counts`, since base-stamped games read as already stamped).
- (c) Eight base keys (`null_maia_stats()`) added to refutation-mode rows: `test_refutation_mode_scores_and_stamps_only_the_pair` failed (the untouched-base assertion).

## Dev Smoke (`--db dev`, user 28, 1 worker, dev CPU shared with the 247-07 backfill)

| Run | Exit | Total line (abridged) |
| --- | --- | --- |
| `--mode refutation --limit 200` | 0 | games_selected=200 games_stamped=200 refutations_scored=240 refutations_null=145 reason_refutation_missing=145, 41.6 s wall, about 6.4 refutations/s (240 inferences + 200 game loads) |
| `--status --mode refutation` after | 0 | refutation_stamped_games=200 refutation_unstamped_games_with_flaws=60 user_blunders_with_refutation=240 user_blunders_total=5396 |
| `--mode full --limit 20` | 0 | games_stamped=20 flaws_scored=98 refutations_scored=30, 20 s; status: base stamped 260 -> 280, refutation stamped 200 -> 220 (both advance) |
| `--mode refutation --limit 200` (remaining) | 0 | games_selected=60 games_stamped=60 refutations_scored=98 refutations_null=1 |
| `--mode refutation --limit 200` (rerun) | 0 | games_selected=0 (idempotent); status refutation_unstamped_games_with_flaws=0, user_blunders_with_refutation=368 of 5396 |

Pace note for plan 07: refutation mode did about 6.4 scored refutations per second per process on a loaded box (full mode: 6.4 flaws/s, 2.0 refutations/s there because every flaw also runs its base inference). Dev coverage caveat: in the first 200 games 145 of 385 user blunders (38%) had a row at ply+1 with neither `best_move` nor `pv` (all `refutation_missing`, none missing the row itself); these dev games are not fully evaluated, so prod's null share must be measured before quoting coverage. `refutations_from_pv` was 0 on dev.

## Verification

- `uv run pytest tests/scripts/test_backfill_maia_flaws.py tests/services/test_maia_flaw_scoring.py`: 73 passed.
- Full backend suite (`pytest -n 8`, excluding plan 04's in-flight calibration test module): 5834 passed, 20 skipped.
- `ruff check`, `ruff format --check` on the touched files, `ty check app/ tests/ scripts/backfill_maia_flaws.py`, `check_function_size.py app/ --fail-over-depth 4`: clean.

## Deviations from Plan

None - plan executed as written. Two small additions inside scope: `refutations_per_s` in the report (the plan asks for the pace in the SUMMARY) and one extra dev run to drain the remaining 60 games and show idempotence.

## Known Stubs

None.

## Threat Flags

None. T-248-06: the mode only selects one of two constant predicate strings (`_STAMP_CLAUSE_BY_MODE`); user id, shard and limit stay bound. T-248-07: `require_unstamped` uses the mode's own stamp (mutation proofs a-c). T-248-05: smokes used `--db dev` only.

## Self-Check: PASSED

- `934952a2e` and `9759a5c87` are ancestors of HEAD; the four modified files exist; reports under `temp/maia-refutation-backfill/` (gitignored).
