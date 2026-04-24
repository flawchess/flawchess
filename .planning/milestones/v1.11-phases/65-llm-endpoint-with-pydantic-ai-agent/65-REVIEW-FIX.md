---
phase: 65
fixed_at: 2026-04-21T00:00:00Z
review_path: .planning/phases/65-llm-endpoint-with-pydantic-ai-agent/65-REVIEW.md
iteration: 1
findings_in_scope: 1
fixed: 1
skipped: 0
status: all_fixed
---

# Phase 65: Code Review Fix Report

**Fixed at:** 2026-04-21
**Source review:** .planning/phases/65-llm-endpoint-with-pydantic-ai-agent/65-REVIEW.md
**Iteration:** 1

**Summary:**
- Findings in scope: 1 (MJ-01; MN-01 through MN-04 and IN-01 excluded per `fix_scope: critical_warning`)
- Fixed: 1
- Skipped: 0

## Fixed Issues

### MJ-01: Service (`insights_llm.py`) Executes Raw SQL — Violates Repository Layer Rule

**Files modified:** `app/repositories/llm_log_repository.py`, `app/services/insights_llm.py`
**Commit:** 22d73c7
**Applied fix:**

Added `get_oldest_recent_miss_timestamp(session, user_id, window)` to `llm_log_repository.py` with a full docstring explaining its purpose. The query logic is identical to what was in the service, moved verbatim.

In `insights_llm.py`:
- Removed `from sqlalchemy import select` (no longer needed in service)
- Added `get_oldest_recent_miss_timestamp` to the repository imports
- Replaced the 12-line inline query block in `_compute_retry_after()` with a single `await get_oldest_recent_miss_timestamp(session, user_id, _RATE_LIMIT_WINDOW)` call
- Retained `from app.models.llm_log import LlmLog` because `LlmLog` is still used as a type annotation in `_maybe_stale_filters()` — this is legitimate (type annotation, not query territory)

Verified: `uv run ty check app/ tests/` passes with zero errors; all 1018 tests pass.

---

_Fixed: 2026-04-21_
_Fixer: Claude (gsd-code-fixer)_
_Iteration: 1_
