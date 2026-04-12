---
phase: 53-endgame-score-gap-material-breakdown
plan: "02"
subsystem: frontend
tags: [endgames, analytics, ui, charts, typescript]
dependency_graph:
  requires: ["53-01"]
  provides: ["EndgameScoreGapSection component", "MaterialRow/ScoreGapMaterialResponse TS types", "score gap & material breakdown UI"]
  affects: ["frontend/src/pages/Endgames.tsx", "frontend/src/types/endgames.ts"]
tech_stack:
  added: []
  patterns: ["InfoPopover for section help text", "charcoal-texture container pattern", "inline style for oklch badge colors", "guard condition matching EndgamePerformanceSection pattern"]
key_files:
  created:
    - frontend/src/components/charts/EndgameScoreGapSection.tsx
  modified:
    - frontend/src/types/endgames.ts
    - frontend/src/pages/Endgames.tsx
decisions:
  - "Used inline style={{ backgroundColor: config.color }} for verdict badge oklch colors — oklch values are not valid Tailwind color classes"
  - "Guard condition: scoreGapData && (perfData?.endgame_wdl.total ?? 0) > 0 — prevents rendering when no endgame games, matches EndgamePerformanceSection pattern"
  - "Single statisticsContent variable covers both desktop and mobile layouts automatically — no duplicate mobile section needed"
  - "Checkpoint:human-verify auto-approved in parallel autonomous execution mode"
metrics:
  duration: "~15 minutes"
  completed: "2026-04-12"
  tasks_completed: 3
  tasks_total: 3
  files_modified: 3
---

# Phase 53 Plan 02: Endgame Score Gap & Material Breakdown Frontend Summary

**One-liner:** React EndgameScoreGapSection component with signed score difference (green/red) and material-stratified WDL table using theme verdict badges, wired into Endgames Stats tab.

## What Was Built

Added the frontend visualization for the endgame score gap and material breakdown metrics computed by the Plan 01 backend:

1. **TypeScript types** in `frontend/src/types/endgames.ts`: `MaterialBucket`, `Verdict`, `MaterialRow`, `ScoreGapMaterialResponse` mirroring the backend Pydantic models. `EndgameOverviewResponse` extended with `score_gap_material` field.

2. **`EndgameScoreGapSection` component** at `frontend/src/components/charts/EndgameScoreGapSection.tsx`:
   - Section header with InfoPopover explanation
   - Score difference display: signed number (`+0.045` / `-0.150`) with `text-green-500` / `text-red-500` coloring, subscript showing endgame and non-endgame scores
   - Material-stratified WDL table: 3 rows (Ahead ≥+1, Equal, Behind ≤−1) with columns: Material at entry, Games, Win%, Draw%, Loss%, Score, Verdict
   - Verdict badges using theme colors: `WDL_WIN` (green), `GAUGE_WARNING` (amber), `WDL_LOSS` (red) via inline `style={{ backgroundColor }}` since oklch values aren't Tailwind classes
   - Rows with 0 games dimmed with `opacity-50`
   - `overflow-x-auto` wrapper + `min-w-[480px]` table for mobile horizontal scroll

3. **Endgames page wiring** in `frontend/src/pages/Endgames.tsx`:
   - Import `EndgameScoreGapSection`
   - Extract `scoreGapData = overviewData?.score_gap_material`
   - Render after `EndgameTimelineChart` section with `charcoal-texture rounded-md p-4` wrapper
   - Guard: `scoreGapData && (perfData?.endgame_wdl.total ?? 0) > 0`
   - Single `statisticsContent` variable covers both desktop and mobile layouts

## Commits

| Task | Commit | Description |
|------|--------|-------------|
| 1 | `7923c5d` | feat(53-02): add MaterialRow/ScoreGapMaterialResponse types and EndgameScoreGapSection component |
| 2 | `6a02c00` | feat(53-02): wire EndgameScoreGapSection into Endgames page statisticsContent |

## Verification

- `npx tsc --noEmit` — passes (0 errors)
- `npm run lint` — passes (0 warnings)
- `npm run build` — passes (builds successfully)
- `npm run knip` — passes (no dead exports)
- Task 3 checkpoint:human-verify — auto-approved (parallel autonomous execution)

## Deviations from Plan

None — plan executed exactly as written.

## Known Stubs

None — component receives real data from the `/api/endgames/overview` endpoint (already returns `score_gap_material` field from Plan 01 backend). No hardcoded empty values or placeholder text.

## Threat Flags

None — component only renders authenticated user's own aggregate stats from existing API endpoint. No new trust boundaries introduced.

## Self-Check: PASSED

- FOUND: frontend/src/components/charts/EndgameScoreGapSection.tsx
- FOUND: frontend/src/types/endgames.ts
- FOUND: frontend/src/pages/Endgames.tsx
- FOUND: .planning/phases/53-endgame-score-gap-material-breakdown/53-02-SUMMARY.md
- FOUND commit: 7923c5d (Task 1)
- FOUND commit: 6a02c00 (Task 2)
