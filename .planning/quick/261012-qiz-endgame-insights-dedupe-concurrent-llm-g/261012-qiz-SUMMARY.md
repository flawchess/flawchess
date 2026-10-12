---
phase: quick-261012-qiz
plan: 01
subsystem: insights
status: complete
tags: [llm, insights, advisory-lock, cache, postgres]
requirements: [QUICK-261012-qiz]
key-files:
  modified:
    - app/repositories/llm_log_repository.py
    - app/services/insights_llm.py
    - app/routers/insights.py
    - app/repositories/import_job_repository.py
    - tests/services/test_insights_llm.py
    - tests/test_insights_router.py
    - frontend/src/components/endgames/useEndgameInsightsState.ts
    - frontend/src/components/endgames/useEndgameInsightsState.test.tsx
    - frontend/src/App.tsx
    - CHANGELOG.md
decisions:
  - "Per-user pg_advisory_xact_lock (two-int4 key, namespace 0x494E5347) taken first in generate_insights"
  - "INSIGHTS_REGEN_COOLDOWN = 24h in one shared get_cached_insights_response used by POST and GET /cached"
commits: 3
plan_head_before: bfed5e02e828783a0a7f82717575e7b6311df000
plan_head_after: abb4d710e75e1ca73731b8243b2b1b540b407a0e
actuals:
  tokens: 30000
  tasks: 3
  commits: 3
---

# Phase quick-261012-qiz Plan 01: Endgame insights dedupe + 24h cooldown Summary

Per-user Postgres advisory xact lock serializes concurrent endgame-insights generations (the waiter returns the first request's report as cache_hit), and a 24h regeneration cooldown lives in a single shared validity helper used by both POST and GET /cached.

## Commits

- 6266dab2f: Task 1, advisory lock + real-DB concurrency test
- 1ff0d2ba8: Task 2, INSIGHTS_REGEN_COOLDOWN + get_cached_insights_response, router delegation, tests
- abb4d710e: Task 3, frontend anyGenerating guard, comments, CHANGELOG

## RED / mutation observations

- Task 1: new concurrency test failed RED before implementation (`assert 2 == 1`, two LLM calls). With the lock call commented out after implementing it, same failure; restored, passes (statuses `["cache_hit", "fresh"]`, one LLM call).
- Task 2: before the change, `test_import_within_cooldown_keeps_cache` (service) and `test_recent_import_within_cooldown_still_served` (router) failed. With the cooldown short-circuit mutated out (`if True:`), exactly those two failed again; restored, all 175 insights backend tests pass. Existing invalidation tests were backdated beyond 24h (not deleted); the GET /cached spy test now patches `app.services.insights_llm.get_latest_successful_log_for_user`.
- Task 3: new frontend test failed without the `anyGenerating` guard (1 failed, 4 passed); restored, endgames folder 69/69 passing.

## Verification

ruff format/check clean, `ty check app/ tests/ scripts/` clean, nesting-depth gate OK (1188 functions), insights backend tests 175 passed, frontend lint + endgames tests + `npm run build` green.

## Deviations from Plan

None - plan executed as written. (The plan-commit ledger from protocol 0c was not created; `commits: 3` was measured as `git rev-list --count bfed5e02e..HEAD`, where bfed5e02e was HEAD at start.)

## Known Stubs

None.

## Threat Flags

None. The advisory-lock key is (namespace, authenticated user id), never request input (T-qiz-02); the shared helper keeps the user_id filter (T-qiz-03).

## Self-Check: PASSED

Commits 6266dab2f, 1ff0d2ba8, abb4d710e exist on main; modified files present.
