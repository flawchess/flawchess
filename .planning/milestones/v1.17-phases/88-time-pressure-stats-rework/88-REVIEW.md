---
phase: 88-time-pressure-stats-rework
reviewed: 2026-05-17T21:20:00Z
depth: standard
scope: plans 88-13, 88-14, 88-15 (frontend polish + restored top-zone clock stats + restored "Average Clock Difference over Time" line chart)
files_reviewed: 14
files_reviewed_list:
  - app/schemas/endgames.py
  - app/services/endgame_service.py
  - frontend/src/components/charts/EndgameClockDiffOverTimeChart.tsx
  - frontend/src/components/charts/EndgameTimePressureCard.tsx
  - frontend/src/lib/pressureBulletConfig.ts
  - frontend/src/pages/Endgames.tsx
  - frontend/src/types/endgames.ts
  - frontend/src/components/charts/__tests__/EndgameClockDiffOverTimeChart.test.tsx
  - frontend/src/components/charts/__tests__/EndgameTimePressureCard.test.tsx
  - frontend/src/components/charts/__tests__/EndgameTimePressureSection.test.tsx
  - frontend/src/lib/pressureBulletConfig.test.ts
  - tests/services/test_insights_service_series.py
  - tests/services/test_time_pressure_service.py
  - tests/test_endgame_service.py
findings:
  critical: 0
  warning: 0
  info: 2
  total: 2
status: clean
---

# Phase 88 (plans 88-13 / 88-14 / 88-15): Code Review Report

**Reviewed:** 2026-05-17
**Depth:** standard
**Scope:** Frontend polish (A-1 / A-4 / A-5), restored card top-zone stats (A-3), restored "Average Clock Difference over Time" line chart (A-2).
**Status:** issues_found

## Summary

Three plans land cleanly against the §2 scope amendment: card chrome split (A-1), Q4 hide + qualitative pressure labels (A-4), widened ±30% axis (A-5), top-zone 3-stat row (A-3), and the restored clock-diff line chart (A-2). Pydantic schema additions ship with defaults as locked (B-2), the unit convention between `net_timeout_rate` (fraction) and `NEUTRAL_TIMEOUT_THRESHOLD` (percent) is explicitly reconciled (B-1), and the chart percent / threshold units stay aligned (B-5).

The dominant defect sits on the backend: `compose_endgame_overview` advertises a rolling-window pre-fill semantics in a code comment ("fetch ... WITHOUT recency cutoff so the clock-diff timeline can pre-fill from games before the cutoff") but then passes the already-cutoff-filtered `clock_rows` into `_compute_clock_diff_timeline`. The function additionally lacks a `cutoff_str` output filter that the sibling score-gap timeline uses. With a recency filter applied, the rolling-window mean for early visible weeks is computed from a short head of the window — the "trailing 100" tooltip becomes a lie, the leading edge of the line swings sharper than the underlying signal warrants, and the comment immediately preceding the call site documents behavior that is not implemented. This is a Warning, not Critical: it degrades the leading weeks rather than corrupting data.

Secondary issues: `Y_DOMAIN: [-30, 30]` combined with `allowDataOverflow={false}` silently clips real values outside the envelope (rapid/classical can legitimately exceed ±30%); two `dict[Any, …]` typings in the timeline aggregator weaken `ty` coverage; a redundant `aria-label="no games"` collides with adjacent visible text; a dead `_pad_to_threshold` helper sits in the test module; an `isMobile` hook is invoked but used only for `margin.left`.

No security issues, no data-loss risks, no schema migrations affected. Frontend tests cover Q4 hide, labels, top-zone formatting, em-dash null fallback, and tinting branches; backend tests cover the 5-average aggregator, timeout-net edge cases, fraction-vs-percent unit pinning, and the rolling-window timeline.

## Warnings

### WR-01: Clock-diff timeline rolling window is NOT pre-filled from games before the recency cutoff (contradicts adjacent comment)

**File:** `app/services/endgame_service.py:2599-2629`
**Category:** Bug
**Severity:** Warning

