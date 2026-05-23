---
phase: 94-backend-frontend-percentile-annotations
reviewed: 2026-05-23T00:00:00Z
depth: standard
files_reviewed: 13
files_reviewed_list:
  - app/schemas/endgames.py
  - app/services/endgame_service.py
  - frontend/src/components/charts/EndgameMetricCard.tsx
  - frontend/src/components/charts/EndgameMetricsSection.tsx
  - frontend/src/components/charts/EndgameOverallPerformanceSection.tsx
  - frontend/src/components/charts/EndgameOverallScoreGapRow.tsx
  - frontend/src/components/charts/PercentileChip.tsx
  - frontend/src/components/charts/__tests__/EndgameMetricCard.test.tsx
  - frontend/src/components/charts/__tests__/EndgameOverallPerformanceSection.test.tsx
  - frontend/src/components/charts/__tests__/PercentileChip.test.tsx
  - frontend/src/types/endgames.ts
  - tests/schemas/test_endgames_schema.py
  - tests/test_endgame_service.py
findings:
  critical: 0
  warning: 2
  info: 4
  total: 6
status: issues_found
---

# Phase 94: Code Review Report

**Reviewed:** 2026-05-23
**Depth:** standard
**Files Reviewed:** 13
**Status:** issues_found

## Summary

The phase ships exactly what the plan describes: 4 nullable `*_percentile`
fields on the two endgame response schemas, gated by `PVALUE_RELIABILITY_MIN_N`
at the two service compute sites (single-N for 3 metrics, dual-N for Endgame
Score Gap), a fresh `PercentileChip` component with banded color + flame tier
stack + Radix popover shell, and 4 wired render sites with mobile/desktop
grid placement and a recovery-card defensive guard.

Backend gate semantics correctly mirror the existing `_p_value` / `_ci_*`
siblings (dual-N for `score_gap`, single-N for `achievable_score_gap` /
`section2_score_gap_conv` / `section2_score_gap_parity`). The
`mean is not None` triple guard for conv/parity correctly defends against
`interpolate_percentile` (NaN-safe, not None-safe). The structural recovery
exclusion is enforced in both schema and runtime tests.

Frontend chip respects theme.ts (modulo the one documented `CHIP_TEXT_COLOR`
oklch literal), uses `text-sm` on the pill (popover body inherits `text-xs`
per the documented hover-tooltip exception), threads `data-testid` /
`aria-label` per the contract, and the `EndgameOverallScoreGapRow` grid
layout correctly places the chip below the bullet on mobile and right of
the label on desktop without DOM duplication.

Findings are mostly small-surface quality issues: one real lifecycle bug
(setTimeout not cleared on unmount), one dead-conditional check, and a few
info-level cleanups around defensive bounds and unused export hygiene.
No critical defects, no security concerns, no Sentry rule violations.

## Warnings

### WR-01: PercentileChip leaks setTimeout when unmounted during hover-open delay

**File:** `frontend/src/components/charts/PercentileChip.tsx:94-104`

**Issue:** `handleMouseEnter` schedules a 100 ms `setTimeout` to open the
popover, storing the handle in `hoverTimeout.current`. If the component
unmounts during that 100 ms window (e.g. the user mouses over the chip,
then navigates to another page or the parent re-renders and replaces the
chip), the timer fires and calls `setOpen(true)` on an unmounted component.

This produces a React "state update on unmounted component" warning in dev
and a small closure leak in prod. The Content element's `onMouseEnter`
clears the same ref but only fires when the popover is already open, so it
doesn't cover the chip-only-hovered-then-unmount path.

The same handle is also leaked on a fast mouseenter → mouseleave → mouseenter
cycle: the second `setTimeout` overwrites `hoverTimeout.current` without
clearing the first, so the original timer keeps a closure alive even though
it's now orphaned. `handleMouseLeave` guards the cleanup with `if
(hoverTimeout.current)` but never nulls the ref afterwards, so a stale
handle can sit there until the next mouseenter overwrites it.

**Fix:**
```tsx
React.useEffect(() => {
  return () => {
    if (hoverTimeout.current) {
      clearTimeout(hoverTimeout.current);
      hoverTimeout.current = null;
    }
  };
}, []);

const handleMouseEnter = (): void => {
  // Clear any previously-scheduled open so back-to-back hovers don't
  // orphan a timer.
  if (hoverTimeout.current) clearTimeout(hoverTimeout.current);
  hoverTimeout.current = setTimeout(() => setOpen(true), HOVER_OPEN_DELAY_MS);
};

