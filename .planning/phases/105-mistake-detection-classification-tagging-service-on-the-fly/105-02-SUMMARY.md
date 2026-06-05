---
phase: 105-mistake-detection-classification-tagging-service-on-the-fly
plan: "02"
subsystem: backend-service
tags: [mistakes, attribution-tags, tempo, miss, unpunished, repository, oracle, unit-tests, integration-tests]
dependency_graph:
  requires:
    - plan 01: FlawRecord, FlawTag, TempoTag, classify_game_mistakes, _run_all_moves_pass
  provides:
    - app.services.mistakes_service (_classify_tempo, _move_time, _is_miss, _is_unpunished, _is_result_changing, _phase_tag, _build_tags — all wired into classify_game_mistakes)
    - app.repositories.mistakes_repository (fetch_game_positions_ordered)
    - tests.test_mistakes_repository (TestFetchGamePositionsOrdered — DB-backed)
    - tests.services.test_mistakes_service (TestTempoTags, TestAttributionTags, TestOracleCloseness)
  affects:
    - plan 03+: Games/Flaws router consumes fully-tagged FlawRecord list via fetch_game_positions_ordered
    - SQL window-scan (future): _run_all_moves_pass tag functions reusable for cross-game filter
tech_stack:
  added: []
  patterns:
    - Relative-to-base-clock tempo thresholds with absolute fallback (tunable on-the-fly)
    - Single-boundary result-changing per actual game outcome (win/draw/loss)
    - All-moves pass adjacency check for miss/unpunished (both players classified)
    - Repository ownership guard via WHERE user_id predicate (STRIDE T-105-03 mitigation)
    - Oracle-closeness test: abs(derived - oracle) <= SANITY_TOLERANCE (not equality)
key_files:
  created:
    - app/repositories/mistakes_repository.py
    - tests/test_mistakes_repository.py
  modified:
    - app/services/mistakes_service.py
    - tests/services/test_mistakes_service.py
decisions:
  - "_classify_tempo defaults to knowledge-gap when clock data missing — conservative, noise-free label"
  - "_is_unpunished restricted to blunders only (not mistakes/inaccuracies) per RESEARCH Pitfall 6"
  - "result-changing uses single boundary per outcome: win=>WIN_THRESHOLD, draw/loss=>DRAW_THRESHOLD"
  - "increment resolved from game.increment_seconds first, falls back to parse_base_and_increment(tc_str)"
  - "derive_user_result and parse_base_and_increment imported and reused (not re-implemented)"
metrics:
  duration: "~10 minutes"
  completed: "2026-06-05T14:22:00Z"
  tasks_completed: 2
  files_created: 2
  files_modified: 2
---

# Phase 105 Plan 02: Attribution Tags + Repository + Oracle Closeness

Completed the mistake-detection service by adding all eight attribution tags to every emitted FlawRecord, creating the repository read helper, and adding the DB-backed repository test plus oracle-closeness sanity test.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 (RED) | Failing tests for attribution tags, tempo, oracle | 8aab8db1 | tests/services/test_mistakes_service.py |
| 1 (GREEN) | Attribution tag helpers wired into classify_game_mistakes | 387db2f4 | app/services/mistakes_service.py, tests/services/test_mistakes_service.py |
| 2 | Repository + DB-backed tests + oracle closeness | 71e61d1c | app/repositories/mistakes_repository.py, tests/test_mistakes_repository.py |

## What Was Built

### `app/services/mistakes_service.py` additions (new helpers):

- **`_move_time(positions, n, increment) -> float | None`**: same-side clock two plies back + increment; returns None for first moves (n < 2) or missing clock.
- **`_classify_tempo(move_time, clock_after, base_time) -> TempoTag`**: LOCKED tempo dimension (exactly one of time-pressure/hasty/knowledge-gap per flaw). Relative-to-base-clock thresholds when available; absolute fallback. Returns knowledge-gap on missing data.
- **`_is_miss(n, all_moves) -> bool`**: opponent's move at N-1 was mistake/blunder (requires all-moves pass).
- **`_is_unpunished(n, all_moves, severity) -> bool`**: user blunder (severity=="blunder" only) where opponent at N+1 was not mistake/blunder. End-of-game counts as unpunished.
- **`_is_result_changing(es_before, es_after, user_result) -> bool`**: one boundary per actual outcome (win=>RESULT_WIN_THRESHOLD 0.70, draw/loss=>RESULT_DRAW_THRESHOLD 0.40).
- **`_phase_tag(phase) -> FlawTag`**: maps GamePosition.phase 0/1/2 to phase-opening/middlegame/endgame; defaults to phase-middlegame for null.
- **`_build_tags(...)` aggregator**: assembles ordered tags list (from-winning, result-changing, miss, unpunished, phase-*, tempo). Wired into `classify_game_mistakes` — every emitted FlawRecord now carries all applicable tags.
- Two new imports: `derive_user_result` from `openings_service`, `parse_base_and_increment` from `normalization`.