The block beginning at line 2599 fetches `clock_rows_all` without a recency cutoff, then filters in Python to `clock_rows` (line 2615). The comment at line 2599-2602 explicitly states: *"Clock pressure: fetch per-span arrays WITHOUT recency cutoff so the clock-diff timeline can pre-fill from games before the cutoff."* But line 2629 passes the post-filter `clock_rows` into `_compute_clock_diff_timeline`, not `clock_rows_all`. Result: when a recency filter is set, the rolling-window mean for the earliest visible weeks is computed from a partial window (just the in-window history), so:

- The "trailing 100" tooltip copy in the chart is misleading for those points (`game_count` will be 1, 2, 3, … instead of the actual 100-game rolling state).
- The leading edge of the line swings more sharply than the underlying signal warrants — exactly the artifact pre-fill exists to suppress.

Compare to the sibling score-gap timeline (`_compute_score_gap_timeline`, line 845+) which takes the `_all` row stream plus a `cutoff_str` argument and drops emitted points before the cutoff inside the loop. That pattern is the codebase's idiom for "pre-fill the window, then trim the output". `_compute_clock_diff_timeline` has no `cutoff_str` parameter at all.

**Fix:**

```python
# In _compute_clock_diff_timeline signature:
def _compute_clock_diff_timeline(
    clock_rows: Sequence[Row[Any] | tuple[Any, ...]],
    window: int = CLOCK_PRESSURE_TIMELINE_WINDOW,
    cutoff_str: str | None = None,
) -> ClockDiffTimelineResponse:
    ...
    # In phase 3 (emit chronologically) — drop pre-cutoff weeks:
    for monday in sorted(week_to_rolling.keys()):
        monday_iso = monday.isoformat()
        if cutoff_str is not None and monday_iso < cutoff_str:
            continue
        avg, n = week_to_rolling[monday]
        ...

# At the call site in compose_endgame_overview (line 2629):
cutoff_str = cutoff.strftime("%Y-%m-%d") if cutoff else None
clock_diff_timeline = _compute_clock_diff_timeline(clock_rows_all, cutoff_str=cutoff_str)
```

Add a regression test asserting that with cutoff and 200 pre-cutoff games, the first emitted post-cutoff point's `game_count` is 100 (window saturated from pre-cutoff history), not the in-window count.

### WR-02: Y axis silently clips values outside ±30% (`allowDataOverflow={false}` + fixed domain)

**File:** `frontend/src/components/charts/EndgameClockDiffOverTimeChart.tsx:146-153`
**Category:** Bug (visual / data integrity)
**Severity:** Warning

`Y_DOMAIN = [-30, 30]` together with `allowDataOverflow={false}` (the explicit prop on line 150) means any point whose `avg_clock_diff_pct` falls outside the envelope is rendered at the nearest edge with no indicator. The backend can legitimately emit values beyond ±30% — rapid/classical games where the user routinely banks 50%+ more clock than the opponent at endgame entry (common in classical against weaker opponents). Silent clipping turns a "5x my opponent's clock" trend into a flat line at 30%, which misleads the user.

Two reasonable fixes:

1. `allowDataOverflow={true}` and let the line briefly leave the visible area (matches the bullet-chart "open-ended whisker" convention).
2. Widen `Y_DOMAIN` to `[-50, 50]` and pad ticks (`[-50, -25, 0, 25, 50]`).

Option 1 mirrors the bullet-chart precedent (`clampDeltaCi`, open whiskers) and is the least intrusive. The existing `EndgameScoreOverTimeChart` uses a fixed `[0, 1]` domain because score is mathematically bounded; clock diff is not.

**Fix:** flip the prop to `allowDataOverflow={true}` and add a test fixture with a point at e.g. `avg_clock_diff_pct: 42.0` asserting the line is not clipped (Recharts emits the point with a y-coord outside the visible viewbox; check `.recharts-line-curve` path includes a coordinate computed from 42).

### WR-03: `dict[Any, …]` typings in `_compute_clock_diff_timeline` weaken ty coverage

**File:** `app/services/endgame_service.py:1829, 1862`
**Category:** Type safety
**Severity:** Warning

Two local accumulators use `Any` as the key type:

```python
per_week_counts: dict[Any, int] = defaultdict(int)        # line 1829
week_to_rolling: dict[Any, tuple[float, int]] = {}         # line 1862
```

