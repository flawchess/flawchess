---
phase: 260504-rvh
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - app/services/eval_confidence.py
  - app/services/stats_service.py
  - app/services/opening_insights_constants.py
  - tests/services/test_eval_confidence.py
  - frontend/src/lib/openingStatsZones.ts
  - frontend/src/lib/__tests__/openingStatsZones.test.ts
  - frontend/src/components/charts/MiniBulletChart.tsx
  - frontend/src/components/insights/EvalConfidenceTooltip.tsx
  - frontend/src/components/insights/BulletConfidencePopover.tsx
  - frontend/src/components/stats/MostPlayedOpeningsTable.tsx
  - frontend/src/pages/Openings.tsx
  - frontend/src/components/charts/__tests__/MiniBulletChart.test.tsx
autonomous: true
requirements: []
must_haves:
  truths:
    - "MG-entry bullet chart axis is centered on 0 cp (engine-balanced) for every cell, regardless of color."
    - "A small reference tick at the per-color baseline (white +0.315 / black -0.189 pawns by default; from API when available) is rendered on the bullet chart axis."
    - "Backend z-test, CI, and opening-insights logic evaluate eval-at-MG-entry against H0: mean == 0 cp (no per-color baseline subtraction)."
    - "MostPlayedOpeningsResponse.eval_baseline_pawns_white / _black are still emitted by the API and used purely for the tick-mark position."
    - "Tooltip copy explains that 0 cp = engine-balanced and the tick marks the typical MG-entry eval for the user's color."
    - "Backend (uv run pytest) and frontend (npm test) suites pass."
    - "Lint / format / typecheck / knip are clean."
  artifacts:
    - path: app/services/eval_confidence.py
      provides: "Two-sided Wald z-test against H0 mean=0 (no baseline_cp param, or default 0 only)"
    - path: app/services/stats_service.py
      provides: "Stats finalizer with no per-color baseline subtraction in z-test calls; still returns eval_baseline_pawns_white/_black"
    - path: app/services/opening_insights_constants.py
      provides: "Removes EVAL_BASELINE_CP_WHITE/_BLACK constants (or keeps as display-only tick positions)"
    - path: frontend/src/lib/openingStatsZones.ts
      provides: "Symmetric ±X pawns neutral zone around 0; EVAL_BASELINE_PAWNS_WHITE/_BLACK retained as tick fallbacks; evalZoneColor takes value only (no center)"
    - path: frontend/src/components/charts/MiniBulletChart.tsx
      provides: "Optional tickPawns prop for rendering a small reference tick at the color-baseline position"
  key_links:
    - from: frontend/src/pages/Openings.tsx
      to: frontend/src/components/stats/MostPlayedOpeningsTable.tsx
      via: "tickPawns={mostPlayedData.eval_baseline_pawns_white|_black ?? EVAL_BASELINE_PAWNS_WHITE|_BLACK}"
      pattern: "tickPawns="
    - from: app/services/stats_service.py
      to: app/services/eval_confidence.py
      via: "compute_eval_confidence_bucket(...) called WITHOUT baseline_cp argument (defaults to 0)"
      pattern: "compute_eval_confidence_bucket\\("
---

<objective>
Remove the per-color eval baseline centering from the MG-entry / opening eval gauge
and the backend statistics that drive it. Recenter the bullet chart axis on 0 cp
(engine-balanced) and add a small reference tick at the color baseline so users
still see "where typical for your color sits."

Purpose: Decouple the visual center (0 cp = engine-balanced) from the per-color
benchmark baseline. The baseline becomes a reference annotation rather than the
chart's coordinate origin, and the backend z-test now answers the simpler,
color-agnostic question "is the mean different from 0 cp?".

Output:
- Backend: eval_confidence.py, stats_service.py, opening_insights_constants.py,
  test_eval_confidence.py refactored — no per-color H0 shift.
- Frontend: zone bounds re-anchored at 0; MiniBulletChart gains a tickPawns prop;
  tooltip rewritten; MostPlayedOpeningsTable / Openings.tsx callsites updated;
  tests updated.
- API contract: eval_baseline_pawns_white / _black retained on the response,
  but their semantics shift from "chart center" to "tick-mark position".
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/STATE.md
@CLAUDE.md
@reports/benchmarks-2026-05-04.md

