---
phase: 109-per-card-expected-score-eval-chart-games-subtab
plan: "01"
subsystem: library/games-backend
tags: [eval-chart, backend, schemas, repository, service, tdd]
dependency_graph:
  requires: []
  provides:
    - EvalPoint/FlawMarker/PhaseTransitions Pydantic models
    - GameFlawCard.eval_series/flaw_markers/phase_transitions fields
    - fetch_page_eval_positions repository function
    - _build_eval_series/_build_opponent_tags service helpers
    - _resolve_increment shared helper
    - tests/services/test_eval_chart_service.py (18 unit tests)
  affects:
    - app/schemas/library.py
    - app/services/library_service.py
    - app/services/flaws_service.py
    - app/repositories/library_repository.py
tech_stack:
  added: []
  patterns:
    - TDD RED/GREEN cycle (Wave 0 unit tests)
    - Batch IN query with Python grouping (same pattern as fetch_page_game_flaws)
    - Mover-POV kernel reuse (_run_all_moves_pass + _build_tags, FEN-free)
    - White-perspective ES via eval_cp_to_expected_score/eval_mate_to_expected_score
    - D-03 opponent tag filtering (flip result + strip user-framed tags)
key_files:
  created:
    - tests/services/test_eval_chart_service.py
  modified:
    - app/schemas/library.py
    - app/services/flaws_service.py
    - app/services/library_service.py
    - app/repositories/library_repository.py
decisions:
  - "D-01: Reuse mover-POV kernel (_run_all_moves_pass) for all flaw dots (both colors, B/M/I)"
  - "D-03: Strip miss/lucky-escape from opponent tags via _build_opponent_tags helper"
  - "D-04: Chart line is white-perspective ES (eval_cp_to_expected_score/eval_mate_to_expected_score with 'white')"
  - "D-06: At most two phase transitions (middlegame_ply, endgame_ply); no ply-0 line"
  - "D-10: Single batched game_positions query (fetch_page_eval_positions); no N+1"
  - "_resolve_increment extracted from classify_game_flaws as single source of truth (RESEARCH open question 2)"
  - "New Pydantic models placed BEFORE GameFlawCard in library.py (no forward references needed)"
metrics:
  duration: "10 minutes"
  completed: "2026-06-06T23:23:31Z"
  tasks_completed: 2
  files_modified: 5
---

# Phase 109 Plan 01: Backend Eval-Chart Series Builder Summary

**One-liner:** Backend eval-chart builder extending GET /library/games GameFlawCard with white-perspective ES series, both-color flaw markers with is_user discriminator, and phase-transition plies via batched game_positions query.

## What Was Built

This plan implements the backend data contract (LIBG-10) for the per-card expected-score eval chart on the Games subtab.

### Schema Models (app/schemas/library.py)

Three new Pydantic models added before `GameFlawCard` (no forward references):

- `EvalPoint(ply, es, eval_cp, eval_mate)` — one ply's white-perspective ES datapoint; `es=None` for missing eval (D-05).
- `FlawMarker(ply, severity, tags, is_user)` — one flaw dot for both colors; `is_user=True` = filled circle (player), `False` = hollow circle (opponent); `tags=[]` for inaccuracies (D-03).
- `PhaseTransitions(middlegame_ply, endgame_ply)` — first ply of each phase; `None` when phase not reached.

`GameFlawCard` extended with `eval_series`, `flaw_markers`, `phase_transitions` (all `None` for unanalyzed games).

### Increment Helper Extraction (app/services/flaws_service.py)

`_resolve_increment(game) -> float` extracted from the inline block in `classify_game_flaws`. Handles: `game.increment_seconds` when set, `parse_base_and_increment(game.time_control_str)` fallback, `0.0` default. `classify_game_flaws` now calls `_resolve_increment(game)` — single source of truth for both the flaws kernel and the chart builder.

### Repository Function (app/repositories/library_repository.py)

`fetch_page_eval_positions(session, user_id, analyzed_game_ids)` batch-loads `GamePosition` ORM objects for analyzed games on a page. Mirrors `fetch_page_game_flaws` pattern: `SELECT GamePosition WHERE user_id == user_id AND game_id IN (...)` scoped to analyzed games only, grouped by game_id in Python. `GamePosition.user_id == user_id` clause is the IDOR control (T-109-01).

### Service Helpers (app/services/library_service.py)

`_USER_FRAMED_TAGS = frozenset({"miss", "lucky-escape"})` constant.

