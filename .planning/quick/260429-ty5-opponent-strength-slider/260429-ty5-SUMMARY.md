---
quick_id: 260429-ty5
slug: opponent-strength-slider
description: Replace 4-option Opponent Strength ToggleGroup with a dual-handle range slider plus preset chips
date: 2026-04-29
status: complete
commit: 124237b
---

# Quick Task 260429-ty5: Opponent Strength Range Slider — Summary

## What changed

Replaced the four-bucket `OpponentStrength` ToggleGroup (`any` / `stronger` / `similar` / `weaker`) with a dual-handle range slider over `[−200, +200]` ELO gap, snapping to multiples of 50, with four preset chips above (Any / Stronger / Similar / Weaker) that snap the slider. Slider endpoints map to unbounded (`null`) on the API, matching Spike 001.

## Backend (commits f99d35a, 123d21f, 08363e6)

- **New module** `app/core/opponent_strength.py` — preset/range mapping helpers (`derive_preset`, `preset_to_range`, `PRESET_THRESHOLD`). Lives in `core` so it can be imported from routers, services, and the LLM cache layer without violating the "no repository imports from services" layering rule.
- **`app/repositories/query_utils.py`** — `apply_game_filters` now takes `opponent_gap_min: int | None` and `opponent_gap_max: int | None` (None = unbounded). Filters by `opp_rating - user_rating >= gap_min` / `<= gap_max`. Removed `DEFAULT_ELO_THRESHOLD` and the `opponent_strength` Literal param.
- **Schemas** (`app/schemas/openings.py`, `opening_insights.py`) — replaced `opponent_strength` Literal field with `opponent_gap_min` / `opponent_gap_max` int fields.
- **Repositories** (`endgame_repository.py`, `openings_repository.py`, `stats_repository.py`) — every function that took `opponent_strength` + `elo_threshold` now takes `opponent_gap_min` + `opponent_gap_max`. The two duplicated inline filter blocks in `openings_repository.py` were rewritten to use the new range form.
- **Services** (`endgame_service.py`, `openings_service.py`, `opening_insights_service.py`, `stats_service.py`) — all signatures updated to forward the new gap params. `insights_service.compute_findings` translates `FilterContext.opponent_strength` (preset name) → range via `preset_to_range` before calling `get_endgame_overview`.
- **Routers** (`endgames.py`, `stats.py`, `insights.py`) — accept `opponent_gap_min` / `opponent_gap_max` query params. The endgame insights endpoint additionally derives the preset name (`derive_preset`) and rejects custom (non-preset) ranges with HTTP 400 — keeping the LLM cache key (still keyed on preset name) stable.
- **LLM cache** (`app/schemas/llm_log.py`, `llm_log_repository.py`, `services/insights_llm.py`) — unchanged; still uses preset-name string for cache key + scoping caveat. The router enforces "preset only" for this endpoint.
- **Tests** updated: `test_stats_router.py`, `test_insights_router.py`, `tests/repositories/test_opening_insights_repository.py`. All 1165 backend tests pass.

## Frontend (commit 124237b)

- **New shadcn-style component** `frontend/src/components/ui/slider.tsx` — wraps `radix-ui/Slider` with two-thumb support, `touch-action: none`, 24px thumbs on a 44px-min hit area. Per-thumb aria-labels via the `thumbLabels` prop.
- **New helper** `frontend/src/lib/opponentStrength.ts` — slider domain constants (`SLIDER_MIN=-200`, `SLIDER_MAX=200`, `SLIDER_STEP=50`), preset definitions, and helpers: `derivePreset`, `presetToRange`, `sliderToRange`, `rangeToSlider`, `formatRangeSummary`, `rangeToQueryParams`.
- **New filter component** `frontend/src/components/filters/OpponentStrengthFilter.tsx`:
  - Header row with label + summary text (preset name in brand color, raw range otherwise).
  - 4 preset chips (44px tall on mobile, 28px on sm+).
  - Radix dual-handle slider with `minStepsBetweenThumbs=1`.
  - Endpoint tick labels `≤−200` / `0` / `≥+200`.
  - InfoPopover explaining presets and unbounded endpoints.
- **`FilterPanel.tsx`**:
  - `FilterState.opponentStrength` shape changed from `OpponentStrength` literal to `OpponentStrengthRange = { min: number | null; max: number | null }`.
  - `DEFAULT_FILTERS.opponentStrength = { min: null, max: null }` (= "Any" preset).
  - `areFiltersEqual` extended with structural compare for the range object.
  - Inline ToggleGroup replaced with `<OpponentStrengthFilter />`.
