---
phase: 122-in-app-feedback-button-seed-049
plan: 01
subsystem: api
tags: [fastapi, sqlalchemy, alembic, pydantic, sentry, rate-limiting, tdd]

requires:
  - phase: position-bookmarks-vertical-slice
    provides: "canonical router/repository/schema pattern (session.flush, thin router, module-level fns)"

provides:
  - "feedback table (Alembic revision 60160718b3b3) with user_id FK ondelete=CASCADE + ix_feedback_user_id"
  - "Feedback ORM model (app/models/feedback.py)"
  - "FeedbackCreate / FeedbackResponse Pydantic schemas + Sentiment Literal + _MAX_FEEDBACK_LEN/_MAX_PAGE_URL_LEN constants"
  - "create_feedback repository fn (app/repositories/feedback_repository.py)"
  - "elo_bucket() helper + push_sentry_signal() with static capture_message (app/services/feedback_service.py)"
  - "feedback_limiter singleton 5/3600s keyed by user_id (app/core/feedback_rate_limiter.py)"
  - "POST /api/feedback endpoint → 201 FeedbackResponse (422 validation, 429 rate-limit, 401 unauth)"

affects:
  - 122-02 (frontend plan mirrors this request/response contract exactly)

tech-stack:
  added: []
  patterns:
    - "Feedback vertical slice clones position_bookmarks: thin router, module-level repo fns, session.flush not commit"
    - "Non-exception Sentry signal: static capture_message + set_tag source/platform/elo_bucket + set_context"
    - "In-process per-user rate limiter: import _SlidingWindowRateLimiter, key by str(user.id)"
    - "Partial indexes (postgresql_where) managed by migrations only — added to _AUTOGEN_INDEX_IGNORELIST in alembic/env.py"

key-files:
  created:
    - app/models/feedback.py
    - app/schemas/feedback.py
    - app/core/feedback_rate_limiter.py
    - app/repositories/feedback_repository.py
    - app/services/feedback_service.py
    - app/routers/feedback.py
    - alembic/versions/20260615_192047_60160718b3b3_phase_122_feedback_table.py
    - tests/test_feedback_repository.py
    - tests/test_feedback_router.py
  modified:
    - app/main.py (added feedback router import + include_router)
    - alembic/env.py (added Feedback model import + extended _AUTOGEN_INDEX_IGNORELIST)

key-decisions:
  - "Alembic revision 60160718b3b3 creates only the feedback table + ix_feedback_user_id; unrelated partial-index autogenerate drift added to ignorelist"
  - "ELO bucket uses highest anchor_rating across all TCs (ASSUMED A1 from RESEARCH.md)"
  - "Sentry signal uses static 'feedback submitted' message; variable data in set_tag/set_context only"
  - "Rate limiter keyed by str(user.id) not IP (per-user abuse guard D-07)"

requirements-completed: [SEED-049, D-04, D-05, D-07, D-08]

duration: 11min
completed: 2026-06-15
---

# Phase 122 Plan 01: Backend Feedback Vertical Slice Summary

**POST /api/feedback endpoint with SQLAlchemy Feedback model, Alembic migration, Pydantic schemas with Sentiment Literal, create_feedback repository, elo_bucket/push_sentry_signal service, feedback_limiter rate guard (5/3600s per user), and 18 integration tests**

## Performance

- **Duration:** 11 min
- **Started:** 2026-06-15T19:18:39Z
- **Completed:** 2026-06-15T19:30:21Z
- **Tasks:** 3 (Tasks 1, 2: TDD with RED/GREEN commits; Task 3: full gate)
- **Files modified:** 11

## Accomplishments

- New `feedback` table with user_id FK (ondelete=CASCADE) + ix_feedback_user_id, applied via Alembic revision 60160718b3b3
- POST /api/feedback endpoint returning 201 for full and guest users, 422 on empty/over-long text, 429 on rate-limit, 401 unauthenticated
- Sentry non-exception signal per submission tagged source=feedback + platform + elo_bucket with static message string
- 18 passing tests across repository and router (TDD RED/GREEN pattern followed)

## Task Commits

Each task was committed atomically (TDD tasks have multiple commits):

1. **Task 1: Model, schema, migration, rate-limiter** (TDD RED)
   - `e9c2ab5b` test(122-01): add failing test for feedback repository create_feedback
   - `c32ff9e7` feat(122-01): implement Feedback model, schema, repository, rate limiter, and migration

2. **Task 2: Repository, service, router, registration, router tests** (TDD RED/GREEN)
   - `c786acbc` test(122-01): add failing test for feedback router and elo_bucket
   - `e23847ba` feat(122-01): implement feedback service, router, and register POST /api/feedback

3. **Task 3: Full backend gate**
   - `60f34a0b` chore(122-01): fix migration to only create feedback table, add partial indexes to autogenerate ignorelist

## Files Created/Modified

