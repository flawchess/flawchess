---
phase: 60-opponent-based-baseline-for-endgame-conversion-recovery
plan: 01
subsystem: endgame-analytics
tags: [backend, endgame, baseline, schema, tests]
requires:
  - Phase 59 bucket accounting (conversion-over-recovery tiebreak, NULL→Even routing, group-then-pick dedupe)
provides:
  - MaterialRow.opponent_score (float | None) and MaterialRow.opponent_games (int)
  - _MIN_OPPONENT_SAMPLE = 10 constant in app/services/endgame_service.py
  - Same-game symmetry math in _compute_score_gap_material
affects:
  - /api/endgames/overview response: drops ScoreGapMaterialResponse.overall_score; each material row carries new opponent_* fields
  - frontend plan 60-02 (EndgameScoreGapSection + types/endgames.ts must mirror)
tech_stack_added: []
patterns:
  - Arithmetic-identity opponent baseline: opp_score = 1 - user_score in the mirror (swap) bucket
  - Muting threshold gating: opponent_score=None when swap-bucket sample < _MIN_OPPONENT_SAMPLE
key_files_created:
  - .planning/phases/60-opponent-based-baseline-for-endgame-conversion-recovery/60-01-SUMMARY.md
  - .planning/phases/60-opponent-based-baseline-for-endgame-conversion-recovery/deferred-items.md
key_files_modified:
  - app/schemas/endgames.py
  - app/services/endgame_service.py
  - tests/test_endgame_service.py
  - tests/test_endgames_router.py
decisions:
  - Drop overall_score entirely (not deprecate) — grep confirmed the only backend consumer was the display path being replaced, and the frontend mirror will drop in plan 60-02.
  - Use same-game symmetry (opp_score = 1 - user_score[swap]) instead of a second SQL query — zero new queries, filter-respecting by construction.
  - Threshold = 10 games (matches WDL-bar mute threshold elsewhere in the app); opponent_games always reports the real count so the frontend can render "n < 10" captions.
metrics:
  duration: ~15 minutes
  completed: 2026-04-13
  tasks: 2
  files_modified: 4
  files_created: 2
  tests_added: 6 (TestScoreGapMaterialOpponentBaseline class)
  tests_deleted: 1 (test_score_gap_material_overall_score_weighted)
---

# Phase 60 Plan 01: Backend opponent baseline in Endgame Conversion & Recovery — Summary

Replaced the global-average baseline in `_compute_score_gap_material` with a self-calibrating opponent baseline derived from the same filtered game set, and removed the now-unused `overall_score` from the response. Pure read-path arithmetic — zero new SQL, zero new queries, zero migrations.

## What Changed

### Schema (`app/schemas/endgames.py`)

- `MaterialRow` gained two fields:
  - `opponent_score: float | None` — mirror-bucket score `1 - user_score[swap_bucket]`, or `None` when the swap-bucket sample is below the 10-game threshold.
  - `opponent_games: int` — opponent's sample size (= swap-bucket game count), always reported.
- `ScoreGapMaterialResponse`:
  - Removed `overall_score` field and its docstring line.
  - Appended a Phase 60 note to the class docstring explaining the new fields and the removal rationale.

### Service (`app/services/endgame_service.py`)

- Added module-level constant `_MIN_OPPONENT_SAMPLE = 10` next to `_MATERIAL_ADVANTAGE_THRESHOLD = 100`.
- Deleted the `combined_wins/draws/total -> overall_score` block in `_compute_score_gap_material` (was only consumed by the old global-average baseline display).
- Refactored the `material_rows` build from one pass into two:
  1. First pass computes per-bucket user score and stores it in `bucket_score` / `bucket_pct` dicts.
  2. Second pass builds each `MaterialRow`, computing `opponent_score = 1.0 - bucket_score[swap[b]]` when `bucket_games[swap[b]] >= _MIN_OPPONENT_SAMPLE`, else `None`. `opponent_games = bucket_games[swap[b]]` always.
- Swap mapping: `{"conversion": "recovery", "even": "even", "recovery": "conversion"}`.
- Return statement dropped the `overall_score=` kwarg.
- Phase 59 bucket accounting (conversion-over-recovery tiebreak, NULL→Even routing, group-then-pick dedupe) is untouched — `bucket_games` / `bucket_wins` / `bucket_draws` / `bucket_losses` accumulation is unchanged.

### Tests

