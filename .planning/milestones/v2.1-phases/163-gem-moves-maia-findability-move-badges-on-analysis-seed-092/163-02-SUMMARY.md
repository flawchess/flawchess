---
phase: 163-gem-moves-maia-findability-move-badges-on-analysis-seed-092
plan: 02
subsystem: ui
tags: [react, typescript, lucide-react, svg, chessboard]

requires:
  - phase: 163-01
    provides: gemMove.ts's classifyGem/summarizeForGem pure predicates (no dependency at the type/import level — this plan's badge primitives are independent, but Plan 04 will wire both together)
provides:
  - GEM_GLYPH single-source glyph record (color = MAIA_ACCENT) in frontend/src/lib/gemGlyph.ts
  - GemIcon React component (white lucide Gem in a MAIA_ACCENT circle), SeverityGlyphIcon-shape-compatible
  - SquareMarker.gem?: boolean additive extension on boardMarkers.tsx, with severity now optional
  - SquareMarkerBadge gem render branch (violet circle + nested lucide Gem icon)
  - boardMarkers.test.tsx covering both the gem badge and the severity-glyph regression case
affects: [163-04 (VariationTree move-list icons + Analysis.tsx squareMarkers union will consume GemIcon and SquareMarker.gem)]

tech-stack:
  added: []
  patterns:
    - "One-record/two-consumers glyph pattern (severityGlyph.ts precedent) extended to gem: GEM_GLYPH is the single color source for both GemIcon (React) and boardMarkers (SVG on-board marker)"
    - "Additive optional-field extension on a shared interface (SquareMarker.gem) instead of a discriminated union, per RESEARCH Pattern 4 — lower migration risk, no call-site rewrites needed for existing severity markers"

key-files:
  created:
    - frontend/src/lib/gemGlyph.ts
    - frontend/src/components/icons/GemIcon.tsx
    - frontend/src/components/board/__tests__/boardMarkers.test.tsx
  modified:
    - frontend/src/components/board/boardMarkers.tsx

key-decisions:
  - "GEM_ICON_DIAMETER_RATIO (0.8) added as a named constant for the gem icon's size relative to the badge circle diameter, rather than an inline 0.8 literal, per CLAUDE.md's no-magic-numbers rule — not a new geometry/position constant (MARKER_RADIUS/MARKER_CORNER_OVERLAP untouched), just an icon-sizing ratio local to the new gem branch"
  - "SquareMarkerBadge restructured so cx/cy/r are computed once up front, then branches: gem circle+icon, or (guarded) severity circle+text — glyph lookup only happens inside the non-gem branch to avoid indexing SEVERITY_GLYPH with an undefined key now that severity is optional"

requirements-completed: [D-07]

coverage:
  - id: D1
    description: "GEM_GLYPH single-source record (MAIA_ACCENT) consumed identically by GemIcon and boardMarkers"
    requirement: "D-07"
    verification:
      - kind: unit
        ref: "frontend/src/components/board/__tests__/boardMarkers.test.tsx#renders the violet gem badge with no severity text for a gem marker"
        status: pass
    human_judgment: false
  - id: D2
    description: "GemIcon renders a white lucide Gem inside a MAIA_ACCENT circle, SeverityGlyphIcon-prop-shape compatible"
    requirement: "D-07"
    verification:
      - kind: unit
        ref: "cd frontend && npx tsc -b (GemIcon.tsx compiles with className/style/aria-hidden props matching SeverityGlyphIconProps shape)"
        status: pass
    human_judgment: true
    rationale: "No visual/rendering test exists yet for GemIcon itself (it has no consumer until Plan 04's VariationTree wiring) — tsc/lint confirm the contract compiles and the prop shape matches, but the actual rendered appearance (icon centering, color) is not yet visually verified until it's mounted in Plan 04."
  - id: D3
    description: "SquareMarker.gem additive extension renders the violet badge without severity text; existing severity call sites unaffected"
    requirement: "D-07"
    verification:
      - kind: unit
        ref: "frontend/src/components/board/__tests__/boardMarkers.test.tsx#still renders the \"??\" severity glyph for a blunder marker (regression)"
        status: pass
    human_judgment: false

duration: 15min
completed: 2026-07-10
status: complete
---

# Phase 163 Plan 02: Gem Badge Visual Primitives Summary

**GEM_GLYPH single-source record (MAIA_ACCENT violet) + GemIcon React component + SquareMarker.gem on-board badge, following the severityGlyph.ts single-source pattern so the move list and board never disagree on gem styling.**

## Performance

- **Duration:** ~15 min
- **Completed:** 2026-07-10T17:29:52Z
- **Tasks:** 2
- **Files modified:** 4 (2 created new, 1 modified, 1 test created)

