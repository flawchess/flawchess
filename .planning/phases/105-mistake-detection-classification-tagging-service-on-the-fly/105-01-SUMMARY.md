---
phase: 105-mistake-detection-classification-tagging-service-on-the-fly
plan: "01"
subsystem: backend-service
tags: [mistakes, classification, severity, eval, chess, unit-tests]
dependency_graph:
  requires: []
  provides:
    - app.services.mistakes_service (FlawRecord, GameNotAnalyzed, GameMistakesResult, classify_game_mistakes)
    - tests.services.test_mistakes_service (Wave-0 unit test scaffold)
  affects:
    - plan 02: consumes FlawRecord, FlawTag, TempoTag, classify_game_mistakes for tag pass
    - SQL window-scan (plan 02+): uses INACCURACY_DROP, MISTAKE_DROP, BLUNDER_DROP as bind params
tech_stack:
  added: []
  patterns:
    - TypedDict output contract (per zobrist.py PlyData precedent)
    - Literal type aliases for all fixed-value fields (CLAUDE.md ty compliance)
    - Named module-level constants (no magic numbers)
    - TDD: test-first RED commit, then GREEN implementation commit
key_files:
  created:
    - app/services/mistakes_service.py
    - tests/services/test_mistakes_service.py
  modified: []
decisions:
  - "Option B mate handling: eval_mate maps to MATE_CP_EQUIVALENT=1000 cp before sigmoid — never eval_mate_to_expected_score for drop math"
  - "Inaccuracy-only analyzed game returns empty list (not GameNotAnalyzed) per 2026-06-05 amendment"
  - "_make_pos factory uses direct GamePosition() constructor (not __new__) — SQLAlchemy ORM instruments __new__ attribute access, requiring proper session state"
metrics:
  duration: "~40 minutes"
  completed: "2026-06-05T13:14:04Z"
  tasks_completed: 2
  files_created: 2
---

# Phase 105 Plan 01: Mistake Classification Engine + Wave-0 Test Scaffold

Implemented the core mistake-classification service: type contract, named threshold constants, ES helpers with mate Option B, severity classifier, eval-coverage gate, FEN recomputation, all-moves classification pass, and the public `classify_game_mistakes()` function. Also created the Wave-0 unit-test scaffold covering all LIBG-02/LIBG-07 behaviors.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 (RED) | Wave-0 test scaffold — failing tests | 4f6c5f19 | tests/services/test_mistakes_service.py |
| 1 (GREEN) | Module type contract, constants, severity classifier | 50c29371 | app/services/mistakes_service.py |
| 2 (RED+GREEN) | Full coverage: classify_game_mistakes, FEN, ES helpers | 65a06f22 | tests/services/test_mistakes_service.py |

## What Was Built

**`app/services/mistakes_service.py`** (282 lines):
- Named constants at locked values: `INACCURACY_DROP=0.05`, `MISTAKE_DROP=0.10`, `BLUNDER_DROP=0.15`, `MATE_CP_EQUIVALENT=1000`, `EVAL_COVERAGE_MIN=0.90`, `FROM_WINNING_ES=0.85`
- `FlawSeverity`, `FlawTag` (10 members), `TempoTag` Literal type aliases
- `FlawRecord` TypedDict (8 fields: ply, fen, side, severity, tags, es_before, es_after, move_san)
- `GameNotAnalyzed` TypedDict (reason, eval_coverage); `GameMistakesResult = list[FlawRecord] | GameNotAnalyzed`
- `_ply_to_es`: Option B mate mapping via MATE_CP_EQUIVALENT cp (never `eval_mate_to_expected_score`)
- `_classify_severity`: boundary-inclusive, highest-band-wins
- `_compute_eval_coverage`: fraction of non-null evals; 0.0 on empty
- `_recompute_fen_map`: PGN replay via python-chess using `board.board_fen()` (never `board.fen()`)
- `_run_all_moves_pass`: classifies both colors for miss/unpunished adjacency support
- `classify_game_mistakes`: coverage gate + emit only mistake/blunder FlawRecords per 2026-06-05 amendment

**`tests/services/test_mistakes_service.py`** (548 lines):
- 43 pure unit tests across 8 test classes: TestConstants, TestTypeContract, TestSeverityClassification, TestPlyToEs, TestMateOptionB, TestEvalCoverageGate, TestFenRecompute, TestClassifyGameMistakes
- `_make_pos` factory: direct `GamePosition()` constructor (see deviation below)
- `_make_game` factory: direct `Game()` constructor

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] `_make_pos` factory uses `GamePosition()` instead of `GamePosition.__new__(GamePosition)`**
- **Found during:** Task 1 test execution (GREEN phase)
- **Issue:** PATTERNS.md specified `GamePosition.__new__(GamePosition)` for in-memory construction. SQLAlchemy 2.x ORM instruments mapped attribute setters via `InstrumentedAttribute.__set__`. Using `__new__` bypasses the `__init__` call that initializes `_sa_instance_state`, so all attribute assignments raise `AttributeError: 'NoneType' object has no attribute 'set'`. The direct constructor `GamePosition()` initializes the ORM state properly without requiring a DB session.
- **Fix:** Changed `_make_pos` and `_make_game` to use `GamePosition()` / `Game()` direct constructors.
- **Files modified:** tests/services/test_mistakes_service.py
- **Commit:** 65a06f22

**2. [Rule 1 - Bug] `test_invalid_pgn_returns_empty` expectation wrong**
- **Found during:** Task 2 test execution
- **Issue:** `chess.pgn.read_game` successfully parses even completely invalid PGN text — it returns an empty game (zero mainline moves) rather than `None`. The test expected an empty dict; the actual return is `{0: initial_fen}`.
- **Fix:** Updated test to assert `{0: initial_fen}` (single-entry dict with ply-0 initial position) — the correct behavior.
- **Files modified:** tests/services/test_mistakes_service.py
- **Commit:** 65a06f22

## Acceptance Criteria Verification

- `INACCURACY_DROP: float = 0.05`, `MISTAKE_DROP: float = 0.10`, `BLUNDER_DROP: float = 0.15`, `MATE_CP_EQUIVALENT: int = 1000`, `EVAL_COVERAGE_MIN: float = 0.90`, `FROM_WINNING_ES: float = 0.85` — all present at exact values.
- `_classify_severity` returns None / "inaccuracy" / "mistake" / "blunder" at drops 0.04 / 0.05 / 0.10 / 0.15 (boundary-inclusive).
- `FlawSeverity`, `FlawTag`, `TempoTag`, `FlawRecord`, `GameNotAnalyzed`, `GameMistakesResult` importable.
- `FlawTag` enumerates all 10 members including all 3 phase-* and 3 tempo tags.
- `uv run ty check` reports zero errors for both files.
- `eval_mate_to_expected_score` and `board.fen()` absent from `mistakes_service.py` (only in comments).
- 43/43 unit tests pass.

## Known Stubs

None. All implemented functionality is complete for this plan's scope. Tags field is `[]` per design (populated in plan 02).

## Threat Flags

None. This plan adds no new trust boundary — pure Python transform over already-owned ORM objects passed by the caller.

## Self-Check: PASSED

- `app/services/mistakes_service.py` exists and contains `classify_game_mistakes`
- `tests/services/test_mistakes_service.py` exists with 43 passing tests
- All 3 commits exist in git log: 4f6c5f19, 50c29371, 65a06f22
- `ty check` and `ruff check` clean on both files
