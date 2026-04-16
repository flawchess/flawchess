---
phase: quick-260416-r3n
plan: 01
subsystem: frontend/endgames
tags: [ui, copy, endgames, score-percent]
requires: []
provides:
  - "Endgames tab uses 'Score %' (integer percent 0-100%) consistently for the weighted-average metric."
affects:
  - frontend/src/components/charts/EndgamePerformanceSection.tsx
  - frontend/src/components/charts/EndgameWDLChart.tsx
  - frontend/src/components/charts/EndgameTimePressureSection.tsx
tech_stack:
  added: []
  patterns:
    - "Display-only conversion: render decimal 0.0-1.0 backend values as `${Math.round(v * 100)}%` at the JSX layer."
key_files:
  created: []
  modified:
    - frontend/src/components/charts/EndgamePerformanceSection.tsx
    - frontend/src/components/charts/EndgameWDLChart.tsx
    - frontend/src/components/charts/EndgameTimePressureSection.tsx
decisions:
  - "Kept backend field names (endgame_score, non_endgame_score, score_difference, score) and chartConfig keys (my_score, opp_score) untouched — pure display refactor."
  - "Left internal JSDoc comment 'Opponent chess score ...' in EndgameWDLChart.tsx unchanged (internal-only comment; out of user-visible scope per plan)."
  - "Y-axis numeric domain kept as 0.2-0.8 (decimal); only the tick formatter converts to percent display, preserving Recharts domain/scale math."
metrics:
  duration_seconds: 176
  tasks_completed: 1
  completed_date: "2026-04-16"
---

# Quick 260416-r3n: Rename Score to Score % across the Endgames tab — Summary

One-liner: Unify the weighted-average chess-score metric on the Endgames tab under the label "Score %" with integer-percent display, removing the mixed `0.54` / `54%` presentation.

## What changed

Display-only relabeling + decimal→percent reformatting in three frontend components. No backend, schema, identifier, or test changes.

### A. `EndgamePerformanceSection.tsx` — Games with vs without Endgame table

Desktop table (`<thead>` + cells):
- Column header `Score` → `Score %`
- Column header `Score Difference` → `Score % Diff`
- Score cell: `row.score.toFixed(2)` → `` `${Math.round(row.score * 100)}%` `` (line ~128)
- Diff `diffFormatted` (used by the header cell and aria-label): `scoreGap.score_difference.toFixed(2)` → `` `${Math.round(scoreGap.score_difference * 100)}%` `` (line ~41). Sign handling preserved via the existing `(diffPositive ? '+' : '')` prefix.

Mobile cards (`lg:hidden` branch):
- Label `Score` → `Score %`
- Score value: `row.score.toFixed(2)` → `` `${Math.round(row.score * 100)}%` ``
- Card heading `Score Difference` → `Score % Diff`

Info popover copy updated: “The Score Difference column shows the signed gap between your endgame score and non-endgame score …” → “The Score % Diff column shows the signed gap between your endgame Score % and non-endgame Score % …”.

Untouched (intentional): `MiniBulletChart` props `value={scoreGap.score_difference}` and `neutralMin`/`neutralMax` still pass the raw decimal domain (±0.05). The `aria-label` template literal `` `Endgame score difference: ${diffFormatted}` `` now interpolates the new percent-formatted string automatically — no additional changes needed.

### B. `EndgameWDLChart.tsx` — Results by Endgame Type info popover

Popover body updated from “chess score (1 per win, ½ per draw, divided by games)” to “Score % (100% per win, 50% per draw, averaged over games)” for both `You` and `Opp` explanations. Table column headers (`You`, `Opp`, `Diff`, `Games`, `Win / Draw / Loss`, `You − Opp`) remain unchanged; they were already using `formatScorePct` → integer percent.

Internal identifiers (`userScore`, `opponentScore`, `formatScorePct`, `MY_SCORE_COLOR`, etc.) and the JSDoc on `opponentScore` (line 56: “Opponent chess score in the same games …”) were intentionally left alone — internal docstrings, not user copy.

### C. `EndgameTimePressureSection.tsx` — Time Pressure vs Performance chart

- `chartConfig.my_score.label`: `'My score'` → `'My Score %'`
- `chartConfig.opp_score.label`: `"Opponent's score"` → `"Opponent's Score %"`
- Y-axis vertical label (desktop rotated HTML): `Avg Score` → `Score %`
- `<YAxis tickFormatter={(v) => v.toFixed(1)}>` → `tickFormatter={(v) => \`${Math.round(v * 100)}%\`}` (renders `20%`, `30%`, …, `80%` against the unchanged `[0.2, 0.8]` domain).
- Tooltip value: `(item.value as number).toFixed(2)` → `Math.round((item.value as number) * 100)%`
- Popover copy updated throughout: “average score” / “your average score” → “Score %” / “your Score %” / “more reliable Score %”, plus an added sentence defining Score % as “the weighted-average score (100% per win, 50% per draw, averaged over games).”

Untouched (intentional): `dataKey="my_score"` / `dataKey="opp_score"` (backend series identifiers), `MY_SCORE_COLOR` / `OPP_SCORE_COLOR` (theme identifiers), `ChartDataPoint.my_score` / `opp_score` (TS interface fields), Y-axis `domain={[0.2, 0.8]}` and `ticks={[0.2…0.8]}` (numeric domain; only the formatter changed), the “lines diverge” sentence (doesn’t mention “score”), the “% of base time remaining” subtitle (unrelated percent).

## Strings renamed (enumeration)