### `app/repositories/mistakes_repository.py` (35 lines):

- `fetch_game_positions_ordered(session, game_id, user_id) -> list[GamePosition]`
- `select(GamePosition).where(game_id, user_id).order_by(GamePosition.ply)` — SQLAlchemy 2.x API
- `user_id` WHERE predicate = ownership guard (T-105-03 mitigation)
- `list(result.scalars().all())` — standard project pattern

### Test additions:

**`tests/services/test_mistakes_service.py`** (3 new test classes, ~450 lines added):
- `TestTempoTags` (8 tests): time-pressure, hasty, knowledge-gap classification; abs fallback; tempo exclusivity in classify_game_mistakes
- `TestAttributionTags` (10 tests): from-winning, miss, no-miss, unpunished-on-blunder, no-unpunished-on-mistake, result-changing, no-result-changing, phase-opening/middlegame/endgame
- `TestOracleCloseness` (2 tests): white and black derived B/M/I counts within SANITY_TOLERANCE of synthetic oracle

**`tests/test_mistakes_repository.py`** (3 DB-backed tests):
- `TestFetchGamePositionsOrdered::test_returns_empty_for_unknown_game`
- `TestFetchGamePositionsOrdered::test_positions_sorted_by_ply_asc`
- `TestFetchGamePositionsOrdered::test_ownership_guard_different_user_returns_empty`

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Two test fixture bugs found during RED→GREEN iteration**

- **Found during:** Task 1 GREEN phase
- **Issue 1:** `test_no_miss_tag_when_preceding_opponent_not_error` used `eval_cp=400` at positions[3] as "neutral" for black, but eval +400 for white at positions[3] means black dropped ~0.22 ES (a blunder) — the opposite of "no error". Test description contradicted the fixture.
- **Fix 1:** Changed positions[2] and positions[3] to both use `eval_cp=20` so black's drop is near zero (no error classified).
- **Issue 2:** `test_unpunished_tag_on_blunder_when_opponent_does_not_recover` expected `unpunished` when opponent also blunders (severity="blunder"), but `_is_unpunished` returns True only when opponent is NOT mistake/blunder (opponent failing to capitalize = fine move, not a blunder). Test semantics were inverted relative to the spec.
- **Fix 2:** Changed opponent's ply-5 to use `eval_cp=-380` (tiny change = fine move), so `_is_unpunished` correctly returns True.
- **Files modified:** tests/services/test_mistakes_service.py
- **Commit:** 387db2f4

## Acceptance Criteria Verification

- `RESULT_WIN_THRESHOLD: float = 0.70`, `RESULT_DRAW_THRESHOLD: float = 0.40`, `TIME_PRESSURE_CLOCK_FRACTION: float = 0.05`, `HASTY_MOVE_FRACTION: float = 0.01`, `TIME_PRESSURE_CLOCK_ABS_SECONDS: float = 30.0`, `HASTY_MOVE_ABS_SECONDS: float = 5.0`, `SANITY_TOLERANCE: int = 2` — all present at exact values.
- Every emitted FlawRecord has exactly one tempo tag (tested by `TestTempoTags::test_exactly_one_tempo_tag_per_flaw_in_classify_game`).
- `_is_unpunished` returns False for non-blunder severities (tested by `test_no_unpunished_tag_on_non_blunder`).
- `derive_user_result` and `parse_base_and_increment` are imported from existing project utilities.
- `app/repositories/mistakes_repository.py` uses `select(GamePosition)...order_by(GamePosition.ply)` and `list(result.scalars().all())`; no `session.query`.
- `TestFetchGamePositionsOrdered` proves ply-ASC ordering, empty-on-unknown-game, and user_id ownership guard.
- `TestOracleCloseness` asserts `abs(derived - oracle) <= SANITY_TOLERANCE` per color per severity.
- 2294/2294 tests pass (full suite with `-n auto`).
- `ty check app/ tests/` — zero errors.
- `ruff check app/ tests/` + `ruff format --check app/ tests/` — clean.

## Known Stubs

None. All tag fields are fully populated. The service is complete for phase 105 scope — no UI, no endpoint wiring (deferred to later phases per CONTEXT.md §Deferred).

## Threat Flags

No new trust boundary surfaces introduced beyond T-105-03/04 documented in the plan's threat model. The repository's `user_id` WHERE clause is the only new security-relevant pattern, and it is tested.

## Self-Check: PASSED
