---
phase: 92-custom-date-range-filter
plan: "06"
subsystem: testing-and-verification
tags: [tests, changelog, uat, date-range, integration]
dependency_graph:
  requires: [92-05]
  provides: [boundary-tests, uat-script, changelog-entry]
  affects:
    - tests/test_integration_routers.py
    - tests/routers/test_insights_openings.py
    - .planning/phases/92-custom-date-range-filter/92-HUMAN-UAT.md
    - CHANGELOG.md
tech_stack:
  added: []
  patterns:
    - "function-scoped fixtures with per-test game seeding for unambiguous matched_count assertions"
    - "direct ORM insert in fixture (async_session_maker) for controlled played_at timestamps"
decisions:
  - "Fresh user + single seeded game per boundary test (function-scoped fixtures) to keep matched_count assertions unambiguous"
  - "Task 3 (browser UAT execution) deferred to HUMAN-UAT.md flow; UAT script written, scenarios pending user run"
metrics:
  duration: ~25 minutes
  completed: "2026-05-22"
  tasks_completed: 2
  tasks_total: 3
  files_modified: 4
---

# Phase 92 Plan 06: Verification Surface Summary

Integration test suite covering from_date/to_date boundary semantics, 422 cross-field validation, and the insights LLM gate; UAT script for visual browser verification; CHANGELOG [Unreleased] entries for Phase 92.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Boundary tests + 422 + insights-gate assertion | 99a29e09 | tests/test_integration_routers.py, tests/routers/test_insights_openings.py |
| 2 | UAT script + CHANGELOG entries | ec9340c9 | .planning/phases/92-custom-date-range-filter/92-HUMAN-UAT.md, CHANGELOG.md |

## Task 3: Deferred

Task 3 (run the 6 UAT scenarios in a browser) is deferred to the HUMAN-UAT.md flow. The script is written at `.planning/phases/92-custom-date-range-filter/92-HUMAN-UAT.md`. Scenarios pending user run.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] PostgreSQL BIGINT overflow on _DATE_TEST_HASH constant**
- **Found during:** Task 1 first test run
- **Issue:** `_DATE_TEST_HASH = 0xDEADBEEFCAFE0001` (16045690984503050241) exceeds signed int64 max (9223372036854775807). asyncpg raised `DataError: invalid input for query argument: value out of int64 range` on the `game_positions.full_hash` BIGINT column.
- **Fix:** Changed constant to `0x0DEADBEEFCAFE001` (998684643807453185), which is well within range.
- **Files modified:** tests/test_integration_routers.py
- **Commit:** 99a29e09

**2. [Rule 1 - Bug] Missing `pgn` NOT NULL field in `_seed_one_game` helper**
- **Found during:** Task 1 first test run
- **Issue:** `games.pgn` is a NOT NULL column. The `Game()` constructor call omitted `pgn=`, triggering a `NotNullViolationError`.
- **Fix:** Added `pgn="1. e4 e5 *"` to match the seeded_user fixture pattern.
- **Files modified:** tests/test_integration_routers.py
- **Commit:** 99a29e09

## Known Stubs

None. Both committed files are complete: tests pass, UAT script is fully written.

## Threat Flags

None. This plan adds only test files and docs. No new network endpoints, auth paths, or trust boundaries introduced.

## Self-Check: PASSED

Checking files exist:
- `tests/test_integration_routers.py` — FOUND
- `tests/routers/test_insights_openings.py` — FOUND
- `.planning/phases/92-custom-date-range-filter/92-HUMAN-UAT.md` — FOUND
- `CHANGELOG.md` — FOUND

Checking commits exist:
- `99a29e09` (Task 1): FOUND in git log
- `ec9340c9` (Task 2): FOUND in git log

Checking acceptance criteria:
- 6 test functions matching name pattern in test_integration_routers.py: YES (grep -c returns 6)
- 1 `test_insights_blocked_when_from_date_set` in test_insights_openings.py: YES
- `uv run pytest tests/test_integration_routers.py tests/routers/test_insights_openings.py -x`: 31 passed
- `uv run pytest -x` (full suite, excluding flaky eval_drain test): 1617 passed, 6 skipped
- `uv run ruff format app/ tests/`: 1 file reformatted (test_integration_routers.py — cosmetic import ordering)
- `uv run ruff check app/ tests/ --fix`: All checks passed
- `uv run ty check app/ tests/`: All checks passed
- `npm run lint`: clean
- `npm test -- --run`: 611/611 passed (54 test files)
- `92-HUMAN-UAT.md`: 6 scenarios, 12 checkboxes, no dev-DB-reset dependency
- `CHANGELOG.md [Unreleased]`: Added/Changed/Removed/Tests Phase 92 bullets (4 occurrences of "Phase 92", 2 of "Custom date range")
