---
phase: 260425-dxh
plan: 01
subsystem: insights
tags: [cache, llm, refactor]
requires: []
provides:
  - "app/repositories/import_job_repository.py:get_latest_completed_import_with_games_at"
  - "app/repositories/llm_log_repository.py:get_latest_successful_log_for_user"
  - "app/services/insights_llm.py:INSIGHTS_CACHE_MAX_AGE_DAYS"
  - "app/services/insights_llm.py:INSIGHTS_CACHE_MAX_AGE"
affects:
  - "app/services/insights_llm.py:generate_insights"
tech-stack:
  added: []
  patterns:
    - "JSONB text-extraction lookup (filter_context['opponent_strength'].astext)"
    - "Cache validity gate via MAX(import_jobs.completed_at WHERE games_imported>0)"
key-files:
  created: []
  modified:
    - app/repositories/import_job_repository.py
    - app/repositories/llm_log_repository.py
    - app/services/insights_llm.py
    - tests/services/test_insights_llm.py
    - tests/test_insights_router.py
decisions:
  - "Structural cache key (user_id, prompt_version, model, opponent_strength) replaces unstable findings_hash key on the hot path."
  - "30-day TTL safety net (INSIGHTS_CACHE_MAX_AGE_DAYS) bounds sliding-window narrative drift on cache hits."
  - "Cache lookup runs BEFORE compute_findings so cache hits skip the heavy DB pipeline."
  - "no-op resyncs (games_imported=0) do NOT invalidate the cache — only imports that fetched new games do."
  - "findings_hash retained on cache-miss writes for diagnostics; old get_latest_log_by_hash helper kept for tests/analytics."
metrics:
  duration_minutes: ~25
  completed: 2026-04-25
---

# Phase 260425-dxh Plan 01: Endgame Insights Structural Cache Summary

Replaced the unstable findings_hash-based tier-1 cache for endgame insights with a structural cache keyed on `(user_id, prompt_version, model, opponent_strength)`, validated against the user's most recent completed import that brought in new games and a 30-day TTL. The cache lookup now runs before `compute_findings`, so cache hits skip the heavy DB pipeline entirely.

## What Changed

### `app/repositories/import_job_repository.py`
- Added `get_latest_completed_import_with_games_at(session, user_id) -> datetime | None`. Returns `MAX(completed_at)` for the user's completed imports with `games_imported > 0`, or `None`. No-op resyncs are intentionally excluded so daily syncs that fetch zero games do not bust the cache.
- Imports updated to `from sqlalchemy import func, select, update`.

### `app/repositories/llm_log_repository.py`
- Added `get_latest_successful_log_for_user(session, user_id, prompt_version, model, opponent_strength, max_age) -> LlmLog | None` alongside (NOT replacing) `get_latest_log_by_hash`. Uses the JSONB text-extraction operator `filter_context['opponent_strength'].astext` to match the opp_strength dimension. Includes a TTL cutoff via `created_at >= now - max_age`. Filters out unsuccessful rows (`response_json IS NOT NULL AND error IS NULL`).
- The old hash-based helper is preserved for tests / future analytics; only its import in `insights_llm.py` was removed.

### `app/services/insights_llm.py`
- Added module constants `INSIGHTS_CACHE_MAX_AGE_DAYS = 30` and `INSIGHTS_CACHE_MAX_AGE = timedelta(days=30)` (CLAUDE.md no-magic-numbers).
- Updated imports: dropped `get_latest_log_by_hash`; added `get_latest_successful_log_for_user` and `get_latest_completed_import_with_games_at`.
- Rewrote `generate_insights`:
  1. Cache lookup runs FIRST via `get_latest_successful_log_for_user`.
  2. On hit, fetches `last_import_at` and validates `last_import_at is None or last_import_at <= cached.created_at`. Valid → return `cache_hit` without calling `compute_findings`.
  3. On miss (or invalidated hit), proceeds to `compute_findings`, rate-limit check, tier-2 soft-fail, and fresh LLM call as before.
- `findings_hash` is still passed to `LlmLogCreate` on cache-miss writes for diagnostics.

## What Was Preserved

