---
phase: quick-260414-ae4
plan: 01
subsystem: endgame-analytics
tags: [backend, frontend, tests, endgames, threshold]
requires: []
provides:
  - "ENDGAME_PLY_THRESHOLD applied uniformly to the binary 'has endgame' split"
affects:
  - app/repositories/endgame_repository.py
  - app/services/endgame_service.py
  - tests/test_endgame_repository.py
  - frontend/src/components/charts/EndgamePerformanceSection.tsx
  - frontend/src/components/charts/EndgameTimePressureSection.tsx
  - frontend/src/pages/Endgames.tsx
tech-stack:
  added: []
  patterns:
    - "Single source of truth for ply thresholds via named constant reuse"
key-files:
  created: []
  modified:
    - app/repositories/endgame_repository.py
    - app/services/endgame_service.py
    - tests/test_endgame_repository.py
    - frontend/src/components/charts/EndgamePerformanceSection.tsx
    - frontend/src/components/charts/EndgameTimePressureSection.tsx
    - frontend/src/pages/Endgames.tsx
decisions:
  - "Preserve invariant sum(material_rows.games) == endgame_wdl.total by applying the same 6-ply HAVING on both sides of the split (symmetric construction) rather than the previous Phase 59 carve-out (asymmetric — bucket query had no HAVING)"
  - "Short-endgame games (<6 plies in any endgame class) are now classified as 'no endgame' consistently across every analysis on the endgames tab"
metrics:
  duration: "~25 min"
  completed: "2026-04-14"
  tasks: 2
  files_touched: 5
---

# Quick Task 260414-ae4: Apply 6-ply Endgame Threshold Uniformly

Applied `ENDGAME_PLY_THRESHOLD = 6` uniformly across every analysis on the endgames tab (WDL bars, material buckets, score gap, timelines, clock stats, binary split) so one semantic definition of "game reached an endgame phase" governs the whole page.

## What changed

### Backend — `app/repositories/endgame_repository.py`

- `_any_endgame_ply_subquery(user_id)` now applies `HAVING count(ply) >= ENDGAME_PLY_THRESHOLD` on its `GROUP BY game_id`. It is the single source of truth for the binary "has endgame" split consumed by `count_endgame_games` and `query_endgame_performance_rows`. Docstring rewritten to state the semantic and to flag that total plies are summed across classes (3 plies in KP_KP + 3 in KR_KR = 6 → qualifies).
- `query_endgame_bucket_rows` applies the same HAVING on its per-game `entry_subq`. The Phase 59 "~11% carve-out" rationale is removed; the invariant `sum(material_rows.games) == endgame_wdl.total` is now preserved by symmetric construction instead of by weakening the filter.
- `count_endgame_games` and `query_endgame_performance_rows` docstrings rewritten to reference the uniform rule and remove "no ply threshold" language.
- `query_endgame_entry_rows`, `query_endgame_games`, `query_endgame_timeline_rows`, `query_clock_stats_rows` unchanged — already enforced the threshold per-class.

### Backend — `app/services/endgame_service.py`

- Two inline comment blocks updated (one in `get_endgame_stats`, one in `get_endgame_overview`) to reference the uniform rule per quick-260414-ae4 and remove stale "no ply threshold" / "~11%" language.
- `_compute_score_gap_material` docstring updated: the invariant is now preserved because both `endgame_wdl` and `entry_rows` come from queries with the same HAVING, not because the bucket query deliberately omits it.

### Tests — `tests/test_endgame_repository.py`

- `TestQueryEndgameBucketRows`:
  - `test_short_endgame_still_counted_as_even` → renamed to `test_short_endgame_is_excluded`; now asserts `rows == []` (old behavior: 1 row with NULL imbalance_after).
  - `test_long_endgame_returns_imbalance_after` / `test_black_user_sign_flip`: fixtures bumped from `PERSISTENCE_PLIES + 1` (5) to `ENDGAME_PLY_THRESHOLD` (6) plies so the games qualify under the uniform rule.
  - `test_invariant_matches_performance_rows_count`: game_b (2 endgame plies) is now routed to `non_endgame_rows` on both queries → `len(bucket_rows) == len(endgame_rows) == 1`, `len(non_endgame_rows) == 2`, and entry_game_ids == bucket_game_ids (consistent).
  - `test_time_control_filter`: endgame seed bumped to `ENDGAME_PLY_THRESHOLD` plies.
  - **New test** `test_binary_endgame_split_uses_6ply_threshold` — game A at exactly 6 plies qualifies, game B at 5 plies does not; asserts presence/absence across bucket_rows, endgame_rows, non_endgame_rows.

### Frontend

- `EndgamePerformanceSection.tsx` — `InfoPopover` for "Games with vs without Endgame" now includes: "Only endgames that span at least 6 plies (3 moves) are counted — shorter tactical endgame transitions are treated as 'no endgame'."
- `EndgameTimePressureSection.tsx` — `InfoPopover` for "Time Pressure vs Performance" now includes: "Only endgames that span at least 6 plies (3 moves) are included." The underlying query (`query_clock_stats_rows`) already enforced the threshold per-class; this change makes the rule visible to users for consistency with the new performance-section copy.
- `Endgames.tsx` — the "Endgame phase" paragraph in the "Endgame statistics concepts" accordion now states the 3-move / 6-ply minimum for a game to be counted as having an endgame phase (follow-up requested mid-execution).

## Deviations from Plan

None — plan executed as written.

Two pre-existing ruff F841 warnings in `app/services/endgame_service.py` (lines 913 `game_id` and 916 `termination`, introduced in Phase 55 commit `0a21775e`) are documented in `deferred-items.md`. They are unrelated to this task's threshold change and were present on `main` before the task started.

## Verification

- `uv run pytest` — 699 passed (incl. all `test_endgame_repository.py`, `test_endgame_service.py`, `test_endgames_router.py`).
- `uv run ty check app/ tests/` — all checks passed.
- `cd frontend && npm run lint` — clean.
- `cd frontend && npm test -- --run` — 73 passed across 5 test files.
- Manual sanity checklist (plan verification section):
  - Backend invariant: both `_any_endgame_ply_subquery` (feeding the binary split) and `query_endgame_bucket_rows` apply the same `HAVING count(ply) >= ENDGAME_PLY_THRESHOLD` → `sum(material_rows.games) == endgame_wdl.total` holds by construction.
  - No magic `6` introduced in production code — every new HAVING references `ENDGAME_PLY_THRESHOLD`.
  - Popover copy on both "Games with vs without Endgame" and "Time Pressure vs Performance" mentions the 6-ply / 3-move rule.
  - Live data sanity (browser check vs a real user's games) is recommended post-deploy but not run here — the query-level change is covered by the new invariant test.

## Commits

- `35120d4` refactor(quick-260414-ae4): apply ENDGAME_PLY_THRESHOLD uniformly to binary endgame split
- `9f5d9da` test(quick-260414-ae4): align bucket_rows tests with uniform 6-ply rule + popover copy
- `0b50fe1` docs(quick-260414-ae4): state 6-ply rule in Endgame phase concepts

## Self-Check: PASSED

- [x] `app/repositories/endgame_repository.py` modified — FOUND
- [x] `app/services/endgame_service.py` modified — FOUND
- [x] `tests/test_endgame_repository.py` modified — FOUND
- [x] `frontend/src/components/charts/EndgamePerformanceSection.tsx` modified — FOUND
- [x] `frontend/src/components/charts/EndgameTimePressureSection.tsx` modified — FOUND
- [x] Commit `35120d4` — FOUND in git log
- [x] Commit `9f5d9da` — FOUND in git log
