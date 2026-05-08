---
phase: 260508-dcp
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - frontend/src/lib/theme.ts
  - frontend/src/lib/arrowColor.ts
  - frontend/src/components/move-explorer/MoveExplorer.tsx
  - frontend/src/components/stats/OpeningStatsCard.tsx
  - frontend/src/components/insights/OpeningFindingCard.tsx
  - frontend/src/pages/Openings.tsx
  - frontend/src/components/charts/EndgameWDLChart.tsx
  - frontend/src/components/charts/EndgamePerformanceSection.tsx
  - frontend/src/components/charts/EndgameScoreGapSection.tsx
autonomous: true
requirements: [QUICK-260508-DCP]

must_haves:
  truths:
    - "On every Openings subtab, the Score % and Stockfish eval text render in zone color (red or green) ONLY when the value falls in the red or green zone AND the result is statistically significant at p < 0.05; otherwise white/foreground."
    - "On every Openings subtab, MiniBulletChart bars render in BULLET_BAR_NEUTRAL (light grey/white), regardless of zone."
    - "On the Endgames Stats tab, MiniBulletChart bars render in BULLET_BAR_NEUTRAL; colored numeric values are unchanged (no statistical tests for endgame stats)."
    - "Chessboard arrows that previously rendered DARK_BLUE (in-between zone, low-data, or low-confidence) now render as a transparent grey on both light and dark themes."
    - "npm run lint, npm run build, and npm test stay green."
  artifacts:
    - path: frontend/src/lib/theme.ts
      provides: "ARROW_NEUTRAL constant (transparent-grey arrow color) — single source of truth for the categorical 'neutral' arrow."
    - path: frontend/src/components/charts/EndgameWDLChart.tsx
      provides: "Endgame Stats WDL bullet bars use barColor='neutral'."
    - path: frontend/src/components/charts/EndgamePerformanceSection.tsx
      provides: "Endgame Stats Performance bullet bars use barColor='neutral'."
    - path: frontend/src/components/charts/EndgameScoreGapSection.tsx
      provides: "Endgame Stats Score Gap bullet bars use barColor='neutral'."
  key_links:
    - from: frontend/src/components/move-explorer/MoveExplorer.tsx
      to: frontend/src/lib/scoreBulletConfig.ts
      via: "scoreZoneColor gated on isReliable AND zone is colored (not neutral)"
      pattern: "scoreZoneColor"
    - from: frontend/src/components/stats/OpeningStatsCard.tsx
      to: frontend/src/lib/scoreConfidence.ts
      via: "scoreStats.confidence !== 'low' AND scoreStats.pValue < 0.05 gate before applying zone color"
      pattern: "scoreZoneColor|evalZoneColor"
    - from: frontend/src/components/insights/OpeningFindingCard.tsx
      to: frontend/src/types/insights.ts
      via: "finding.p_value < 0.05 AND finding.eval_p_value < 0.05 gate before applying zone colors to the Score % and Eval text"
      pattern: "scoreZoneColor|evalZoneColor"
    - from: frontend/src/lib/arrowColor.ts
      to: frontend/src/lib/theme.ts
      via: "DARK_BLUE re-exported from theme.ts ARROW_NEUTRAL constant"
      pattern: "ARROW_NEUTRAL"
---

<objective>
Visual styling tweak across the Openings subtabs and Endgames Stats tab:

1. **Neutralize non-significant zone-color fonts** on every Openings subtab. Score % and Stockfish eval text only carry zone color (red/green) when the value is in the red or green zone AND the result is statistically significant at p < 0.05. Otherwise the text reads in the default foreground color (the same color used for "other numbers"). The neutral (in-between) zone keeps its current neutral rendering — there is nothing to gate, since the zone itself is not signaling strength/weakness.

