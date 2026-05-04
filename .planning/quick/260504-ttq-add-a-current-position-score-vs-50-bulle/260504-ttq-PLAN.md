---
phase: quick-260504-ttq
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - app/schemas/openings.py
  - app/services/openings_service.py
  - tests/test_openings_service.py
  - frontend/src/types/api.ts
  - frontend/src/lib/scoreBulletConfig.ts
  - frontend/src/lib/__tests__/scoreBulletConfig.test.ts
  - frontend/src/components/insights/ScoreConfidencePopover.tsx
  - frontend/src/pages/Openings.tsx
  - frontend/src/pages/__tests__/Openings.statsBoard.test.tsx
autonomous: true
requirements:
  - quick-260504-ttq
must_haves:
  truths:
    - "When the user opens the Openings → Moves tab on a position with games, a score-vs-50% bullet chart renders directly under the existing 'Results played as White/Black' WDL bar."
    - "The bullet shows the current position's score (W + 0.5·D)/N as a fill bar centered on 0.5, with a 95% Wald CI whisker."
    - "Bullet zones are danger (<0.45), neutral (0.45–0.55), and success (>0.55), matching MoveExplorer's MINOR_EFFECT_SCORE threshold."
    - "When position_stats.total < 10, both the bullet and the WDL bar above it render at UNRELIABLE_OPACITY so the bullet doubles as a trust indicator for the bar."
    - "Hovering or tapping a help icon next to the bullet opens a popover containing WdlConfidenceTooltip with score, p_value, game count, and confidence level."
    - "The chart is rendered exactly once in Openings.tsx (Moves tab moveExplorerContent block); it is NOT rendered per move and NOT rendered in the Stats tab."
    - "Backend NextMovesResponse.position_stats now includes score, confidence, p_value, ci_low, ci_high, computed via the existing compute_confidence_bucket helper (same Wald formula as the per-move pipeline)."
  artifacts:
    - path: "app/schemas/openings.py"
      provides: "WDLStats Pydantic model extended with score/confidence/p_value/ci_low/ci_high fields"
      contains: "score: float"
    - path: "app/services/openings_service.py"
      provides: "get_next_moves builds position_stats with the new score-confidence fields via compute_confidence_bucket"
      contains: "compute_confidence_bucket"
    - path: "tests/test_openings_service.py"
      provides: "Test asserting position_stats includes score/confidence/p_value/ci_low/ci_high with correct Wald math"
    - path: "frontend/src/types/api.ts"
      provides: "WDLStats TS interface extended to mirror backend; confidence as Literal 'low'|'medium'|'high'"
    - path: "frontend/src/lib/scoreBulletConfig.ts"
      provides: "Score-domain bullet constants (SCORE_BULLET_CENTER, NEUTRAL_MIN/MAX, DOMAIN, helpers for CI in domain units)"
      contains: "SCORE_BULLET_CENTER"
    - path: "frontend/src/lib/__tests__/scoreBulletConfig.test.ts"
      provides: "Unit tests for any non-trivial helpers in scoreBulletConfig.ts"
    - path: "frontend/src/components/insights/ScoreConfidencePopover.tsx"
      provides: "Help-icon popover wrapping WdlConfidenceTooltip (score-domain sibling to BulletConfidencePopover)"
      contains: "WdlConfidenceTooltip"
    - path: "frontend/src/pages/Openings.tsx"
      provides: "Renders MiniBulletChart + ScoreConfidencePopover under WDLChartRow in moveExplorerContent; applies UNRELIABLE_OPACITY when total < MIN_GAMES_FOR_RELIABLE_STATS"
      contains: "MiniBulletChart"
    - path: "frontend/src/pages/__tests__/Openings.statsBoard.test.tsx"
      provides: "Test asserting the Moves-tab score bullet renders with expected testid, value, CI whisker, and mute-state when n<10"
  key_links:
    - from: "app/services/openings_service.py (get_next_moves)"
      to: "app/services/score_confidence.py (compute_confidence_bucket)"
      via: "(w, d, lo, total) → (confidence, p_value, se); CI built as score ± 1.96·se, clamped to [0, 1]"
      pattern: "compute_confidence_bucket\\(.*total\\)"
    - from: "frontend/src/pages/Openings.tsx (moveExplorerContent)"
      to: "frontend/src/components/charts/MiniBulletChart.tsx"
      via: "value=position_stats.score, center=0.5, neutralMin=-0.05, neutralMax=+0.05, domain=0.20, ciLow/ciHigh from response"
      pattern: "MiniBulletChart"
    - from: "ScoreConfidencePopover.tsx"
      to: "WdlConfidenceTooltip.tsx"
      via: "renders tooltip body inside Radix Popover content"
      pattern: "WdlConfidenceTooltip"
