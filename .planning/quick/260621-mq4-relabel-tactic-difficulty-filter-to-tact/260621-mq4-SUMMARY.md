---
quick_id: 260621-mq4
status: complete
---

# Quick Task 260621-mq4 — Summary

Relabel the tactic filter, switch to 1-12 numbering, and surface tactic depth on
the library miniboards (game card + flaw card).

## What changed

### Backend — expose per-flaw tactic depth in the API
The `missed_tactic_depth` / `allowed_tactic_depth` columns already existed in
`game_flaws` (used by the depth filter) but were never returned. Now exposed,
gated identically to the tactic motif chip (so depth is non-null exactly when its
chip shows):
- `app/schemas/library.py` — added both depth fields to `FlawMarker` and `FlawListItem`.
- `app/repositories/library_repository.py` — populate depth in the FlawListItem builder.
- `app/services/library_service.py` — extended the `tactic_by_ply` payload
  (new `_TacticByPlyEntry` 6-tuple type alias) and passed depth into `FlawMarker`.

### Frontend — relabel + 1-based display
- `frontend/src/lib/tacticDepth.ts` — added `DEPTH_DISPLAY_OFFSET = 1` +
  `toDisplayDepth()`; `formatDepthSummary` now renders 1..12. Internal values,
  slider domain, presets, and API query params stay 0-based.
- `TacticDepthFilter.tsx` — label "Tactic Difficulty" → **"Tactic Depth"**; info
  copy updated to 1..12 ("1 = immediate").
- `frontend/src/types/library.ts` — mirrored the new depth fields.

### Frontend — depth badge on miniboards
- `MiniBoard.tsx` — `MiniBoardArrow` gained an optional `label`; the arrow overlay
  draws it as a colored disc + white number at the arrow's target square (on top
  of the arrowhead).
- `LazyMiniBoard.tsx` — widened the arrow prop type.
- `FlawCard.tsx` — blue best-move arrow → missed-tactic depth; flaw-move arrow →
  allowed-tactic depth (both as `toDisplayDepth`).
- `LibraryGameCard.tsx` — built a ply→depths map from `flaw_markers` and attached
  the same labels to the hover-scrub arrows (shared `boardArrows` covers both the
  mobile and desktop bodies).

### Tests
- `tacticDepth.test.ts` — updated summary expectations to 1-based; added a
  `toDisplayDepth` case.
- `FlawCard.test.tsx` — fixture gains the new depth fields; added two badge tests
  (renders "5" for missed_tactic_depth 4; no badge when null).
- `LibraryGameCard.test.tsx` — `marker()` fixture gains the new depth fields.

## Verification
- Backend: `uv run ty check app/` ✓; `pytest -k "library or flaw or tactic"` → 435 passed.
- Frontend: `npm run lint` ✓, `npm test -- --run` → 1075 passed, `npm run build`
  (full tsc) ✓, `npm run knip` ✓.

## Notes / deviations
- The pairing (blue best-move arrow ↔ missed depth, flaw arrow ↔ allowed depth)
  follows the existing arrow semantics — no design change there.
- One self-caught slip: an early edit to `FlawListItem` dropped `best_move`; tsc
  flagged it and it was restored before any commit.

## Commits
- `04a85e20` feat(library): expose per-flaw tactic depth in API
- `67599a79` feat(library): relabel filter to Tactic Depth, show 1-12
- `7df1b056` feat(library): show tactic depth badge on miniboard arrows
