---
phase: 109-per-card-expected-score-eval-chart-games-subtab
plan: "03"
subsystem: library/games-tests
tags: [eval-chart, integration-tests, idor, no-n-plus-1, payload-measurement]
dependency_graph:
  requires:
    - EvalPoint/FlawMarker/PhaseTransitions schema (plan 01)
    - fetch_page_eval_positions repository function (plan 01)
    - _build_eval_series service function (plan 01)
  provides:
    - tests/test_library_router.py TestEvalSeriesPayload class (5 tests)
    - D-05 payload measurement: 574 bytes gzipped for 2-game page
  affects:
    - tests/test_library_router.py
tech_stack:
  added: []
  patterns:
    - SQLAlchemy before_cursor_execute event listener for query counting (established pattern)
    - Module-scoped committed-data fixture (same as flaws_test_state)
    - gzip.compress() for D-05 payload measurement
key_files:
  created: []
  modified:
    - tests/test_library_router.py
decisions:
  - "D-05 measured: 574 bytes gzipped for 2-game page (1 analyzed + 1 unanalyzed) — well below 40 KB ceiling"
  - "N+1 test implemented at repository level (fetch_page_eval_positions) for precision per plan guidance"
  - "IDOR test verified at repository level (user_a sees 0 positions for user_b game)"
  - "eval_coverage fix: ply 0 must carry eval_cp to reach 90% coverage with n=10 plies"
metrics:
  duration: "15 minutes"
  completed: "2026-06-07T00:00:00Z"
  tasks_completed: 2
  files_modified: 1
---

# Phase 109 Plan 03: Eval-Series Integration Tests Summary

**One-liner:** Integration tests proving analyzed GameFlawCard eval fields are non-null, unanalyzed cards are null, fetch_page_eval_positions is a single batched query (no N+1), IDOR user-scoping holds, and gzipped payload delta is 574 bytes (D-05 closed).

## What Was Built

This plan extends `tests/test_library_router.py` with a `TestEvalSeriesPayload` class of 5 integration tests that close LIBG-10 criterion 6. No production code was added — the router propagates the plan-01 `GameFlawCard` fields automatically via Pydantic.

### New Test Helpers

**`_seed_positions_committed(session_maker, *, user_id, game_id, positions)`** — inserts and commits `GamePosition` rows for integration tests. Each position dict specifies ply, eval_cp (optional), eval_mate (optional), phase (optional). Zobrist hash columns use dummy values (not needed by the chart builder).

**`_make_analyzed_positions(n_plies=10)`** — builds a representative position list with:
- eval_cp set on all plies 0..8 (9/10 = 90% coverage, exactly at EVAL_COVERAGE_MIN gate)
- final ply (9) has no eval_cp (standard convention: last position has no move annotation)
- deliberate blunder at ply 2 (white mover): positions[1].eval_cp=100 → positions[2].eval_cp=-500, mover-POV drop ≈ 0.436 ≥ BLUNDER_DROP=0.15
- phase transitions: ply 3 → middlegame (phase=1), ply 6 → endgame (phase=2)

**`eval_series_test_state` fixture (module-scoped)** — commits:
- User A: `game_analyzed` (white user, 10 positions with >=90% eval coverage, blunder at ply 2)
- User A: `game_unanalyzed` (no positions at all — 0% coverage, unanalyzed state)
- User B: `game_b_analyzed` (10 positions owned by user_b — IDOR target for user_a)

### Test Class: `TestEvalSeriesPayload`

**`test_eval_series_analyzed_game_has_non_null_fields`** (matchable with `-k eval_series`):
- Requests `GET /library/games` as user_a
- Finds the `game_analyzed` card by `game_id`
- Asserts `eval_series` is a non-empty list of EvalPoints with `ply` and `es` fields
- Asserts at least one EvalPoint has non-null `es` (plies 0-8 have eval_cp set)
- Asserts `flaw_markers` is a non-empty list with `is_user`, `severity`, `ply` fields
- Asserts at least one player blunder (`is_user=True`, `severity="blunder"`) from the seeded drop
- Asserts `phase_transitions` has `middlegame_ply=3` and `endgame_ply=6`

**`test_unanalyzed_game_has_null_eval_fields`** (matchable with `-k unanalyzed`):
- Requests `GET /library/games` as user_a
- Finds the `game_unanalyzed` card
- Asserts `eval_series is None`, `flaw_markers is None`, `phase_transitions is None`
- Confirms `analysis_state == "no_engine_analysis"`