---

<objective>
Add a single current-position score-vs-50% bullet chart to the Openings → Moves tab, rendered directly under the existing "Results played as White/Black" WDL bar inside `moveExplorerContent`. The bullet visualizes `(W + 0.5·D) / N` for the current position with a Wald 95% CI whisker, neutral zone 0.45–0.55, domain 0.30–0.70. When `position_stats.total < 10` (MIN_GAMES_FOR_RELIABLE_STATS) the bullet AND the WDL bar above it render dimmed via UNRELIABLE_OPACITY so the bullet doubles as a trust indicator for the bar above. A help-icon popover next to the bullet opens `WdlConfidenceTooltip` with score / p_value / game count / confidence level.

Server-side, extend `NextMovesResponse.position_stats` (the `WDLStats` schema) with `score`, `confidence`, `p_value`, `ci_low`, `ci_high` computed via the existing `compute_confidence_bucket` helper — same Wald formula as the per-move pipeline (`openings_service.get_next_moves` lines 437-446).

Purpose: give the user an at-a-glance signal of whether their current-position WDL is meaningfully different from 50% baseline, with confidence bounds that also indicate how trustworthy the WDL bar above is.

Output: extended schema + computed CI on the backend, single-rendering-site bullet on the Moves tab frontend, popover, mute behavior, tests on both sides.
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/STATE.md
@CLAUDE.md
@frontend/src/pages/Openings.tsx
@frontend/src/components/charts/MiniBulletChart.tsx
@frontend/src/components/insights/WdlConfidenceTooltip.tsx
@frontend/src/components/insights/BulletConfidencePopover.tsx
@frontend/src/components/move-explorer/MoveExplorer.tsx
@frontend/src/types/api.ts
@app/services/score_confidence.py
@app/services/openings_service.py
@app/schemas/openings.py
@tests/test_openings_service.py
@frontend/src/pages/__tests__/Openings.statsBoard.test.tsx

<interfaces>
<!-- Pre-extracted contracts so the executor doesn't need to re-explore. -->

Backend — current shape (app/schemas/openings.py:52):
```python
class WDLStats(BaseModel):
    wins: int
    draws: int
    losses: int
    total: int
    win_pct: float
    draw_pct: float
    loss_pct: float
```

Backend — confidence helper (app/services/score_confidence.py):
```python
def compute_confidence_bucket(
    w: int, d: int, losses: int, n: int
) -> tuple[Literal["low", "medium", "high"], float, float]:
    """Returns (confidence_bucket, one_sided_p_value, standard_error).
    SE is the Wald SE of (W + 0.5·D)/N. Use score ± 1.96·SE for 95% CI."""
```

Backend — current per-move usage (app/services/openings_service.py:437-446):
```python
score = (w + 0.5 * d) / gc if gc > 0 else 0.5
confidence, p_value, _se = compute_confidence_bucket(w, d, lo, gc)
```
Note: per-move call discards SE. The position_stats path needs SE for CI.

Frontend — current shape (frontend/src/types/api.ts:67-75):
```typescript
export interface WDLStats {
  wins: number;
  draws: number;
  losses: number;
  total: number;
  win_pct: number;
  draw_pct: number;
  loss_pct: number;
}
```