2. **White bullet bars across all Openings subtabs and the Endgames Stats tab.** The Openings Stats and Insights tabs already pass `barColor="neutral"` to MiniBulletChart (reference implementation: `OpeningStatsCard.tsx` lines 112, 167; `OpeningFindingCard.tsx` lines 139, 164). Apply the same pattern to:
   - Openings Moves subtab "current position" score bullet (`Openings.tsx` line 848 — currently omits `barColor`, defaults to `'zone'`).
   - Endgames Stats tab MiniBulletCharts in `EndgameWDLChart.tsx`, `EndgamePerformanceSection.tsx`, `EndgameScoreGapSection.tsx`.

3. **Chessboard arrows: blue → transparent grey.** Replace the categorical `DARK_BLUE` arrow color (used for in-between, low-data, and low-confidence arrows on the Move Explorer board) with a transparent grey. The lowest-friction implementation: change `DARK_BLUE`'s hex value in `arrowColor.ts` from `#1E40AF` to a neutral grey, and rely on the existing `ARROW_LOW_EMPHASIS_OPACITY = 0.30` for the "transparent" feel. Move the constant to `theme.ts` (per the project's theme-constants rule) and re-export from `arrowColor.ts` so the existing categorical-equality identity (`color === DARK_BLUE`) keeps working.

