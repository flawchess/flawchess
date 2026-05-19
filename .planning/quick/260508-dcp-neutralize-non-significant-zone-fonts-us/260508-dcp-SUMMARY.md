---
status: complete
phase: 260508-dcp
plan: 01
subsystem: frontend (Openings + Endgames UI)
tags: [styling, significance-gating, theme-constants]
type: execute
duration_minutes: ~30
completed: 2026-05-08
commits:
  - 912aa058
  - fb8ca37a
  - 4a67a901
  - 4a409726
files_modified:
  - frontend/src/lib/theme.ts
  - frontend/src/lib/arrowColor.ts
  - frontend/src/lib/significance.ts          # new
  - frontend/src/components/move-explorer/MoveExplorer.tsx
  - frontend/src/components/move-explorer/__tests__/MoveExplorer.test.tsx
  - frontend/src/pages/Openings.tsx
  - frontend/src/components/stats/OpeningStatsCard.tsx
  - frontend/src/components/insights/OpeningFindingCard.tsx
  - frontend/src/components/charts/EndgameWDLChart.tsx
  - frontend/src/components/charts/EndgamePerformanceSection.tsx
  - frontend/src/components/charts/EndgameScoreGapSection.tsx
---

# Quick Task 260508-dcp: Neutralize non-significant zone fonts + white bullet bars

## One-liner

Gate Score % and Stockfish eval font colors on every Openings subtab to require a confident bucket (`'medium'` or `'high'`, not `'low'`) AND colored zone, neutralize all Openings + Endgames Stats MiniBulletChart bars, and recolor the categorical "neutral" board arrow from blue to transparent grey.

## What changed

### 1. Significance gating on Openings text labels

The Score % and Stockfish eval text on every Openings subtab now render in zone color (red or green) only when:

- the value lands in the red or green zone (not the in-between band), AND
- the result is statistically confident — bucket is `'medium'` or `'high'`, not `'low'`.

Otherwise the text reads in the default foreground color.

The gate is keyed on the categorical confidence bucket rather than a hard-coded p-value, so the underlying bucket thresholds in `scoreConfidence.ts` (`CONFIDENCE_MEDIUM_MAX_P = 0.05`, `CONFIDENCE_HIGH_MAX_P = 0.01`) can move without touching every call site.

```ts
// frontend/src/lib/significance.ts
import type { ConfidenceLevel } from '@/lib/scoreConfidence';

export function isConfident(
  confidence: ConfidenceLevel | null | undefined,
): boolean {
  return confidence != null && confidence !== 'low';
}
```

Applied at:

- **Openings → Moves subtab** (`MoveExplorer.tsx`): the Score column on each row.
- **Openings → Moves subtab** (`Openings.tsx`): the "current position" Score % text above the WDL bar.
- **Openings → Stats subtab** (`OpeningStatsCard.tsx`): Score % and Eval text. The card's left-edge border keeps the existing reliability-only gate (out of scope for the significance tightening).
- **Openings → Insights subtab** (`OpeningFindingCard.tsx`): Score % and Eval text. The card's left-edge border + on-board candidate-arrow keep the existing score zone tint.

### 2. White bullet bars on every Openings subtab + Endgames Stats tab

`MiniBulletChart` already had an opt-in `barColor="neutral"` mode that renders the bar in `BULLET_BAR_NEUTRAL` (light grey/white) — Tufte/Few bullet-chart convention where the bar carries position only and the colored zone bands behind it carry the qualitative verdict. The Stats and Insights cards already used it. Extended to:

- **Openings → Moves subtab** (`Openings.tsx`): "current position" score bullet (previously omitted, defaulted to `'zone'`).
- **Endgames → Stats** (`EndgameWDLChart.tsx`, `EndgamePerformanceSection.tsx`, `EndgameScoreGapSection.tsx`): all six MiniBulletChart usages (desktop table + mobile card branches).

No font changes on the Endgames side — we don't have statistical tests for endgames stats yet, so colored numeric labels (gauge zones, Diff text) are untouched.

### 3. Chessboard arrow palette: blue → transparent grey

The categorical neutral arrow color (used for in-between, low-data, and low-confidence arrows on the Move Explorer board) is now grey. Implemented as a one-line value swap:

