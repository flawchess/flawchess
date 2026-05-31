---
phase: 101-frontend-major-dependency-upgrades
reviewed: 2026-05-31T23:05:00Z
depth: deep
files_reviewed: 14
files_reviewed_list:
  - frontend/src/components/ui/chart.tsx
  - frontend/src/components/charts/ScoreGapByTimePressureChart.tsx
  - frontend/src/components/charts/EndgameEloTimelineSection.tsx
  - frontend/src/components/charts/EndgameScoreOverTimeChart.tsx
  - frontend/src/components/charts/EndgameClockDiffOverTimeChart.tsx
  - frontend/src/components/charts/ScoreChart.tsx
  - frontend/src/components/charts/__tests__/ScoreGapByTimePressureChart.test.tsx
  - frontend/src/components/charts/__tests__/EndgameClockDiffOverTimeChart.test.tsx
  - frontend/src/components/charts/__tests__/EndgameScoreOverTimeChart.test.tsx
  - frontend/src/components/charts/__tests__/InactivityGapReferenceLines.test.tsx
  - frontend/src/components/charts/__tests__/MiniBulletChart.test.tsx
  - frontend/eslint.config.js
  - frontend/tsconfig.json
  - frontend/tsconfig.app.json
findings:
  critical: 0
  warning: 1
  info: 4
  total: 5
status: issues_found
---

# Phase 101: Code Review Report

**Reviewed:** 2026-05-31T23:05:00Z
**Depth:** deep
**Files Reviewed:** 14
**Status:** issues_found (1 Warning, 4 Info — no Blockers)

## Summary

Reviewed the hand-written source changes from the recharts 2→3 migration plus the ESLint 10 / TypeScript 6 config tweaks. Version-bump-only files (`package.json`, `package-lock.json`) and the docs commit were excluded per scope.

The migration is mechanically sound. I independently re-ran the gates the SUMMARY claimed green: `tsc -b` passes, `knip` reports nothing, and all 88 tests across the five touched chart test files pass with no stray recharts console warnings (including no warning about the synthetic `dataKey="__bleed__"`). I traced the most substantive change — the `__bleed__` hidden-axis full-bleed fix in `ScoreGapByTimePressureChart.tsx` — and confirmed it is correct: the visible data `Line` carries no `xAxisId`, so it binds to the category axis (`dataKey="label"`), not the bleed axis. The synthetic `__bleed__` dataKey only affects the hidden numeric axis the `ReferenceArea` bands bind to, exactly as the inline comment claims. The Test-2b regression guard (asserting band rect `x < 80` and `width > 600` in an 800px mock) is a genuine, meaningful guard against the "left-third" regression, not a tautology.

No bugs, no security issues, no data-loss risks. The findings below are quality/maintainability only. As expected for a dependency-maintenance phase, security surface is unchanged.

The single Warning is a real (if justified) regression-coverage reduction: one chart's end-to-end domain-application test was downgraded to a pure-function unit test. The Info items are documentation/consistency nits.

## Narrative Findings (AI reviewer)

## Warnings

### WR-01: Domain-application coverage downgraded to a pure-function unit test

**File:** `frontend/src/components/charts/__tests__/EndgameClockDiffOverTimeChart.test.tsx:175-218`
**Issue:** The "expands Y domain to include values outside the ±30% envelope" test previously rendered the chart and asserted that the 42% dot's `cy` sat above the +30% tick's `y` — an end-to-end check that the computed domain is *actually applied to the axis and consumed by the renderer*. The migration replaced it with three assertions on the now-exported `computeYDomain([...])` helper. That verifies the math but no longer verifies that the chart wires the domain into `<YAxis>`. A future regression that computed the right domain but failed to pass it to the axis (e.g. a dropped `domain={yDomain}` prop) would now pass this test. The justification (jsdom 29 + recharts 3 portals make SVG pixel-position assertions unreliable) is legitimate, and the sibling `ScoreGapByTimePressureChart` Test-2b proves domain→pixel application still works for the analogous chart, so this is a partial mitigation rather than a true gap. But the specific chart under test loses its only end-to-end domain-wiring assertion, leaving that path covered solely by the human UAT (D-01), which does not re-run on future edits.
**Fix:** Keep the `computeYDomain` unit assertions, but add one lightweight render assertion that the axis received the expanded domain without depending on pixel layout — e.g. assert the expanded tick label is present in the rendered axis tick-label layer:
```tsx
const { container } = render(<EndgameClockDiffOverTimeChart timeline={OVERFLOW_FIXTURE} />);
const tickTexts = Array.from(
  container.querySelectorAll('.recharts-yAxis-tick-labels .recharts-cartesian-axis-tick-value'),
).map((n) => (n.textContent ?? '').replace(/\s/g, ''));
expect(tickTexts).toContain('+42%'); // proves the +42 outlier entered the axis domain
```
This stays robust to jsdom/portal layout changes (text presence, not geometry) while restoring the wiring guarantee.