const handleMouseLeave = (): void => {
  if (hoverTimeout.current) {
    clearTimeout(hoverTimeout.current);
    hoverTimeout.current = null;
  }
  setOpen(false);
};
```

The existing `MetricStatPopover` (the documented reference shell) almost
certainly has the same pattern; if it doesn't, the bug is pre-existing
upstream and Phase 94 just inherits it — worth a quick cross-check.

### WR-02: `conv_n is not None` / `parity_n is not None` are always-true dead conditionals

**File:** `app/services/endgame_service.py:1384`, `app/services/endgame_service.py:1389`

**Issue:** `_compute_per_bucket_score_gap` (line 1228) declares its return
type as `tuple[float | None, int, float | None, float | None, float | None]`
— `n` is `int`, never `None`. The destructured `conv_n` / `parity_n`
locals therefore cannot be `None`, and the `conv_n is not None` /
`parity_n is not None` clauses in the gate expressions at lines 1384 and
1389 are dead conditions.

The check looks like it's defending against a None-shaped sibling
(`section2_score_gap_conv_n: int | None` in the schema), but the local
value comes from the helper which gates at `int`. The dead clause is
harmless but misleads readers into thinking `n` could be None here.

This is a minor smell, but it sits next to the *real* defensive check
(`mean is not None`) which is genuinely load-bearing — the dead clause
weakens the signal-to-noise of the real one.

**Fix:** Drop the redundant clauses; keep only the load-bearing ones.
```python
section2_score_gap_conv_percentile: float | None = (
    interpolate_percentile("section2_score_gap_conv", conv_mean)
    if conv_mean is not None and conv_n >= PVALUE_RELIABILITY_MIN_N
    else None
)
section2_score_gap_parity_percentile: float | None = (
    interpolate_percentile("section2_score_gap_parity", parity_mean)
    if parity_mean is not None and parity_n >= PVALUE_RELIABILITY_MIN_N
    else None
)
```
Add a one-line comment if you want to preserve the design intent: `# n is
int, not int|None — the schema field is nullable but the local is always
populated by _compute_per_bucket_score_gap.`

## Info

### IN-01: `PercentileChip` test helper trips noUncheckedIndexedAccess silently

**File:** `frontend/src/components/charts/__tests__/PercentileChip.test.tsx:87-91`

**Issue:** `parseOklch` returns `[Number(m[1]), Number(m[2]), Number(m[3])]`
after a single `if (!m) return null` narrowing. With `noUncheckedIndexedAccess`
enabled (per CLAUDE.md Frontend §Code Style), `m[1]` / `m[2]` / `m[3]` are
`string | undefined`. `Number(undefined)` returns `NaN` rather than a type
error, so the assertion would silently start passing on garbage if the regex
were ever weakened to allow optional groups.

This is benign today because the regex literal `oklch\(\s*([\d.]+)\s+
([\d.]+)\s+([\d.]+)\s*\)` requires all three captures, but it dodges the
project's narrowing discipline.

**Fix:** Destructure with explicit narrowing or use `String.prototype.split`:
```ts
function parseOklch(s: string): readonly [number, number, number] | null {
  const m = s.match(/oklch\(\s*([\d.]+)\s+([\d.]+)\s+([\d.]+)\s*\)/);
  if (!m) return null;
  const [, a, b, c] = m;
  if (a === undefined || b === undefined || c === undefined) return null;
  return [Number(a), Number(b), Number(c)] as const;
}
```

### IN-02: `formatTopXPercent` accepts out-of-range negative percentiles silently

**File:** `frontend/src/components/charts/PercentileChip.tsx:67-69`

**Issue:** `formatTopXPercent` uses `Math.max(MIN_TOP_PERCENT, Math.round(
100 - pct))` to floor the right tail at "Top 1%". A negative input
(`pct = -5`) would render `Top 105%` because the upper bound is unbounded.

The backend documents the percentile as `[0, 100]` per the schema field
docstring, and callers explicitly gate on `!= null` before rendering, so
this path is unreachable today. But the chip is the wire-contract enforcer
for any future consumer (test fixtures, Storybook stories, screenshot
harnesses), and a `Top 105%` render would silently look wrong rather than
crashing.

**Fix:** Clamp both ends, or assert/throw on out-of-range:
```ts
function formatTopXPercent(pct: number): string {
  const clamped = Math.min(100, Math.max(0, pct));
  return `Top ${Math.max(MIN_TOP_PERCENT, Math.round(100 - clamped))}%`;
}
```

### IN-03: `PercentileChip` chip span uses `role="button"` + `tabIndex={0}` but no `onKeyDown` handler

**File:** `frontend/src/components/charts/PercentileChip.tsx:113-138`

**Issue:** The chip is a `<span role="button" tabIndex={0}>` wrapping a
Radix `Popover.Trigger asChild`. Radix typically attaches keyboard
handlers via the trigger primitive, so Space/Enter likely work via the
asChild composition — but `<span role="button">` does not implicitly
fire click on Space/Enter the way `<button>` does. If Radix's
`asChild` doesn't forward a `onKeyDown` to the trigger's child, keyboard
users get focus but no way to toggle the popover.

A `<button type="button">` would be the semantically correct trigger
element (it provides Space/Enter click semantics natively, removes the
need for `role` + `tabIndex`, and inherits browser focus styling for
free). The only reason to use `<span>` is to avoid the default button
styling, which Tailwind `className` already overrides.

**Fix:** Either swap to `<button type="button" ...>` (cleanest), or add
an explicit `onKeyDown` handler:
```tsx
onKeyDown={(e) => {
  if (e.key === 'Enter' || e.key === ' ') {
    e.preventDefault();
    setOpen((o) => !o);
  }
}}
```
Worth a quick manual verification with keyboard-only navigation; the
existing `MetricStatPopover` may already have solved this and provide a
direct reference pattern.

### IN-04: `PercentileChip` export comment about knip is stale post-Wave-3

**File:** `frontend/src/components/charts/PercentileChip.tsx:14-16`

**Issue:** The file-level docstring says:

> Wired into rows by Plan 94-03 — until then this export is intentionally
> unused; knip will flag it as dead code in the Wave-2-only snapshot, but
> the import lands together with Wave 3 in the same PR.

Wave 3 has shipped (the chip is imported by `EndgameOverallPerformanceSection`
and `EndgameMetricCard`), so the comment is now misleading historical
context. Future readers will spend a minute checking whether the chip is
still unused before realising it isn't.

**Fix:** Drop the paragraph, or condense it to a single line referencing
the call sites for navigation:
```
Imported by EndgameOverallPerformanceSection (Endgame + Achievable Score
Gap chips) and EndgameMetricCard (Conversion + Parity ΔES chips, Recovery
excluded per D-12).
```

---

_Reviewed: 2026-05-23_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
