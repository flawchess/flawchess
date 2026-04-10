---
phase: 51-stats-subtab-homepage-global-stats
plan: 03
subsystem: ui
tags: [react, tailwind, homepage, responsive-design]

# Dependency graph
requires:
  - phase: 51-stats-subtab-homepage-global-stats
    provides: Phase context and plan definitions
provides:
  - Desktop 2-column split hero on homepage with Opening Explorer preview in right column
  - Removal of callout pills row from hero
  - Removal of opening-explorer from FEATURES alternating sections
affects: []

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "2-column desktop hero with lg:grid-cols-[2fr_3fr]: left=hero content, right=feature preview"
    - "Desktop-only feature preview via hidden lg:block wrapper"

key-files:
  created: []
  modified:
    - frontend/src/pages/Home.tsx

key-decisions:
  - "Used lg:grid-cols-[2fr_3fr] ratio (left narrower for text, right wider for image) matching existing feature section convention"
  - "Reduced hero padding from lg:py-24 to lg:py-12 to keep both columns visible on 1280x720 fold"
  - "Dropped Opening Explorer feature section entirely on both mobile and desktop (not kept as mobile-only fallback) per D-07"
  - "Used &apos; HTML entity for apostrophes in right-column bullet JSX to satisfy linter"

patterns-established:
  - "Desktop-only column: hidden lg:block wrapper with data-testid for testability"

requirements-completed: [HOME-01]

# Metrics
duration: 15min
completed: 2026-04-10
---

# Phase 51 Plan 03: Homepage Desktop Hero Split Summary

**Static 2-column desktop hero on homepage: left=hero content, right=Interactive Opening Explorer preview (heading + screenshot + bullets), pills row removed, Opening Explorer removed from FEATURES**

## Performance

- **Duration:** 15 min
- **Started:** 2026-04-10T14:30:00Z
- **Completed:** 2026-04-10T14:45:00Z
- **Tasks:** 1
- **Files modified:** 1

## Accomplishments
- Replaced single-column centered hero with `lg:grid-cols-[2fr_3fr]` 2-column split for desktop
- Added right-column static Opening Explorer preview (heading, screenshot, 3 bullets) hidden on mobile via `hidden lg:block`
- Removed callout pills row (`mt-12 hidden lg:flex flex-wrap justify-center gap-2`) entirely
- Removed `opening-explorer` entry from FEATURES array, reducing alternating sections from 5 to 4
- Removed unused `ArrowRightLeft` import (knip-clean)
- Reduced vertical padding (`lg:py-24` → `lg:py-12`) and logo size (`lg:h-36` → `lg:h-24`) to fit both columns above the 1280×720 fold

## Task Commits

1. **Task 1: Restructure Home.tsx — remove Opening Explorer from FEATURES, split hero into 2-col desktop layout, remove pills, preserve mobile hero** - `08bb94a` (feat)

## Files Created/Modified
- `frontend/src/pages/Home.tsx` - 2-column desktop hero split, pills removed, opening-explorer removed from FEATURES, ArrowRightLeft import removed

## Decisions Made
- Used `lg:grid-cols-[2fr_3fr]` ratio matching the existing feature section convention (left text narrower, right image wider)
- Reduced `lg:py-24` to `lg:py-12` and mascot logo from `lg:h-36` to `lg:h-24` to ensure both columns fit above the 1280×720 fold
- Dropped Opening Explorer feature section entirely on both viewports (not kept as mobile-only fallback) — mobile users see the 4 remaining alternating sections directly below the hero, which is sufficient per D-07
- Applied left-aligned text and buttons on desktop (`text-center lg:text-left`, `justify-center lg:justify-start`) for visual balance next to the right-column image

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- HOME-01 complete: desktop 1280×720 shows hero left column + Opening Explorer right column without vertical scroll
- Mobile hero unchanged in structure and visual appearance
- All acceptance criteria verified: lint, knip, build all green; 4 FEATURES entries; no ArrowRightLeft; no pills wrapper; correct testids present

---
*Phase: 51-stats-subtab-homepage-global-stats*
*Completed: 2026-04-10*
