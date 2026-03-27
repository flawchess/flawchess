---
phase: quick
plan: 260327-jfd
subsystem: frontend
tags: [ui, endgames, badge]
key-files:
  modified:
    - frontend/src/pages/Endgames.tsx
    - frontend/src/components/charts/EndgameTimelineChart.tsx
decisions: []
metrics:
  duration: "~5 minutes"
  completed: "2026-03-27"
  tasks: 1
  files: 2
---

# Quick Task 260327-jfd: Add Beta Badge to Endgames Statistics Tab

One-liner: Amber pill-style "Beta" badge added inline with Statistics tab text in both desktop and mobile layouts.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Add Beta badge to Endgames Statistics tab | 6329006 | frontend/src/pages/Endgames.tsx, EndgameTimelineChart.tsx |

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Removed unused `windowSize` variable in EndgameTimelineChart**
- **Found during:** Task 1 build verification
- **Issue:** `windowSize` was declared but never read in the tooltip render — TypeScript strict unused-variable error blocked `npm run build`
- **Fix:** Removed the unused variable declaration (line 144 in EndgameTimelineChart.tsx)
- **Files modified:** frontend/src/components/charts/EndgameTimelineChart.tsx
- **Commit:** 6329006

## Self-Check: PASSED

- frontend/src/pages/Endgames.tsx — modified (badge added to both tab triggers)
- frontend/src/components/charts/EndgameTimelineChart.tsx — modified (unused var removed)
- Commit 6329006 exists
