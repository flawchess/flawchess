---
phase: 92-custom-date-range-filter
reviewed: 2026-05-22T00:00:00Z
depth: standard
files_reviewed: 62
files_reviewed_list:
  - app/repositories/endgame_repository.py
  - app/repositories/openings_repository.py
  - app/repositories/query_utils.py
  - app/repositories/stats_repository.py
  - app/routers/endgames.py
  - app/routers/insights.py
  - app/routers/stats.py
  - app/schemas/insights.py
  - app/schemas/opening_insights.py
  - app/schemas/openings.py
  - app/schemas/stats.py
  - app/services/endgame_service.py
  - app/services/insights_service.py
  - app/services/opening_insights_service.py
  - app/services/openings_service.py
  - app/services/stats_service.py
  - app/services/insights_llm.py
  - frontend/knip.json
  - frontend/package.json
  - frontend/src/api/client.ts
  - frontend/src/components/charts/__tests__/EndgameEloTimelineSection.test.tsx
  - frontend/src/components/filters/CustomRangeDrawer.tsx
  - frontend/src/components/filters/CustomRangePopover.tsx
  - frontend/src/components/filters/FilterPanel.tsx
  - frontend/src/components/insights/OpeningInsightsBlock.test.tsx
  - frontend/src/components/insights/OpeningInsightsBlock.tsx
  - frontend/src/components/insights/__tests__/EndgameInsightsBlock.test.tsx
  - frontend/src/components/ui/button.tsx
  - frontend/src/components/ui/calendar.tsx
  - frontend/src/components/ui/drawer.tsx
  - frontend/src/hooks/__tests__/useEndgameInsights.test.tsx
  - frontend/src/hooks/__tests__/useOpeningInsights.test.tsx
  - frontend/src/hooks/useEndgameInsights.ts
  - frontend/src/hooks/useEndgames.ts
  - frontend/src/hooks/useNextMoves.ts
  - frontend/src/hooks/useOpeningInsights.ts
  - frontend/src/hooks/useOpenings.ts
  - frontend/src/hooks/useStats.ts
  - frontend/src/lib/recency.ts
  - frontend/src/lib/__tests__/recency.test.ts
  - frontend/src/pages/GlobalStats.tsx
  - frontend/src/pages/Openings.tsx
  - frontend/src/types/api.ts
  - frontend/src/types/position_bookmarks.ts
  - frontend/src/types/stats.ts
  - tests/repositories/test_opening_insights_repository.py
  - tests/routers/test_insights_openings.py
  - tests/services/test_insights_llm.py
  - tests/services/test_insights_service.py
  - tests/test_aggregation_sanity.py
  - tests/test_endgame_repository.py
  - tests/test_endgame_service.py
  - tests/test_insights_router.py
  - tests/test_insights_schema.py
  - tests/test_integration_routers.py
  - tests/test_openings_repository.py
  - tests/test_openings_service.py
  - tests/test_openings_time_series.py
  - tests/test_query_utils.py
  - tests/test_stats_repository_phase_entry.py
  - tests/test_stats_repository.py
  - tests/test_stats_router.py
  - tests/test_stats_service.py
findings:
  critical: 0
  warning: 3
  info: 5
  total: 8
status: fixed
fixes:
  - id: WR-01
    status: fixed
    fix_commits:
      - 59dce407
      - fd113a23
  - id: WR-02
    status: fixed
    fix_commits:
      - 588add37
  - id: WR-03
    status: fixed
    fix_commits:
      - 71fb6336
---

# Phase 92: Code Review Report

**Reviewed:** 2026-05-22T00:00:00Z
**Depth:** standard
**Files Reviewed:** 62
**Status:** fixed (all 3 warnings resolved 2026-05-22)

## Summary