Purpose: bring statistical-significance discipline to the Openings tabs (don't paint a value red/green unless we're confident it's actually red/green), keep the chart bar a position-only mark per the Tufte/Few bullet convention already used on the Stats/Insights cards, and tone down the visually-loud blue arrows.

Output: theme constants for the neutral arrow color and an optional shared `isSignificant` helper, updated bar/font rendering on the affected components, no behavioral changes to data fetching or domain logic.
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@CLAUDE.md
@frontend/src/lib/theme.ts
@frontend/src/lib/scoreBulletConfig.ts
@frontend/src/lib/scoreConfidence.ts
@frontend/src/lib/openingStatsZones.ts
@frontend/src/lib/arrowColor.ts

<interfaces>
<!-- Significance: backend reports p_value on every relevant payload. The
     existing `confidence: 'low' | 'medium' | 'high'` maps to a p-value bucket
     where 'medium'/'high' === p < 0.05 (see scoreConfidence.ts:
     CONFIDENCE_MEDIUM_MAX_P = 0.05 and CONFIDENCE_HIGH_MAX_P = 0.01). So the
     significance gate for the score bullet/text can be expressed either as
     `p_value < 0.05` (numeric) or `confidence !== 'low'` (categorical) — they
     are equivalent for score-domain values. Prefer p_value when the field is
     directly available on the payload; fall back to `confidence !== 'low'` for
     OpeningStatsCard which derives confidence client-side via
     computeScoreConfidence. For the eval domain use eval_p_value < 0.05 (the
     eval_confidence bucket is computed from a different statistical test). -->

From `frontend/src/types/api.ts` (NextMoveEntry):
```typescript
interface NextMoveEntry {
  score: number;
  ci_low: number;
  ci_high: number;
  game_count: number;
  confidence: 'low' | 'medium' | 'high';
  p_value: number;            // already plumbed through, used in WdlConfidenceTooltip
  // ...
}
```

From `frontend/src/types/api.ts` (PositionStats — the "current position" stats on the Moves subtab):
```typescript
interface PositionStats {
  score: number;
  ci_low: number;
  ci_high: number;
  total: number;
  confidence: 'low' | 'medium' | 'high';
  p_value: number;
  // ...
}
```

From `frontend/src/types/insights.ts` (OpeningInsightFinding):
```typescript
interface OpeningInsightFinding {
  score: number;
  p_value: number;             // score-domain, two-sided Wilson test vs 0.5
  confidence: 'low' | 'medium' | 'high';
  avg_eval_pawns: number | null;
  eval_p_value?: number | null;     // eval-domain, t-test vs per-color baseline
  eval_confidence?: 'low' | 'medium' | 'high';
  // ...
}
```

From `frontend/src/types/stats.ts` (OpeningWDL — the Stats tab card row):
```typescript
interface OpeningWDL {
  // wins/draws/losses/total drive client-side computeScoreConfidence().
  // Eval significance comes from the backend:
  avg_eval_pawns: number | null;
  eval_p_value?: number | null;
  eval_confidence?: 'low' | 'medium' | 'high';
  eval_n: number;
}
```

From `frontend/src/lib/scoreConfidence.ts`:
```typescript
interface ScoreConfidence {
  score: number;
  ciLow: number;
  ciHigh: number;
  confidence: 'low' | 'medium' | 'high';   // medium/high <=> p < 0.05
  pValue: number;
}
export function computeScoreConfidence(wins: number, draws: number, total: number): ScoreConfidence;
```

From `frontend/src/lib/scoreBulletConfig.ts`:
```typescript
// Returns ZONE_SUCCESS (green) for score >= 0.55, ZONE_DANGER (red) for score <= 0.45,
// ZONE_NEUTRAL (blue) for the in-between band.
export function scoreZoneColor(score: number): string;
```

From `frontend/src/lib/openingStatsZones.ts`:
```typescript
// Returns ZONE_SUCCESS for eval >= +0.30, ZONE_DANGER for eval <= -0.30, ZONE_NEUTRAL between.
export function evalZoneColor(value: number): string;
```

From `frontend/src/lib/arrowColor.ts`:
```typescript
export const DARK_GREEN = '#1E6B1E';
export const DARK_RED = '#9B1C1C';
export const DARK_BLUE = '#1E40AF';   // CHANGE to a neutral grey via theme.ts
```

From `frontend/src/components/charts/MiniBulletChart.tsx`:
```typescript
interface MiniBulletChartProps {
  // ...
  // 'zone' (default): bar fill follows the zone color (green/red/blue).
  // 'neutral': bar fill is BULLET_BAR_NEUTRAL (light grey/white).
  barColor?: 'zone' | 'neutral';
}
```
</interfaces>

<reference_implementation>
The "white bar across Openings" pattern was implemented in 260507-t4r and lives at:
- `frontend/src/components/stats/OpeningStatsCard.tsx` (lines 104-114, 159-169) — passes `barColor="neutral"` to both the score and eval bullets.
- `frontend/src/components/insights/OpeningFindingCard.tsx` (lines 131-141, 156-167) — same pattern.

Backing constant: `BULLET_BAR_NEUTRAL = 'oklch(0.85 0 0)'` in `theme.ts` (already exists, no new constant needed for the bar).

The font-gating reference is `OpeningStatsCard.tsx` line 80 (`isReliableScore = opening.total >= MIN_GAMES_FOR_RELIABLE_STATS`) and line 178 (conditional `style={{ color: isReliableScore ? scoreZoneColor(...) : undefined }}`). It currently gates only on n>=10 — this plan extends the gate to also require p < 0.05 (i.e. `confidence !== 'low'`), and applies the same gate to surfaces that don't yet have it.
</reference_implementation>
</context>

<tasks>

<task type="auto">
  <name>Task 1: Add ARROW_NEUTRAL theme token + significance helper, switch arrow palette to grey</name>
  <files>
    frontend/src/lib/theme.ts,
    frontend/src/lib/arrowColor.ts,
    frontend/src/lib/significance.ts (new)
  </files>
  <action>
**1a. Add ARROW_NEUTRAL to `frontend/src/lib/theme.ts`** (alongside the other arrow/board constants — pick a sensible insertion point, e.g. just after `BULLET_BAR_NEUTRAL`):

```ts
// Categorical "neutral" board arrow color (Move Explorer). Used for arrows
// whose move falls in the in-between score band, has too few games, or has
// low statistical confidence. Rendered at ARROW_LOW_EMPHASIS_OPACITY (0.30)
// in ChessBoard.tsx so it visually reads as a transparent grey on both the
// warm-wood light squares and the darker square — high contrast against
// DARK_GREEN/DARK_RED in the same overlay.
//
// Hex (not oklch) because the Move Explorer + ChessBoard rely on string
// equality `arrow.color === DARK_BLUE` to choose the low-emphasis opacity
// branch, so DARK_BLUE in arrowColor.ts re-exports this exact string.
export const ARROW_NEUTRAL = '#6B7280';  // Tailwind gray-500 / matches WDL_BORDER_DRAW
```

**1b. Re-point `DARK_BLUE` in `frontend/src/lib/arrowColor.ts`** to use the theme token:

```ts
// at top of file, near other imports
import { ARROW_NEUTRAL } from '@/lib/theme';

// existing line:
//   export const DARK_BLUE = '#1E40AF';
// becomes:
export const DARK_BLUE = ARROW_NEUTRAL;
```

Keep the constant **name** `DARK_BLUE` for now to minimize blast radius — every call site (`ChessBoard.tsx`, `MoveExplorer.tsx`) uses `=== DARK_BLUE` for the categorical equality check, and renaming is out of scope. The semantic mismatch (the constant is named DARK_BLUE but holds a grey) is acceptable for this quick task; flag it in a one-line comment above the export ("Historically blue; now grey via ARROW_NEUTRAL — categorical equality preserved.").

Also update the file-top comment block (lines 1-17) so the docstring says "the board renders these grey arrows at a much lower opacity" instead of "blue arrows". One pass through all "blue" mentions in this file is fine.

**1c. Create `frontend/src/lib/significance.ts`** — small shared helper used by Tasks 2-4:

```ts
/**
 * Statistical-significance helper for zone-coloring text labels.
 *
 * The Openings tabs only paint a value red/green when (a) the value falls in
 * the red or green zone, and (b) the result is statistically significant at
 * p < 0.05. Otherwise the text renders in the default foreground color so the
 * eye is drawn to values we're confident about.
 *
 * For the score domain, `confidence !== 'low'` is equivalent to `p < 0.05`
 * because computeScoreConfidence buckets at CONFIDENCE_MEDIUM_MAX_P = 0.05
 * (see scoreConfidence.ts). Either expression works at call sites; this
 * helper accepts both shapes so callers can pass whichever they have on
 * hand.
 */
export const SIGNIFICANCE_P_THRESHOLD = 0.05;

export function isSignificant(pValue: number | null | undefined): boolean {
  return pValue != null && pValue < SIGNIFICANCE_P_THRESHOLD;
}
```

Export from this file so Tasks 2-4 can `import { isSignificant, SIGNIFICANCE_P_THRESHOLD } from '@/lib/significance'`. Keep this helper tiny and dependency-free.
  </action>
  <verify>
    <automated>cd /home/aimfeld/Projects/Python/flawchess/frontend && npm run lint 2>&1 | tail -20 && npm run build 2>&1 | tail -10</automated>
  </verify>
  <done>
    `ARROW_NEUTRAL` exists in theme.ts; `DARK_BLUE` in arrowColor.ts re-exports it; `significance.ts` exists with `isSignificant` + `SIGNIFICANCE_P_THRESHOLD`; npm run lint and npm run build are green; chessboard arrows that previously rendered blue now render grey at low opacity (verifiable manually but not gated here — covered by Task 5 visual verify).
  </done>
</task>

<task type="auto">
  <name>Task 2: Gate Openings Moves subtab score-text + add neutral bullet bar</name>
  <files>
    frontend/src/components/move-explorer/MoveExplorer.tsx,
    frontend/src/pages/Openings.tsx
  </files>
  <action>
**2a. `MoveExplorer.tsx` (per-row Score column).** The row currently gates on `isReliable = entry.game_count >= MIN_GAMES_FOR_RELIABLE_STATS && entry.confidence !== 'low'` (line 265-266). The user wants the gate to also require the value be in a colored zone (not the in-between band). Change the gate to also require zone-coloring is meaningful:

```ts
import { isSignificant } from '@/lib/significance';
import { ZONE_NEUTRAL } from '@/lib/theme';

// Replace existing isReliable + scoreColor block (around lines 262-267) with:
const zoneHex = scoreZoneColor(entry.score);
const isInColoredZone = zoneHex !== ZONE_NEUTRAL;
const showZoneFontColor =
  entry.game_count >= MIN_GAMES_FOR_RELIABLE_STATS &&
  isSignificant(entry.p_value) &&
  isInColoredZone;
// `scoreColor` previously drove the Score % text color. Now: zone color when
// significant + in colored zone, else undefined (falls back to default text).
const scoreColor = showZoneFontColor ? zoneHex : undefined;
```

Then line 380 changes from:
```tsx
<span className="font-semibold" style={{ color: scoreColor }}>
```
to:
```tsx
<span className="font-semibold" style={scoreColor ? { color: scoreColor } : undefined}>
```

Keep the existing **row-bg tint** logic (`zoneTintHex` from `getArrowColor`) untouched — that's the row background, not the font, and the user only spoke about font and bullet-chart bar. The arrow-tint stays gated on the existing reliability rule. Note the row tint will already shift to grey for low-confidence rows because we're changing `DARK_BLUE`'s hex in Task 1.

Keep the `isUnreliable` opacity dim (line 256, drives `rowStyle.opacity = UNRELIABLE_OPACITY`) — that's a row-wide cue independent of font color and is out of scope.

**2b. `Openings.tsx` "current position" panel (Moves subtab)** — the score text + bullet at lines 832-857.

The current code at line 808-809 computes:
```ts
const isReliableScore =
  stats.total >= MIN_GAMES_FOR_RELIABLE_STATS && stats.confidence !== 'low';
const scoreColor = isReliableScore ? scoreZoneColor(stats.score) : ZONE_NEUTRAL;
```

Apply the same gate as 2a (also require colored zone, also require p < 0.05):

```ts
import { isSignificant } from '@/lib/significance';
// ZONE_NEUTRAL already imported (line 73 area).

const zoneHex = scoreZoneColor(stats.score);
const isInColoredZone = zoneHex !== ZONE_NEUTRAL;
const showZoneFontColor =
  stats.total >= MIN_GAMES_FOR_RELIABLE_STATS &&
  isSignificant(stats.p_value) &&
  isInColoredZone;
const scoreColor = showZoneFontColor ? zoneHex : undefined;
```

Then line 842 changes from:
```tsx
<span className="font-semibold" style={{ color: scoreColor }}>{scorePct}%</span>
```
to:
```tsx
<span className="font-semibold" style={scoreColor ? { color: scoreColor } : undefined}>{scorePct}%</span>
```

**2c. Add `barColor="neutral"` to the Moves subtab "current position" MiniBulletChart** (Openings.tsx around line 848-857). Currently the prop is omitted, which defaults to `'zone'`. Add it so the bar reads white like the rest of the Openings tabs:

```tsx
<MiniBulletChart
  value={stats.score}
  center={SCORE_BULLET_CENTER}
  neutralMin={SCORE_BULLET_NEUTRAL_MIN}
  neutralMax={SCORE_BULLET_NEUTRAL_MAX}
  domain={scoreBulletDomain()}
  ciLow={clampScoreCi(stats.ci_low)}
  ciHigh={clampScoreCi(stats.ci_high)}
  barColor="neutral"   // <-- ADD
  ariaLabel={`Score ${scorePct}% vs 50% baseline`}
/>
```

**Mobile parity:** This whole block lives in the shared `moveExplorerContent` definition that gets rendered in both the desktop (`<TabsContent value="explorer">` at line 1374) and the mobile (`<TabsContent value="explorer">` at the mobile Tabs section near line 1485) trees. Visually inspect once that both branches render via the same `moveExplorerContent` variable so the change applies on both viewports. If the mobile branch defines its own duplicate JSX, apply the change there too.
  </action>
  <verify>
    <automated>cd /home/aimfeld/Projects/Python/flawchess/frontend && npm run lint 2>&1 | tail -20 && npm test -- --run src/components/move-explorer 2>&1 | tail -25</automated>
  </verify>
  <done>
    Moves subtab Score column: red/green only when n>=10 AND p<0.05 AND zone is colored, else default foreground. "Current position" score panel same gating. "Current position" MiniBulletChart bar reads white. Tests still pass; lint clean.
  </done>
</task>

<task type="auto">
  <name>Task 3: Tighten Stats + Insights card font gating to require p < 0.05</name>
  <files>
    frontend/src/components/stats/OpeningStatsCard.tsx,
    frontend/src/components/insights/OpeningFindingCard.tsx
  </files>
  <action>
Both cards already use `barColor="neutral"` for both bullet bars — no bar changes here. Only the Score % and Eval text gating needs to be tightened.

**3a. `OpeningStatsCard.tsx`:**

The existing reliability gate (lines 79-80):
```ts
const isReliableScore = opening.total >= MIN_GAMES_FOR_RELIABLE_STATS;
const borderLeftColor = isReliableScore ? scoreZoneColor(derivedScore) : 'transparent';
```

This drives both the **left border** of the card AND the **Score % text color** (line 178). The user's rule applies to fonts only — keep `borderLeftColor` driven by `isReliableScore` alone (border treatment is out of scope), but introduce a separate `showScoreZoneFont` gate for the text:

```ts
import { isSignificant } from '@/lib/significance';
import { ZONE_NEUTRAL } from '@/lib/theme';

// Existing: derivedScore + scoreStats from computeScoreConfidence (lines 68-73).
// Existing: borderLeftColor logic stays unchanged (out of scope per user constraint).

// NEW: separate gate for the SCORE % font color. Requires:
//   - n >= MIN_GAMES_FOR_RELIABLE_STATS (existing reliability gate)
//   - p < 0.05 (significance) — equivalent to scoreStats.confidence !== 'low'
//   - zone is colored (red or green), not the in-between band
const scoreZoneHex = scoreZoneColor(derivedScore);
const showScoreZoneFont =
  opening.total >= MIN_GAMES_FOR_RELIABLE_STATS &&
  isSignificant(scoreStats.pValue) &&
  scoreZoneHex !== ZONE_NEUTRAL;
```

Then line 178 changes from:
```tsx
style={{ color: isReliableScore ? scoreZoneColor(derivedScore) : undefined }}
```
to:
```tsx
style={showScoreZoneFont ? { color: scoreZoneHex } : undefined}
```

**For the Eval (Stockfish) text** — line 89-93:
```tsx
const mgEvalTextContent = hasMgEval ? (
  <span
    className="font-semibold inline-flex items-center gap-0.5"
    style={{ color: evalZoneColor(opening.avg_eval_pawns as number) }}
  >
```

Apply the eval-significance gate using `eval_p_value` and check the eval value is in a colored zone:

```ts
const evalZoneHex = hasMgEval ? evalZoneColor(opening.avg_eval_pawns as number) : null;
const showEvalZoneFont =
  hasMgEval &&
  isSignificant(opening.eval_p_value) &&
  evalZoneHex !== ZONE_NEUTRAL;
```

Then update the span to `style={showEvalZoneFont ? { color: evalZoneHex } : undefined}`.

**3b. `OpeningFindingCard.tsx`:**

Currently has NO font-significance gating — line 173 paints the Score % in `borderLeftColor` (which is `scoreZoneColor(finding.score)`) unconditionally, and line 121 paints the Eval text in `evalZoneColor(...)` unconditionally. Add gating identical to 3a, using `finding.p_value` and `finding.eval_p_value` directly:

```ts
import { isSignificant } from '@/lib/significance';
import { ZONE_NEUTRAL } from '@/lib/theme';

// Score gate
const scoreZoneHex = scoreZoneColor(finding.score);
const showScoreZoneFont =
  finding.n_games >= MIN_GAMES_FOR_RELIABLE_STATS &&
  isSignificant(finding.p_value) &&
  scoreZoneHex !== ZONE_NEUTRAL;

// Eval gate
const evalZoneHex = hasMgEval ? evalZoneColor(avgEvalPawns as number) : null;
const showEvalZoneFont =
  hasMgEval &&
  isSignificant(finding.eval_p_value) &&
  evalZoneHex !== ZONE_NEUTRAL;
```

Then update:
- Line 173: `style={{ color: borderLeftColor }}` → `style={showScoreZoneFont ? { color: scoreZoneHex } : undefined}`.
- Line 121 (inside `mgEvalTextContent`): `style={{ color: evalZoneColor(avgEvalPawns as number) }}` → `style={showEvalZoneFont ? { color: evalZoneHex } : undefined}`.

Leave `borderLeftColor` (the card's left edge stripe) untouched — it's a card-frame treatment, not a font; the user constraint is scoped to font + bullet bars. The card border is also already gated on `isUnreliable` (line 64-69) which collapses to transparent when low-confidence, so no double-gating is needed.

**Mobile parity:** Both cards have a `sm:hidden` mobile branch and a `hidden sm:flex` desktop branch (OpeningStatsCard lines 257-285, OpeningFindingCard lines 267-304). Both branches render the SAME `scoreEvalBlock` variable, so the gating change applies to both automatically. Verify by re-reading the JSX after editing — there is no duplicated text/bullet JSX to worry about.
  </action>
  <verify>
    <automated>cd /home/aimfeld/Projects/Python/flawchess/frontend && npm run lint 2>&1 | tail -10 && npm test -- --run src/components/insights src/components/stats 2>&1 | tail -30</automated>
  </verify>
  <done>
    Stats card and Insights card render Score % and Eval text in zone color ONLY when n>=10 AND p<0.05 AND value falls in red/green zone. Otherwise default foreground. Existing tests for these components still pass (no test currently asserts the un-gated behavior; if any do, update them to assert the new gated behavior — most use `hasMgEval` semantics that will not regress).
  </done>
</task>

<task type="auto">
  <name>Task 4: Endgames Stats — neutral bullet bars only (no font changes)</name>
  <files>
    frontend/src/components/charts/EndgameWDLChart.tsx,
    frontend/src/components/charts/EndgamePerformanceSection.tsx,
    frontend/src/components/charts/EndgameScoreGapSection.tsx
  </files>
  <action>
Per the user constraint: "In the Endgames Stats tab, also use only white bars in the bullet charts, but **don't change any colored values** (we don't have statistical tests for endgames stats yet)."

For each MiniBulletChart usage in the three files below, add `barColor="neutral"`. Do NOT touch any zone-colored text, gauge, or border code in these files.

**4a. `EndgameWDLChart.tsx` line 159 + line 249** — both omit `barColor`. Add `barColor="neutral"`.

**4b. `EndgamePerformanceSection.tsx` line 179 + line 242** — both omit `barColor`. Add `barColor="neutral"`.

**4c. `EndgameScoreGapSection.tsx` line 377 + line 489** — both omit `barColor`. Add `barColor="neutral"`.

Each edit is a one-line prop addition. Open the file, locate the `<MiniBulletChart` JSX, and insert `barColor="neutral"` on its own line before `ariaLabel`. Match the indentation of surrounding props.

**Mobile parity:** These chart components are unified across desktop/mobile via responsive Tailwind classes — there is no separate mobile JSX to update. The Endgames page (`Endgames.tsx`) renders the same chart components for both viewports.

**Out of scope reminders:**
- DO NOT change `evalZoneColor`, gauge zone fills, `scoreZoneColor`, line colors, or any other colored value in the Endgames tab.
- DO NOT add a `barColor="neutral"` to `EndgameGauge.tsx`, `EndgameConvRecovChart.tsx`, `EndgameClockPressureSection.tsx`, or `EndgameTimePressureSection.tsx` — only the three files listed above use MiniBulletChart in the Endgames Stats tab.
  </action>
  <verify>
    <automated>cd /home/aimfeld/Projects/Python/flawchess/frontend && grep -c 'barColor="neutral"' src/components/charts/EndgameWDLChart.tsx src/components/charts/EndgamePerformanceSection.tsx src/components/charts/EndgameScoreGapSection.tsx && npm run lint 2>&1 | tail -10 && npm test -- --run src/components/charts 2>&1 | tail -20</automated>
  </verify>
  <done>
    `grep -c 'barColor="neutral"'` reports `2` for each of the three files (six total additions). Lint green. Existing chart tests pass (the prop default is 'zone' so no test should hard-code a zone color expectation; if any do, update them to expect BULLET_BAR_NEUTRAL).
  </done>
</task>

<task type="auto">
  <name>Task 5: Final cross-check — knip, build, manual visual smoke</name>
  <files>(no file changes — verification only)</files>
  <action>
Run the frontend full-pipeline checks. Fix any issues that surface (most likely: unused imports of `ZONE_NEUTRAL` or `isSignificant` if a previous task left a stale import; or knip flagging a now-unused export).

If `npm run knip` complains that `SIGNIFICANCE_P_THRESHOLD` is unused, that's expected if no consumer imported it — leave it exported for now (it's a small documented constant), or remove it if knip blocks. The `isSignificant` function MUST be used by Tasks 2 and 3 — if knip says it's unused, you missed a call site.

Manual visual smoke (note in the SUMMARY for the user to check, do not gate on this):
1. `bin/run_local.sh` (or just `npm run dev` in `frontend/`).
2. Navigate to /openings/explorer with a user that has imported games. Confirm:
   - Move Explorer table: rows in the in-between band or low-confidence rows render the Score % in default white text; reliable + significant + colored-zone rows render red/green.
   - "Current position" panel above the table: Score % uses default white when in-between band or insignificant, red/green only when in colored zone AND significant. Bullet bar is white.
   - Board arrows: previously-blue arrows (in-between, low-data, low-confidence) now render as transparent grey instead of blue.
3. /openings/stats: Stats cards already pass barColor=neutral. Confirm the Score % and Eval text ONLY tint red/green when significant + in colored zone.
4. /openings/insights: same as Stats, on OpeningFindingCard.
5. /endgames/stats: bullet bars are white across WDL, Performance, and Score Gap sections. Numeric labels (gauge zones, eval/score numbers) are UNCHANGED.
6. Mobile viewport (DevTools width <640px): repeat 2-5; the same components render via shared JSX so no per-viewport regression is expected.
  </action>
  <verify>
    <automated>cd /home/aimfeld/Projects/Python/flawchess/frontend && npm run lint && npm run knip && npm run build && npm test 2>&1 | tail -30</automated>
  </verify>
  <done>
    All four checks (lint, knip, build, test) green. SUMMARY.md notes the manual visual smoke checklist for the user.
  </done>
</task>

</tasks>

<verification>
1. `cd frontend && npm run lint` — green.
2. `cd frontend && npm run knip` — green.
3. `cd frontend && npm run build` — green (TypeScript compile + Vite production build).
4. `cd frontend && npm test` — all existing tests pass; new behavior is asserted only by the visual smoke (this is a pure styling tweak, no new logic worth a unit test beyond what `MiniBulletChart.test.tsx` already covers for `barColor="neutral"`).
5. Manual visual smoke (see Task 5 action) — operator-confirmed, not gated.
</verification>

<success_criteria>
- Every Openings subtab renders Score % and Stockfish eval text in zone color (red/green) ONLY when the value is in the red or green zone AND the result is statistically significant at p < 0.05; otherwise default foreground.
- Every Openings subtab MiniBulletChart bar renders in BULLET_BAR_NEUTRAL.
- Endgames Stats tab MiniBulletChart bars render in BULLET_BAR_NEUTRAL; no other colors changed.
- Chessboard arrows that previously rendered DARK_BLUE now render as a transparent grey via the new `ARROW_NEUTRAL` theme token.
- `npm run lint`, `npm run knip`, `npm run build`, and `npm test` are all green.
</success_criteria>

<output>
After completion, create `.planning/quick/260508-dcp-neutralize-non-significant-zone-fonts-us/260508-dcp-SUMMARY.md` summarizing:
- Files touched (theme.ts, arrowColor.ts, significance.ts, MoveExplorer.tsx, Openings.tsx, OpeningStatsCard.tsx, OpeningFindingCard.tsx, EndgameWDLChart.tsx, EndgamePerformanceSection.tsx, EndgameScoreGapSection.tsx).
- The 4-line significance helper introduced (and that confidence !== 'low' equals p < 0.05 for the score domain).
- That `DARK_BLUE` was kept as the constant name to preserve categorical equality, but its hex value is now grey via `ARROW_NEUTRAL`. A future quick task can rename it if/when the naming starts confusing readers.
- Manual visual smoke checklist for the operator.
</output>
