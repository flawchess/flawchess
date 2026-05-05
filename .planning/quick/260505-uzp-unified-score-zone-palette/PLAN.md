---
type: quick
slug: 260505-uzp-unified-score-zone-palette
status: in-progress
created: 2026-05-05
---

# Quick Task: Unified score-zone palette across arrow + Score column + row tint

Follow-up to `260504-acl`. See `/home/aimfeld/.claude/plans/let-s-try-this-harmonic-haven.md` for full plan.

## Behavior summary

| Condition                                                | Arrow      | Score column   | Row bg                  |
|----------------------------------------------------------|------------|----------------|-------------------------|
| Reliable (n≥10 ∧ conf≠low) ∧ score ≥ 0.55                | DARK_GREEN | ZONE_SUCCESS   | DARK_GREEN @ rest alpha |
| Reliable ∧ score ≤ 0.45                                   | DARK_RED   | ZONE_DANGER    | DARK_RED @ rest alpha   |
| Reliable ∧ 0.45 < score < 0.55                            | DARK_BLUE  | ZONE_NEUTRAL   | none                    |
| Unreliable (n<10 OR conf=low)                            | DARK_BLUE  | ZONE_NEUTRAL   | none                    |

Arrow opacity at rest:
- Green / Red: `ARROW_OPACITY = 0.75` (existing)
- Blue: new `ARROW_LOW_EMPHASIS_OPACITY = 0.30`

Hover (row ⇄ arrow):
- Row bg overlay → grey (`hover:bg-foreground/10!`, already in place)
- Arrow → keep zone color, scale 1.3x and opacity 0.9 (existing constants)

Deep-link from Insights:
- Steady-state row tint comes from score zone (no special severity tint).
- Pulse animation runs through grey alpha levels (not severity hex).
- Arrow pulse keeps zone color; opacity/size animation only.

## Files

- `frontend/src/lib/arrowColor.ts` — drop `isHovered` param; low-data/low-conf → DARK_BLUE; in-between → DARK_BLUE.
- `frontend/src/components/board/ChessBoard.tsx` — per-color base opacity.
- `frontend/src/components/move-explorer/MoveExplorer.tsx` — Score column color rule, score-zone row tint, grey pulse stops, drop muted-grey path.
- `frontend/src/pages/Openings.tsx` — drop `isHovered` arg in `getArrowColor`; drop deep-link severity color; rewrite both InfoPopover tooltips.
- `frontend/src/lib/arrowColor.test.ts` — rewrite suite for new signature.
- `frontend/src/components/move-explorer/__tests__/MoveExplorer.test.tsx` — update muted-grey tests; add row-tint tests.

## Verification

- `npm run lint`, `npm test -- --run`, `npm run build`, `npm run knip`
- 2 pre-existing `MostPlayedOpeningsTable` failures (D-10 tooltip) remain unrelated
