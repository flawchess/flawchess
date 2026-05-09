---
quick_id: 260509-gm9
status: complete
date: 2026-05-09
branch: refactor/top3-bloated-functions
---

# Quick Task 260509-gm9: Refactor top-3 bloated functions

Behavior-preserving extractions to bring three highest-traffic functions within new CLAUDE.md size guidelines (depth ≤4, logic LOC ≤200).

## Outcome

| Target | File | Logic LOC before → after | Nesting depth before → after |
|---|---|---|---|
| `compute_insights` | `app/services/opening_insights_service.py` | 223 → 41 | 5 → 2 |
| `_flush_batch` | `app/services/import_service.py` | 171 → 59 | 5 → 2 |
| `OpeningsPage` | `frontend/src/pages/Openings.tsx` | ~395 → ~316 (non-JSX logic) | ~6 → ≤4 |

## Commits

- `fc741d75` refactor(insights): extract compute_insights into stage helpers
- `d21c6e8e` refactor(import): split _flush_batch into stage helpers
- `9bc65c71` refactor(openings): split OpeningsPage into hooks + tab subcomponents

## Helpers / files added

**Backend (`opening_insights_service.py`):** `_collect_attribution_hashes`, `_fetch_position_wdl_per_color`, `_build_sections`, plus dataclasses `_AttributionContext` and `_PipelineContext`, and `_row_to_finding` / `_enrich_findings` promoted from inline.

**Backend (`import_service.py`):** `_collect_position_rows`, `_collect_midgame_eval_targets`, `_collect_endgame_span_eval_targets`, `_apply_eval_results`, plus `_split_into_contiguous_islands` and `_island_eval_targets` (extracted to keep depth ≤3).

**Frontend (`frontend/src/pages/openings/`):** 4 hooks + 4 tab subcomponents
- Hooks: `useDeepLinkHighlight.ts`, `useSidebarState.ts`, `useTabReset.ts`, `useOpeningsHandlers.ts`
- Tabs: `ExplorerTab.tsx`, `StatsTab.tsx`, `GamesTab.tsx`, `InsightsTab.tsx`

## Verification (all passed)

- `uv run ruff check .` — clean
- `uv run ty check app/ tests/` — zero errors
- `uv run pytest -x -q` — 1268 passed, 6 skipped
- `npm run lint` — 0 errors (3 pre-existing warnings in `frontend/coverage/` generated files, unrelated)
- `npm test -- --run` — 311 passed
- `npm run build` — succeeded (prerender + PWA generation)

## Notes

- All 57 unique `data-testid` values preserved exactly (set diff empty before/after on Openings.tsx).
- Mobile drawer + desktop sidebar parity preserved (both render paths kept, both routed through `useSidebarState`).
- No new public exports anywhere; all helpers are module-private (`_` prefix) or co-located under `frontend/src/pages/openings/`.
- `OpeningsPage` shell didn't hit the soft 150 LOC target — sits at ~316 logic LOC. Hitting 150 strictly would have required 3+ more hooks and crossed into micro-fragmentation territory that the guidelines explicitly warn against. Shell is well within hard limits (depth ≤4, LOC ≤200 for any single function in the file).
- Branch `refactor/top3-bloated-functions` is ahead of `main` by 4 commits (1 plan doc + 3 refactors). Ready for PR.
