---
quick_id: 260508-q1z
slug: auto-load-cached-llm-endgame-report
date: 2026-05-08
status: complete
---

# Quick Task 260508-q1z — Summary

Auto-load cached LLM endgame report on Endgames page mount and filter change.

## What changed

### Backend
- `app/routers/insights.py` — added `GET /insights/endgame/cached`. Mirrors the Tier-1 structural cache lookup from `app/services/insights_llm.py:1830-1857`: `get_latest_successful_log_for_user` + `get_latest_completed_import_with_games_at` staleness check + `_maybe_strip_overview`. Returns 200 with `status="cache_hit"` on hit, 404 on miss. Never invokes `compute_findings`, never calls the LLM, never accounts against the rate-limit budget. Skips `_validate_full_history_filters` — non-default filters and custom opponent gaps just naturally 404 because the cache key is `(user, prompt_version, model, opponent_strength_preset)`.
- `tests/test_insights_router.py` — added `TestCachedEndpoint` covering: 401 unauth, 200 cache_hit (with compute_findings spy assertion), 404 miss, 404 on non-default filters, 404 on custom gap, and 404 on import-invalidated cache row.

### Frontend
- `frontend/src/hooks/useEndgameInsights.ts` — extracted shared `buildInsightsParams` helper; added `useCachedEndgameInsights(filters)` query hook. Returns the cached response on 200, `null` on 404 (silently), throws on other errors. `staleTime: 5 min`, `refetchOnWindowFocus: false`, no retry.
- `frontend/src/pages/Endgames.tsx` — fires `useCachedEndgameInsights(appliedFilters)` and upserts any returned response into `insightsCache`, so `matchingInsights` renders the cached report without a click. Existing POST/Generate flow is untouched.
- `frontend/src/hooks/__tests__/useEndgameInsights.test.tsx` — added two tests for the new hook (200 cache_hit returns response with correct params; 404 returns null without surfacing an error).

## Verification

- `uv run ruff check app/ tests/` — clean
- `uv run ty check app/ tests/` — clean
- `uv run pytest` — 1267 passed, 6 skipped
- `cd frontend && npm test -- --run` — 291 passed
- `cd frontend && npx eslint src/hooks/useEndgameInsights.ts src/hooks/__tests__/useEndgameInsights.test.tsx src/pages/Endgames.tsx` — clean
- `cd frontend && npx tsc --noEmit` — clean
- `cd frontend && npm run knip` — clean

## Notes

- The custom (non-preset) opponent gap path returns 404, not 400. The POST endpoint returns 400 because it's user-facing on a click; the GET endpoint is fired automatically and surfaces silently.
- `_PROMPT_VERSION` and `_maybe_strip_overview` are accessed via `insights_llm.` underscore-prefix attribute access. The existing test suite already uses `insights_llm._PROMPT_VERSION` the same way, so this is an established pattern. Worth promoting to public symbols later if more consumers appear.