The Phase 92 `recency` → `from_date`/`to_date` rename appears correctly executed
across all backend layers and TanStack Query hooks. The hot-path boundary
contract (`played_at >= from_date`, `played_at < to_date + 1 day`) is consistent
between `query_utils.apply_game_filters` and the duplicated copy in
`openings_repository._build_base_query`, both Pydantic body `model_validator`s
and inline `HTTPException` paths cover the `from_date > to_date` guard, the
insights router gate keys on `filters.from_date is not None or filters.to_date
is not None` (not the deleted `recency != "all_time"` predicate), and the
internal LLM `last_3mo` window correctly resolves to `today - 90d` with
`to_date=None`. New boundary tests in `test_integration_routers.py` and
`test_insights_openings.py` exercise the inclusive-from / inclusive-to /
day-after-to / no-filter / 422-on-reversed paths against real seeded games.

Defects found are non-blocking: one real state-sync bug in `CustomRangeDrawer`
that mishandles parent-driven `value` resets while the component stays mounted,
plus stale docstrings that still reference the deleted `recency` /
`recency_cutoff` concepts, plus a dead `open` prop on `CustomRangePopover`, and
a small minimum-font-size deviation that this phase inherited rather than
authored.

## Warnings

### WR-01: `CustomRangeDrawer` `localRange` never resyncs to `value` prop

**Status:** fixed (commits 59dce407, fd113a23) — Initial useEffect resync hit
eslint's `react-hooks/set-state-in-effect`; switched to React's
adjusting-state-on-prop-change pattern (useState + compare during render).

**File:** `frontend/src/components/filters/CustomRangeDrawer.tsx:48-50`

**Issue:** `localRange` is initialised from `value` via `useState`'s lazy
initialiser, but there is no `useEffect` watching `value` to resync. The drawer
is rendered unconditionally by `FilterPanel.tsx` (line 269-277) — it is NOT
unmounted when closed; vaul's `NestedRoot` keeps the React subtree alive even
while `open=false`. Consequence: if `filters.customRange` mutates from a path
other than this drawer's Apply button (e.g. the user taps "Reset Filters" in
the parent panel, which clears `customRange` to `null`; or a Popover commit
from the desktop branch races with mobile breakpoint flipping), the drawer
still shows the stale in-progress selection on its next open. Reopening then
Apply re-commits that stale range and silently overrides the Reset.

The desktop sibling `CustomRangePopover` is unaffected because it derives
`selected` directly from `value` on every render (no local state).

