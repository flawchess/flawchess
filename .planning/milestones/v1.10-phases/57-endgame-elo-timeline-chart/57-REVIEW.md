---
phase: 57-endgame-elo-timeline-chart
reviewed: 2026-04-18T00:00:00Z
depth: standard
files_reviewed: 11
files_reviewed_list:
  - app/repositories/endgame_repository.py
  - app/schemas/endgames.py
  - app/services/endgame_service.py
  - frontend/src/components/charts/EndgameEloTimelineSection.tsx
  - frontend/src/lib/theme.ts
  - frontend/src/lib/utils.test.ts
  - frontend/src/lib/utils.ts
  - frontend/src/pages/Endgames.tsx
  - frontend/src/types/endgames.ts
  - tests/test_endgame_service.py
  - tests/test_integration_routers.py
findings:
  critical: 0
  warning: 3
  info: 5
  total: 8
status: issues_found
---

# Phase 57: Code Review Report

**Reviewed:** 2026-04-18
**Depth:** standard
**Files Reviewed:** 11
**Status:** issues_found

## Summary

Phase 57 adds a paired-line "Endgame ELO vs Actual ELO" weekly timeline per (platform, time control) combo. The backend side introduces one new repo query, one orchestrator function, and two pure helpers (`_endgame_elo_from_skill`, `_endgame_skill_from_bucket_rows`, `_compute_endgame_elo_weekly_series`). The frontend side adds the `EndgameEloTimelineSection` component, the `niceEloAxis` utility, the `ELO_COMBO_COLORS` palette, and integration tests.

Overall the implementation is cohesive and well-documented. Sequential `await` on the shared `AsyncSession` is correctly preserved (no `asyncio.gather`), Pydantic v2 + Literal types are used consistently, and the rolling-window pre-fill pattern (unfiltered SQL + cutoff_str in Python) mirrors the existing chart timelines.

Three warnings flag a magic number that bypasses an existing module constant, a duplicated magic literal pair (`-100`/`100` in imbalance classification), and a stale docstring bucket comment. Five info items note minor duplication and documentation drift.

No critical security or correctness issues found. No `asyncio.gather` misuse, no hardcoded secrets, no Sentry coverage gaps (no new try/except blocks added in this phase).

## Warnings

### WR-01: Magic number `100` in `_endgame_skill_from_bucket_rows` bypasses `_MATERIAL_ADVANTAGE_THRESHOLD`

**File:** `app/services/endgame_service.py:920,924`
**Issue:** The new `_endgame_skill_from_bucket_rows` helper uses bare `100` and `-100` literals for the material imbalance persistence threshold:

```python
if imbalance_after is not None and imbalance_after >= 100:
    conv_count += 1
    ...
elif imbalance_after is not None and imbalance_after <= -100:
    recov_count += 1
    ...
```

The module already defines `_MATERIAL_ADVANTAGE_THRESHOLD = 100` (line 164) and uses it in `_aggregate_endgame_stats` and `_compute_score_gap_material`. The docstring even references "(abs(imbalance) < 100 at persistence ply)" — pointing to a shared concept. Violates CLAUDE.md §Coding Guidelines "no magic numbers" rule and creates a divergence risk: if the threshold is ever retuned, this function will silently desync from the rest of the module.

**Fix:**
```python
if imbalance_after is not None and imbalance_after >= _MATERIAL_ADVANTAGE_THRESHOLD:
    conv_count += 1
    if outcome == "win":
        conv_wins += 1
elif imbalance_after is not None and imbalance_after <= -_MATERIAL_ADVANTAGE_THRESHOLD:
    recov_count += 1
    if outcome in ("win", "draw"):
        recov_saves += 1
```

### WR-02: `createDateTickFormatter` docstring advertises a "> 2 months" bucket that does not exist

**File:** `frontend/src/lib/utils.ts:23-28`
**Issue:** The JSDoc lists three behavior branches, but the implementation has only two:

```ts
/**
 * Returns a tick formatter that adapts to the date range:
 * - > 18 months: "Jan '24" (month + abbreviated year)
 * - > 2 months:  "Jan 5"   (month + day)
 * - <= 2 months: "Jan 5"   (month + day)
 */
```

The last two bullets produce identical output (`"Jan 5"`) and collapse into a single `else` branch in code. The `> 2 months` bullet is meaningless — it looks like a leftover from a pre-implementation design sketch. A future reader may conclude behavior differs around the 2-month mark and spend time chasing phantom logic.

**Fix:**
```ts
/**
 * Returns a tick formatter that adapts to the date range:
 * - > 18 months: "Jan '24" (month + abbreviated year)
 * - otherwise:   "Jan 5"   (month + day, no year)
 */
```

### WR-03: `EIGHTEEN_MONTHS` approximation uses `18 * 30 = 540` days (not calendar months)

**File:** `frontend/src/lib/utils.ts:31`
**Issue:** `const EIGHTEEN_MONTHS = 18 * 30;` is a 540-day rough estimate, not 18 calendar months (which vary between 546 and 551 days). The matching test file even notes this discrepancy explicitly:

