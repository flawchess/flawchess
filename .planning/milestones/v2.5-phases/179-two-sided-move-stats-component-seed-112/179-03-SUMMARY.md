---
phase: 179-two-sided-move-stats-component-seed-112
plan: 03
subsystem: ui
tags: [react, typescript, frontend, library-card, analysis-board, vitest]

# Dependency graph
requires:
  - phase: 179-02-two-sided-move-stats-component
    provides: MoveStats.tsx shared component, moveStatsCounts.ts derivation, moverColorAtPly, Best/Good icons
provides:
  - MoveStats wired into LibraryGameCard.tsx (mobile compact row + expandable table, D-06)
  - MoveStats wired into AnalysisTagsPanel.tsx (empty-state early return dropped, D-03)
  - (category x side) cell cycling extended into both consumers' FlawRef unions (D-09)
  - user-scoped filter ring on player-side cells only (D-10, library)
  - GemGreatBadge.tsx + test deleted knip-clean; SeverityBadge.tsx preserved
affects: []

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Shared MoveStats mounted on two surfaces; per-cell (category x side) dispatch reuses MoveStatsCellRef from Plan 02"
    - "Unified best/good move glyphs across move list and board via frontend/src/lib/bestGlyph.ts"

key-files:
  created:
    - frontend/src/lib/bestGlyph.ts
  modified:
    - frontend/src/components/results/LibraryGameCard.tsx
    - frontend/src/components/analysis/AnalysisTagsPanel.tsx
    - frontend/src/pages/Analysis.tsx
    - frontend/src/components/library/MoveStats.tsx
    - frontend/src/components/library/ChipColumn.tsx
    - frontend/src/components/board/boardMarkers.tsx
    - frontend/src/components/analysis/VariationTree.tsx
    - frontend/src/components/icons/BestMoveIcon.tsx
    - frontend/src/components/icons/GoodMoveIcon.tsx
    - frontend/src/components/icons/SeverityGlyphIcon.tsx
  deleted:
    - frontend/src/components/library/GemGreatBadge.tsx
    - frontend/src/components/library/__tests__/GemGreatBadge.test.tsx

key-decisions:
  - "Library game card switches to the mobile (stacked) layout at the lg breakpoint, not md, so the accuracies + Move Stats cards have room on tablet widths"
  - "Best/Good glyphs unified across the move list and the board through a single bestGlyph.ts helper so the two surfaces never drift"
  - "Desktop analysis board reduced by 20px on the final computed size (not the ceiling) to fit the Move Stats card row without overflow"
  - "Empty-state early return in AnalysisTagsPanel dropped (RESEARCH Pitfall 2); the panel now always renders the 7-row table gated on analyzed state (D-03/D-07)"

requirements-completed: [D-03, D-06, D-07, D-08, D-09, D-10, D-11]

coverage:
  - id: D1
    description: "MoveStats renders on both LibraryGameCard and AnalysisTagsPanel with correct mobile/desktop behavior"
    requirement: "D-06"
    verification:
      - kind: unit
        ref: "frontend/src/components/results/__tests__/LibraryGameCard.test.tsx + frontend/src/components/analysis/__tests__/AnalysisTagsPanel.test.tsx"
        status: pass
      - kind: manual
        ref: "Live-browser UAT (desktop + mobile) signed off by user; 7 follow-up polish commits address UAT feedback"
        status: pass
    human_judgment: true
  - id: D2
    description: "(category x side) cell cycling + user-scoped filter ring on player-side cells only"
    requirement: "D-09/D-10"
    verification:
      - kind: unit
        ref: "LibraryGameCard.test.tsx cycling + ring assertions"
        status: pass
    human_judgment: false
  - id: D3
    description: "GemGreatBadge.tsx + test deleted knip-clean; SeverityBadge.tsx preserved (still used by FlawCard Flaws tab)"
    requirement: "D-11"
    verification:
      - kind: build
        ref: "npm run knip clean; npx tsc -b clean"
        status: pass
    human_judgment: false

# Metrics
duration: UAT-iterated
completed: 2026-07-18
status: complete
---

# Phase 179 Plan 03: Move Stats Frontend Wiring Summary

**Wired the shared `MoveStats` component into both `LibraryGameCard.tsx` and `AnalysisTagsPanel.tsx`, replacing the old badge rows: (category x side) cell cycling, a user-scoped filter ring on player-side cells, mobile compact/expandable behavior, and the analysis-panel empty-state early return dropped. `GemGreatBadge.tsx` deleted knip-clean; `SeverityBadge.tsx` preserved. Followed by a round of live-browser UAT polish.**

## Accomplishments

- `LibraryGameCard.tsx` migrated to `MoveStats` (D-06/D-08/D-09/D-10) — accuracies card + two-sided category table, mobile compact row that expands, player-side-only filter ring
- `AnalysisTagsPanel.tsx` migrated to `MoveStats` (D-03), dropping the empty-state early return so the always-7-row table renders whenever the game is analyzed (D-07)
- `GemGreatBadge.tsx` and its test deleted; knip confirms no orphan; `SeverityBadge.tsx` deliberately kept (still consumed by `FlawCard.tsx`)
- `frontend/src/lib/bestGlyph.ts` added to unify the Best/Good move glyphs across the move list and the board
- UAT polish commits: accuracies/charcoal card treatment, mobile compact row, desktop analysis board sizing (-20px on final size), library card mobile layout at `lg` not `md`, pointer cursors on clickable counts, tag-click sideline unfold + top-aligned move list, `??`/`?!` glyph spacing

## Task Commits

1. **Migrate LibraryGameCard to MoveStats (D-06/D-08/D-09/D-10)** - `4612fdac` (feat)
2. **Migrate AnalysisTagsPanel to MoveStats, drop empty-return (D-03)** - `62e26357` (feat)
3. **UAT polish (accuracies/charcoal cards, mobile compact row, analysis layout)** - `122ce9e2` (feat)

Follow-up UAT fixes: `f5672bb0`, `7b419bc5`, `6a5d84f5`, `471962fd`, `e31f7906`, `0c71a456`, `0043ee69`, `0b2ad51a`.

## Deviations from Plan

The plan's single delivered SUMMARY was folded in at ship time (Phase 179 was shipped as one unit after the full UAT-polish pass). Work matches the plan objective: both surfaces render the shared two-sided Move Stats component with correct mobile/desktop behavior, (category x side) cycling, user-scoped filter ring, retained chips, opponent tiers surfaced, and a stable always-7-row table; GemGreatBadge deleted knip-clean; visual UAT approved.

## Next Phase Readiness

Phase 179 complete — final phase of milestone v2.5. Ready for milestone close.

---
*Phase: 179-two-sided-move-stats-component-seed-112*
*Completed: 2026-07-18*