`_build_eval_series(game, positions) -> tuple[list[EvalPoint], list[FlawMarker], PhaseTransitions]`:
- Calls `_run_all_moves_pass(positions)` once for both-color mover-POV detection (D-01/D-02).
- ES line: `eval_mate_to_expected_score(mate, "white")` when mate set, else `eval_cp_to_expected_score(cp, "white")`, else `None` — rounded to 3dp.
- Phase transitions: first `ply > 0` where `phase == 1` (middlegame) and `phase == 2` (endgame) — no ply-0 line (D-06).
- Flaw markers: for B/M user moves calls `_build_tags` with user perspective; for B/M opponent moves calls `_build_opponent_tags`; inaccuracies get empty tags (D-03).

`_build_opponent_tags(...)`: flips result to opponent's perspective, calls `_build_tags`, strips `_USER_FRAMED_TAGS`.

`_build_card` extended with `positions: list[GamePosition]` parameter. Pipeline injection in `get_library_games`: computes `analyzed_game_ids`, calls `fetch_page_eval_positions`, passes `page_positions.get(game.id, [])` to each `_build_card` call. Total: 5 queries per page request (up from 4).

### Wave 0 Unit Tests (tests/services/test_eval_chart_service.py)

18 unit tests in three classes, no DB required:

- `TestEvalSeries` (6 tests): white-perspective ES for positive/negative cp, null eval to es=None, eval_mate hard 1.0/0.0 for chart line, ES rounded to 3dp, raw eval_cp/eval_mate preserved.
- `TestFlawMarkers` (6 tests): both-color detection, is_user=True for player, is_user=False for opponent, inaccuracy to empty tags, opponent tags strip miss/lucky-escape, blunder carries at least one tag.
- `TestPhaseTransitions` (6 tests): no ply-0 line, middlegame_ply = first ply with phase==1, endgame_ply = first ply with phase==2, at most two transitions, absent phase to None, both transitions populated.

## Verification Results

- `uv run pytest tests/services/test_eval_chart_service.py -x` — 18 passed
- `uv run pytest -n auto -x` — 2426 passed, 10 skipped, 1 warning
- `uv run ty check app/ tests/` — All checks passed (zero errors)
- `uv run ruff check app/` — All checks passed

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing functionality] TDD stub pattern for test collectability**
- **Found during:** Task 1 execution
- **Issue:** The test file imports `_build_eval_series` from `library_service`, but the function doesn't exist yet in Task 1. The `--collect-only` acceptance criterion requires the tests to be listed (collected). An ImportError prevents collection.
- **Fix:** Added stub implementations (`raise NotImplementedError(...)`) for `_build_eval_series` and `_build_opponent_tags` in Task 1 so the test module can be imported and collected. Added `# noqa: F401` comments on imports used only by Task 2. Task 2 replaced stubs with full implementations.
- **Files modified:** `app/services/library_service.py`

**2. [Rule 2 - Refactor] EvalPoint/FlawMarker/PhaseTransitions placed before GameFlawCard**
- **Found during:** Task 1 schema work
- **Issue:** The PATTERNS.md showed adding the new classes after `FlawListItem`, but this required forward references (string annotations) in `GameFlawCard`. Placing them before `GameFlawCard` eliminates forward references and is cleaner for Pydantic v2.
- **Fix:** Moved all three new model classes to before `GameFlawCard` definition.
- **Files modified:** `app/schemas/library.py`

## Threat Surface Scan

The new `fetch_page_eval_positions` repository function introduces a new batched game_positions read. Security controls verified:

| Flag | File | Description |
|------|------|-------------|
| MITIGATED: T-109-01 (IDOR) | app/repositories/library_repository.py | `GamePosition.user_id == user_id` WHERE clause scopes query to requesting user; user_id from `current_active_user`, never from request body |
| MITIGATED: T-109-02 (SQLi) | app/repositories/library_repository.py | `game_id.in_(analyzed_game_ids)` uses SQLAlchemy parameterized query, no f-string interpolation |

No new unmitigated threat surface.

## Known Stubs

None. All functionality is fully implemented. The `_build_eval_series` stub from Task 1 is replaced by the full implementation in Task 2.

## Self-Check: PASSED

| Check | Result |
|-------|--------|
| tests/services/test_eval_chart_service.py exists | FOUND |
| app/schemas/library.py exists | FOUND |
| app/services/flaws_service.py exists | FOUND |
| app/services/library_service.py exists | FOUND |
| app/repositories/library_repository.py exists | FOUND |
| commit 7abf83f6 (Task 1) exists | FOUND |
| commit d91d534b (Task 2) exists | FOUND |