```ts
// tests/utils.test.ts:29-31
// The threshold is 18 * 30 = 540 days. A range of exactly 540 days is NOT > 540,
// so it falls into the short format. 2023-01-01 to 2024-06-23 = exactly 540 days.
```

This is arguably acceptable for a coarse chart heuristic, but the name `EIGHTEEN_MONTHS` claims calendar-month semantics that the value does not deliver. At minimum the name should communicate what the constant actually is.

**Fix:** Either rename to reflect the day count, or compute with a calendar library:
```ts
// Option A — honest naming
const LONG_RANGE_THRESHOLD_DAYS = 18 * 30;

// Option B — use a date library for true 18 months (heavier, likely overkill for tick formatting)
```

## Info

### IN-01: Duplicated label-lookup pattern in tooltip and legend

**File:** `frontend/src/components/charts/EndgameEloTimelineSection.tsx:240-262,288-303`
**Issue:** The legend renderer (`renderLegend`) and the tooltip content both call `getComboColors(combo.combo_key)` + `getComboLabel(combo.combo_key)` for each combo. The pattern is small enough that extracting isn't strictly required, but if combo presentation grows (e.g. adding icons per combo), the duplication will compound.

**Fix:** Consider precomputing a `ComboPresentation[]` array once per render:
```ts
const comboPresentations = useMemo(
  () => data.combos.map(c => ({
    combo: c,
    colors: getComboColors(c.combo_key),
    label: getComboLabel(c.combo_key),
    isHidden: hiddenKeys.has(c.combo_key),
  })),
  [data.combos, hiddenKeys],
);
```

### IN-02: TODO marker in production code references "Phase 56" that may already have landed

**File:** `app/services/endgame_service.py:874-876`
**Issue:**
```python
# TODO (Phase 56): deduplicate with the backend endgame_skill() port introduced
# by Phase 56 when that phase lands.
```

The phase branch is `gsd/phase-57-endgame-elo-timeline-chart` so Phase 56 should already be merged. If there is an existing `endgame_skill()` function in the backend, this is dead documentation and the dedup should have been done; if not, the TODO is stale.

**Fix:** Either complete the dedup or delete/update the TODO to reference a real follow-up (a GSD "quick" ID is more actionable than a phase number).

### IN-03: O(window) opp-average recomputation per event in `_compute_endgame_elo_weekly_series`

**File:** `app/services/endgame_service.py:1016-1029`
**Issue:** On every event in the merged stream, the function re-walks the entire `endgame_window` (up to 100 rows) to sum opponent ratings. For a user with N endgame games, this is O(N * window) total. Performance is out of v1 review scope but a running sum + dequeue on `endgame_window` rotation would be O(N). Flagging only because it sits inside an async orchestrator path reached by every endgames dashboard load; worth revisiting if wall-clock latency becomes an issue.

**Fix:** Deferred — not a correctness issue. If revisited, maintain `opp_sum`/`opp_count` as running totals alongside `endgame_window` and update on both append and trim.

### IN-04: `getComboColors` / `getComboLabel` accept `string` instead of `EloComboKey`

**File:** `frontend/src/components/charts/EndgameEloTimelineSection.tsx:44-50`
**Issue:** The signatures widen the input type unnecessarily:
```ts
function getComboColors(combo_key: string): { bright: string; dark: string } {
  return ELO_COMBO_COLORS[combo_key as EloComboKey] ?? FALLBACK_COMBO_COLOR;
}
```
All call sites pass `combo.combo_key` which is already typed as `EloComboKey` from `EndgameEloTimelineCombo`. Taking `string` forces the `as EloComboKey` cast and hides any future drift (e.g. if a caller passes a raw string that genuinely isn't a valid key, the fallback silently kicks in).

**Fix:** Accept the narrow type and keep the fallback only for defensive runtime handling at boundaries:
```ts
function getComboColors(combo_key: EloComboKey): { bright: string; dark: string } {
  return ELO_COMBO_COLORS[combo_key];
}
```
The `ELO_COMBO_COLORS` record is already exhaustively keyed on `EloComboKey`, so the fallback becomes unreachable for any type-checked caller.

### IN-05: `dict[int, list[Row[Any]]]` comment references key safety but comment is in wrong file

**File:** `app/repositories/endgame_repository.py:447`
**Issue:** `_ENDGAME_CLASS_INTS = range(1, 7)` is defined as a `range` object but annotated comment above says "Integer values for all six endgame classes". Using `range(1, 7)` as a dict key source works, but `list(range(1, 7))` or an explicit tuple would be more intention-revealing and type-stable (ty may widen `range` to `Iterable[int]` in some contexts). Minor consistency nit.

**Fix:**
```python
# Integer values for all six endgame classes — used in per-type timeline queries.
# Avoids importing from endgame_service which would create a circular import.
_ENDGAME_CLASS_INTS: tuple[int, ...] = (1, 2, 3, 4, 5, 6)
```

---

_Reviewed: 2026-04-18_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