Frontend — MiniBulletChart accepts (relevant props):
```typescript
{ value, neutralMin?, neutralMax?, domain?, center?, ariaLabel?,
  heightClass?, valueHeightClass?, ciLow?, ciHigh?, tickPawns? }
```
- `neutralMin` / `neutralMax` are OFFSETS from `center` (not absolute).
- For score domain: center=0.5, neutralMin=-0.05, neutralMax=+0.05, domain=0.20.
- `ciLow` / `ciHigh` are ABSOLUTE values (not offsets); pass `score - 1.96·SE` and `score + 1.96·SE` clamped to [0, 1].

Frontend — WdlConfidenceTooltip props:
```typescript
{ level: 'low'|'medium'|'high'; pValue: number; score: number; gameCount: number }
```

Frontend — existing constants to reuse:
- `MIN_GAMES_FOR_RELIABLE_STATS = 10` from `@/lib/theme`
- `UNRELIABLE_OPACITY = 0.5` from `@/lib/theme`
- `SCORE_PIVOT = 0.5`, `MINOR_EFFECT_SCORE = 0.05` from `@/lib/arrowColor`

Rendering site (Openings.tsx:924-957) — desktop and mobile share this JSX:
```tsx
const moveExplorerContent = (
  <div className="flex flex-col gap-4">
    {gamesData && gamesData.stats.total > 0 && (
      <div className="charcoal-texture rounded-md p-4 order-2 lg:order-1">
        <WDLChartRow data={gamesData.stats} ... testId="wdl-moves-position" />
        {/* ← INSERT BULLET CHART HERE, INSIDE the same charcoal-texture wrapper */}
      </div>
    )}
    ...
  </div>
);
```
</interfaces>
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: Extend backend WDLStats with score/confidence/p_value/ci_low/ci_high</name>
  <files>app/schemas/openings.py, app/services/openings_service.py, tests/test_openings_service.py</files>
  <behavior>
    - `NextMovesResponse.position_stats` returns a `WDLStats` that now includes `score`, `confidence` (Literal["low","medium","high"]), `p_value`, `ci_low`, `ci_high`.
    - Values are computed from (wins, draws, losses, total) via `compute_confidence_bucket`, identical math to the per-move pipeline at openings_service.py:437-446.
    - `score = (w + 0.5·d) / total` when total > 0, else 0.5.
    - `ci_low = max(0.0, score - 1.96·se)`, `ci_high = min(1.0, score + 1.96·se)` (clamped to [0, 1]).
    - When `total == 0` (no games for position), score=0.5, confidence="low", p_value=0.5, ci_low=0.5, ci_high=0.5 (the existing zero-row early-return path at openings_service.py:414).
    - The empty-position-stats branch (no games) still returns a valid WDLStats with the new fields populated to those neutral defaults — not Optional.
    - Test in tests/test_openings_service.py asserts position_stats.score, confidence, p_value, ci_low, ci_high are present and numerically correct for a known (W,D,L,N) fixture (extend the existing `test_basic_next_moves` test or add a sibling test in the same TestNextMoves class). At minimum: assert `position_stats.score == pytest.approx((wins + 0.5·draws) / total)` and `ci_low <= score <= ci_high` and `0 <= ci_low` and `ci_high <= 1`.
  </behavior>
  <action>
    1. Edit `app/schemas/openings.py` — extend `WDLStats` (line 52) to add five new required fields:
       ```python
       score: float
       confidence: Literal["low", "medium", "high"]
       p_value: float
       ci_low: float
       ci_high: float
       ```
       Import `Literal` from `typing` if not already imported. Note: `WDLStats` is also used by `OpeningsResponse.stats` (line 89) — that call site MUST be updated too (see step 3).

    2. Add a small constant for the 95% Wald multiplier in `openings_service.py` (do NOT use a magic 1.96):
       ```python
       # Wald 95% CI multiplier (z_{0.975}); kept local to openings_service to avoid
       # cross-module churn. Matches the bookmark/insights services' CI bound.
       _WALD_95_Z = 1.959964
       ```
       Or, if `app/services/opening_insights_constants.py` already exports a 1.96 constant (grep first), reuse that. Otherwise define it locally with the comment above.

    3. Edit `app/services/openings_service.py`:
       - In `get_next_moves` around line 388, after `total` is computed, call `compute_confidence_bucket(wins, draws, losses, total)` to get `(confidence, p_value, se)`. Compute `score`, `ci_low`, `ci_high` (clamped to [0, 1]). Pass them to the `WDLStats(...)` constructor.
       - Handle the early-return zero-rows branch (line 413-414): the `WDLStats` built before that branch already has the new fields, so the early return needs no change. Verify by reading `query_wdl_counts` semantics — when no games match, total=0, and `compute_confidence_bucket(0, 0, 0, 0)` returns `("low", 0.5, 0.0)` per the n<=0 guard, giving score=0.5, ci_low=0.5, ci_high=0.5. Good.
       - **Other call sites of WDLStats**: grep `WDLStats(` across `app/` and update every constructor to pass the new fields. Most likely sites: the `/openings/positions` route in `openings_service.py` populating `OpeningsResponse.stats`. Use `compute_confidence_bucket` there too with the same formula. Do NOT skip these — Pydantic will raise at runtime since the fields are required.

    4. Edit `tests/test_openings_service.py`:
       - Extend `TestNextMoves::test_basic_next_moves` (around line 356) to assert the new fields on `response.position_stats`:
         - `score == pytest.approx((wins_count + 0.5 * draws_count) / total)`
         - `confidence in {"low", "medium", "high"}`
         - `0.0 <= p_value <= 0.5` (one-sided)
         - `0.0 <= ci_low <= score <= ci_high <= 1.0`
       - Add a small unit test verifying that with a fabricated (W=8, D=0, L=2, N=10) fixture, `score == 0.8` and `ci_low/ci_high` bracket 0.8 within [0, 1].
       - If `OpeningsResponse.stats` is exercised by an existing test (`test_wdl_computation` line 171), update its assertions to spot-check at least one of the new fields so the regression catches missing wiring.

    5. Run `uv run ruff check app/ tests/`, `uv run ruff format app/ tests/`, `uv run ty check app/ tests/`, `uv run pytest tests/test_openings_service.py -x`. All must pass with zero errors. Per CLAUDE.md: explicit return types on any new helper, `Literal` for the new field, no `# type: ignore` (use `# ty: ignore[rule]` only with a reason if absolutely needed).
  </action>
  <verify>
    <automated>uv run ruff check app/ tests/ && uv run ty check app/ tests/ && uv run pytest tests/test_openings_service.py -x</automated>
  </verify>
  <done>
    - `WDLStats` schema has score, confidence, p_value, ci_low, ci_high.
    - All `WDLStats(...)` constructor sites pass the new fields (grep returns zero stale call sites).
    - `tests/test_openings_service.py` asserts new fields on position_stats; pytest passes.
    - ruff, ty, pytest all clean for the touched files.
  </done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: Add score-bullet config + ScoreConfidencePopover + frontend WDLStats type</name>
  <files>frontend/src/types/api.ts, frontend/src/lib/scoreBulletConfig.ts, frontend/src/lib/__tests__/scoreBulletConfig.test.ts, frontend/src/components/insights/ScoreConfidencePopover.tsx</files>
  <behavior>
    - `frontend/src/types/api.ts` `WDLStats` interface mirrors the backend exactly (adds score: number, confidence: 'low'|'medium'|'high', p_value: number, ci_low: number, ci_high: number).
    - `frontend/src/lib/scoreBulletConfig.ts` exports score-domain constants and a single CI-clamping helper:
      - `SCORE_BULLET_CENTER = 0.5`
      - `SCORE_BULLET_NEUTRAL_MIN = -0.05` (offset from center, matching MINOR_EFFECT_SCORE)
      - `SCORE_BULLET_NEUTRAL_MAX = 0.05`
      - `SCORE_BULLET_DOMAIN = 0.20` (axis spans 0.30–0.70)
      - `clampScoreCi(value: number): number` — clamps to [0, 1].
    - The lib's `__tests__/scoreBulletConfig.test.ts` asserts `clampScoreCi(-0.1) === 0`, `clampScoreCi(1.2) === 1`, `clampScoreCi(0.5) === 0.5`, and that the constants form a coherent domain (center ± domain ⊂ [0, 1], neutralMin < 0 < neutralMax).
    - `ScoreConfidencePopover.tsx` mirrors `BulletConfidencePopover.tsx` but renders `WdlConfidenceTooltip` instead of `EvalConfidenceTooltip`. Props:
      ```typescript
      interface ScoreConfidencePopoverProps {
        level: 'low' | 'medium' | 'high';
        pValue: number;
        score: number;
        gameCount: number;
        testId: string;
        ariaLabel?: string;
        triggerClassName?: string;
      }
      ```
    - The popover's HelpCircle trigger is hover- and tap-activated (same UX as BulletConfidencePopover).
  </behavior>
  <action>
    1. Edit `frontend/src/types/api.ts` (line 67) — extend `WDLStats`:
       ```typescript
       export interface WDLStats {
         wins: number;
         draws: number;
         losses: number;
         total: number;
         win_pct: number;
         draw_pct: number;
         loss_pct: number;
         score: number;
         confidence: 'low' | 'medium' | 'high';
         p_value: number;
         ci_low: number;
         ci_high: number;
       }
       ```

    2. Create `frontend/src/lib/scoreBulletConfig.ts`:
       ```typescript
       /**
        * Score-domain bullet chart configuration. Used by the current-position
        * score-vs-50% bullet on the Openings → Moves tab. Domain matches the
        * MoveExplorer Conf-column visual scale.
        */

       // Center the bullet on the 50% score baseline.
       export const SCORE_BULLET_CENTER = 0.5;

       // Neutral zone: ±5 score points around 0.5, matching MoveExplorer's
       // MINOR_EFFECT_SCORE threshold for "no meaningful edge".
       export const SCORE_BULLET_NEUTRAL_MIN = -0.05;
       export const SCORE_BULLET_NEUTRAL_MAX = 0.05;

       // Axis half-width: spans 0.30–0.70 around center, matching the visual
       // range used elsewhere in the move explorer.
       export const SCORE_BULLET_DOMAIN = 0.20;

       /** Clamp a score-domain value (or CI bound) to the valid [0, 1] range. */
       export function clampScoreCi(value: number): number {
         if (value < 0) return 0;
         if (value > 1) return 1;
         return value;
       }
       ```

    3. Create `frontend/src/lib/__tests__/scoreBulletConfig.test.ts` with vitest:
       ```typescript
       import { describe, it, expect } from 'vitest';
       import {
         SCORE_BULLET_CENTER,
         SCORE_BULLET_NEUTRAL_MIN,
         SCORE_BULLET_NEUTRAL_MAX,
         SCORE_BULLET_DOMAIN,
         clampScoreCi,
       } from '../scoreBulletConfig';

       describe('scoreBulletConfig', () => {
         it('center is 0.5', () => { expect(SCORE_BULLET_CENTER).toBe(0.5); });
         it('neutral zone is symmetric and non-empty', () => {
           expect(SCORE_BULLET_NEUTRAL_MIN).toBeLessThan(0);
           expect(SCORE_BULLET_NEUTRAL_MAX).toBeGreaterThan(0);
         });
         it('domain stays inside [0, 1] when applied to center', () => {
           expect(SCORE_BULLET_CENTER - SCORE_BULLET_DOMAIN).toBeGreaterThanOrEqual(0);
           expect(SCORE_BULLET_CENTER + SCORE_BULLET_DOMAIN).toBeLessThanOrEqual(1);
         });
       });

       describe('clampScoreCi', () => {
         it('clamps below 0', () => { expect(clampScoreCi(-0.1)).toBe(0); });
         it('clamps above 1', () => { expect(clampScoreCi(1.2)).toBe(1); });
         it('passes through values inside [0, 1]', () => {
           expect(clampScoreCi(0)).toBe(0);
           expect(clampScoreCi(0.5)).toBe(0.5);
           expect(clampScoreCi(1)).toBe(1);
         });
       });
       ```

    4. Create `frontend/src/components/insights/ScoreConfidencePopover.tsx` by copying `BulletConfidencePopover.tsx` and:
       - Replace import of `EvalConfidenceTooltip` with `WdlConfidenceTooltip` from `./WdlConfidenceTooltip`.
       - Change props interface to: `{ level, pValue, score, gameCount, testId, ariaLabel?, triggerClassName? }` (drop the eval-specific props and prefaceText — popover content is just the tooltip).
       - Default `ariaLabel = 'Show score confidence details'`.
       - Inside the Popover.Content, render:
         ```tsx
         <WdlConfidenceTooltip
           level={level}
           pValue={pValue}
           score={score}
           gameCount={gameCount}
         />
         ```
       - Keep all hover/tap/keyboard behavior identical to BulletConfidencePopover (same Radix Popover wiring, same 100ms hover delay, same HelpCircle icon, same className tokens).
       - data-testid on trigger uses the `testId` prop (not hardcoded). aria-label uses `ariaLabel` prop. Per CLAUDE.md browser automation rules: HelpCircle button gets aria-label since it's icon-only.

    5. Run `npm run lint` and `npm test -- scoreBulletConfig` and `npm run knip` from `frontend/`. All clean.
  </action>
  <verify>
    <automated>cd frontend && npm run lint && npm test -- scoreBulletConfig.test && npm run knip</automated>
  </verify>
  <done>
    - WDLStats TS interface mirrors backend.
    - scoreBulletConfig.ts + its test file exist; vitest passes.
    - ScoreConfidencePopover.tsx renders WdlConfidenceTooltip and exposes the documented props.
    - Lint, knip, and the new test all pass.
  </done>
