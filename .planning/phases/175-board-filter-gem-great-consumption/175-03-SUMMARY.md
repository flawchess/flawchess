---
phase: 175-board-filter-gem-great-consumption
plan: 03
subsystem: ui
tags: [react, typescript, svg, theme, gem-great]

# Dependency graph
requires:
  - phase: 175-board-filter-gem-great-consumption
    provides: "175-02: EvalPoint.best_move_tier/maia_prob backend read path — this plan mirrors those fields on the TS EvalPoint and builds the frontend rendering primitives that will consume them"
provides:
  - "GREAT_ACCENT (theme.ts) + GREAT_GLYPH (greatGlyph.ts) — single blue color source for the great tier, one-record-two-consumers shape"
  - "GreatMoveIcon — custom SVG '!' badge (no lucide dependency), shape-compatible with GemIcon/SeverityGlyphIcon"
  - "classifyGreat + GREAT_MAIA_MAX_PROB (0.5) in gemMove.ts — fallback-only live-engine classifier, same C2 gate as classifyGem, over the (0.20, 0.50] maia_prob band"
  - "'great' MoveQuality bucket + colorForQuality/bucketKeyForQuality cases"
  - "TS EvalPoint.best_move_tier / maia_prob mirroring the Plan 02 backend schema"
  - "SquareMarker.great (board corner badge), GemMoveBadge tier prop, UnifiedMovePopover.isGreat, VariationTree FlawMarkerEntry.great* fields — great renders on every surface gem already renders on"
affects: [175-04, 175-05]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "tier prop on a shared badge component (GemMoveBadge tier='gem'|'great') instead of a sibling component, avoiding drift between two near-identical badges"
    - "One-record-two-consumers glyph module (greatGlyph.ts) extended to a third instance (gem, book, great) — same shape every time"
    - "Precedence chain extended in-place: severity > gem/great > book, great inserted in the same tier as gem (not a new tier)"

key-files:
  created:
    - frontend/src/lib/greatGlyph.ts
    - frontend/src/components/icons/GreatMoveIcon.tsx
  modified:
    - frontend/src/lib/theme.ts
    - frontend/src/lib/gemMove.ts
    - frontend/src/lib/moveQuality.ts
    - frontend/src/types/library.ts
    - frontend/src/components/analysis/MovesByRatingChart.tsx
    - frontend/src/components/board/boardMarkers.tsx
    - frontend/src/components/analysis/GemMoveBadge.tsx
    - frontend/src/components/analysis/UnifiedMovePopover.tsx
    - frontend/src/components/analysis/VariationTree.tsx
    - frontend/src/lib/__tests__/gemMove.test.ts
    - frontend/src/components/board/__tests__/boardMarkers.test.tsx

key-decisions:
  - "GREAT_ACCENT = oklch(0.58 0.18 220) — a distinct blue hue from gem's violet (290), Stockfish's blue (255), and Book's desaturated blue-grey (250); higher chroma than Book (0.04) so it reads as an alert-tier badge, not a muted context marker."
  - "GreatMoveIcon draws a hand-rolled SVG '!' (vertical line + dot) rather than a lucide icon, per D-02 — chess.com's 'Great Move' glyph has no direct lucide equivalent."
  - "Modified frontend/src/components/analysis/MovesByRatingChart.tsx (colorForQuality) even though it is not in the plan's files_modified frontmatter list — the plan's own Task 1 action text ('add colorForQuality/bucketKeyForQuality cases returning GREAT_ACCENT') and the plan's must_haves truth ('Great appears on ... the eval/moves-by-rating chart') both require it; colorForQuality lives in this file, not moveQuality.ts. Treated as a plan-list omission, not scope creep — the plan's own words already called for it."
  - "GemMoveBadge extended with a tier: 'gem' | 'great' prop (default 'gem') rather than a sibling GreatMoveBadge component, per 175-PATTERNS.md's explicit recommendation to avoid badge drift; both existing call sites (VariationTree's gem branch) are unchanged since tier defaults to 'gem'."

requirements-completed: [BOARD-01]

