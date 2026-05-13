---
phase: 85-section-1-games-with-vs-without-endgame-cards
reviewed: 2026-05-13T00:00:00Z
depth: standard
files_reviewed: 11
files_reviewed_list:
  - app/schemas/endgames.py
  - app/services/endgame_service.py
  - frontend/src/components/charts/EndgameOverallPerformanceSection.tsx
  - frontend/src/components/charts/EndgameScoreOverTimeChart.tsx
  - frontend/src/components/charts/__tests__/EndgameOverallPerformanceSection.test.tsx
  - frontend/src/components/charts/__tests__/EndgameScoreOverTimeChart.test.tsx
  - frontend/src/components/popovers/AchievableScorePopover.tsx
  - frontend/src/pages/Endgames.tsx
  - frontend/src/pages/__tests__/Endgames.overallPerformance.test.tsx
  - frontend/src/types/endgames.ts
  - tests/test_endgame_service.py
findings:
  critical: 0
  warning: 4
  info: 6
  total: 10
status: issues_found
---

# Phase 85: Code Review Report

**Reviewed:** 2026-05-13
**Depth:** standard
**Files Reviewed:** 11
**Status:** issues_found

## Summary

Phase 85 merges legacy "Games with vs without Endgame" cards plus the "Where you start" tile into a single 3-card `EndgameOverallPerformanceSection`, plus extracts `EndgameScoreOverTimeChart` to its own file and adds a backend `non_endgame_score_p_value` for parity sig-gating on Card 1.

The implementation is clean overall: backend change is a faithful mirror of `endgame_score_p_value` with a dedicated unit test, frontend composite section preserves the documented CR-01 OFFSET-form fix, and the extracted chart carries its own focused test suite.

Findings are concentrated in maintainability — duplicated confidence-bucket logic and a missing regression test for the OFFSET-form CR-01 fix — plus a few minor quality issues (timer cleanup, dead-code prop, magic numbers). No correctness or security defects were found.

## Warnings

### WR-01: Duplicated confidence-bucket constants and `deriveLevel` helper

**File:** `frontend/src/components/charts/EndgameOverallPerformanceSection.tsx:80-91`
**Issue:** `CONFIDENCE_HIGH_MAX_P = 0.01`, `CONFIDENCE_MEDIUM_MAX_P = 0.05`, and the `deriveLevel` function are re-declared locally, duplicating the bucketing in `frontend/src/lib/scoreConfidence.ts:17-18, 78-87`. The comment explicitly acknowledges the duplication ("Identical to EndgameStartVsEndSection.deriveLevel — kept in lockstep with scoreConfidence.computeScoreConfidence's bucketing"), which is a known drift risk. If the canonical bucketing in `scoreConfidence.ts` ever changes (e.g., adjust `CONFIDENCE_MEDIUM_MAX_P` to 0.10), this consumer will silently disagree with the rest of the app's confidence labels.

**Fix:** Export the constants from `scoreConfidence.ts` and either (a) export a shared `deriveLevel(p, n)` helper there, or (b) re-use `computeScoreConfidence(w, d, n).confidence` directly when WDL is available. The cheapest fix:

```ts
// scoreConfidence.ts
export const CONFIDENCE_HIGH_MAX_P = 0.01;
export const CONFIDENCE_MEDIUM_MAX_P = 0.05;

export function deriveLevel(p: number | null, n: number): ConfidenceLevel {
  if (n < CONFIDENCE_MIN_N || p == null) return 'low';
  if (p < CONFIDENCE_HIGH_MAX_P) return 'high';
  if (p < CONFIDENCE_MEDIUM_MAX_P) return 'medium';
  return 'low';
}
```

Then `EndgameOverallPerformanceSection` imports `deriveLevel` and drops its local copy. Note `MIN_GAMES_FOR_RELIABLE_STATS` (theme.ts) and `CONFIDENCE_MIN_N` (scoreConfidence.ts) are both 10 — the duplicated constant problem is wider than this file.

### WR-02: CR-01 OFFSET-form fix is not covered by a regression test

**File:** `frontend/src/components/charts/__tests__/EndgameOverallPerformanceSection.test.tsx:30-40, 296-356`
**Issue:** The component file documents that the achievable-score `MiniBulletChart` must receive OFFSET-form `neutralMin/neutralMax` (registry value minus `SCORE_BULLET_CENTER`), and labels this as "CR-01 preserved". However, the test-time `MiniBulletChart` mock only forwards `domain` and `center` to its rendered stub — `neutralMin`/`neutralMax` are not surfaced into the DOM, so no test asserts the OFFSET arithmetic at `EndgameOverallPerformanceSection.tsx:302-303`. If a future refactor accidentally passes the absolute registry bounds again (the exact CR-01 regression), all tests will still pass and the neutral band will silently collapse in production.