```ts
// frontend/src/lib/theme.ts
export const ARROW_NEUTRAL = '#6B7280';  // Tailwind gray-500

// frontend/src/lib/arrowColor.ts
import { ARROW_NEUTRAL } from '@/lib/theme';
// Historically blue; now grey via ARROW_NEUTRAL — categorical equality preserved.
export const DARK_BLUE = ARROW_NEUTRAL;
```

The constant **name** `DARK_BLUE` is kept as-is (with an explanatory comment) because every call site uses `=== DARK_BLUE` for categorical equality (`ChessBoard.tsx`, `MoveExplorer.tsx`). Renaming would touch every consumer and is out of scope for this quick task. A future quick task can rename it if/when the naming starts confusing readers. The existing `ARROW_LOW_EMPHASIS_OPACITY = 0.30` continues to render these arrows as a transparent grey on both light and dark themes.

## Verification

All four frontend pipeline checks green:

- `npm run lint` — green (3 unrelated warnings on `frontend/coverage/` JS files).
- `npm run knip` — green.
- `npm run build` — green.
- `npm test` — 24 files, 284 tests passing.

Three pre-existing `MoveExplorer.test.tsx` cases that asserted the **old** behavior (in-between band / low-data / low-conf rendered the score in the neutral zone color) were updated to assert the **new** behavior (no inline color in those cases). Test count is unchanged.

## Manual visual smoke (operator follow-up)

1. `bin/run_local.sh` (or `npm run dev` in `frontend/`).
2. **`/openings/explorer`** with a user that has imported games:
   - Move Explorer table: rows in the in-between band or with low confidence/few games render Score % in default white text; reliable + significant + colored-zone rows render red/green.
   - "Current position" panel above the table: Score % uses default white when in-between or insignificant, red/green only when in colored zone AND significant. Bullet bar reads white.
   - Board arrows: previously blue (in-between, low-data, low-confidence) now render as transparent grey instead of blue.
3. **`/openings/stats`**: Score % and Eval text only tint red/green when significant AND in colored zone. Bullets remain white (already shipped previously).
4. **`/openings/insights`**: same as Stats, on `OpeningFindingCard`.
5. **`/endgames/stats`**: bullet bars are white across WDL, Performance, and Score Gap sections. Numeric labels (gauge zones, eval/score numbers, Diff text) are UNCHANGED.
6. Mobile viewport (DevTools width <640px): repeat 2-5; the same components render via shared JSX so no per-viewport regression is expected.

## Deviations from plan

None. Three pre-existing test cases needed their assertions updated (anticipated by the plan: "if any do, update them to assert the new gated behavior") — done in commit `fb8ca37a`.

A follow-up post-execution refactor (after user feedback) swapped the `isSignificant(pValue)` helper for `isConfident(confidence)` so the gate keys on the categorical bucket; the redundant artificial low-data test case (`confidence: 'high', game_count: 9` — impossible in real data because n<10 always buckets to `'low'`) was deleted. Other callers naturally collapsed: the explicit `n >= MIN_GAMES_FOR_RELIABLE_STATS` check disappeared from the font gate because `confidence !== 'low'` already encodes it.

## Commits

| Hash       | Message                                                                                                       |
| ---------- | ------------------------------------------------------------------------------------------------------------- |
| `912aa058` | Add ARROW_NEUTRAL token + isSignificant helper, switch arrow palette to grey                                  |
| `fb8ca37a` | Gate Openings Moves subtab score-text on significance + neutralize position bullet                            |
| `4a67a901` | Gate Stats + Insights card score/eval font on significance + colored zone                                     |
| `4a409726` | Neutralize Endgames Stats MiniBulletChart bars (no font changes)                                              |
| (this)     | Switch significance gate from raw p-value to `confidence !== 'low'` bucket                                    |

## Self-Check: PASSED

All artifacts present:

- `frontend/src/lib/significance.ts` — found.
- `ARROW_NEUTRAL` in `frontend/src/lib/theme.ts` — found.
- `DARK_BLUE = ARROW_NEUTRAL` in `frontend/src/lib/arrowColor.ts` — found.
- 6× `barColor="neutral"` additions across the three endgame chart files — found (2 each).
- All 4 commits present in git log.
