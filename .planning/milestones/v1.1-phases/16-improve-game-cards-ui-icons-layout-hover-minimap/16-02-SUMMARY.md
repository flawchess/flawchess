---
phase: 16-improve-game-cards-ui-icons-layout-hover-minimap
plan: 02
subsystem: ui
tags: [react, lucide-react, radix-ui, tooltip, miniboard, chess]

# Dependency graph
requires:
  - phase: 16-improve-game-cards-ui-icons-layout-hover-minimap
    provides: "result_fen field in GameRecord API type and games table (Plan 01)"
provides:
  - "3-row GameCard layout with BookOpen, Clock, Calendar, Swords, Hash icons"
  - "Null-safe metadata rendering (omit vs placeholder)"
  - "Desktop hover tooltip MiniBoard showing final position"
  - "Mobile tap-to-expand inline MiniBoard with single-card-at-a-time state"
  - "TooltipProvider wrapping card stack in GameCardList"
affects: []

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Single TooltipProvider wrapping all cards in list (avoid N-context overhead)"
    - "Radix tooltip with hidden sm:block for desktop-only hover; mobile uses inline expand"
    - "Null-safe metadata: render only when value is present, not dash placeholders"

key-files:
  created: []
  modified:
    - frontend/src/components/results/GameCard.tsx
    - frontend/src/components/results/GameCardList.tsx

key-decisions:
  - "Player names in regular font weight (not bold) for both user and opponent — locked from research"
  - "Opening name only, no ECO code — locked from research"
  - "Desktop tooltip hidden sm:block; mobile uses isExpanded/onToggle inline expand"
  - "Single TooltipProvider in GameCardList (not per-card) to avoid 50x context overhead"

patterns-established:
  - "TooltipContent className override: p-1 bg-card border border-border overrides dark default styling"
  - "stopPropagation on external link anchor prevents mobile tap-expand trigger"

requirements-completed: [GCUI-03, GCUI-04, GCUI-05]

# Metrics
duration: 10min
completed: 2026-03-18
---

# Phase 16 Plan 02: Game Card UI — 3-Row Layout, Icons, Hover Minimap Summary

**3-row GameCard with lucide-react icons, null-safe metadata, and hover/tap MiniBoard showing final position oriented from user perspective**

## Performance

- **Duration:** ~10 min
- **Started:** 2026-03-18T21:10:00Z
- **Completed:** 2026-03-18T21:14:23Z
- **Tasks:** 2
- **Files modified:** 2

## Accomplishments
- Rebuilt GameCard.tsx with 3-row layout: Row 1 players+result, Row 2 opening with BookOpen icon, Row 3 metadata with Clock/Calendar/Swords/Hash icons
- Null-safe metadata rendering — time control, date, move count, termination omitted when null (no NaN, no dash placeholders)
- Desktop hover tooltip using Radix Tooltip with 120px MiniBoard of final position, hidden on mobile
- Mobile tap-to-expand inline MiniBoard below metadata, one card at a time via expandedGameId state in GameCardList
- TooltipProvider wrapping entire card stack in GameCardList (single context for performance)

## Task Commits

Each task was committed atomically:

1. **Task 1: Rebuild GameCard with 3-row layout, icons, null handling, and minimap** - `2ecb5c0` (feat)
2. **Task 2: Update GameCardList with TooltipProvider and mobile expand state** - `2d09d14` (feat)

**Plan metadata:** (docs commit below)

## Files Created/Modified
- `frontend/src/components/results/GameCard.tsx` - Rebuilt with 3-row layout, lucide icons, Tooltip+MiniBoard, isExpanded/onToggle props
- `frontend/src/components/results/GameCardList.tsx` - Added TooltipProvider, expandedGameId state, onToggle callbacks

## Decisions Made
- Player names use regular font weight (not bold) for both user and opponent — per locked decision from research
- No ECO code displayed — opening name only, per locked decision
- Desktop tooltip uses `hidden sm:block` so it never fires on mobile (mobile uses inline expand)
- Single `<TooltipProvider>` in GameCardList wraps all cards to avoid 50x context overhead
- `stopPropagation` on external link `<a>` tag prevents mobile tap-expand when clicking platform link

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None. Pre-existing lint errors in unrelated files (FilterPanel.tsx, badge.tsx, button.tsx, tabs.tsx, toggle.tsx, SuggestionsModal.tsx) are out of scope per deviation rules.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

Phase 16 is now complete. Both plans executed:
- Plan 01: result_fen stored at import time, threaded through API
- Plan 02: GameCard UI rebuilt with icons, null-safe rendering, hover minimap

No blockers or concerns.

---
*Phase: 16-improve-game-cards-ui-icons-layout-hover-minimap*
*Completed: 2026-03-18*

## Self-Check: PASSED

- FOUND: frontend/src/components/results/GameCard.tsx
- FOUND: frontend/src/components/results/GameCardList.tsx
- FOUND: commit 2ecb5c0 (Task 1)
- FOUND: commit 2d09d14 (Task 2)
