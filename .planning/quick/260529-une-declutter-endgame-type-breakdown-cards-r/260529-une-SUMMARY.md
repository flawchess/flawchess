---
phase: quick-260529-une
plan: "01"
subsystem: frontend/endgames
tags: [ui, endgames, cleanup]
decisions:
  - "Removed Conv/Recov gauges from EndgameTypeCard; backend still computes them for LLM insights narration"
  - "Endgames.overallPerformance.test.tsx confirmed untouched — no gauge testid assertions existed"
metrics:
  duration: ~10 minutes
  completed: "2026-05-29T20:15:19Z"
  tasks_completed: 3
  tasks_total: 3
key-files:
  modified:
    - frontend/src/components/charts/EndgameTypeCard.tsx
    - frontend/src/components/charts/__tests__/EndgameTypeCard.test.tsx
    - frontend/src/components/charts/__tests__/EndgameTypeBreakdownSection.test.tsx
    - frontend/src/pages/Endgames.tsx
---

# Phase quick-260529-une Plan 01: Declutter Endgame Type Breakdown Cards Summary

Removed Conv/Recov gauges from EndgameTypeCard; WDL bar, Score bullet, and Score Gap bullet remain. Gauge-free cards remove section overload and eliminate TC-band mispaint without touching the backend.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Remove Conv/Recov gauges from EndgameTypeCard | d3453597 | EndgameTypeCard.tsx |
| 2 | Drop gauge assertions from tests; trim breakdown InfoPopover | 1de3d408 | EndgameTypeCard.test.tsx, EndgameTypeBreakdownSection.test.tsx, Endgames.tsx |
| 3 | Run and green frontend pre-PR gates | (no code change) | — |

## What Was Built

- `EndgameTypeCard.tsx`: deleted both gauge blocks (live render + empty-state shell), removed `bands`/`convZones`/`recovZones` derivation, removed `PER_TYPE_GAUGE_SIZE` constant, removed unused imports (`EndgameGauge`, `PER_CLASS_GAUGE_ZONES`, `colorizeGaugeZones`). WDL bar + Games link, Score bullet, Score Gap row all preserved intact.
- `EndgameTypeCard.test.tsx`: removed `conv-gauge`/`recov-gauge`/`gauges` testid assertions; re-anchored DOM ordering test on WDL block (was gauges); updated file-level doc comment.
- `EndgameTypeBreakdownSection.test.tsx`: updated comment example sub-element from `conv-gauge` to `score-bullet`.
- `Endgames.tsx`: trimmed breakdown h2 InfoPopover second paragraph — removed Conversion/Recovery clause, kept taxonomy sentence and WDL-rate sentence. Concepts accordion untouched.

## Frontend Gate Results

All three gates passed from `frontend/`:
- `npm run lint`: clean
- `npm run knip`: clean (`PER_CLASS_GAUGE_ZONES` is already knip-ignored in `frontend/knip.json`)
- `npm test -- --run`: 717 tests passed (61 test files)

## Deviations from Plan

None. Plan executed exactly as written.

Note: `Endgames.overallPerformance.test.tsx` was confirmed to have no gauge testid assertions (`grep -E "conv-gauge|recov-gauge|-gauges"` returned empty), so no edits were needed. This matches the plan's explicit note to leave it untouched if no gauge assertions exist.

## Threat Flags

None. This change removes rendered surface; no new network endpoints, auth paths, or schema changes introduced.

## Self-Check: PASSED

- `frontend/src/components/charts/EndgameTypeCard.tsx`: exists, no `EndgameGauge`/`PER_CLASS_GAUGE_ZONES`/`colorizeGaugeZones`/`PER_TYPE_GAUGE_SIZE`/`convZones`/`recovZones`/`bands!` references
- Commits d3453597 and 1de3d408: confirmed in git log
- No backend files (`app/`, `scripts/`) modified
- All 717 frontend tests pass
