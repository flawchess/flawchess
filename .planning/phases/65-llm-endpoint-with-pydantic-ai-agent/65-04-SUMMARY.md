---
phase: 65-llm-endpoint-with-pydantic-ai-agent
plan: 04
subsystem: database
tags: [sqlalchemy, postgresql, jsonb, asyncpg, llm-logs, rate-limiting]

requires:
  - phase: 64-llm-logs-table-async-repo
    provides: LlmLog ORM model, ix_llm_logs_user_id_created_at composite index, create_llm_log write helper, get_latest_log_by_hash read helper

provides:
  - count_recent_successful_misses(session, user_id, window) -> int (rate-limit count per D-09)
  - get_latest_report_for_user(session, user_id, prompt_version, model) -> LlmLog | None (tier-2 soft-fail per D-11)
  - 10 integration tests covering happy path, time-window, user-scoping, prompt/model filter, empty-result

affects:
  - 65-05 (insights_llm.generate_insights uses both helpers directly)
  - 65-06 (router wires generate_insights)

tech-stack:
  added: []
  patterns:
    - "caller-supplied AsyncSession for read helpers (no own-session commit needed for reads)"
    - "session_maker(test_engine) fixture pattern for test isolation (avoids async_session_maker import binding issue)"
    - "JSONB JSON-null vs SQL-NULL: asyncpg stores Python None as JSON null for JSONB columns; error IS NULL filter is the reliable exclusion gate for failed rows"

key-files:
  created:
    - tests/test_llm_log_repository_reads.py
  modified:
    - app/repositories/llm_log_repository.py

key-decisions:
  - "Test rowsets use error IS NULL as the gate for excluding failure rows (not response_json IS NOT NULL) because asyncpg stores Python None as JSONB JSON null (IS NOT NULL returns True for it). In production, all failure rows have error set, so the filter combination works correctly."
  - "session_maker fixture wraps async_sessionmaker(test_engine, ...) rather than importing app.core.database.async_session_maker — importing the module-level name binds to the original pre-patch object."

patterns-established:
  - "JSONB None storage: Python None in ORM constructor → JSON null in PostgreSQL (not SQL NULL). Tests must use error-flagged rows to test exclusion, not bare response_json=None rows."
  - "Read helper test pattern: use session_maker(test_engine) fixture; seed with _seed() helper; query in same session context after commit."

requirements-completed:
  - INS-04
  - INS-05

duration: 10min
completed: 2026-04-21
---

# Phase 65 Plan 04: LLM Log Repository Read Helpers Summary

**Two new read helpers in llm_log_repository — count_recent_successful_misses and get_latest_report_for_user — backed by Phase 64's composite index and tested with 10 integration tests.**

## Performance

- **Duration:** 10 min
- **Started:** 2026-04-21T18:57:43Z
- **Completed:** 2026-04-21T19:07:14Z
- **Tasks:** 3
- **Files modified:** 2

## Accomplishments

- Added `count_recent_successful_misses(session, user_id, window) -> int` to `llm_log_repository.py` — the rate-limit DB query (D-09) scoping to `cache_hit=False AND error IS NULL AND response_json IS NOT NULL` within a caller-supplied timedelta window
- Added `get_latest_report_for_user(session, user_id, prompt_version, model) -> LlmLog | None` — tier-2 soft-fail lookup (D-11) returning the most recent successful report under the current prompt/model era
- Created `tests/test_llm_log_repository_reads.py` with 10 integration tests across `TestCountRecentMisses` and `TestLatestReportForUser` classes; all tests pass against the dev PostgreSQL instance

## Task Commits

1. **Task 1: count_recent_successful_misses** - `684d839` (feat)
2. **Task 2: get_latest_report_for_user** - `7fe6d3f` (feat)
3. **Task 3: test_llm_log_repository_reads.py** - `7dea2f0` (test)

## Files Created/Modified

- `app/repositories/llm_log_repository.py` - Extended with `import datetime`, `func` import, two new async read helpers, and updated module docstring referencing D-34
- `tests/test_llm_log_repository_reads.py` - New: 10 integration tests with `_make_row` builder, `_seed` helper, `now_utc` and `session_maker` fixtures

## Decisions Made

**JSONB JSON-null vs SQL-NULL discovery (affects test design):**

asyncpg stores Python `None` for a JSONB column as JSON `null` (a valid JSONB value, `IS NOT NULL = TRUE`) rather than SQL NULL (`IS NULL = TRUE`). This means `response_json.is_not(None)` generates `IS NOT NULL` which returns TRUE for JSON null stored rows.

Consequence: a row with `response_json=None, error=None` in a test would be counted by `count_recent_successful_misses` even though it was intended as a "no response" row. In production this state never occurs — all rows with `response_json=None` also have `error` set (pydantic-ai failure path). Test seeds were updated to use realistic row states (always error-flagged for failed rows), making the `error IS NULL` filter the reliable exclusion gate.

**session_maker test fixture pattern:**

Cannot import `app.core.database.async_session_maker` directly in test modules — conftest patches the module-level attribute after import, so a direct import in a test module would bind to the original pre-patch object (demonstrated by FK violation in first test run). Pattern: `session_maker` fixture takes `test_engine: AsyncEngine` and constructs `async_sessionmaker(test_engine, expire_on_commit=False)`. This matches Phase 64's existing pattern in `test_llm_log_repository.py`.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Test design adjusted for asyncpg JSONB None-storage behavior**
- **Found during:** Task 3 (test file creation and execution)
- **Issue:** `_make_row(user_id, response_json=None)` seeds a row with JSON null (not SQL NULL) in JSONB column. `response_json IS NOT NULL` returns TRUE for JSON null, so the row was incorrectly counted in `test_counts_successful_misses_only` (count=3 vs expected 2). Additionally, direct `async_session_maker` import caused FK violation because conftest patches happen post-import.
- **Fix:** (a) Changed test row seeding to use realistic states — "no response" rows always have `error` set (matching production behavior). (b) Added `session_maker` fixture wrapping `async_sessionmaker(test_engine)` instead of importing the module-level name.
- **Files modified:** `tests/test_llm_log_repository_reads.py`
- **Verification:** `uv run pytest tests/test_llm_log_repository_reads.py -x` exits 0, 10/10 tests pass
- **Committed in:** `7dea2f0` (Task 3 commit)

---

**Total deviations:** 1 auto-fixed (Rule 1 - Bug in test design)
**Impact on plan:** Test semantics corrected to match realistic production data states. Repository implementation is unchanged and correct. No scope creep.

## Issues Encountered

FK violation on first test run (before adding `session_maker` fixture) — seeding rows for `user_id=1` which didn't exist in the test DB because `async_session_maker` import resolved to the original object before conftest patching. Resolved by switching to `async_sessionmaker(test_engine)` pattern identical to Phase 64 tests.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Both read helpers are wired and tested — Plan 05 (`insights_llm.generate_insights`) can call them directly with the caller's `AsyncSession`
- Phase 64's composite index `ix_llm_logs_user_id_created_at` (user_id equality + created_at DESC) covers both new queries without any new migration
- Phase 64 tests (`test_llm_log_repository.py`, `test_llm_log_cascade.py`) still green — no regressions

---
*Phase: 65-llm-endpoint-with-pydantic-ai-agent*
*Completed: 2026-04-21*