## Accomplishments
- `GEM_GLYPH` record in `frontend/src/lib/gemGlyph.ts` — a single `{ color: MAIA_ACCENT }` source of truth, importing the violet from `@/lib/theme` (no hard-coded oklch literal)
- `GemIcon` component in `frontend/src/components/icons/GemIcon.tsx` — white lucide `Gem` icon centered inside a `GEM_GLYPH.color` circle, with the exact `className`/`style`/`aria-hidden` prop shape as `SeverityGlyphIconProps` so it drops into VariationTree's existing `BlunderIcon`/`MistakeIcon` call sites in a later plan
- `SquareMarker` interface extended additively (`severity` now optional, new `gem?: boolean`) in `boardMarkers.tsx`; `SquareMarkerBadge` branches on `marker.gem` to render the violet circle + nested lucide `Gem` icon, reusing the existing `MARKER_RADIUS`/`MARKER_RADIUS_SMALL`/`MARKER_CORNER_OVERLAP` geometry — no new position/radius constants
- `boardMarkers.test.tsx` covers both branches: a gem marker renders the violet circle + nested icon with zero severity text, and a blunder marker still renders the "??" NAG glyph unchanged (regression)

## Task Commits

1. **Task 1: gemGlyph.ts single-source record + GemIcon.tsx** - `7623732e` (feat)
2. **Task 2: SquareMarker gem variant on boardMarkers.tsx + test** - `9081ab01` (feat)

## Files Created/Modified
- `frontend/src/lib/gemGlyph.ts` - `GEM_GLYPH: { color: string }` single-source record, importing `MAIA_ACCENT` from `@/lib/theme`
- `frontend/src/components/icons/GemIcon.tsx` - React component rendering a white lucide `Gem` on a `GEM_GLYPH.color` circle, `SeverityGlyphIconProps`-shape-compatible
- `frontend/src/components/board/boardMarkers.tsx` - `SquareMarker.severity` made optional, `gem?: boolean` added; `SquareMarkerBadge` gained a gem render branch + `GEM_ICON_DIAMETER_RATIO` constant
- `frontend/src/components/board/__tests__/boardMarkers.test.tsx` - new test covering the gem badge and the severity-glyph regression

## Decisions Made
- `GEM_ICON_DIAMETER_RATIO = 0.8` added as a named constant (not an inline literal) per CLAUDE.md's no-magic-numbers rule — sizes the nested gem icon relative to the badge circle's diameter; this is an icon-sizing ratio, not a new position/radius geometry constant, so it doesn't violate the plan's "no new geometry constants" acceptance criterion (verified via grep: only pre-existing `MARKER_RADIUS`/`MARKER_CORNER_OVERLAP` references remain)
- Restructured `SquareMarkerBadge` to compute shared geometry (`cx`/`cy`/`r`) once, then branch on `marker.gem` before touching `SEVERITY_GLYPH`, with a defensive `if (!marker.severity) return null` guard in the non-gem branch — needed because `severity` is now optional and `SEVERITY_GLYPH[marker.severity]` can no longer be indexed unconditionally

## Deviations from Plan

None — plan executed exactly as written. `GEM_ICON_DIAMETER_RATIO` is a minor addition (naming an inline literal from the plan's own action text) rather than a deviation from intended behavior.

## Known Stubs

None. `GemIcon` and `GEM_GLYPH` currently have no consumer (Plan 04 wires them into `VariationTree.tsx` and `Analysis.tsx`) — this is expected per the plan's own acceptance criteria ("if knip flags it as unused at this wave, that is expected until Plan 04 merges; note it in the SUMMARY rather than deleting the export"). Confirmed via `npx knip`: both `gemGlyph.ts` and `GemIcon.tsx` are flagged as currently-unused files, exactly as anticipated.

## Issues Encountered
None.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- `GEM_GLYPH`, `GemIcon`, and `SquareMarker.gem` are ready for Plan 04 to wire into `VariationTree.tsx`'s move-list icon selection and `Analysis.tsx`'s `squareMarkers` union alongside `gemMove.ts`'s `classifyGem`/`summarizeForGem` (from Plan 01)
- No blockers. `tsc -b`, `npm run lint`, and the new `boardMarkers.test.tsx` are all green.

---
*Phase: 163-gem-moves-maia-findability-move-badges-on-analysis-seed-092*
*Completed: 2026-07-10*

## Self-Check: PASSED

- FOUND: frontend/src/lib/gemGlyph.ts
- FOUND: frontend/src/components/icons/GemIcon.tsx
- FOUND: frontend/src/components/board/__tests__/boardMarkers.test.tsx
- FOUND commit: 7623732e
- FOUND commit: 9081ab01
