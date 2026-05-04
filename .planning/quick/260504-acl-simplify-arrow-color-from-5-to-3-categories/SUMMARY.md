---
type: quick
slug: 260504-acl-simplify-arrow-color-from-5-to-3-categories
status: complete
created: 2026-05-04
completed: 2026-05-04
---

# Summary

Collapsed the board-arrow palette on the Openings → Moves tab from 5 effect-size buckets to 3 score zones, matched to the bullet-chart neutral band.

## What changed

- **`arrowColor.ts`** — `getArrowColor` now returns `DARK_GREEN` (>=0.55), `DARK_RED` (<=0.45), `DARK_BLUE` (in between, new), or `GREY` (low data / low confidence / hovered). New `SCORE_BOUNDARY = 0.05`. Replaced `HOVER_BLUE` with `GREY` for the hover state. `LIGHT_GREEN`/`LIGHT_RED` kept as exported constants — still used by `OpeningFindingCard` severity borders on the Insights tab.
- **`ChessBoard.tsx`** — sort prioritises `isHovered` first so hovered (now grey) arrows still render on top.
- **`MoveExplorer.tsx`** — dropped the `hasEffectOfInterest` gate on `showScoreColor` so 45-55% scores render in the neutral blue zone color (was muted grey). Hover/selected row tints switched from `bg-blue-500/15` to `bg-foreground/10` (grey).
- **`Openings.tsx`** — chessboard InfoPopover (desktop + mobile) rewritten: now describes Score = (W + 0.5·D)/N, the 3-color scheme, and the grey-for-low-data / grey-for-hover states.
- **Tests** — `arrowColor.test.ts` rewritten for the 3-category palette; one MoveExplorer test inverted from "muted in 45-55%" to "blue zone color in 45-55%".

## Out of scope (intentional)

- `OpeningFindingCard` severity-border palette on the Insights tab still uses the 4-shade light/dark pairs. Not in scope for this task.
- Bullet chart and `scoreZoneColor` already used 0.45/0.55 with `ZONE_NEUTRAL`. No behavior change there.

## Verification

- `npm run lint` — clean
- `npm test -- --run MoveExplorer arrowColor` — 44/44 passing
- Full suite: 284/286 passing. The 2 failures (`MostPlayedOpeningsTable` D-10 tooltip) are pre-existing on `main` and unrelated to this change.
- `npm run build` — clean
- `npm run knip` — clean