- `findings_hash` column on `llm_logs` (still populated; just no longer the lookup key).
- `get_latest_log_by_hash` repository helper (kept for tests + future analytics).
- `compute_findings` and `_compute_hash` in `app/services/insights_service.py` (untouched).
- All Sentry context patterns and `_run_agent` invocation logic.
- Rate-limit, tier-2 soft-fail, and fresh-call paths.

## Test Coverage Added

New `TestStructuralCacheInvalidation` class in `tests/services/test_insights_llm.py` with 5 tests:

1. `test_import_with_new_games_invalidates_cache` — completed import with `games_imported > 0` after the cached row was written invalidates the cache (next call is `fresh`).
2. `test_no_op_import_does_not_invalidate` — completed import with `games_imported = 0` does NOT invalidate the cache (next call is `cache_hit`).
3. `test_ttl_expiry_misses` — cached row older than `INSIGHTS_CACHE_MAX_AGE_DAYS` is treated as a miss (next call is `fresh`).
4. `test_other_users_log_not_returned` — log row owned by a different user is not served as cache hit (regression test for missing user_id filter on the old hash-based lookup). Uses a real second `User` row to comply with the `llm_logs.user_id` FK.
5. `test_cache_hit_skips_compute_findings` — patches `compute_findings` to raise `AssertionError`; verifies cache-hit path never invokes it.

`TestCacheBehavior.test_second_call_cache_hits` docstring updated to describe the new structural key. Existing `test_prompt_version_bump_misses` and `test_model_swap_misses` remain valid (both fields are still part of the structural key).

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Pre-existing rate-limit tests started returning `cache_hit` instead of expected status**
- **Found during:** Task 2 (running pytest)
- **Issue:** With the cache lookup now running BEFORE `compute_findings`, three pre-existing tests seeded rows that match the structural cache key (default `opponent_strength="any"` plus default `model="test"` plus default `prompt_version="endgame_v15"`):
  - `tests/services/test_insights_llm.py::TestRateLimit::test_boundary_3_misses_allowed_4th_stale`
  - `tests/services/test_insights_llm.py::TestRateLimit::test_window_rollover`
  - `tests/test_insights_router.py::TestRateLimit::test_200_stale_when_rate_limited_with_tier2`
- **Fix:** Extended `_make_log_row` (and the parallel `_make_row` in `tests/test_insights_router.py`) with an `opponent_strength` parameter (default `"any"` for compatibility). Updated the three failing tests to seed rate-limit rows with `opponent_strength="stronger"`. The structural cache lookup now misses them (call uses `"any"`), but `count_recent_successful_misses` and `get_latest_report_for_user` do NOT filter by `opponent_strength`, so they still serve as rate-limit consumers and tier-2 fallbacks respectively.
- **Files modified:** `tests/services/test_insights_llm.py`, `tests/test_insights_router.py`
- **Commit:** 9029f7e

## Verification Results

```bash
$ uv run ruff check .
All checks passed!

$ uv run ruff format --check tests/services/test_insights_llm.py tests/test_insights_router.py app/repositories/import_job_repository.py app/repositories/llm_log_repository.py app/services/insights_llm.py
5 files already formatted

$ uv run ty check app/ tests/
All checks passed!

$ uv run pytest tests/
1062 passed in 15.03s
```

Note: `uv run ruff format --check .` reports 92 pre-existing files would be reformatted (alembic migrations, several scripts, several tests). Confirmed by stashing my changes and re-running — these are repo-wide pre-existing format drift, not caused by this plan. Out of scope per CLAUDE.md ("Only auto-fix issues DIRECTLY caused by the current task's changes."). Recommend a separate `chore: ruff format .` cleanup pass before next phase.

## Self-Check: PASSED

- File `app/repositories/import_job_repository.py` exists with `get_latest_completed_import_with_games_at` (verified by `grep`).
- File `app/repositories/llm_log_repository.py` exists with `get_latest_successful_log_for_user` AND `get_latest_log_by_hash` (both present).
- File `app/services/insights_llm.py` defines `INSIGHTS_CACHE_MAX_AGE_DAYS = 30` and uses `get_latest_successful_log_for_user` BEFORE `compute_findings`.
- Tests file contains `TestStructuralCacheInvalidation` class with 5 test methods (verified).
- Commit c7e4d0c (feat) and 9029f7e (test) both present in `git log`.
- Full backend test suite passes (1062 tests).