</task>

<task type="auto" tdd="true">
  <name>Task 3: Render score bullet + popover under WDL bar in Openings.tsx Moves tab + page test</name>
  <files>frontend/src/pages/Openings.tsx, frontend/src/pages/__tests__/Openings.statsBoard.test.tsx</files>
  <behavior>
    - Inside `moveExplorerContent` (Openings.tsx around lines 924-957), inside the existing `charcoal-texture` wrapper that hosts `WDLChartRow`, render below the WDL bar:
      1. A `MiniBulletChart` configured for score domain.
      2. A `ScoreConfidencePopover` HelpCircle next to the bullet, hover/tap-opening.
    - The bullet receives:
      - `value={gamesData.stats.score}`
      - `center={SCORE_BULLET_CENTER}` (0.5)
      - `neutralMin={SCORE_BULLET_NEUTRAL_MIN}` (-0.05)
      - `neutralMax={SCORE_BULLET_NEUTRAL_MAX}` (+0.05)
      - `domain={SCORE_BULLET_DOMAIN}` (0.20)
      - `ciLow={clampScoreCi(gamesData.stats.ci_low)}`
      - `ciHigh={clampScoreCi(gamesData.stats.ci_high)}`
      - `ariaLabel={ \`Score \${(stats.score * 100).toFixed(0)}% vs 50% baseline\` }`
    - When `gamesData.stats.total < MIN_GAMES_FOR_RELIABLE_STATS`, the entire card (the `charcoal-texture` div containing both `WDLChartRow` and the bullet) renders at `UNRELIABLE_OPACITY`. This satisfies the spec line "the bullet doubles as a trust indicator for the WDL bar above" — applying opacity to the wrapper dims both atomically. Implement via inline `style={{ opacity: isUnreliable ? UNRELIABLE_OPACITY : undefined }}` on the existing `charcoal-texture` div.
    - Bullet container has `data-testid="score-bullet-position"`. Popover trigger has `data-testid="score-bullet-popover-trigger"`.
    - Popover receives `level={stats.confidence}`, `pValue={stats.p_value}`, `score={stats.score}`, `gameCount={stats.total}`.
    - The WDL bar card only renders when `gamesData && gamesData.stats.total > 0` (existing condition). When total=0 (no games for position) NEITHER bar nor bullet renders — same as today. Do not introduce a separate render path for the bullet when there are no games.
    - Single rendering site: only the Moves tab `moveExplorerContent` block. Do NOT touch Stats tab markup or any other location. Do NOT render per move.
    - Apply identical changes if any other render site shares the same WDL-bar-in-Moves-tab JSX (re-grep for `wdl-moves-position` to confirm uniqueness — orchestrator says it's a single site, but verify). Mobile and desktop both consume `moveExplorerContent` per the orchestrator's scout, so a single edit covers both.
  </behavior>
  <action>
    1. Open `frontend/src/pages/Openings.tsx`. Add imports at the top alongside existing chart/insight imports:
       ```typescript
       import { MiniBulletChart } from '@/components/charts/MiniBulletChart';
       import { ScoreConfidencePopover } from '@/components/insights/ScoreConfidencePopover';
       import {
         SCORE_BULLET_CENTER,
         SCORE_BULLET_DOMAIN,
         SCORE_BULLET_NEUTRAL_MAX,
         SCORE_BULLET_NEUTRAL_MIN,
         clampScoreCi,
       } from '@/lib/scoreBulletConfig';
       ```
       Verify `MIN_GAMES_FOR_RELIABLE_STATS` and `UNRELIABLE_OPACITY` are already imported from `@/lib/theme`; if not, add them.

    2. Locate `moveExplorerContent` (around line 924). Modify the WDL-bar `charcoal-texture` block:
       ```tsx
       {gamesData && gamesData.stats.total > 0 && (() => {
         const stats = gamesData.stats;
         const isUnreliable = stats.total < MIN_GAMES_FOR_RELIABLE_STATS;
         const scorePct = Math.round(stats.score * 100);
         return (
           <div
             className="charcoal-texture rounded-md p-4 order-2 lg:order-1"
             style={{ opacity: isUnreliable ? UNRELIABLE_OPACITY : undefined }}
           >
             <WDLChartRow
               data={stats}
               label={positionResultsLabel}
               barHeight="h-6"
               gamesLink="/openings/games"
               onGamesLinkClick={() => window.scrollTo({ top: 0 })}
               gamesLinkTestId="btn-moves-to-games"
               gamesLinkAriaLabel="View games for this position"
               testId="wdl-moves-position"
             />
             <div
               className="mt-2 flex items-center gap-2"
               data-testid="score-bullet-position"
             >
               <div className="flex-1">
                 <MiniBulletChart
                   value={stats.score}
                   center={SCORE_BULLET_CENTER}
                   neutralMin={SCORE_BULLET_NEUTRAL_MIN}
                   neutralMax={SCORE_BULLET_NEUTRAL_MAX}
                   domain={SCORE_BULLET_DOMAIN}
                   ciLow={clampScoreCi(stats.ci_low)}
                   ciHigh={clampScoreCi(stats.ci_high)}
                   ariaLabel={`Score ${scorePct}% vs 50% baseline`}
                 />
               </div>
               <ScoreConfidencePopover
                 level={stats.confidence}
                 pValue={stats.p_value}
                 score={stats.score}
                 gameCount={stats.total}
                 testId="score-bullet-popover-trigger"
                 ariaLabel="Show score confidence details"
               />
             </div>
           </div>
         );
       })()}
       ```
       Notes:
       - The IIFE pattern lets us name `stats` once without a new top-level memo. If the existing component already pulls `stats` out into a local, reuse it instead.
       - Keep `order-2 lg:order-1` and the `charcoal-texture` styling unchanged — they preserve the current desktop/mobile layout ordering.
       - No magic numbers in JSX (per CLAUDE.md): all four bullet config values come from `scoreBulletConfig.ts`, opacity from `theme.ts`.

    3. Verify there's only one rendering site:
       ```bash
       grep -n "wdl-moves-position" frontend/src/pages/Openings.tsx
       ```
       If a second instance exists (mobile drawer divergence), apply the same edit there. Per orchestrator scout, only one exists.

    4. Add a frontend test in `frontend/src/pages/__tests__/Openings.statsBoard.test.tsx` (extend existing file, do not create a new one). Read the file's existing render setup first; mirror its mocking of `useNextMoves` / TanStack Query. Add tests:
       - **Renders bullet when total ≥ 10**: render Openings with mock `useNextMoves` returning `position_stats: { wins: 6, draws: 2, losses: 2, total: 10, score: 0.7, confidence: 'high', p_value: 0.02, ci_low: 0.55, ci_high: 0.85, win_pct: 60, draw_pct: 20, loss_pct: 20 }`. Switch to Moves tab. Assert `getByTestId('score-bullet-position')` exists and `getByTestId('score-bullet-popover-trigger')` exists. Assert `getByTestId('mini-bullet-chart')` is inside `score-bullet-position`. Assert no `UNRELIABLE_OPACITY` style is applied to the wrapper.
       - **Mutes bullet+bar when total < 10**: same mock but `total: 5`, score 0.6, ci_low 0.3, ci_high 0.9. Assert the parent card container (the `charcoal-texture` div ancestor of `wdl-moves-position`) has `style="opacity: 0.5"` (or use `getComputedStyle` if vitest-jsdom needs it). Bullet still renders.
       - **Does not render when total = 0**: mock total=0. Assert `queryByTestId('score-bullet-position')` is null AND `queryByTestId('wdl-moves-position')` is null (existing behavior — sanity check).
       - If the existing test file does not yet mock `useNextMoves` for the Moves tab path, copy that wiring from the closest existing Moves-tab test in the file (or the bookmark/insights-card tests, whichever is structurally similar). If no Moves-tab tests exist at all in this file, add the minimum mocking needed; keep scope tight — three test cases, one mock builder.

    5. Run `cd frontend && npm run lint && npm test && npm run knip`. All must pass. Verify ty is not relevant for frontend (it's Python only); TS compile errors would surface via `vitest`/`tsc` invoked by lint.
  </action>
  <verify>
    <automated>cd frontend && npm run lint && npm test -- Openings.statsBoard && npm run knip</automated>
  </verify>
  <done>
    - Score bullet + popover render directly under the WDL bar in the Moves tab when total > 0.
    - When total < 10, the wrapper card (bullet + WDL bar) renders at UNRELIABLE_OPACITY.
    - All bullet config values come from constants (no magic numbers).
    - data-testid present on bullet container and popover trigger; aria-label on the icon-only popover trigger.
    - Three new tests in Openings.statsBoard.test.tsx pass.
    - Lint, knip, all frontend tests green.
  </done>
</task>

</tasks>

<verification>
- `uv run ruff check app/ tests/` → clean
- `uv run ty check app/ tests/` → zero errors
- `uv run pytest tests/test_openings_service.py -x` → all green
- `cd frontend && npm run lint` → clean
- `cd frontend && npm test` → all green (new tests included)
- `cd frontend && npm run knip` → clean
- Visual smoke (manual, optional): `bin/run_local.sh`, open Openings page, switch to Moves tab on a position with ≥10 games — bullet appears under the WDL bar with a CI whisker, popover opens on hover/tap; on a position with <10 games, both bar and bullet are dimmed.
</verification>

<success_criteria>
- Backend `WDLStats` schema includes score, confidence, p_value, ci_low, ci_high; all `WDLStats(...)` constructors updated.
- `compute_confidence_bucket` is the single source of truth for the math (no re-implementation).
- Frontend `WDLStats` TS interface mirrors backend exactly.
- Score bullet + popover render exactly once, in the Moves tab `moveExplorerContent`, directly under the existing `WDLChartRow`.
- Bullet uses center=0.5, neutral ±0.05, domain 0.20, with Wald 95% CI whisker clamped to [0, 1].
- When `total < 10`, the wrapping card renders at UNRELIABLE_OPACITY (mutes both bar and bullet).
- All zone/score constants live in `scoreBulletConfig.ts` and `theme.ts` — no magic numbers in JSX.
- Hover/tap on HelpCircle opens popover containing `WdlConfidenceTooltip` with score / p_value / game count / level.
- All new interactive elements have `data-testid`; HelpCircle has `aria-label`.
- ruff, ty, pytest, npm lint, npm test, knip all pass.
</success_criteria>

<output>
After completion, create `.planning/quick/260504-ttq-add-a-current-position-score-vs-50-bulle/260504-ttq-SUMMARY.md` summarizing:
- Files modified, with one-liner per file
- Backend math: how position_stats CI is computed
- Frontend: rendering site, mute logic, test coverage
- Any deviations from plan with rationale
</output>