@frontend/src/lib/openingStatsZones.ts
@frontend/src/lib/__tests__/openingStatsZones.test.ts
@frontend/src/types/stats.ts
@frontend/src/components/charts/MiniBulletChart.tsx
@frontend/src/components/insights/EvalConfidenceTooltip.tsx
@frontend/src/components/insights/BulletConfidencePopover.tsx
@frontend/src/components/stats/MostPlayedOpeningsTable.tsx
@frontend/src/pages/Openings.tsx
@app/services/eval_confidence.py
@app/services/stats_service.py
@app/services/opening_insights_constants.py
@tests/services/test_eval_confidence.py

<interfaces>
<!-- Key interfaces involved. Executor should use these directly without re-exploring. -->

frontend/src/types/stats.ts (KEEP UNCHANGED — API contract):
```typescript
export interface MostPlayedOpeningsResponse {
  white: OpeningWDL[];
  black: OpeningWDL[];
  eval_baseline_pawns_white: number; // semantics shift: now tick-mark position, not chart center
  eval_baseline_pawns_black: number; // semantics shift: now tick-mark position, not chart center
}
```

frontend/src/lib/openingStatsZones.ts (current — to be refactored):
```typescript
export const EVAL_NEUTRAL_MIN_PAWNS = -0.30;
export const EVAL_NEUTRAL_MAX_PAWNS =  0.30;
export const EVAL_BULLET_DOMAIN_PAWNS = 1.5;
export const EVAL_BASELINE_PAWNS_WHITE = 0.315; // KEEP — now a fallback TICK position
export const EVAL_BASELINE_PAWNS_BLACK = -0.189; // KEEP — now a fallback TICK position
export function evalZoneColor(value: number, center: number): string; // -> simplify: drop center param
export function buildMgEvalHeaderTooltip(evalBaselinePawns: number): string; // -> rewrite copy
```

frontend/src/components/charts/MiniBulletChart.tsx (relevant props):
```typescript
interface MiniBulletChartProps {
  value: number;
  neutralMin?: number;       // offset from center, default -0.10
  neutralMax?: number;       // offset from center, default 0
  domain?: number;
  center?: number;           // KEEP, but MG-entry callsites stop passing it (default 0 is correct)
  ariaLabel?: string;
  ciLow?: number;
  ciHigh?: number;
  // NEW: tickPawns?: number — optional reference tick at this absolute position
}
```

app/services/eval_confidence.py (current):
```python
def compute_eval_confidence_bucket(
    eval_sum: float, eval_sumsq: float, n: int, baseline_cp: float = 0.0
) -> tuple[Literal["low", "medium", "high"], float, float, float]:
    # H0: mean == baseline_cp -> after this plan, simplify to H0: mean == 0
```

app/services/opening_insights_constants.py (current):
```python
EVAL_BASELINE_CP_WHITE: float = 31.5  # to be removed (or kept comment-only as display-doc)
EVAL_BASELINE_CP_BLACK: float = -18.9
EVAL_CONFIDENCE_MIN_N: int = 20  # KEEP
```

app/services/stats_service.py (current):
```python
def _baseline_cp_for_color(color: Literal["white", "black"] | None) -> float: ...
# call site:
compute_eval_confidence_bucket(..., baseline_cp=_baseline_cp_for_color(user_color))
# response builder:
eval_baseline_pawns_white=_baseline_cp_for_color("white") / 100.0,
eval_baseline_pawns_black=_baseline_cp_for_color("black") / 100.0,
```
</interfaces>

Reference reading (load if context permits):
- reports/benchmarks-2026-05-04.md §3a — confirms +0.315 / -0.189 baselines.
- Quick task 260504-my2 (parent of this rollback) introduced the centering being removed.

Key facts from CLAUDE.md to follow:
- No magic numbers — extract zone widths and baselines into named constants.
- Use `Literal[...]` for fixed string fields; pass `uv run ty check` clean.
- Em-dashes used sparingly in user-facing copy (tooltips).
- "Always apply changes to mobile too" — verify mobile MostPlayedOpeningsTable
  layout in `frontend/src/pages/Openings.tsx` (lines 185–225) uses the same
  refactored helpers.
