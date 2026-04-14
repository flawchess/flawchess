---
phase: quick-260413-qq0
plan: 01
subsystem: frontend/endgames
tags: [ui, refactor, endgames]
dependency-graph:
  requires: [MiniBulletChart, EndgamePerformanceSection, EndgameScoreGapSection]
  provides: ["Consolidated endgame-vs-non-endgame WDL + score-diff visual unit"]
  affects: [Endgames page layout]
tech-stack:
  added: []
  patterns: ["Optional prop-driven block (scoreGap?: ScoreGapMaterialResponse) inside EndgamePerformanceSection"]
key-files:
  created: []
  modified:
    - frontend/src/components/charts/EndgamePerformanceSection.tsx
    - frontend/src/components/charts/EndgameScoreGapSection.tsx
    - frontend/src/pages/Endgames.tsx
decisions:
  - "Renamed score-gap-section-info testId to material-breakdown-section-info (no other selectors referenced it)"
  - "EndgameGaugesSection given its own narrow props interface so EndgamePerformanceSection can extend with optional scoreGap without leaking the prop into gauges"
metrics:
  duration: ~5 min
  completed: 2026-04-13
requirements: [QQ0-01, QQ0-02, QQ0-03]
---

# Quick Task 260413-qq0: Move Endgame Score Difference into 'Games with vs without Endgame' Summary

Consolidates the endgame-vs-non-endgame visual unit by relocating the signed score-difference (with MiniBulletChart) from `EndgameScoreGapSection` into `EndgamePerformanceSection`, and renames labels so both pieces speak the same language ("Games with/without Endgame").

## What Changed

- **`EndgamePerformanceSection.tsx`**
  - Section heading: `Endgame vs. Non-Endgame Games` → `Games with vs without Endgame`
  - WDL row labels (desktop + mobile): `Endgame games` / `Non-endgame games` → `Games with Endgame` / `Games without Endgame`
  - New optional prop `scoreGap?: ScoreGapMaterialResponse` and a `MiniBulletChart`-based row rendered below the two WDL rows when supplied
    - 3-column responsive grid (label + InfoPopover | signed colored number | bullet chart)
    - `neutralMin=-0.05`, `neutralMax=0.05`
    - Caption `Endgame: X.XX | Non-endgame: Y.YY` retained at the new location
    - `data-testid="score-gap-difference"` preserved on the outer wrapper
  - Extended InfoPopover body to mention the new bullet chart
  - `EndgameGaugesSection` given its own `EndgameGaugesSectionProps` interface to avoid inheriting the (unused-for-gauges) `scoreGap` prop
- **`EndgameScoreGapSection.tsx`**
  - Removed the score-difference block (`data-testid="score-gap-difference"` and `diffPositive`/`diffFormatted` locals)
  - Heading renamed `Endgame Score Gap & Material Breakdown` → `Endgame Material Breakdown`
  - Info popover testId renamed to `material-breakdown-section-info` and body text refocused on the material table
  - Material-breakdown table left untouched (testIds, neutral zones, rendering all unchanged)
- **`Endgames.tsx`**
  - `<EndgamePerformanceSection data={perfData} />` → `<EndgamePerformanceSection data={perfData} scoreGap={scoreGapData} />`
  - `EndgameScoreGapSection` still rendered below in its own `charcoal-texture` panel

## Verification

- `cd frontend && npm run lint` — clean
- `cd frontend && npx tsc --noEmit` — zero errors (incl. `noUncheckedIndexedAccess`)
- `cd frontend && npm run build` — succeeds
- `cd frontend && npm run knip` — clean
- Grep confirms old labels (`"Endgame games"`, `"Non-endgame games"`, `"Endgame vs. Non-Endgame Games"`) gone from `frontend/src/`
- `data-testid="score-gap-difference"` matches exactly once, in `EndgamePerformanceSection.tsx`

## Commits

| Task | Commit | Description |
| ---- | ------ | ----------- |
| 1 | a895496 | Rename Endgame WDL section and add score-difference bullet chart |
| 2 | af13a26 | Remove score-difference block from EndgameScoreGapSection |
| 3 | e4e2768 | Pass scoreGapData into EndgamePerformanceSection |

## Deviations from Plan

None — plan executed exactly as written. Renaming the info testId to `material-breakdown-section-info` was authorized by the plan after confirming no other selectors referenced the old name.

## Self-Check: PASSED

- Files exist:
  - `frontend/src/components/charts/EndgamePerformanceSection.tsx` — FOUND
  - `frontend/src/components/charts/EndgameScoreGapSection.tsx` — FOUND
  - `frontend/src/pages/Endgames.tsx` — FOUND
- Commits exist: a895496, af13a26, e4e2768 — FOUND
- All success criteria from PLAN.md satisfied.
