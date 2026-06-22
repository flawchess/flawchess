---
quick_id: 260620-l5k
status: complete
phase: 130
commits:
  - 8a58280b  # backend: depth [min,max] range + mate exemption removed
  - 6682a145  # frontend: depth range slider 0-11
---

# Quick Task 260620-l5k — Summary

Converted the **Tactic Difficulty** filter from a single-handle "full moves" cap
into a two-handle **range slider in depth units** (0-based ply, domain 0–11).

## What changed

**Decision (asked + locked):** mates now **obey the depth range** — the Phase 129
D-04 "forced mates always show" exemption was removed (user picked "Bound mates too").

**Backend** (`8a58280b`)
- `_depth_ok(depth_col, motif_col, max)` → `_depth_in_range(depth_col, min, max)`:
  `depth >= min AND depth <= max`, each side optional, no mate exemption.
- Threaded `min_tactic_depth` through `build_flaw_filter_clauses`, `query_flaws`,
  `apply_game_filters`, `get_library_flaws`, and the `/library/flaws` router
  (`ge=0, le=11` on both bounds — **0 is now selectable**; was `ge=1`).
- Flipped the two `test_mate_exemption_present_*` tests to assert the exemption is
  gone (no `OR` in a single-orientation depth clause); added min-bound tests.

**Frontend** (`6682a145`)
- `lib/tacticDepth.ts` rewritten around a `{min, max}` range: `DEPTH_MIN=0`,
  `DEPTH_MAX=11`, presets Beginner `0–1` / Intermediate `0–5` / Advanced `0–11`,
  `derivePreset/presetToRange/sliderToRange/formatDepthSummary/depthToQueryParams`.
- `TacticDepthFilter.tsx` → two-handle `Slider` (domain 0–11, `minStepsBetweenThumbs={0}`
  so `0–0` is selectable), tick labels `0`/`11`, updated info copy (depth/plies).
- Store now holds `tacticDepthMin` + `tacticDepthMax` (dropped `tacticDepthPreset`);
  preset chip + filter-dot derive from the actual range (non-default ≠ `{0,5}`).
- `useLibrary`/`client.ts` send `min_tactic_depth` + `max_tactic_depth`.
- Rewrote `tacticDepth.test.ts`; updated store/FlawsTab/TacticComparisonGrid mocks.

## Verification

- `ruff format`/`ruff check`/`ty check app/ tests/` — clean.
- Backend: `test_library_repository`, `test_query_utils`, `test_library_router` — 102 passed.
- Frontend: `npx tsc -b` clean, `npm run lint` clean, `npm run knip` clean,
  full `npm test` — **1049 passed**.

## Not done / follow-up

- No live browser UAT (covered by component + integration tests). Offer stands if
  the user wants a visual check of the 0–0 selection and preset chips.
- `DB depth max = 11` confirmed empirically on the dev DB at implementation time.