**Fix:**
```tsx
import { useEffect, useState } from 'react';
...
const [localRange, setLocalRange] = useState<DateRange | undefined>(
  value ? { from: value.from, to: value.to } : undefined,
);

// Resync local in-progress selection whenever the committed value changes
// from outside (Reset Filters, sibling popover commit on mobile/desktop
// breakpoint flip). Preserves D-08 backdrop-dismiss semantics because the
// effect only fires when the *committed* value changes, not on every keystroke.
useEffect(() => {
  setLocalRange(value ? { from: value.from, to: value.to } : undefined);
}, [value?.from?.getTime(), value?.to?.getTime(), value === null]);
```
(Compare on `getTime()` rather than reference so `presetToDates`-style
memoised ranges don't trigger spurious resets.)

### WR-02: Stale `recency` / `recency_cutoff` references in service docstrings

**Status:** fixed (commit 588add37) — All flagged docstrings rewritten to refer
to `from_date`/`to_date`. Internal `Window` literals in `endgame_zones.py`
and `insights_llm.py` were left alone (legitimate per the finding note).

**File:** `app/services/insights_service.py:132-137`, `app/services/insights_llm.py:421`, `app/services/endgame_service.py:2501`, `app/schemas/openings.py:155`, `app/repositories/stats_repository.py:153,211`

**Issue:** Several backend docstrings still describe the now-deleted
`recency` parameter. The code itself is correct — these are doc-only stale
references — but they actively mislead future readers: `compute_findings`'s
docstring (lines 132-137) claims it calls `get_endgame_overview` "with
`recency=None`, then `recency="3months"`" and that the two-window shape is
"independent of `filter_context.recency`". The actual code passes
`from_date=None` then `from_date=date.today() - 90d`, and `FilterContext` has
no `recency` field anymore (`app/schemas/insights.py` line 135-136 carries
`from_date` / `to_date`). Similar issue in `insights_llm._format_filters_for_prompt`
("The router enforces defaults for `recency`, ...") and in three repository
docstrings ("Optionally filtered by ... recency, ...").

**Fix:** Replace each occurrence of `recency` (where it describes the deleted
wire-format param) with `from_date / to_date`. Example for
`insights_service.py:132-137`:
```python
"""...
Makes two sequential calls to `endgame_service.get_endgame_overview`
(all_time window with from_date=None, to_date=None, then last_3mo window
with from_date=date.today() - 90d, to_date=None) on the same
`AsyncSession` — never concurrent gather, per CLAUDE.md §Critical
Constraints. The two-window shape is independent of the user's dashboard
date filter (filter_context.from_date / .to_date): the user's range is
forwarded only to the repositories, not the LLM-window split (RESEARCH.md
§Pitfall 4).
"""
```
And in `app/repositories/stats_repository.py` lines 153 and 211, change
`"Optionally filtered by platform, recency, opponent_type, ..."` to
`"Optionally filtered by platform, from_date/to_date, opponent_type, ..."`.

(Note: legitimate internal `Window` literals like `"all_time"` / `"last_3mo"`
in `app/services/endgame_zones.py` and `insights_llm.py` are NOT stale —
they're the LLM-window concept, distinct from the deleted wire-format
preset. Leave those alone.)

### WR-03: `CustomRangePopoverProps.open` declared but unused

**Status:** fixed (commit 71fb6336) — Dropped the `open` prop from the
interface and removed the `open={customOpen && !isMobile}` line at the
FilterPanel callsite. The Popover open state remains correctly managed by the
parent `<Popover open={...}>` wrapper.

**File:** `frontend/src/components/filters/CustomRangePopover.tsx:53,66-70`

**Issue:** The interface requires `open: boolean` (line 53) so all callers
must pass it, but the component destructures only `value`, `onChange`, and
`onOpenChange` (line 66-70) — `open` is never read. `FilterPanel.tsx` line
263 passes `open={customOpen && !isMobile}` to satisfy the type contract,
but that value has no effect on render. The actual open state lives on the
parent `<Popover open={...}>` wrapper (line 222). At best this is dead API
surface that confuses readers about how to wire the popover; at worst, a
future change might assume the prop is load-bearing.

**Fix:** Either drop the prop from the interface and the FilterPanel
callsite:
```tsx
interface CustomRangePopoverProps {
  value: { from?: Date; to?: Date } | null;
  onChange: (range: { from?: Date; to?: Date } | null) => void;
  onOpenChange: (open: boolean) => void;
}
```
…and at the callsite remove `open={customOpen && !isMobile}` from
`<CustomRangePopover ...>`. Or, if there is intent to use `open` (e.g.
defensive logging), destructure it and add a comment explaining the
forward-compat reservation.

## Info

### IN-01: Date-filter logic duplicated between `apply_game_filters` and `openings_repository._build_base_query`

**File:** `app/repositories/openings_repository.py:111-114` vs `app/repositories/query_utils.py:68-73`

**Issue:** `_build_base_query` reimplements the same `played_at >= from_date`
/ `played_at < to_date + 1 day` filter inline rather than delegating to
`apply_game_filters`. The two are currently identical, but the duplication
violates CLAUDE.md's "Shared Query Filters" rule and is a future-drift
hazard: if the boundary semantics ever change (e.g. UTC normalisation,
client_timezone param per D-16), both copies need to be updated in lockstep.

This duplication pre-exists Phase 92 — the rename simply mirrored the old
`recency_cutoff` predicate. Calling it out as INFO so the next pass-through
of `openings_repository.py` can lift the date branch (and the rest of
`_build_base_query`'s filter block) onto `apply_game_filters`.

**Fix:** Refactor `_build_base_query` to call `apply_game_filters` for the
shared filter cluster (time_control / platform / rated / opponent_type /
from_date / to_date / color / opponent_gap_*). Keep the
position-vs-all-games join branching as the only logic local to this
helper. Out of scope for Phase 92 — track as a separate small task.

### IN-02: `apply_game_filters` doc inverts the boundary semantics for `to_date`

**File:** `app/repositories/query_utils.py:34-36`

**Issue:** The docstring on `to_date` reads "Include games played on or
before this date (inclusive, shifted +1 day in SQL so `played_at < to_date
+ 1 day` covers the whole day)". The first phrase ("on or before this
date") could be misread as "played_at <= to_date 00:00 UTC" (which would
EXCLUDE end-of-day games). The parenthesised clarification is correct,
but the lead-in primes the wrong mental model.

**Fix:** Reword to lead with the inclusive-full-day semantics:
```python
to_date: Include games played any time on this calendar date or earlier
         (full-day inclusive — the SQL predicate is
         ``played_at < to_date + 1 day`` so a game at 23:59 UTC on
         ``to_date`` still matches). None = no upper bound.
```

### IN-03: `OpeningInsightsRequest` and other request schemas accept negative dates with no min bound

**File:** `app/schemas/opening_insights.py:29-30`, `app/schemas/openings.py:39-40,227-228`, `app/schemas/stats.py:133-134`, `app/schemas/insights.py:135-136`

**Issue:** All `from_date`/`to_date` fields are typed `datetime.date | None`
with only the cross-field `from_date <= to_date` validator. They accept any
year Pydantic parses, including `0001-01-01` or `9999-12-31`. The current
SQL is tolerant of those values (they just match zero games), but it
allows the frontend to construct (or a malicious client to submit) a
request that bypasses the intended UI presets without any server-side
sanity floor.

Severity is INFO because the SQL filter does the right thing on degenerate
inputs and the UI Calendar is bounded; flagging only as defense-in-depth.

**Fix:** Optional — add a `field_validator` that rejects dates more than,
say, 20 years before/after `date.today()`. Likely YAGNI; surface as a note
rather than a required change.

### IN-04: Test mock returns response missing required Pydantic fields

**File:** `frontend/src/hooks/__tests__/useEndgameInsights.test.tsx:53-64`

**Issue:** The mock for `apiClient.post` returns a `report` payload with
only `overview`, `sections`, `model_used`, and `prompt_version`. The
real `EndgameInsightsReport` Pydantic model requires `player_profile`
(min_length=1) and `recommendations` (min_length=2). The frontend
`EndgameInsightsResponse` TS interface (frontend/src/types/insights.ts:34,41)
also requires both fields. Since the test mocks at the axios layer there's
no runtime validation, but the mock now diverges from the schema and will
silently miss any future change that depends on those fields being
present.

Independent of Phase 92 — the mock predates this phase — but worth
flagging while reviewing the hook test that ships with it.

**Fix:** Add `player_profile: 'profile'` and `recommendations: ['rec one',
'rec two']` to the mocked report so the fixture matches the contract.

### IN-05: `insights_service._series_for_endgame_elo_combo` swallows window arg

**File:** `app/services/insights_service.py:627-629,1162-1193`

**Issue:** `_findings_score_timeline` constructs three timeseries by
calling `_weekly_points_to_time_points(... , "last_3mo")` with a
hard-coded string even when the enclosing function's `window` parameter
is `"all_time"` (line 627-629). The docstring on `_findings_score_timeline`
explains this is intentional ("Granularity stays WEEKLY in both windows
... `_series_granularity` in insights_llm.py pins this explicitly for
subsection_id == 'score_timeline'"), so behavior is correct, but the
hard-coded `"last_3mo"` literal is brittle: if someone refactors
`_weekly_points_to_time_points` to switch on a different sentinel, the
score-timeline series silently changes shape. Out of scope for Phase 92
but worth a clearer signal.

**Fix:** Introduce a named constant or sentinel for "pass-through grain"
in `_weekly_points_to_time_points` rather than overloading the `Window`
literal. Out of scope; INFO only.

---

_Reviewed: 2026-05-22T00:00:00Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
