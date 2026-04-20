---
id: 260420-kzb
description: Rename Score % Difference metric to Score Gap in EndgamePerformanceSection
date: 2026-04-20
status: complete
commit: 277ef31
---

# Quick Task 260420-kzb: Summary

## What changed

Renamed the endgame-vs-non-endgame score metric from **"Score % Difference"** to **"Score Gap"**. The timeline heading uses the fully-qualified form **"Endgame vs Non-Endgame Score Gap over Time"** when the chart stands alone.

Timeline subtitle on L330 reworded to emphasize the *relative* nature of the metric — what distinguishes it from the absolute Endgame Skill and Endgame ELO metrics: *"Is your endgame improving faster than the rest of your game?"*

## Files modified

- `frontend/src/components/charts/EndgamePerformanceSection.tsx`
  - User-facing labels: table header, mobile card label, timeline title, InfoPopover bodies, aria-labels, y-axis label, tooltip row.
  - Testids: `score-diff-*` → `score-gap-*` (timeline section, info, chart, volume bars, dot key).
  - Internal: `ScoreDiffTimelineChart` → `ScoreGapTimelineChart`, `ScoreDiffTimelineChartProps` → `ScoreGapTimelineChartProps`, `ScoreDiffChartPoint` → `ScoreGapChartPoint`, `scoreDiffZoneColor` → `scoreGapZoneColor`, `SCORE_DIFF_*` constants → `SCORE_GAP_*`, `diff_pct` → `gap_pct`, local `diff*` identifiers → `gap*`.
- `frontend/src/pages/Endgames.tsx` — import + JSX tag renamed to match.
- `frontend/src/types/endgames.ts` — two stale comments updated (`score-difference` / `Score % Difference` in JSDoc and inline comments). Backend field name `score_difference` preserved.

## Out of scope

- Backend schema field `score_difference` on `ScoreGapTimelinePoint` and `ScoreGapMaterialResponse` — rename would touch backend, DB response shape, and tests. Not worth the blast radius for a copy change.
- `EndgameScoreGapSection.tsx` — uses a separate "Diff" concept (material-stratified, opponent-relative). Unaffected.
- `MiniBulletChart.tsx` — reused by multiple sections; its internal "score-diff" comment is generic and context-free.
- testids `score-gap-difference` / `score-gap-difference-mobile` — already used `gap`; kept stable for test compatibility.

## Verification

- `npm run lint` → 0 errors (3 pre-existing warnings in `coverage/`).
- `npm run build` → built successfully in 4.45s, 2975 modules transformed.
- `npm run knip` → 0 issues.
- Backend not touched; no backend tests needed.
- Browser spot-check deferred — the changes are pure copy/identifier renames with zero behavior change.

## Commit

`277ef31 refactor(endgames): rename "Score % Difference" metric to "Score Gap"` on branch `quick/260420-kzb-score-gap-rename`.
