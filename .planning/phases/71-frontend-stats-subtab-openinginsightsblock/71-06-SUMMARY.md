---
phase: 71-frontend-stats-subtab-openinginsightsblock
plan: "06"
subsystem: frontend-page-integration
tags: [opening-insights, page-integration, deep-link, openings-page]
dependency_graph:
  requires: [71-01, 71-05]
  provides: [openings-page-insights-wiring, handle-open-finding-deep-link]
  affects:
    - frontend/src/pages/Openings.tsx
tech_stack:
  added: []
  patterns: [usecallback-deep-link, conditional-render-on-most-played, mirror-handle-open-games]
key_files:
  created: []
  modified:
    - frontend/src/pages/Openings.tsx
decisions:
  - "handleOpenFinding mirrors handleOpenGames exactly — chess.loadMoves(entry_san_sequence) → setBoardFlipped → setFilters → navigate('/openings/explorer') → window.scrollTo(top:0). Same dep array [chess, navigate, setFilters]"
  - "Block visibility gated on mostPlayedData having at least one white or black opening (D-18 — proxy for 'has imported games'); avoids rendering empty insights for guest/unimported users"
  - "Block keeps sending color: 'all' regardless of the active page-level color filter — the InfoPopover copy explains this"
  - "handleOpenFinding does NOT set hoveredMove or any candidate-move highlight on arrival; existing red/green arrows from getArrowColor convey the candidate (D-14)"
metrics:
  shipped_in_pr: "#67 (5da9a3c)"
  page_lines_modified: ~30
ship_status: shipped
---

# Phase 71 Plan 06: Page Integration — Openings.tsx Wiring + UAT (retroactive summary)

**One-liner:** Final integration step — `OpeningInsightsBlock` wired into the Stats subtab as the first child, `handleOpenFinding` deep-links into the Move Explorer; UAT passed.

## Tasks Completed

| Task | Name | Files |
|------|------|-------|
| 1 | Add `handleOpenFinding` callback + render `<OpeningInsightsBlock>` at top of Stats subtab | frontend/src/pages/Openings.tsx |
| 2 | Manual UAT checkpoint — block placement, severity colors, deep-link semantics, mobile (375px), filter reactivity, error/loading states | (verified live) |

## What Was Built

- New imports in `Openings.tsx`: `OpeningInsightsBlock` from `@/components/insights/OpeningInsightsBlock` and the type `OpeningInsightFinding` from `@/types/insights`.
- `handleOpenFinding` `useCallback` defined alongside the existing `handleOpenGames`. Body: `chess.loadMoves(finding.entry_san_sequence)` → `setBoardFlipped(finding.color === 'black')` → `setFilters((prev) => ({ ...prev, color: finding.color, matchSide: 'both' as MatchSide }))` → `navigate('/openings/explorer')` → `window.scrollTo({ top: 0 })`. Dependency array `[chess, navigate, setFilters]`.
- `OpeningInsightsBlock` rendered as the first child of `statisticsContent`'s flex column, gated on `mostPlayedData && (mostPlayedData.white.length > 0 || mostPlayedData.black.length > 0)`. Above the bookmarks section.
- knip exceptions from prior plans resolved — every Phase 71 export is now consumed.

## Deviations from Plan

None — plan executed as written.

## UAT Outcome

Approved. All checklist items passed:
- Block placement (top of Stats, above bookmarks), heading + Lightbulb icon + InfoPopover.
- Four sections in fixed order (W/B Weaknesses → W/B Strengths) with severity-colored borders matching arrowColor.ts.
- Move-sequence trimming with `...` prefix on long entry sequences (D-05).
- Empty-section / empty-block / loading skeleton / error-state copy per spec.
- Deep-link click: URL → /openings/explorer, color filter switches, board renders entry FEN, board flipped if Black, scroll to top, candidate-move arrow color matches card border.
- Filter reactivity via debouncedFilters (no new wiring).
- Color filter independence — block always shows all four sections.
- Hidden when no most-played openings (no imported games proxy).
- Mobile 375px verified — no horizontal scroll, ≥44px touch targets, all data-testids in place.
- No console errors.

## Verification Gates

- `npm test -- --run` passes (full frontend suite)
- `npm run lint` passes
- `npm run build` succeeds
- `npm run knip` passes with no exceptions
- Backend `uv run pytest tests/services/test_opening_insights_service.py -x` still green

## Follow-ups Already Shipped

Subsequent quick tasks landed on top of Phase 71:
- 260427-g4a: Fix opening insights IllegalMoveError when entry_san_sequence does not start from initial position (#71 hotfix)
- 260427-h3u: Replace OpeningFindingCard whole-card deeplink with explicit Moves + Games links
- 260427-j41: Highlight candidate move in Move Explorer when arriving via Insights Moves link

## Self-Check

- [x] `OpeningInsightsBlock` imported and rendered conditionally at top of Stats subtab
- [x] `handleOpenFinding` defined and passed as `onFindingClick`
- [x] Block hidden when mostPlayedData is empty
- [x] All test/lint/build/knip gates green
- [x] UAT approved
- [x] Shipped as part of PR #67 (5da9a3c)