- **API client** (`frontend/src/api/client.ts`) — `buildFilterParams` now accepts `opponent_strength: OpponentStrengthRange` and emits `opponent_gap_min` / `opponent_gap_max` query params (omitted when null).
- **Hooks** (`useStats`, `useEndgames`, `useEndgameInsights`, `useOpeningInsights`, `useOpenings`, `useNextMoves`) — all wired to send the new range. Query keys include `range.min` and `range.max` so cache invalidation tracks the new shape.
- **`EndgameInsightsBlock`** — Generate button now disabled when `derivePreset(filters.opponentStrength) === null` (custom range), with tooltip "Snap opponent strength to a preset". This mirrors the router-side 400 enforcement.
- **Bookmarks** — `TimeSeriesRequest` accepts `opponent_gap_min` / `opponent_gap_max` instead of `opponent_strength`. `pages/Openings.tsx` uses `rangeToQueryParams` to spread the gap params into the request.
- **Tests** — fixtures in `useEndgameInsights.test.tsx`, `useOpeningInsights.test.tsx`, `EndgameInsightsBlock.test.tsx`, `OpeningInsightsBlock.test.tsx` updated. All 211 frontend tests pass.

## Design decisions (locked from spike)

- Slider domain `[-200, +200]`, step 50; both handles default to extremes (= "Any" preset, no filter).
- Endpoints unbounded: handle at `-200` → `null` (no lower bound); handle at `+200` → `null` (no upper bound).
- Preset ranges:
  - **Any** → `{min: null, max: null}`
  - **Stronger** → `{min: 50, max: null}`
  - **Similar** → `{min: -50, max: 50}`
  - **Weaker** → `{min: null, max: -50}`
- Inclusive bounds (gap ≥ min AND gap ≤ max). Differs slightly from the prior strict-similar SQL — a gap of exactly +50 now matches both Stronger and Similar presets, but presets are user-facing shortcuts, not partitions.
- `minStepsBetweenThumbs={1}` — handles can sit adjacent (e.g. `[-50, 0]`) but not on the same value.
- LLM endgame insights endpoint accepts only the four preset ranges; custom ranges return 400. The frontend disables the Generate button proactively.

## Verification

- `uv run ruff check app/ tests/` — clean
- `uv run ty check app/ tests/` — clean
- `uv run pytest tests/` — 1165 passed
- `npm run lint` — 0 errors (3 unrelated coverage-file warnings)
- `npm run build` — success
- `npm test -- --run` — 211 passed
- `npm run knip` — clean

## No DB migration

Nothing is stored as `opponent_strength` in any column. `LlmLog.filter_context` is JSONB and continues to store the preset name string — unchanged on the cache side.

## Files

- New: `app/core/opponent_strength.py`, `frontend/src/components/ui/slider.tsx`, `frontend/src/components/filters/OpponentStrengthFilter.tsx`, `frontend/src/lib/opponentStrength.ts`
- Modified backend: `app/repositories/{query_utils,endgame_repository,openings_repository,stats_repository}.py`, `app/routers/{insights,endgames,stats}.py`, `app/schemas/{openings,opening_insights}.py`, `app/services/{endgame_service,openings_service,opening_insights_service,stats_service,insights_service}.py`, `tests/{test_stats_router,test_insights_router,repositories/test_opening_insights_repository}.py`
- Modified frontend: `frontend/src/api/client.ts`, `frontend/src/components/filters/FilterPanel.tsx`, `frontend/src/components/insights/{EndgameInsightsBlock,OpeningInsightsBlock,OpeningInsightsBlock.test}.tsx`, `frontend/src/components/insights/__tests__/EndgameInsightsBlock.test.tsx`, `frontend/src/hooks/{useStats,useNextMoves,useOpeningInsights,useOpenings}.ts`, `frontend/src/hooks/__tests__/{useEndgameInsights,useOpeningInsights}.test.tsx`, `frontend/src/pages/Openings.tsx`, `frontend/src/types/{api,position_bookmarks}.ts`

## Follow-ups (not in scope)

- Real-phone mobile UX validation per spike checklist (`.planning/todos/pending/opponent-filter-mobile-ux-check.md`).
