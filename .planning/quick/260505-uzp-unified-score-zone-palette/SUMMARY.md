---
type: quick
slug: 260505-uzp-unified-score-zone-palette
status: complete
created: 2026-05-05
completed: 2026-05-05
---

# Summary

Tied the Moves-tab arrow color, Score column text color, and row background tint to one score-zone signal. Faded blue arrows so reliable strong/weak moves dominate visually. Hover now amplifies (size + opacity) instead of recoloring. Deep-link from Insights pulses through grey alpha levels.

## What changed

- **`arrowColor.ts`** — `getArrowColor(score, gameCount, confidence)` (dropped `isHovered` parameter). Low `gameCount` (<10) OR `confidence === 'low'` → `DARK_BLUE` (was `GREY`). In-between zone → `DARK_BLUE`. `GREY` constant removed; the only remaining hex constants for arrows are `DARK_GREEN` / `DARK_RED` / `DARK_BLUE`. `LIGHT_GREEN` / `LIGHT_RED` kept (still used by `OpeningFindingCard` borders on Insights tab).
- **`ChessBoard.tsx`** — added `ARROW_LOW_EMPHASIS_OPACITY = 0.30`. Blue arrows render at 0.30 base opacity; green/red stay at 0.75. Hover bumps every arrow back to 0.9 (existing) and scales 1.3x — color is preserved.
- **`MoveExplorer.tsx`**:
  - Score column: dropped `showScoreColor` / `hasEffectOfInterest` / muted-grey path. Text always inline-styled with `scoreZoneColor(score)` when reliable, or `ZONE_NEUTRAL` (blue) when unreliable.
  - Row background: when `isReliable && (score >= 0.55 || score <= 0.45)`, sets `backgroundColor = ${DARK_GREEN|DARK_RED}${HIGHLIGHT_BG_REST_ALPHA}`. In-between or unreliable rows have no tint.
  - Deep-link pulse: keyframe `--row-highlight-low/high` now use grey hex (`#808080`) + alpha; `--row-highlight-rest` lands smoothly on the row's natural score-zone tint. Drops the `highlightColor` prop on `MoveRow` entirely.
  - Header InfoPopover copy updated: "low data → blue zone color" instead of "always grey".
- **`Openings.tsx`**:
  - Drops the `isHovered` arg in `getArrowColor` call.
  - `highlightedMove` state narrowed to `{ san: string }` — no severity color.
  - Drops `getSeverityBorderColor` import (still used in `openingInsights.ts` for the Insights card border, untouched).
  - Both InfoPopover tooltips (desktop + mobile) rewritten: now describe Score, the 3 categories, the faded blue, and the "row grey + arrow grows + opacity bump" hover behavior.
- **Tests** — `arrowColor.test.ts` rewritten for the new 3-arg signature + low-data-→-blue assertions. `MoveExplorer.test.tsx`: muted-grey tests inverted to "blue zone color"; new tests for green/red row tint at score 0.75 / 0.30; new tests asserting NO row tint at 0.50, n<10, or confidence=low. Existing `highlightedMove` tests retargeted from "row tinted in red" to "pulse animation class + grey CSS custom props".

## Out of scope (intentional)

- `OpeningFindingCard` severity border (Insights tab) — still uses `LIGHT_GREEN` / `LIGHT_RED` via `getSeverityBorderColor`. Independent palette.
- Bullet chart neutral band (`scoreBulletConfig.ts`) — already 0.45..0.55 blue.
- Backend / data shape — purely a frontend visual change.

## Verification

- `npm run lint` — clean
- `npm test -- --run arrowColor MoveExplorer` — 43/43 passing
- Full suite: 283/285 passing. The 2 failures (`MostPlayedOpeningsTable` D-10 tooltip) are pre-existing on this branch and unrelated.
- `npm run build` — clean
- `npm run knip` — clean