coverage:
  - id: D1
    description: "GREAT_ACCENT/GREAT_GLYPH/GreatMoveIcon primitives exist; classifyGreat classifies a live maia_prob in the (GEM_MAIA_MAX_PROB, GREAT_MAIA_MAX_PROB] band with the same C2 only-good-move gate as gem, fallback-path only"
    requirement: "BOARD-01"
    verification:
      - kind: unit
        ref: "frontend/src/lib/__tests__/gemMove.test.ts::classifyGreat (11 tests: qualifying band, GREAT_MAIA_MAX_PROB=0.5, gem-ceiling false, great-ceiling false, shared-C2-margin false, null/not-best guards, (0.20,0.50] half-open boundary both ends, null bestEs/secondBestEs)"
        status: pass
    human_judgment: false
  - id: D2
    description: "TS EvalPoint mirrors the backend exactly: best_move_tier 'gem'|'great'|null, maia_prob number|null"
    requirement: "BOARD-01"
    verification:
      - kind: unit
        ref: "npx tsc -b (clean — confirms the literal union type matches usage across the codebase)"
        status: pass
    human_judgment: false
  - id: D3
    description: "Great renders on every surface gem already renders on: board corner badge (SquareMarker.great), move-list badge (GemMoveBadge tier='great'), popover (UnifiedMovePopover.isGreat), variation tree (FlawMarkerEntry.great*), and the moves-by-rating chart (colorForQuality), with severity > gem/great > book precedence and no hard-coded colors"
    requirement: "BOARD-01"
    verification:
      - kind: unit
        ref: "frontend/src/components/board/__tests__/boardMarkers.test.tsx (4 new tests: great badge renders blue circle + '!' glyph no severity text; gem-vs-great precedence tie, gem wins by ordering; great-vs-book precedence, great wins)"
        status: pass
      - kind: unit
        ref: "cd frontend && npm test -- --run (full suite, 2242 tests, all passing — no regression in any consumer of theme.ts/moveQuality.ts/gemMove.ts/boardMarkers.tsx/GemMoveBadge.tsx/UnifiedMovePopover.tsx/VariationTree.tsx)"
        status: pass
    human_judgment: false

# Metrics
duration: 15min
completed: 2026-07-16
status: complete
---

# Phase 175 Plan 03: Great-Tier Frontend Primitives + Board/Badge/Popover/Variation-Tree Consumption Summary

**Introduces the "great" move tier to the frontend for the first time — a distinct blue (`GREAT_ACCENT`, `oklch(0.58 0.18 220)`) badge family with a custom hand-drawn "!" glyph, a fallback-only `classifyGreat` classifier, and a great branch on every surface gem already renders on (board, move-list badge, popover, variation tree, moves-by-rating chart).**

## Performance

- **Duration:** 15 min
- **Started:** 2026-07-16T20:59:00Z (approx, immediately following 175-02)
- **Completed:** 2026-07-16T21:14:00Z
- **Tasks:** 2
- **Files modified:** 11 (2 created, 9 modified)