The actual key is `datetime.date` (computed by `played_at.date() - timedelta(...)`). CLAUDE.md's type-safety rule is explicit: "Avoid `any`, prefer explicit types ..." and ty compliance requires zero errors. The function passes ty today because `Any` consumes any annotation, but losing the key-type guarantee makes future refactors (swapping ISO Monday for ISO year-week tuples, for example) unsafe — the bad assignment would not surface until a runtime KeyError on `sorted()` of mixed-type keys.

**Fix:**

```python
from datetime import date  # add to module imports

per_week_counts: dict[date, int] = defaultdict(int)
week_to_rolling: dict[date, tuple[float, int]] = {}
```

### WR-04: Card top-zone net-flag-rate tinting drops zone information from screen readers

**File:** `frontend/src/components/charts/EndgameTimePressureCard.tsx:358-363`
**Category:** Accessibility
**Severity:** Warning

The net-flag-rate cell tints its value span with `style={tint ? { color: tint } : undefined}` but provides no `aria-label`, no `aria-describedby`, no text qualifier. For a sighted user the red/green tint conveys directionality; for a screen-reader user the cell reads "Net flag rate: +6.0%" — ambiguous without the WDL convention reference. The neighboring Clock Gap bullet uses `MetricStatPopover` which includes a `vocabulary="score"` semantic hint; the net-flag-rate cell has no popover or semantic equivalent.

**Fix:** either add a small popover trigger (`MetricStatPopover` or a plain `InfoPopover`) next to the value with a one-sentence explainer, OR augment the colored span with an `aria-label` that names the direction:

```tsx
<span
  style={tint ? { color: tint } : undefined}
  aria-label={`Net flag rate: ${formatNetTimeoutRate(card.net_timeout_rate)} ${
    card.net_timeout_rate > 0 ? '(in your favor)' : card.net_timeout_rate < 0 ? '(against you)' : ''
  }`}
>
  {formatNetTimeoutRate(card.net_timeout_rate)}
</span>
```

Popover is preferred for consistency with the rest of the card.

### WR-05: `useIsMobile` hook scaffolded but only adjusts `margin.left`

**File:** `frontend/src/components/charts/EndgameClockDiffOverTimeChart.tsx:54-67, 85, 142`
**Category:** Code quality / mobile compliance
**Severity:** Warning

The chart imports `useState`, `useEffect`, defines a 14-line `useIsMobile` hook with a media-query listener, then uses the value once in `margin: { left: isMobile ? 0 : 10 }`. The sibling `EndgameScoreOverTimeChart` uses `useIsMobile` for tick density, chart height, label positioning. If mobile responsiveness needs to extend beyond left-margin (label rotation, tick interval, Y axis width), the hook is set up but underused — alternatively, if margin is truly the only mobile difference, a Tailwind class on the wrapper avoids the listener entirely.

Per CLAUDE.md mobile rule the current setup is sufficient, but the hook scaffolding suggests an unfinished thought. Either remove the hook and replace with a Tailwind responsive class on the wrapper (`<div className="-ml-2 sm:ml-0">`) and tighten the chart margin to a constant 10, or expand mobile-awareness to match the sibling chart's level of polish.

## Info

### IN-01: Redundant `aria-label="no games"` on em-dash duplicates adjacent visible text

**File:** `frontend/src/components/charts/EndgameTimePressureCard.tsx:283-289`
**Category:** Accessibility / quality
**Severity:** Info

```tsx
<span className="text-muted-foreground text-sm" aria-label="no games">
  &mdash;
</span>
<span className="text-muted-foreground text-sm">no games</span>
```

The aria-label on the em-dash announces "no games", then the adjacent visible-text span also announces "no games". Screen readers read "no games no games".

**Fix:** `<span className="text-muted-foreground text-sm" aria-hidden="true">&mdash;</span>`.

### IN-02: `_pad_to_threshold` helper in test module is dead code

**File:** `tests/services/test_time_pressure_service.py:574-584`
**Category:** Dead code
**Severity:** Info