| File | Before | After |
|---|---|---|
| EndgamePerformanceSection | header `Score` | `Score %` |
| EndgamePerformanceSection | header `Score Difference` | `Score % Diff` |
| EndgamePerformanceSection | mobile label `Score` | `Score %` |
| EndgamePerformanceSection | mobile heading `Score Difference` | `Score % Diff` |
| EndgamePerformanceSection | popover `score difference` language | `Score % Diff` / `Score %` |
| EndgameWDLChart | popover `chess score (1 per win, ½ per draw, divided by games)` | `Score % (100% per win, 50% per draw, averaged over games)` |
| EndgameWDLChart | popover `your opponents' score` | `your opponents' Score %` |
| EndgameTimePressureSection | legend `My score` | `My Score %` |
| EndgameTimePressureSection | legend `Opponent's score` | `Opponent's Score %` |
| EndgameTimePressureSection | y-axis vertical label `Avg Score` | `Score %` |
| EndgameTimePressureSection | popover `average score` / `more reliable score` | `Score %` / `more reliable Score %` |

## Decimal → percent conversions applied

| File | Location | Before | After |
|---|---|---|---|
| EndgamePerformanceSection | desktop score cell (~L128) | `row.score.toFixed(2)` | `` `${Math.round(row.score * 100)}%` `` |
| EndgamePerformanceSection | mobile score cell (~L186) | `row.score.toFixed(2)` | `` `${Math.round(row.score * 100)}%` `` |
| EndgamePerformanceSection | `diffFormatted` (~L41) | `scoreGap.score_difference.toFixed(2)` | `` `${Math.round(scoreGap.score_difference * 100)}%` `` |
| EndgameTimePressureSection | YAxis tickFormatter (~L166) | `v.toFixed(1)` | `` `${Math.round(v * 100)}%` `` |
| EndgameTimePressureSection | tooltip value (~L193) | `(item.value as number).toFixed(2)` | `Math.round((item.value as number) * 100)%` |

## Out-of-scope files confirmed untouched

- `frontend/src/components/charts/EndgameScoreGapSection.tsx` (Conversion / Parity / Recovery — different metrics) — not modified.
- `frontend/src/pages/Endgames.tsx` concepts accordion — not modified.
- `EndgameClockPressureSection.tsx`, `EndgameTimelineChart.tsx`, `MiniBulletChart.tsx` — not modified.
- Backend schemas / field names — not modified (`grep -r` against `app/schemas` and `app/services` confirms nothing in backend carried the word `Score` in display copy; no touches there).

Confirmation commands run:

```bash
git status --short
# Only the three in-scope frontend files plus the .planning/ quick directory.
```

## Edge cases and notes

- **Sign handling on `Score % Diff`:** `Math.round(x * 100)` for negative `x` yields a negative integer that carries its own `-` sign; the existing `(diffPositive ? '+' : '')` prefix only prepends `+` for non-negative values, so there is no double-negative risk. Verified mentally with `x = -0.063` → `Math.round(-6.3) = -6` → `` `${-6}%` `` → `-6%` (prefix branch empty).
- **`aria-label` template literals:** The aria-labels in EndgamePerformanceSection and EndgameWDLChart reference `${diffFormatted}` / `${formatDiffPct(...)}` respectively; they pick up the new percent-formatted strings automatically. No per-ARIA-label edits needed.
- **Internal comments:** Two internal references to the word "score" remain and are intentionally out of user-visible scope:
  - `EndgamePerformanceSection.tsx` top-of-file comment on the neutral zone.
  - `EndgameWDLChart.tsx` JSDoc on `opponentScore` ("Opponent chess score in the same games …").
- **Chart numeric domain kept decimal:** Recharts' `domain={[0.2, 0.8]}` stays in decimal so the underlying scale math is unchanged. Only the `tickFormatter` shows percent — this is the correct place to convert (plan explicitly calls this out).
- **No tests broken:** A quick scan with `grep -r "Avg Score" frontend/src` produced no matches (no tests or other components referenced the renamed string). No test files assert against `"My score"` / `"Opponent's score"` / `"Score Difference"` / `toFixed(2)` for these values.

## Commits

- `0b022b1` — refactor(quick-260416-r3n): rename Score to Score % across Endgames tab (3 files changed, 20 insertions(+), 20 deletions(-))

## Verification

- `cd frontend && npm run lint` — 0 errors.
- `cd frontend && npm run build` — succeeded; `tsc -b` then `vite build` both clean, 2964 modules transformed, prerender + PWA steps succeeded.
- Grep sanity checks (from PLAN `<verify>`):
  - Standalone `Score` in JSX/strings in EndgamePerformanceSection.tsx → only `Score %` / `Score % Diff` remain (expected).
  - Standalone `Score` in EndgameTimePressureSection.tsx → no matches (expected).
  - `chess score` in EndgameWDLChart.tsx → one JSDoc comment match only (intentional per scope).
  - `Score Difference` in EndgamePerformanceSection.tsx → no matches (expected).
  - `toFixed(2)` in the two edited score-formatting files → no matches (expected).
  - `Avg Score` in EndgameTimePressureSection.tsx → no matches (expected).

## Self-Check: PASSED

- FOUND: frontend/src/components/charts/EndgamePerformanceSection.tsx (modified)
- FOUND: frontend/src/components/charts/EndgameWDLChart.tsx (modified)
- FOUND: frontend/src/components/charts/EndgameTimePressureSection.tsx (modified)
- FOUND commit: 0b022b1