**Fix:** Either (a) extend the mock to also forward `neutralMin/neutralMax` (`data-neutral-min={String(props.neutralMin)}`) and add an assertion that the values equal `ENTRY_EXPECTED_SCORE_NEUTRAL_MIN - SCORE_BULLET_CENTER` and `_MAX - SCORE_BULLET_CENTER`, or (b) spy on `MiniBulletChart` calls with `vi.mocked(MiniBulletChart).mock.calls` and assert the props of the call rendered for the achievable-score row. Option (a) is the simpler change:

```ts
MiniBulletChart: vi.fn((props: Record<string, unknown>) => (
  <div
    data-testid="mock-mini-bullet"
    data-domain={String(props.domain)}
    data-center={String(props.center)}
    data-neutral-min={String(props.neutralMin)}
    data-neutral-max={String(props.neutralMax)}
  />
)),
```

Then a dedicated test renders Card 2 with `entry_expected_score_n >= 10` and asserts the achievable-row bullet's `data-neutral-min` ≈ `-0.05` (i.e. `0.45 - 0.50`) and `data-neutral-max` ≈ `+0.05`.

### WR-03: AchievableScorePopover hover timeout not cleaned up on unmount

**File:** `frontend/src/components/popovers/AchievableScorePopover.tsx:68-78`
**Issue:** `handleMouseEnter` schedules `setTimeout(() => setOpen(true), 100)` and stores the handle in a ref, but there is no `useEffect` cleanup that clears the timeout on unmount. If a user hovers the trigger and the component unmounts within the 100 ms window (e.g., filters change and the parent re-renders away from Card 2's empty-state branch, or the page navigates), the timer fires after unmount and `setOpen(true)` runs on a stale instance. React 18 silently no-ops the update but logs a dev-mode warning; under `<React.StrictMode>` the warning is more pronounced.

**Fix:** Add a cleanup effect:

```ts
React.useEffect(() => {
  return () => {
    if (hoverTimeout.current) clearTimeout(hoverTimeout.current);
  };
}, []);
```

### WR-04: `pValue` prop accepts `number` but caller may pass a meaningless `1` fallback

**File:** `frontend/src/components/popovers/AchievableScorePopover.tsx:43, 132` and `frontend/src/components/charts/EndgameOverallPerformanceSection.tsx:292`
**Issue:** `AchievableScorePopoverProps.pValue: number` (non-nullable), and the popover renders `(p = {pValue.toFixed(3)})`. The caller passes `data.entry_expected_score_p_value ?? 1` to satisfy the non-nullable signature. The two gates currently align (popover renders only when `entry_expected_score_n >= 10`, and the backend returns a non-null p-value when `ex_n >= 10`), so the fallback never triggers in practice. But this is fragile: a backend change that gates p-value on a different sample size, or a frontend gate that drifts off `MIN_GAMES_FOR_RELIABLE_STATS`, would silently show "(p = 1.000)" — which reads as "definitely consistent with H0" rather than "not enough data". The popover would also display its `headline()` "Inconclusive" or "Possibly/Likely" line based on the `level` prop, compounding the mismatch.

**Fix:** Make the prop accept null and short-circuit:

```ts
pValue: number | null;
// ...
{pValue == null ? '—' : `(p = ${pValue.toFixed(3)})`}
```

Then drop the `?? 1` in the call site. This makes the contract honest about the "no p-value available" case.

## Info

### IN-01: Magic threshold `10` repeated 4× in `_get_endgame_performance_from_rows`

**File:** `app/services/endgame_service.py:1744, 1760, 1770, 1803`
**Issue:** The bare integer `10` recurs as the sample-size gate for `entry_eval_p_value`, `endgame_score_p_value`, `non_endgame_score_p_value` (added in this phase), and `entry_expected_score_p_value`. The frontend has the same threshold as `MIN_GAMES_FOR_RELIABLE_STATS` in `theme.ts` and `CONFIDENCE_MIN_N` in `scoreConfidence.ts`. Phase 85 added one more occurrence (line 1770) rather than promoting a constant.

**Fix:** Extract once near the top of `endgame_service.py`:

```python
# Wire-format reliability gate for sig-test p-values (mirror of
# frontend MIN_GAMES_FOR_RELIABLE_STATS / CONFIDENCE_MIN_N).
PVALUE_RELIABILITY_MIN_N = 10
```

and replace the 4 sites. Per the project's "tweak constants over props" memory, this is a clean local refactor. Pre-existing pattern — flag for cleanup, not strictly Phase 85's fault.

### IN-02: Local `ConfidenceLevel` type re-declared instead of importing canonical

**File:** `frontend/src/components/popovers/AchievableScorePopover.tsx:6`
**Issue:** `type ConfidenceLevel = 'low' | 'medium' | 'high';` is defined locally even though the same alias is already exported from `frontend/src/lib/scoreConfidence.ts:20`. Two copies of the same string-union type drift the moment one side adds a fourth bucket.

**Fix:**

```ts
import type { ConfidenceLevel } from '@/lib/scoreConfidence';
```

and drop the local declaration.

### IN-03: Hover-open delay is a magic number

**File:** `frontend/src/components/popovers/AchievableScorePopover.tsx:72`
**Issue:** `setTimeout(() => setOpen(true), 100)` uses a bare `100`. Per CLAUDE.md "No magic numbers", thresholds and delays should be named. The same hover-delay value is likely used in other popovers across the codebase.

**Fix:**

```ts
const POPOVER_HOVER_DELAY_MS = 100;
// ...
hoverTimeout.current = setTimeout(() => setOpen(true), POPOVER_HOVER_DELAY_MS);
```

If this delay is reused elsewhere, lift it to a shared `popoverConfig.ts`.

### IN-04: `BulletConfidencePopover` `color="white"` is a fallback prop with documented no-op behavior

**File:** `frontend/src/components/charts/EndgameOverallPerformanceSection.tsx:248-253`
**Issue:** The `color` prop is set to `"white"` purely to satisfy a required-prop signature, even though `showBaselineTick={false}` makes it unused. The inline comment explains this. Required props that are no-ops in some contexts indicate the `BulletConfidencePopover` API could be tightened (e.g., make `color` optional or required-only when `showBaselineTick` is true via a discriminated union). Out of scope for this phase but worth flagging.

**Fix:** Refactor `BulletConfidencePopover` props to a discriminated union:

```ts
type Props =
  | { showBaselineTick: true; color: string; ... }
  | { showBaselineTick: false; ... };
```

so callers cannot accidentally rely on a meaningless `color` value.

### IN-05: Score Gap formatting yields asymmetric sign display near zero

**File:** `frontend/src/components/charts/EndgameOverallPerformanceSection.tsx:339-341`
**Issue:** `gapPositive = scoreGap.score_difference >= 0` AND `Math.round(scoreGap.score_difference * 100)` produces asymmetric near-zero output:

- `score_difference = +0.004` → `+0%` (sign shown)
- `score_difference = -0.004` → `0%` (no sign, because `Math.round(-0.4) = 0` and `gapPositive` is false → empty prefix)
- `score_difference = -0.006` → `-1%` (sign carried by the negative number)

Not a correctness defect — the rounded display is technically consistent — but a user staring at `+0%` vs `0%` on similar weeks will read them as different states. Also worth noting: `Math.round` rounds half-away-from-zero in most JS engines except at exact half-integer cases where `-0.5` rounds to `0` (banker's rounding) — this can produce one more boundary inconsistency.

**Fix:** Round once, then sign from the rounded value:

```ts
const gapRounded = Math.round(scoreGap.score_difference * 100);
const gapFormatted = `${gapRounded > 0 ? '+' : ''}${gapRounded}%`;
```

`gapRounded === 0` displays as `0%` regardless of input sign, and negatives keep their `-` from the number itself.

### IN-06: Score Gap card lacks an empty-state guard

**File:** `frontend/src/components/charts/EndgameOverallPerformanceSection.tsx:385-413`
**Issue:** Unlike the per-card score rows (gated on `total >= MIN_GAMES_FOR_RELIABLE_STATS`), the Score Gap card renders unconditionally with whatever `scoreGap.score_difference` value the backend returns. If both endgame and non-endgame games are filtered down to very small samples (or zero), the card displays a precise-looking signed percentage with a zone-colored hue and no warning that the difference is statistically meaningless. The component-level comment notes "Score Gap font color is zone-only (no sig test) per D-04" — that's the documented design call, so this is informational only, but a minimum-sample guard (`scoreGap.endgame_score > 0 && scoreGap.non_endgame_score > 0` or a backend-supplied `min(endgame_total, non_endgame_total) >= 10` flag) would make Card 4 honest about uncertainty without contradicting D-04 (zones stay color-only).

**Fix:** Either accept as designed (D-04), or surface a sample-size precondition from the response and render an empty state when unmet. No code change required if D-04 stands.

---

_Reviewed: 2026-05-13_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