- Sentry: not relevant here (no new exception handling).
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: Backend — drop per-color H0 shift; null hypothesis is 0 cp</name>
  <files>
    app/services/eval_confidence.py,
    app/services/stats_service.py,
    app/services/opening_insights_constants.py,
    tests/services/test_eval_confidence.py
  </files>
  <behavior>
    - compute_eval_confidence_bucket called without baseline_cp argument computes the same numbers as a call passing baseline_cp=0 today (regression-equivalent).
    - For an N=100, mean=+31.5 cp, sd=50 cp white-color cell, the new behavior reports "high" confidence with p < 0.001 (whereas before — with baseline_cp=+31.5 — it reported "low" / p≈1.0). This is the intended semantic change.
    - The MostPlayedOpeningsResponse still carries eval_baseline_pawns_white = 0.315 and eval_baseline_pawns_black = -0.189, sourced from named module-level constants (not magic numbers).
    - Removed: EVAL_BASELINE_CP_WHITE and EVAL_BASELINE_CP_BLACK from opening_insights_constants.py — backend no longer needs cp baselines, only the pawn values for the API response. Replace with EVAL_BASELINE_PAWNS_WHITE = 0.315 / EVAL_BASELINE_PAWNS_BLACK = -0.189 (display-only, in pawns, expressed at the API boundary).
    - tests/services/test_eval_confidence.py: drop or rewrite the four `baseline_cp`-dependent tests (test_baseline_cp_shifts_test_reference, test_baseline_cp_does_not_shift_displayed_mean_or_ci, test_baseline_cp_zero_variance_uses_baseline_for_mean_compare, test_black_baseline_is_negative). The function MAY keep a `baseline_cp: float = 0.0` parameter for arithmetic generality, but no caller passes a non-zero value. If kept, retain ONE minimal test asserting that passing baseline_cp=0 explicitly equals omitting it. Otherwise drop the parameter entirely and simplify the docstring.
  </behavior>
  <action>
    Step 1 — eval_confidence.py: Decide on signature. Recommended: keep `baseline_cp: float = 0.0` param for math generality but remove all references to "color-aware callers", "EVAL_BASELINE_CP_WHITE/_BLACK", and Stockfish-asymmetry justification from the module docstring and function docstring. Rewrite the docstring to describe a plain "two-sided z-test against H0: mean == 0 cp (default)". Cross-reference the new tick-mark semantics in 1–2 sentences: the engine-asymmetry baseline is now a display annotation, not part of the test.

    Step 2 — opening_insights_constants.py: Remove `EVAL_BASELINE_CP_WHITE` and `EVAL_BASELINE_CP_BLACK` constants and their lengthy comment block. Add new constants:

    ```python
    # Engine-asymmetry MG-entry tick-mark positions (in pawns, signed user-perspective).
    # Per-game mean from the 2026-05-04 Lichess benchmark, reports/benchmarks-2026-05-04.md §3a.
    # Used only as a visual reference tick on the MG-entry bullet chart — NOT as the
    # H0 reference for the z-test (the test runs against 0 cp). See quick task
    # 260504-rvh for the rationale behind decoupling visual baseline from test H0.
    EVAL_BASELINE_PAWNS_WHITE: float = 0.315
    EVAL_BASELINE_PAWNS_BLACK: float = -0.189
    ```

    Keep `EVAL_CONFIDENCE_MIN_N = 20` and update its comment if it still references the removed CP baselines.

    Step 3 — stats_service.py:
    - Drop the `_baseline_cp_for_color` helper entirely.
    - Remove the `EVAL_BASELINE_CP_BLACK / EVAL_BASELINE_CP_WHITE` import.
    - Add imports: `EVAL_BASELINE_PAWNS_BLACK, EVAL_BASELINE_PAWNS_WHITE`.
    - At the call site (line ~427) replace `baseline_cp=_baseline_cp_for_color(user_color)` with no argument (use the default of 0).
    - At the second call site (~line 505) do the same.
    - In the response builder (~lines 476–477) replace the `_baseline_cp_for_color("white") / 100.0` form with the named pawn constants directly:

      ```python
      eval_baseline_pawns_white=EVAL_BASELINE_PAWNS_WHITE,
      eval_baseline_pawns_black=EVAL_BASELINE_PAWNS_BLACK,
      ```

    Step 4 — tests/services/test_eval_confidence.py:
    - Remove the four baseline_cp-dependent tests listed above.
    - Update the module docstring to drop the `baseline_cp = EVAL_BASELINE_CP_*` framing.
    - Drop the `EVAL_BASELINE_CP_BLACK, EVAL_BASELINE_CP_WHITE` imports.
    - If you kept the `baseline_cp` parameter, add ONE small test asserting `compute_eval_confidence_bucket(s, sq, n)` equals `compute_eval_confidence_bucket(s, sq, n, baseline_cp=0.0)` for a representative input.

    Run `uv run ruff check . && uv run ruff format . && uv run ty check app/ tests/ && uv run pytest tests/services/test_eval_confidence.py tests/services/test_stats_service.py -x` (or whichever stats test file matches; if there is no separate stats_service test, run the full suite scoped to `tests/services/`).

    Then commit:
      `refactor(quick-260504-rvh): drop per-color H0 shift in MG-entry eval z-test`
  </action>
  <verify>
    <automated>uv run ruff check . && uv run ruff format --check . && uv run ty check app/ tests/ && uv run pytest -x</automated>
  </verify>
  <done>
    - eval_confidence.py docstring no longer references EVAL_BASELINE_CP_*.
    - opening_insights_constants.py exports EVAL_BASELINE_PAWNS_WHITE / _BLACK in pawns; CP variants removed.
    - stats_service.py has no _baseline_cp_for_color helper; both compute_eval_confidence_bucket call sites omit baseline_cp; response includes the new pawn constants.
    - test_eval_confidence.py has no remaining baseline_cp shift tests; suite passes.
    - Full backend suite green; ruff / ty clean.
    - One atomic commit landed.
  </done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: Frontend — recenter zones on 0, add tick prop, rewrite tooltip, update tests</name>
  <files>
    frontend/src/lib/openingStatsZones.ts,
    frontend/src/lib/__tests__/openingStatsZones.test.ts,
    frontend/src/components/charts/MiniBulletChart.tsx,
    frontend/src/components/charts/__tests__/MiniBulletChart.test.tsx,
    frontend/src/components/insights/EvalConfidenceTooltip.tsx,
    frontend/src/components/insights/BulletConfidencePopover.tsx,
    frontend/src/components/stats/MostPlayedOpeningsTable.tsx,
    frontend/src/pages/Openings.tsx
  </files>
  <behavior>
    - openingStatsZones.ts:
        * EVAL_NEUTRAL_MIN_PAWNS / _MAX_PAWNS remain symmetric ±0.30 (current values preserve sensitivity per locked decision; the zone is now anchored at 0, not at the per-color baseline).
        * EVAL_BULLET_DOMAIN_PAWNS unchanged (1.5).
        * EVAL_BASELINE_PAWNS_WHITE = 0.315 / EVAL_BASELINE_PAWNS_BLACK = -0.189 retained as fallback tick positions for places without per-API baselines (e.g. bookmark sections).
        * evalZoneColor(value: number) signature: drops the `center` parameter; tests success/danger purely via value vs ±0.30 around 0.
        * buildMgEvalHeaderTooltip rewritten to drop centering language. New copy (no em-dashes): "Engine evaluation at middlegame entry. 0 cp = engine-balanced position. The tick shows the typical MG-entry eval for your color (a reference for how openings usually leave the position)."
    - MiniBulletChart.tsx: gains an optional `tickPawns?: number` prop. When provided AND inside the chart axis ([center - domain, center + domain]), renders a thin dashed (or distinct from the existing solid neutral-bound tick) reference line at that absolute position. When undefined, no tick rendered. Backwards-compatible (no other callsite needs to change).
    - EvalConfidenceTooltip.tsx & BulletConfidencePopover.tsx: drop the `centerPawns` prop and the "Centered (vs X baseline)" line. Tooltip now shows only the raw mean ± CI (already in pawns). Update prop interfaces accordingly.
    - MostPlayedOpeningsTable.tsx: prop renamed semantically — instead of `evalBaselinePawns` driving `center`, pass `tickPawns` to MiniBulletChart and drop the now-unused `centerPawns` plumbing through the popover. The prop on the table itself can be renamed `evalTickPawns` or kept as `evalBaselinePawns` (whichever incurs the smaller diff; preserve the variable name on Openings.tsx callers if possible).
    - Openings.tsx: stop passing `center={evalBaselinePawns}` to MiniBulletChart; pass `tickPawns={evalBaselinePawns}` instead. Update the desktop table call (line ~193) AND mobile / per-row call paths if they exist (the file currently has both desktop sections and a mobile section around lines 1150–1300). evalZoneColor calls drop their second arg.
    - Tests:
        * openingStatsZones.test.ts: drop the `evalZoneColor — baseline-centered` describe block and rewrite around delta-from-zero. Keep the EVAL_BASELINE_PAWNS_WHITE/_BLACK fallback-value assertions.
        * MiniBulletChart.test.tsx: add a small describe block for the new `tickPawns` prop (renders when provided, omitted when undefined, clamped within axis).
  </behavior>
  <action>
    Step 1 — openingStatsZones.ts:
    - Update the file header comment to describe the new semantics: zone bounds anchored on 0 cp; baselines retained as tick-mark fallback values.
    - Change `evalZoneColor` signature to `(value: number) => string` and remove the `delta = value - center` line; thresholds compare value directly.
    - Replace `buildMgEvalHeaderTooltip(evalBaselinePawns: number)` body with the new copy above. Keep the parameter (callers still pass it) but the implementation no longer needs to interpolate it. If knip flags the unused parameter, you can drop the parameter entirely and update callers in MostPlayedOpeningsTable.tsx and Openings.tsx accordingly.
    - Keep EVAL_BASELINE_PAWNS_WHITE / _BLACK constants and their comment (now: "fallback tick-mark position for sections without per-API baseline").

    Step 2 — MiniBulletChart.tsx:
    - Add `tickPawns?: number` to the props interface with a JSDoc comment: "Optional reference tick at this absolute axis position. Used to mark the per-color MG-entry baseline alongside the 0-cp center."
    - In the render body, after the existing center/neutral-tick rendering, add a tick at `tickPawns` when defined and within the axis. Use `border-dashed` or a different color (e.g. `bg-foreground/30`) to visually distinguish from the solid center reference. Add a `data-testid="mini-bullet-tick"` for testability.

    Step 3 — EvalConfidenceTooltip.tsx & BulletConfidencePopover.tsx:
    - Drop the `centerPawns` prop and the "Centered (vs X baseline): …" line from EvalConfidenceTooltip.
    - Remove the prop and its plumbing from BulletConfidencePopover.
    - Tooltip now shows only the raw mean and CI. If the existing `prefaceText` mechanism is what feeds buildMgEvalHeaderTooltip, leave it intact and let the new copy flow through.

    Step 4 — MostPlayedOpeningsTable.tsx:
    - At the MiniBulletChart call (~line where `mgBulletContent` is built; check the file): drop `center={evalBaselinePawns}`, add `tickPawns={evalBaselinePawns}`.
    - At the BulletConfidencePopover call (~line 172): remove `centerPawns={evalBaselinePawns}` and the now-irrelevant prop.
    - Strip the second argument to `evalZoneColor(...)` calls (line ~185 in Openings.tsx and similar in this file).

    Step 5 — Openings.tsx:
    - Apply the same change to the inline MiniBulletChart at line ~193 (desktop `MostPlayedOpeningsTable` path AND any inline cell rendering path).
    - In the mobile section (the duplicated bullet-chart markup around lines ~1140–1300), apply the same edits to maintain parity per CLAUDE.md "Always apply changes to mobile too".
    - Drop the now-unused `EVAL_BASELINE_PAWNS_WHITE` / `_BLACK` imports IF they are no longer referenced (they MAY still be referenced as fallbacks for the tick position when `mostPlayedData?.eval_baseline_pawns_white` is undefined — check before deleting). The ?? fallback pattern (`mostPlayedData?.eval_baseline_pawns_white ?? EVAL_BASELINE_PAWNS_WHITE`) should remain.

    Step 6 — Tests:
    - openingStatsZones.test.ts: Drop the `evalZoneColor — baseline-centered (260504-my2)` describe entirely and add a new describe `evalZoneColor — zero-centered (260504-rvh)` with cases:
        * value within ±0.30 -> ZONE_NEUTRAL
        * value >= +0.30 -> ZONE_SUCCESS
        * value <= -0.30 -> ZONE_DANGER
    - MiniBulletChart.test.tsx: Add a describe `MiniBulletChart — tickPawns prop (260504-rvh)`:
        * tickPawns omitted -> no `[data-testid="mini-bullet-tick"]` in DOM.
        * tickPawns=0.315, domain=1.5 -> tick rendered at the expected % position.
        * tickPawns outside [-domain, +domain] -> tick NOT rendered (clamped/omitted; pick whichever is simpler to implement and assert).

    Step 7 — Run:
    ```
    cd frontend && npm run lint && npm test && npm run knip
    ```

    Step 8 — Commit:
      `refactor(quick-260504-rvh): recenter MG-entry bullet chart on 0 cp; baseline becomes a tick`
  </action>
  <verify>
    <automated>cd frontend && npm run lint && npm test -- --run && npm run knip</automated>
  </verify>
  <done>
    - openingStatsZones.ts: evalZoneColor takes only `value`; tooltip copy rewritten without em-dashes; baseline pawn constants retained as tick fallbacks.
    - MiniBulletChart has a working `tickPawns` prop with test coverage.
    - EvalConfidenceTooltip / BulletConfidencePopover no longer reference centerPawns.
    - MostPlayedOpeningsTable + Openings.tsx pass `tickPawns` (not `center`); evalZoneColor calls updated; mobile sections updated with the same edits.
    - Frontend tests, lint, knip clean.
    - One atomic commit landed.
  </done>