## Accomplishments
- `GREAT_ACCENT` (theme.ts, blue oklch) and `GREAT_GLYPH` (greatGlyph.ts, `{ color }`) — a distinct hue (220) from gem's violet (290), Stockfish's blue (255), and Book's desaturated blue-grey (250), with higher chroma than Book so it reads as an alert-tier badge.
- `GreatMoveIcon` (icons/GreatMoveIcon.tsx) — a custom inline SVG "!" (vertical stroke + dot) on a blue circle, NOT a lucide icon (D-02: chess.com's "Great Move" mark has no direct lucide equivalent), matching GemIcon's/BookIcon's prop shape and accessible-`<title>` convention.
- `classifyGreat` + `GREAT_MAIA_MAX_PROB = 0.5` in gemMove.ts — the same C2 only-good-move gate as `classifyGem`, applied over the `(GEM_MAIA_MAX_PROB, GREAT_MAIA_MAX_PROB]` half-open band; fallback-path only (D-03c), with a cross-reference comment to the backend's `best_move_candidates.py` constants added to both `GEM_MAIA_MAX_PROB` and the new `GREAT_MAIA_MAX_PROB` for future-retune discoverability.
- `'great'` added to the `MoveQuality` union with `bucketKeyForQuality` (moveQuality.ts) and `colorForQuality` (MovesByRatingChart.tsx) cases, so the moves-by-rating chart colors great moves distinctly instead of falling through to the pending/neutral color.
- `EvalPoint.best_move_tier: 'gem' | 'great' | null` and `EvalPoint.maia_prob: number | null` added to `types/library.ts`, mirroring the Plan 02 backend Pydantic schema field-for-field.
- `SquareMarker.great` (boardMarkers.tsx) — blue circle + the same hand-drawn "!" glyph markup as `GreatMoveIcon.tsx` (inlined via a nested `<svg>` so the two never drift), reusing `GEM_ICON_DIAMETER_RATIO` verbatim, inserted in the same precedence tier as gem (`severity > gem/great > book`).
- `GemMoveBadge.tsx` extended with a `tier: 'gem' | 'great'` prop (default `'gem'`, so existing call sites are unchanged) selecting the icon and per-tier popover copy (heading + rule sentence), rather than a duplicate `GreatMoveBadge` component — the codebase's own pattern map explicitly recommended this to avoid badge drift.
- `UnifiedMovePopover.tsx` gains `isGreat`, mirroring the existing `isGem` row with `GREAT_ACCENT`/`GreatMoveIcon` and copy-minimalism-style prose ("Great — players at this rating rarely find this.").
- `VariationTree.tsx`: `FlawMarkerEntry` gains `great`/`greatMaiaProbability`/`greatElo`/`greatByOpponent` fields; `resolveMarkerIcon` gains a great branch in the `severity > gem/great > book` precedence chain; `MoveListMarker` renders `GemMoveBadge` with `tier="great"` for great entries.

## Task Commits

Each task was committed atomically:

1. **Task 1: Great-tier primitives + TS EvalPoint mirror + live-fallback classifier** - `96da758b` (feat)
2. **Task 2: Great branch on board, badge, popover, and variation-tree surfaces** - `54b0981c` (feat)

## Files Created/Modified
- `frontend/src/lib/theme.ts` - `GREAT_ACCENT` constant
- `frontend/src/lib/greatGlyph.ts` - `GREAT_GLYPH` (new file)
- `frontend/src/components/icons/GreatMoveIcon.tsx` - custom SVG "!" badge icon (new file)
- `frontend/src/lib/gemMove.ts` - `classifyGreat`, `GREAT_MAIA_MAX_PROB`, cross-reference comments
- `frontend/src/lib/moveQuality.ts` - `'great'` `MoveQuality` member + `bucketKeyForQuality` case
- `frontend/src/components/analysis/MovesByRatingChart.tsx` - `colorForQuality` `'great'` case (plan-list omission, see Decisions)
- `frontend/src/types/library.ts` - `EvalPoint.best_move_tier` / `EvalPoint.maia_prob`
- `frontend/src/components/board/boardMarkers.tsx` - `SquareMarker.great` field + render branch
- `frontend/src/components/analysis/GemMoveBadge.tsx` - `tier` prop, per-tier icon/copy
- `frontend/src/components/analysis/UnifiedMovePopover.tsx` - `isGreat` prop + row
- `frontend/src/components/analysis/VariationTree.tsx` - `FlawMarkerEntry.great*` fields, `resolveMarkerIcon` great branch
- `frontend/src/lib/__tests__/gemMove.test.ts` - `classifyGreat` test suite (11 tests)
- `frontend/src/components/board/__tests__/boardMarkers.test.tsx` - great-marker tests (4 tests)

## Decisions Made
- `GREAT_ACCENT = oklch(0.58 0.18 220)` (blue) — deliberately distinct from gem's violet (290), Stockfish's blue (255), and Book's desaturated blue-grey (250); higher chroma than Book (0.04) so great reads as an alert-tier badge rather than a muted context marker.
- `GreatMoveIcon` draws a hand-rolled SVG "!" (line + dot) instead of using a lucide icon, per D-02 — no direct lucide equivalent exists for chess.com's "Great Move" mark.
- Modified `frontend/src/components/analysis/MovesByRatingChart.tsx` (`colorForQuality`) even though it is not listed in the plan's `files_modified` frontmatter — the plan's own Task 1 action text ("add colorForQuality/bucketKeyForQuality cases returning GREAT_ACCENT") and its `must_haves.truths` ("Great appears on ... the eval/moves-by-rating chart") both require it, and `colorForQuality` has always lived in `MovesByRatingChart.tsx`, not `moveQuality.ts`. Treated as a plan file-list omission rather than scope creep, since the plan's own action text and truths already called for the change.
- `GemMoveBadge` extended with a `tier` prop rather than a sibling `GreatMoveBadge` component — 175-PATTERNS.md explicitly recommends the shared-component approach to avoid drift between two near-identical badges; both approaches satisfy the plan's D-02b requirement.

## Deviations from Plan

None beyond the file-list note above (which is a plan-list omission, not unplanned scope — see Decisions). No architectural changes, no auto-fixed bugs, no blocking issues encountered.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- The great-tier frontend primitives (GREAT_ACCENT, GREAT_GLYPH, GreatMoveIcon, classifyGreat, the `'great'` MoveQuality bucket) and every rendering surface (board, badge, popover, variation tree, chart) are ready to consume a `best_move_tier: 'great'` value the moment it's wired onto the mainline.
- Per the plan's explicit negative constraint, this plan does NOT wire `classifyGreat`/`classifyGem` onto the Analysis mainline — the stored (analyzed) path must never call these fallback classifiers, and neither `Analysis.tsx` nor `useGemSweep.ts` were touched. That wiring (switching mainline reads to `EvalPoint.best_move_tier`, retiring/demoting `useGemSweep.ts`) is Plan 04's job.
- The Library game-filter UI toggles (consuming Plan 01's `has_gem`/`has_great` query params) also remain for a subsequent 175-series plan.

---
*Phase: 175-board-filter-gem-great-consumption*
*Completed: 2026-07-16*

## Self-Check: PASSED

All 13 created/modified source/test files confirmed present on disk; both
task commits (`96da758b`, `54b0981c`) confirmed in git history.
