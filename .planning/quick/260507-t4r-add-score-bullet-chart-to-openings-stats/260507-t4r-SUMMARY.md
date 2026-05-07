---
phase: 260507-t4r
plan: 01
subsystem: frontend/openings
tags: [openings, charts, bullet-chart, score, eval, layout, quick-task]
dependency_graph:
  requires: []
  provides:
    - MiniBulletChart barColor prop (opt-in neutral grey bar)
    - BULLET_BAR_NEUTRAL theme constant
    - OpeningStatsCard WDL+Score+Eval three-row layout
    - OpeningFindingCard WDL+Score+Eval three-row layout, move-anchor caption
  affects:
    - frontend/src/components/charts/MiniBulletChart.tsx
    - frontend/src/components/stats/OpeningStatsCard.tsx
    - frontend/src/components/insights/OpeningFindingCard.tsx
tech_stack:
  added: []
  patterns:
    - Tufte/Few bullet-chart convention: neutral bar for position, colored zones for verdict
    - Unified single-column card layout (removes sm:hidden / hidden sm:flex split)
    - Opt-in prop with explicit default to preserve existing consumers unchanged
key_files:
  created: []
  modified:
    - frontend/src/lib/theme.ts
    - frontend/src/components/charts/MiniBulletChart.tsx
    - frontend/src/components/charts/__tests__/MiniBulletChart.test.tsx
    - frontend/src/components/stats/OpeningStatsCard.tsx
    - frontend/src/components/stats/__tests__/OpeningStatsCard.test.tsx
    - frontend/src/components/insights/OpeningFindingCard.tsx
    - frontend/src/components/insights/OpeningFindingCard.test.tsx
decisions:
  - "Icon pick: Users (lucide-react) for score row — aligns with 'your performance' semantics vs Cpu for engine eval"
  - "Board size: single BOARD_SIZE = 110 constant in both cards (was DESKTOP_BOARD_SIZE=110 / MOBILE_BOARD_SIZE=115 pair)"
  - "Troll watermark: kept hidden sm:block class unchanged — visual placement to confirm at checkpoint"
  - "Contradiction guard (toFixed(1) fallback): dropped from FindingCard since prose line is gone; score-text uses Math.round only"
metrics:
  duration: "~30 minutes"
  completed: "2026-05-07T19:15:11Z"
  tasks_completed: 2
  files_modified: 7
---

# Phase 260507-t4r Plan 01: Add score bullet chart to Openings Stats and Insights tabs

## One-liner

Added score bullet row (neutral grey bar, Wilson CI on Insights, Users icon) and unified single-column layout to Openings Stats and Insights cards, with score-zone border replacing eval-zone; eval bullet preserved; Endgame consumers unaffected via opt-in barColor prop.

## What Was Built

### Task 1: MiniBulletChart barColor prop

Added `BULLET_BAR_NEUTRAL = 'oklch(0.85 0 0)'` to `theme.ts` and a `barColor?: 'zone' | 'neutral'` prop to `MiniBulletChart`. Default is `'zone'` (existing behavior unchanged). With `barColor="neutral"`, the value-fill bar renders in light grey regardless of zone — zone bands still carry the verdict via background color. Added `data-testid="mini-bullet-value-bar"` for direct test targeting.

Endgame consumers (`EndgamePerformanceSection`, `EndgameScoreGapSection`) omit the prop and remain visually identical.

### Task 2: OpeningStatsCard and OpeningFindingCard restructuring

**OpeningStatsCard:**
- Derives `score = (wins + 0.5 * draws) / total` on the frontend (no backend change)
- New score bullet row: `MiniBulletChart` with `barColor="neutral"`, `SCORE_BULLET_*` config, no CI whisker (OpeningWDL lacks score CI — accepted)
- Score-text element shows `{Math.round(derivedScore * 100)}%` with `Users` icon in score-zone color
- Border-left switched from `evalZoneColor` to `scoreZoneColor(derivedScore)`, gated on `total >= MIN_GAMES_FOR_RELIABLE_STATS` (transparent if sparse)
- Unified single-column layout: removed the `sm:hidden` / `hidden sm:flex` two-block split; single `flex-col` with header, centered board, WDL, score bullet, eval bullet, links
- Eval bullet row: `barColor="neutral"` added; otherwise unchanged

**OpeningFindingCard:**
- Score bullet row: uses `finding.score`, `finding.ci_low/ci_high` (Wilson CIs from backend), shows whisker; `BulletConfidencePopover` for score confidence
- Move anchor caption "after 2.c4" rendered as `<span class="text-xs text-muted-foreground">` directly under the miniboard
- "Score X% after [move]" prose line dropped entirely
- Unified single-column layout: same structure as Stats card
- Eval bullet row: `barColor="neutral"` added; otherwise unchanged
- Troll watermark: kept as `hidden sm:block` (behavior unchanged pending visual review at checkpoint)

## Executor Decisions

| Decision | Choice | Rationale |
|---|---|---|
| Score row icon | `Users` (lucide-react) | "Your performance" semantics vs `Cpu` for engine |
| Board size | `BOARD_SIZE = 110` (single constant) | Desktop size is clean; mobile size difference (115 vs 110) is imperceptible |
| Stats card score CI | No whisker | OpeningWDL has no score CI; accepted limitation |
| Troll watermark on unified layout | `hidden sm:block` unchanged | Visual placement to verify at checkpoint before changing |
| Contradiction guard (toFixed(1)) | Dropped | Prose line is gone; score-text shows Math.round; no contradiction to guard against |

## Deviations from Plan

None. Plan executed exactly as written.

## Test Results

- All 296 frontend tests pass
- ESLint: clean
- Knip: clean (no dead exports)
- Tests added: 10 new for MiniBulletChart barColor, 8 new for OpeningStatsCard score/layout
- Tests updated: OpeningFindingCard tests updated for unified layout (1 board instead of 2, score-bullet now present)

## Self-Check

### Created files exist
- SUMMARY.md: this file

### Commits exist
- `ec1c40c6`: Task 1 (MiniBulletChart barColor + BULLET_BAR_NEUTRAL)
- `881b3f15`: Task 2 (Stats and Insights card restructuring)

## Self-Check: PASSED

Both commits verified. All files modified per plan. No unexpected deletions.

## Visual Verification Needed (Task 3 Checkpoint)

The following require human visual confirmation:

1. `/openings/stats`: Three rows (WDL, Score, Eval) on each card; neutral grey bars; score-zone border; Users icon on score row; Cpu icon on eval row; single-column layout on all viewports
2. `/openings/insights`: Three rows; move-anchor caption under miniboard (not prose line); CI whisker on score bullet; score-zone border
3. `/endgames`: Eval bullets remain zone-colored (regression check for barColor default)
4. Troll watermark placement on unified layout (previously absolute-positioned relative to the two-block layout)