## Info

### IN-01: `ignoreDeprecations: "6.0"` added without the planned removal TODO

**File:** `frontend/tsconfig.json:9`, `frontend/tsconfig.app.json:28`
**Issue:** RESEARCH.md explicitly listed under "Anti-Patterns to Avoid": *"Don't use `ignoreDeprecations: '6.0'` as permanent — if used for `baseUrl`, add a TODO comment noting it must be removed before TypeScript 7.0."* The suppression was added to both tsconfigs with no such note. `baseUrl` is removed entirely in the upcoming TS 7 line, so this escape hatch is time-bounded and will become a hard error; without a breadcrumb the next person hits it cold.
**Fix:** Add a JSON-comment breadcrumb at each site (tsconfig supports `//` comments):
```jsonc
// Suppresses the TS6 baseUrl deprecation warning (paired with "paths" → "@/*").
// TODO(TS7): remove this and migrate "paths" off "baseUrl" before upgrading to TypeScript 7.
"ignoreDeprecations": "6.0",
```

### IN-02: Deep type import into recharts internals is fragile across minor versions

**File:** `frontend/src/components/ui/chart.tsx:5`
**Issue:** `import type { Props as DefaultLegendContentProps } from "recharts/types/component/DefaultLegendContent"` reaches into a non-public, version-specific path under `recharts/types/...`. It is type-only (zero runtime cost) and currently resolves (verified the `.d.ts` exists in the installed `recharts@3.8.1`), but recharts does not treat `types/` as a stability contract — a future patch/minor that reorganizes its emitted declarations could break `tsc` with an unhelpful "cannot find module" error far from any code change. The inline comment explains *why* `payload` moved but not the stability risk of the chosen import path.
**Fix:** Prefer a public re-export if one exists in this recharts version (e.g. a top-level `LegendPayload` / `DefaultLegendContentProps` export from `"recharts"`), and only fall back to the deep path if no public type is exported. If the deep path must stay, note the fragility in the comment so a future `tsc` break is diagnosed quickly:
```ts
// Deep import: recharts does not publicly export this prop type. Path is recharts@3.x-specific
// and may move on a recharts minor — if tsc can't find it after an upgrade, re-check this path.
```

### IN-03: Inconsistent react-refresh suppression strategy between charts and filters

**File:** `frontend/src/components/charts/EndgameClockDiffOverTimeChart.tsx:91`, `frontend/eslint.config.js:43-48`
**Issue:** Two different mechanisms now suppress the same `react-refresh/only-export-components` rule for non-component exports. The `filters/` directory got a blanket `eslint.config.js` override (and the per-line `eslint-disable` comments in `CustomRangePopover.tsx` / `FilterPanel.tsx` were removed in favor of it), while `EndgameClockDiffOverTimeChart.tsx`'s newly-exported `computeYDomain` uses a per-line inline `eslint-disable-next-line`. Both are valid; the per-line form is arguably the cleaner (narrowly-scoped) choice. The inconsistency is cosmetic, but it means a reader has to learn two conventions for the same rule. Note also the SUMMARY's stated rationale for the filters override ("react-refresh 0.5 narrowed allowConstantExport") describes a behavior change, whereas the chart export is a deliberate test-only seam — different motivations, same rule, two patterns.
**Fix:** No action required. If you want uniformity, prefer the per-line `eslint-disable-next-line` at each genuine test-only/util export (most precise, self-documenting at the export) and reserve directory-wide overrides for directories where the co-export pattern is pervasive (the `filters/` and `ui/` dirs qualify). Optionally drop a one-line note in `eslint.config.js` that charts use per-line disables intentionally.

### IN-04: `ScoreChart` dataKey fallback to `'value'` is unreachable and could mask a future key collision

**File:** `frontend/src/components/charts/ScoreChart.tsx:161-167`
**Issue:** The recharts-3 narrowing `const dataKey = typeof item.dataKey === 'string' || 'number' ? String(item.dataKey) : 'value'` is correct for the type, but in this chart every series uses a distinct string `dataKey` (`bkm_${id}` or the explicit series keys), so the function-typed branch — and thus the `'value'` fallback — is dead. If a future caller ever did add a function `dataKey`, two such items would both resolve to `'value'`, colliding both the React `key` (`key={dataKey}`) and the `chartConfig[dataKey]` lookup, silently rendering only one row or mislabeling. This is defensive code that is currently safe, not a bug.
**Fix:** Acceptable as-is. If you want to harden it, fall back to a guaranteed-unique token (e.g. the array index) for the React key rather than the shared literal `'value'`, so a future function-dataKey can't collide:
```tsx
.map((item, i) => {
  const dataKey = (typeof item.dataKey === 'string' || typeof item.dataKey === 'number')
    ? String(item.dataKey) : `series-${i}`;
  // ...use `dataKey` for config lookup AND the React key (now unique per row)
```

---

_Reviewed: 2026-05-31T23:05:00Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: deep_
