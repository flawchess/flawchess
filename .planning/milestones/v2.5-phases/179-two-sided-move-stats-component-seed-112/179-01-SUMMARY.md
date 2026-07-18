---
phase: 179-two-sided-move-stats-component-seed-112
plan: 01
subsystem: api
tags: [fastapi, pydantic, sqlalchemy, typescript, library-service]

# Dependency graph
requires:
  - phase: 178-lichess-compatible-accuracy-acpl-computed-columns
    provides: Game.white_accuracy/black_accuracy canonical REAL columns (Phase 178 D-01)
provides:
  - GameFlawCard.white_accuracy/black_accuracy (backend Pydantic schema, nullable float)
  - _build_card passthrough of game.white_accuracy/game.black_accuracy
  - frontend GameFlawCard TS interface mirror (number | null)
affects: [179-02-move-stats-frontend-component, 179-03-move-stats-frontend-component]

# Tech tracking
tech-stack:
  added: []
  patterns: [additive nullable Pydantic field passthrough with no new query/repository/migration]

key-files:
  created: []
  modified:
    - app/schemas/library.py
    - app/services/library_service.py
    - tests/services/test_library_service.py
    - frontend/src/types/library.ts

key-decisions:
  - "Sourced white_accuracy/black_accuracy ONLY from game.white_accuracy/game.black_accuracy (Phase 178 canonical columns), never *_accuracy_imported, per D-01"
  - "Placed both new fields adjacent to severity_counts in both the backend schema and frontend interface, matching the plan's artifact spec"
  - "New test cases added directly to TestGetLibraryGame (not a new test class) to match the existing normalized-rating-null-case pattern in the same file"

patterns-established:
  - "Accuracy passthrough pattern: no new query, no repository change, no migration — the full-entity select(Game) already loads canonical accuracy columns"

requirements-completed: [D-01, D-05, D-07]

coverage:
  - id: D1
    description: "GET /library/games and GET /library/games/{game_id} both return white_accuracy and black_accuracy on every GameFlawCard, sourced from Game.white_accuracy/black_accuracy (never *_accuracy_imported), with null when unavailable"
    requirement: "D-01"
    verification:
      - kind: unit
        ref: "tests/services/test_library_service.py::TestGetLibraryGame::test_accuracy_round_trips_from_canonical_columns"
        status: pass
      - kind: unit
        ref: "tests/services/test_library_service.py::TestGetLibraryGame::test_null_accuracy_card_has_none_accuracy"
        status: pass
    human_judgment: false
  - id: D2
    description: "Frontend GameFlawCard TypeScript interface mirrors the two new nullable float fields (number | null), with no ACPL or per-side count fields added"
    requirement: "D-05"
    verification:
      - kind: unit
        ref: "cd frontend && npx tsc -b (exits 0)"
        status: pass
    human_judgment: false

# Metrics
duration: 18min
completed: 2026-07-18
status: complete
---

# Phase 179 Plan 01: Surface Canonical Per-Color Accuracy on GameFlawCard Summary

**Added `white_accuracy`/`black_accuracy: float | None` to the shared `GameFlawCard` Pydantic model and its frontend TS mirror, sourced exclusively from Phase 178's canonical `Game.white_accuracy`/`black_accuracy` columns via the existing single `_build_card()` construction site — zero new queries, repositories, or migrations.**

## Performance

- **Duration:** 18 min
- **Started:** 2026-07-18T11:45:00Z
- **Completed:** 2026-07-18T12:03:00Z
- **Tasks:** 2
- **Files modified:** 4

## Accomplishments
- `GameFlawCard` (backend Pydantic schema) gains `white_accuracy: float | None` / `black_accuracy: float | None`, placed adjacent to `severity_counts`
- `_build_card()`'s single `GameFlawCard(...)` construction site now passes `game.white_accuracy` / `game.black_accuracy` through with a code comment noting the D-01 prohibition against `*_accuracy_imported`
- `tests/services/test_library_service.py` extended: `_seed_db_game` gained optional `white_accuracy`/`black_accuracy` params (default `None`, no behavior change for existing callers), plus two new round-trip/null-serialization test cases in `TestGetLibraryGame`
- Frontend `GameFlawCard` TypeScript interface in `frontend/src/types/library.ts` mirrors both fields as `number | null`, adjacent to `severity_counts`

## Task Commits

Each task was committed atomically:

1. **Task 1: Surface canonical per-color accuracy on GameFlawCard (schema + builder + backend test)** - `2cc86def` (feat)
2. **Task 2: Mirror the two accuracy fields onto the frontend GameFlawCard type** - `f2188bb8` (feat)

_No TDD tasks — plan tasks were type="auto"._

## Files Created/Modified
- `app/schemas/library.py` - Added `white_accuracy`/`black_accuracy: float | None = None` to `GameFlawCard`, adjacent to `severity_counts`
- `app/services/library_service.py` - `_build_card`'s `GameFlawCard(...)` call now passes `white_accuracy=game.white_accuracy` / `black_accuracy=game.black_accuracy`, with a D-01 comment
- `tests/services/test_library_service.py` - `_seed_db_game` gained optional accuracy params; added `test_accuracy_round_trips_from_canonical_columns` and `test_null_accuracy_card_has_none_accuracy`
- `frontend/src/types/library.ts` - `GameFlawCard` interface gained `white_accuracy`/`black_accuracy: number | null`, adjacent to `severity_counts`

## Decisions Made
- Sourced both fields exclusively from `game.white_accuracy`/`game.black_accuracy` (Phase 178 canonical `REAL` columns) — never `game.white_accuracy_imported`/`black_accuracy_imported`, satisfying D-01. Confirmed via grep: no `_imported` reference exists in the passthrough site (only a comment documenting the prohibition).
- Backend fields default to `None` (not required) so existing `GameFlawCard(...)` construction sites elsewhere (if any) continue to compile without changes — none existed beyond `_build_card`'s single site per the plan's must_haves.
- Frontend fields left non-optional/nullable (`number | null`, no `?`) to match the plan's exact artifact spec; `npx tsc -b` confirmed no existing test fixtures or mock-card constructors break under the stricter shape.
- New test cases placed in `TestGetLibraryGame` (not a new test class), reusing user IDs 99994/99995 — confirmed safe via `db_session`'s per-test rollback-scoped transaction fixture (existing tests in the same file already reuse these IDs across independent test functions).

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
- `uv run ty check app/` reports 3 pre-existing `unresolved-import` diagnostics for `onnxruntime`/`numpy` in `app/services/maia_engine.py` (the isolated `maia-inference` uv group is not synced in this environment). Confirmed via `git stash` that these errors exist identically on the pre-plan HEAD — unrelated to this plan's changes and out of scope per the deviation-rules scope boundary. `app/schemas/library.py` and `app/services/library_service.py` themselves introduce zero new `ty` diagnostics.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- `GameFlawCard.white_accuracy`/`black_accuracy` are live on both `GET /library/games` and `GET /library/games/{game_id}`, ready for Plans 02-03's frontend Move Stats accuracy strip to consume.
- No blockers. The 14 per-(category × side) counts referenced in the plan objective remain client-derivable from existing `flaw_markers`/`eval_series` fields (D-05) — no further backend work needed for Plans 02-03's count table.

---
*Phase: 179-two-sided-move-stats-component-seed-112*
*Completed: 2026-07-18*

## Self-Check: PASSED

All modified files and task commit hashes (2cc86def, f2188bb8, 0e819907) verified present.