</task>

<task type="auto">
  <name>Task 3: End-to-end verification + cross-stack lint sweep</name>
  <files>
    (no new files modified — verification + small fixups only)
  </files>
  <action>
    Step 1 — Cross-stack search for any lingering centering references:
    ```
    grep -rn "EVAL_BASELINE_CP\|_baseline_cp_for_color\|baseline_cp=" app tests
    grep -rn "centerPawns\|evalBaselinePawns" frontend/src
    ```
    For each hit:
    - Backend: must be zero hits for `EVAL_BASELINE_CP` and `_baseline_cp_for_color` (they were removed).
    - Frontend: `centerPawns` must be zero hits (the prop was dropped). `evalBaselinePawns` may persist as the variable name passed as `tickPawns` — verify each remaining reference is now feeding the tick, not the chart center.

    Step 2 — Run the full cross-stack quality gate:
    ```
    uv run ruff check .
    uv run ruff format --check .
    uv run ty check app/ tests/
    uv run pytest -x
    cd frontend && npm run lint && npm test -- --run && npm run knip && npm run build
    ```
    `npm run build` is included to catch any TS errors that lint/test missed (props interfaces, removed prop drilling).

    Step 3 — Manual smoke (note in commit message — no code change required):
    - Confirm `mgBulletContent` in MostPlayedOpeningsTable visually places the tick at +0.315 / -0.189 pawns and the bar/zone is anchored at 0.

    Step 4 — If knip flags newly-unused exports (likely candidates: `buildMgEvalHeaderTooltip` parameter dropping leaving an unused const, or one of the tooltip components if all callers were stripped), remove them in this task and commit:
      `chore(quick-260504-rvh): drop unused exports after baseline-centering removal`

    If everything is clean (no knip diffs), skip the chore commit. Two commits total (Task 1, Task 2) is acceptable; three (Task 1, Task 2, Task 3 cleanup) is also acceptable.
  </action>
  <verify>
    <automated>uv run ruff check . && uv run ty check app/ tests/ && uv run pytest -x && cd frontend && npm run lint && npm test -- --run && npm run knip && npm run build</automated>
  </verify>
  <done>
    - Zero hits for `EVAL_BASELINE_CP` / `_baseline_cp_for_color` / `centerPawns` in the codebase.
    - `evalBaselinePawns` only flows into `tickPawns` (or is renamed accordingly).
    - Full cross-stack quality gate green.
    - Optional cleanup commit landed if knip surfaced anything.
  </done>