**`tests/test_endgame_service.py`:**
- Deleted `test_score_gap_material_overall_score_weighted` (field no longer exists).
- Added `TestScoreGapMaterialOpponentBaseline(TestScoreGapMaterial)` class with 6 methods:
  - `test_opponent_baseline_symmetric_60_40` — user Conv 60% / Recov 40% over 100 games each; asserts Conv.opponent_score ≈ 0.60 and Rec.opponent_score ≈ 0.40.
  - `test_opponent_baseline_empty_swap_bucket` — user Conv has games, Recov has zero; asserts Conv.opponent_score is None, opponent_games == 0.
  - `test_opponent_baseline_below_threshold_9_games` — swap bucket has 9 games (< 10); asserts None baseline, opponent_games == 9.
  - `test_opponent_baseline_at_threshold_10_games` — swap bucket has 10 games (≥ 10); asserts baseline is computed, opponent_games == 10.
  - `test_opponent_baseline_even_self_mirror` — Even bucket with 10 games at 50% score; opponent_score ≈ 0.5.
  - `test_opponent_baseline_even_below_threshold` — Even with 1 game; opponent_score is None.

**`tests/test_endgames_router.py`:**
- Changed `assert "overall_score" in sgm` → `assert "overall_score" not in sgm`.
- Appended a loop asserting every `material_rows[i]` has `opponent_score` (None or 0.0-1.0 float) and `opponent_games` (int ≥ 0).

## Verification

| Gate                                                                  | Result                                                |
| --------------------------------------------------------------------- | ----------------------------------------------------- |
| `uv run pytest tests/test_endgame_service.py tests/test_endgames_router.py` | 155 passed                                            |
| `uv run ty check app/ tests/`                                         | All checks passed                                     |
| TestScoreGapMaterialInvariant (Phase 59)                              | Still green — no regression                           |
| grep `overall_score` in app/ or tests/                                | 0 (outside docstring reference explaining removal)    |

## Deviations from Plan

**None for the primary tasks.** One minor adjustment during execution:

1. **[Rule 3 - Blocking]** Initial ty-ignore comments on the `MaterialBucket` reassignment turned out to be unnecessary — `ty` accepts the plain `b: MaterialBucket = bucket_key` form for a Literal-typed tuple of literal strings. Removed the unused suppression comments to silence ty's `unused-ignore-comment` warning.

2. **Ruff auto-reformat** wrapped the `opponent_score: float | None` annotation onto multiple lines because the inline comment pushed past the line-length limit. Rewrote the comment as a leading `#` line so the annotation stays on one line (matches the surrounding style and the grep-based acceptance criterion).

## Deferred Issues

See `deferred-items.md` — two pre-existing `ruff F841` errors in `_compute_clock_pressure` (lines 892, 895: `game_id`, `termination`). Confirmed pre-existing via a `git stash` check; not in Phase 60 scope. Would be a one-line `_` prefix fix in a future cleanup.

## Known Stubs

None.

## Commits

- `28586b5` test(60-01): add opponent-baseline tests and drop overall_score assertions (RED)
- `efcc079` feat(60-01): opponent baseline via same-game symmetry (GREEN)

## Handoff to Plan 60-02

Backend is ready for frontend consumption. Plan 60-02 needs to:

1. Mirror the schema in `frontend/src/types/endgames.ts` (drop `overall_score`, add `opponent_score: number | null` and `opponent_games: number` on `MaterialRow`).
2. Rewrite `EndgameScoreGapSection.tsx` bullet chart to compare `row.score` vs `row.opponent_score` per row; handle `null` baseline with a muted `n < 10` caption.
3. Collapse `NEUTRAL_ZONES` into a single symmetric zone around zero (`±0.03` start, widen to `±0.05` if visually cramped).
4. Update info popover + per-row diff label copy per CONTEXT decision #3.
5. Apply changes to both desktop table and mobile cards (CLAUDE.md mobile rule).

## Self-Check: PASSED

- `.planning/phases/60-opponent-based-baseline-for-endgame-conversion-recovery/60-01-SUMMARY.md` — FOUND
- `.planning/phases/60-opponent-based-baseline-for-endgame-conversion-recovery/deferred-items.md` — FOUND
- Commit `28586b5` — FOUND
- Commit `efcc079` — FOUND
- `_MIN_OPPONENT_SAMPLE = 10` in app/services/endgame_service.py — FOUND
- `opponent_score: float | None` in app/schemas/endgames.py — FOUND
- `opponent_games: int` in app/schemas/endgames.py — FOUND
- 0 `overall_score` references in app/ or tests/ (outside docstring note) — VERIFIED
- 155 endgame + router tests passing — VERIFIED
- ty check clean — VERIFIED