**`test_no_n_plus_1_query_count`**:
- Seeds a fresh user_c with 1 analyzed game; attaches `before_cursor_execute` event listener
- Calls `fetch_page_eval_positions(session, user_c_id, [game_1])` directly and counts SELECT statements
- Seeds 4 more analyzed games (total 5); calls `fetch_page_eval_positions` with all 5 game IDs
- Asserts both calls issue exactly 1 SELECT each — proves single IN query, no N+1 scaling

**`test_idor_eval_positions_user_scoped`**:
- Calls `fetch_page_eval_positions(session, user_a_id, [game_b_analyzed])` directly
- Asserts the result has 0 positions for `game_b_analyzed` (user_b's game)
- Confirms the `GamePosition.user_id == user_id` WHERE clause blocks cross-user access (T-109-01)

**`test_payload_gzip_size_below_threshold`** (D-05 measurement):
- Requests `GET /library/games` as user_a
- Serializes response to JSON bytes, compresses with `gzip.compress()`
- Asserts compressed size < `_EVAL_PAYLOAD_GZIP_CEILING_BYTES = 40_960` (40 KB)

### Named Constant

`_EVAL_PAYLOAD_GZIP_CEILING_BYTES: int = 40_960` — documented ceiling for the gzipped response, consistent with RESEARCH's <20 KB estimate for 20 analyzed games (conservative 2x headroom).

## D-05 Payload Measurement

**Measured payload size:** 574 bytes gzipped for a 2-game page (1 analyzed game with 10 EvalPoints, 1 unanalyzed game).

**Analysis:**
- Uncompressed JSON for 10 EvalPoints (typed objects with ply/es/eval_cp/eval_mate): ~500 bytes
- Gzip compression of the full response (metadata + eval_series + null unanalyzed fields): 574 bytes total
- For a realistic 20-game page with 100-ply analyzed games: estimate ~10-15 KB compressed (well within threshold)
- No perceptible payload regression confirmed — D-05 passes without columnar encoding

**Threshold assertion:** The test asserts compressed size < 40,960 bytes (40 KB ceiling). The measured 574 bytes is 98.6% below the ceiling, confirming negligible regression.

## Verification Results

- `uv run pytest tests/test_library_router.py -x -k "eval_series or unanalyzed"` — 2 passed
- `uv run pytest tests/test_library_router.py -x -k "eval_series or unanalyzed or payload"` — 5 passed
- `uv run pytest tests/test_library_router.py -x -v` — 36 passed (all existing tests also green)
- `uv run pytest -n auto -x` — 2431 passed, 10 skipped, 0 failures
- `uv run ty check tests/` — All checks passed (zero errors)
- `uv run ruff check tests/test_library_router.py` — All checks passed

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] eval_coverage below gate with ply 0 having no eval_cp**
- **Found during:** Task 1 — first test run failed with `eval_series is None`
- **Issue:** `_make_analyzed_positions` seeded ply 0 with no eval_cp and ply 9 with no eval_cp → 8/10 = 80% coverage < EVAL_COVERAGE_MIN=0.90. The game was reported as unanalyzed.
- **Fix:** Added `eval_cp=25` to ply 0 (initial position). With only ply 9 (final ply) lacking eval_cp, coverage = 9/10 = 90% exactly, passing the gate.
- **Files modified:** tests/test_library_router.py (helper function)
- **Commit:** fc8cb24e

**2. [Rule 1 - Lint] Unused `AsyncSession` import in no-N+1 test**
- **Found during:** Task 1 — `ruff check` flagged F401 unused import
- **Fix:** Removed the unused `AsyncSession` import from the local import in `test_no_n_plus_1_query_count`
- **Files modified:** tests/test_library_router.py
- **Commit:** fc8cb24e

## Known Stubs

None. All test assertions are fully implemented and green.

## Threat Flags

No new threat surface introduced. This plan adds tests only; no production endpoints or schema changes.

## Self-Check: PASSED

| Check | Result |
|-------|--------|
| tests/test_library_router.py exists | FOUND |
| TestEvalSeriesPayload class exists | FOUND |
| test_eval_series_analyzed_game_has_non_null_fields passes | PASSED |
| test_unanalyzed_game_has_null_eval_fields passes | PASSED |
| test_no_n_plus_1_query_count passes | PASSED |
| test_idor_eval_positions_user_scoped passes | PASSED |
| test_payload_gzip_size_below_threshold passes | PASSED |
| Full suite (2431 tests) green | PASSED |
| ty check tests/ zero errors | PASSED |
| Gzipped payload size recorded (D-05) | 574 bytes |
| commit fc8cb24e exists | FOUND |