- `app/models/feedback.py` - Feedback ORM model with user_id FK, page_url, text, sentiment, created_at
- `app/schemas/feedback.py` - FeedbackCreate/FeedbackResponse + Sentiment Literal + length constants
- `app/core/feedback_rate_limiter.py` - feedback_limiter singleton (5 req/3600s, keyed by user_id)
- `app/repositories/feedback_repository.py` - create_feedback with session.flush(), never commit()
- `app/services/feedback_service.py` - elo_bucket() helper + push_sentry_signal() with static Sentry message
- `app/routers/feedback.py` - thin POST /feedback router with rate guard
- `alembic/versions/20260615_192047_60160718b3b3_phase_122_feedback_table.py` - creates feedback table + FK + index
- `app/main.py` - added feedback router import + include_router(feedback.router, prefix="/api")
- `alembic/env.py` - added Feedback model import + partial indexes to _AUTOGEN_INDEX_IGNORELIST
- `tests/test_feedback_repository.py` - 4 repository-level tests
- `tests/test_feedback_router.py` - 14 router integration tests + elo_bucket boundary tests

## Decisions Made

- Alembic revision 60160718b3b3 creates ONLY the feedback table + ix_feedback_user_id. The autogenerate also detected pre-existing index drift (partial indexes managed by Phase 116/119 migrations, not in ORM declarations). These were added to `_AUTOGEN_INDEX_IGNORELIST` in `alembic/env.py` to prevent future noise.
- ELO bucket uses highest `anchor_rating` across all TCs (ASSUMED A1 from RESEARCH.md) as the single Sentry tag.
- `capture_message("feedback submitted", level="info")` is a static literal — variable data goes in set_tag/set_context per CLAUDE.md grouping rule.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Autogenerate migration included unrelated index changes**
- **Found during:** Task 1 (migration generation) and confirmed during Task 3 (full gate)
- **Issue:** `alembic revision --autogenerate` detected pre-existing drift between ORM model declarations and the database for partial indexes (`ix_games_evals_pending`, `ix_games_full_evals_pending`, `ix_games_full_pv_pending`, `ix_games_needs_engine_full_evals`) and `ix_eval_jobs_user_id`. These were managed by Phase 91/116/119 migrations only, never by ORM `Index()` declarations. Including their drops in the Phase 122 migration broke `test_migration_116_full_evals.py`.
- **Fix:** Edited the migration to only include the `feedback` table creation + `ix_feedback_user_id`. Added the partial index names to `_AUTOGEN_INDEX_IGNORELIST` in `alembic/env.py`. Dropped `flawchess_test_template` (via `docker exec ... psql -U postgres`) to force conftest to rebuild the template with the correct migration.
- **Files modified:** `alembic/versions/20260615_192047_60160718b3b3_phase_122_feedback_table.py`, `alembic/env.py`
- **Verification:** Full test suite passed (2671 passed, 10 skipped) after rebuild.
- **Committed in:** `60f34a0b`

---

**Total deviations:** 1 auto-fixed (Rule 1 - Bug in autogenerated migration)
**Impact on plan:** Necessary correction — the migration drift would have silently broken Phase 116 migration tests. The ignorelist fix prevents recurrence.

## Issues Encountered

- `alembic revision --autogenerate` included pre-existing index drift alongside the new feedback table. Root cause: partial indexes defined in migrations via `op.create_index(postgresql_where=...)` are invisible to Alembic's ORM-level comparison, so they appear as "removed from ORM" on each autogenerate run. Fixed by ignorelisting them and editing the migration.

## Known Stubs

None — the repository, service, and router are fully wired with real DB persistence and Sentry signals. No hardcoded empty values or placeholder data.

## Threat Surface Scan

No new network endpoints beyond the plan's `POST /api/feedback`. All STRIDE threats from the plan's `<threat_model>` are mitigated:
- T-122-01 (spoofing): user_id from current_active_user, never from body
- T-122-02 (DoS): feedback_limiter 5/3600s per user → 429
- T-122-03 (oversized payload): Pydantic Field(max_length=2000/500) → 422
- T-122-04 (SQL injection): SQLAlchemy ORM parameterizes
- T-122-05 (PII to Sentry): only user_id/page_url/sentiment in set_context; raw email/text excluded

## Next Phase Readiness

- `POST /api/feedback` contract is stable: `{ text: str (1..2000), sentiment?: "negative"|"neutral"|"positive", page_url: str (≤500) }` → `{ id: int, created_at: datetime }`
- Plan 02 (frontend) can mirror this contract exactly from `app/schemas/feedback.py`
- Alembic head is `60160718b3b3` — Plan 02 does not need any DB changes

## Self-Check: PASSED

Files created/verified:
- app/models/feedback.py: FOUND
- app/schemas/feedback.py: FOUND
- app/core/feedback_rate_limiter.py: FOUND
- app/repositories/feedback_repository.py: FOUND
- app/services/feedback_service.py: FOUND
- app/routers/feedback.py: FOUND
- alembic/versions/20260615_192047_60160718b3b3_phase_122_feedback_table.py: FOUND
- tests/test_feedback_repository.py: FOUND
- tests/test_feedback_router.py: FOUND

Commits verified:
- e9c2ab5b: FOUND
- c32ff9e7: FOUND
- c786acbc: FOUND
- e23847ba: FOUND
- 60f34a0b: FOUND

---
*Phase: 122-in-app-feedback-button-seed-049*
*Completed: 2026-06-15*