The helper is defined but never called; its body is `return rows` despite a docstring promising padding behavior. Tests pad rows inline instead (see `test_averages_computed_from_clock_eligible_rows`'s own repeats loop).

**Fix:** delete the function. A future test author may import it expecting real padding — the stub is a bug attractor.

### IN-03: `MIN_GAMES_PER_TC_CARD` / `MIN_GAMES_PER_PRESSURE_BIN` redefined as test-local constants instead of imported from codegen

**File:** `frontend/src/components/charts/__tests__/EndgameTimePressureCard.test.tsx:25-26`
**Category:** Magic-number / coupling
**Severity:** Info

```ts
const MIN_GAMES_PER_TC_CARD = 20;
const MIN_GAMES_PER_PRESSURE_BIN = 5;
```

with a comment "Constants match the component — reference symbolically, not as magic numbers." These constants are exported from `@/generated/endgameZones` (codegen-mirrored from `app/services/endgame_zones.py`). Hard-coding their numeric values in the test means a future bump on the backend (e.g. `MIN_GAMES_PER_PRESSURE_BIN = 10`) would not fail the test — it would silently use the wrong threshold and possibly pass for the wrong reasons.

**Fix:** `import { MIN_GAMES_PER_TC_CARD, MIN_GAMES_PER_PRESSURE_BIN } from '@/generated/endgameZones';`. The codegen drift gate then catches any backend bump that would otherwise silently desync the test.

### IN-04: `text-xs` caption under the clock-diff chart violates min-font-size rule (precedent exists in sibling chart)

**File:** `frontend/src/components/charts/EndgameClockDiffOverTimeChart.tsx:237`
**Category:** Frontend convention
**Severity:** Info

```tsx
<p className="text-xs text-muted-foreground text-center mt-1">
  Week (rolling average of the last 100 games)
</p>
```

CLAUDE.md says "Minimum font size is `text-sm`" and the popover-body exception does NOT cover plain captions. `EndgameScoreOverTimeChart` does the same thing at line 327, so this is a pre-existing convention drift, not a new violation. The Recharts `ChartTooltip` content at line 193 of the new chart is `text-xs` too, but that one IS a transient, opt-in tooltip surface and probably falls under the popover exception.

**Fix:** bump line 237 to `text-sm`. Leave line 193 alone (chart tooltip).

### IN-05: `played_at = row[8] if len(row) > 8 else None` defensive guard hides a contract mismatch

**File:** `app/services/endgame_service.py:1836`
**Category:** Quality / contract
**Severity:** Info

`query_clock_stats_rows` documented row shape always has 9 columns including `played_at` at index 8. The `if len(row) > 8` guard means if some upstream changes the row shape, the timeline silently treats every row as "no played_at" — the chart renders empty rather than failing loudly. The sibling `_iterate_clock_rows` (line 1533+) does NOT defend the same way; it accesses `row[6]`, `row[7]` directly and would `IndexError` on a shape regression.

The two accessors should agree: either both defend or neither does. Defending only in one place causes one consumer to fail loudly and the other to silently degrade — worst of both worlds for diagnosing a future schema bump.

**Fix:** replace `row[8] if len(row) > 8 else None` with a plain `row[8]` and let an `IndexError` raise on shape regression. The repo function's contract is documented; trust it.

## Recommendations

1. **Land WR-01 as a follow-up** in this phase before re-verification. The chart-shape regression is small (add `cutoff_str` parameter, swap the call-site argument, add a 10-line test) and the visible-chart bias on the leading edge is exactly the kind of subtle correctness issue that gets attributed to "data noise" once it ships.
2. **WR-02 (clip-on-overflow)** is also pre-verification-worthy — production likely has classical/rapid users whose values legitimately exceed ±30%. A single fixture point at 42% in a unit test + `allowDataOverflow={true}` is a 3-line change.
3. **WR-03, WR-04, WR-05** can be addressed in the same wave as WR-01/WR-02 since they cluster on the same two files (`endgame_service.py`, `EndgameClockDiffOverTimeChart.tsx`).
4. **Info items** are housekeeping; bundle them into the next `gsd-quick` pass on the chart/card files. IN-03 has the highest "future bug-attractor" cost — hard-coded thresholds in tests silently desync.

The §2 scope amendment (A-1..A-5) is delivered honestly; the CHANGELOG entries in 88-13/88-14/88-15 SUMMARYs frame the SC #1 walk-back correctly. No structural findings outside the narrative above.

---

_Reviewed: 2026-05-17_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