</task>

</tasks>

<verification>
- Backend: `uv run pytest` green; `uv run ruff check .` and `uv run ruff format --check .` clean; `uv run ty check app/ tests/` zero errors.
- Frontend: `cd frontend && npm test -- --run` green; `npm run lint` clean; `npm run knip` clean; `npm run build` succeeds.
- API contract: a sample `GET /api/stats/most-played-openings` response (manual or spot-check via the stats_service unit) still emits `eval_baseline_pawns_white = 0.315` and `eval_baseline_pawns_black = -0.189`.
- Visual smoke (manual, not blocking): the MG-entry bullet chart for a white-color row places its solid center reference line at 0 cp and a smaller tick at +0.315 pawns; for a black-color row, tick at -0.189 pawns.
</verification>

<success_criteria>
- Per-color H0 shift fully removed from backend (eval_confidence.py, stats_service.py, opening_insights_constants.py, test_eval_confidence.py).
- Bullet chart anchored on 0 cp with a tick at the per-color baseline; symmetric ±0.30 pawns neutral zone preserved.
- Tooltip rewritten without em-dashes; centering language gone.
- Mobile and desktop bullet-chart paths updated identically (CLAUDE.md mobile parity rule).
- Two or three atomic commits with `quick-260504-rvh` scope token.
- Full cross-stack quality gate (ruff / ty / pytest / lint / knip / build / vitest) green.
</success_criteria>

<output>
After completion, create `.planning/quick/260504-rvh-remove-eval-color-baseline-centering-fro/260504-rvh-SUMMARY.md`.
</output>
