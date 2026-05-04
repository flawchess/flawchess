---
type: quick
slug: 260504-acl-simplify-arrow-color-from-5-to-3-categories
status: in-progress
created: 2026-05-04
---

# Quick Task: Simplify arrow color (5 → 3 categories)

## Goal

Collapse the board-arrow color scheme on the Openings → Moves tab from 5 effect-size buckets to 3 score-zone categories, matching the bullet chart's neutral band.

## Changes

1. **`frontend/src/lib/arrowColor.ts`** — replace 5-bucket palette with 3 categories:
   - `score >= 0.55` → DARK_GREEN
   - `score <= 0.45` → DARK_RED
   - in between → new DARK_BLUE constant
   - low-confidence / `gameCount < MIN_GAMES_FOR_COLOR` / hover → GREY (replaces HOVER_BLUE)
   - Drop `LIGHT_GREEN`, `LIGHT_RED`, `HOVER_BLUE`, `MINOR_EFFECT_SCORE`, `MAJOR_EFFECT_SCORE` exports (where unused). LIGHT_GREEN/LIGHT_RED stay only if still used by `openingInsights.ts` (severity border for insights cards — different feature).
   - Rewrite `arrowSortKey` for the new palette.
2. **`frontend/src/lib/arrowColor.test.ts`** — rewrite to assert the 3-category scheme.
3. **`frontend/src/components/move-explorer/MoveExplorer.tsx`**:
   - Drop the `hasEffectOfInterest` gate so the score column renders the blue zone color in the 45–55% band (currently muted-grey).
   - Replace `hover:bg-blue-500/15!` and `selectedMove ... 'bg-blue-500/15'` with grey equivalents.
4. **`frontend/src/pages/Openings.tsx`** — rewrite the chessboard InfoPopover tooltip (desktop + mobile) to:
   - Reference **Score = (W + 0.5·D)/N**, not "win rate".
   - Describe the new 3-category scheme + grey for low-data / hover.
5. **Tests** — adjust any MoveExplorer / arrowColor / openingInsights tests that assert old thresholds.

## Out of scope

- `openingInsights.ts` severity-border colors (used by OpeningFindingCard on the Insights tab) — stay on the existing 4-shade palette. The user's request is scoped to the Moves tab.
- Bullet chart neutral zone — already 45–55% (`scoreBulletConfig.ts`); nothing to change.
- Score column zone color helper — `scoreZoneColor` already returns `ZONE_NEUTRAL` for 45–55%; the only change needed is removing the upstream `hasEffectOfInterest` gate in MoveExplorer.

## Verification

- `npm run lint`
- `npm test -- arrowColor` and full frontend suite
- `npm run build`
- Spot-check the Moves tab: arrows should render in red/blue/green; hovering an arrow / row should turn grey; tooltip wording mentions Score.
