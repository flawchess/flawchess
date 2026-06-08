---
phase: 110-flaw-tag-taxonomy-overhaul-rename-impact-family-rebuild-tool
reviewed: 2026-06-08T09:00:00Z
depth: standard
files_reviewed: 35
files_reviewed_list:
  - alembic/versions/20260607_alter_game_flaws_impact_cols.py
  - app/models/game_flaw.py
  - app/repositories/game_flaws_repository.py
  - app/repositories/library_repository.py
  - app/repositories/query_utils.py
  - app/services/flaws_service.py
  - app/services/library_service.py
  - app/schemas/library.py
  - scripts/gen_flaw_thresholds_ts.py
  - frontend/src/generated/flawThresholds.ts
  - frontend/src/lib/tagDefinitions.ts
  - frontend/src/lib/theme.ts
  - frontend/src/types/library.ts
  - frontend/src/hooks/useFlawFilterStore.ts
  - frontend/src/components/filters/FlawFilterControl.tsx
  - frontend/src/components/library/TagChip.tsx
  - frontend/src/components/library/FlawStatsPanel.tsx
  - frontend/src/components/library/FlawStatsBand.tsx
  - frontend/src/components/library/FlawTagDistribution.tsx
  - frontend/src/components/library/FlawTrendChart.tsx
  - frontend/src/components/library/LibraryGameCard.tsx
  - frontend/src/components/library/FlawsTab.tsx
  - frontend/src/pages/LibraryPage.tsx
  - frontend/src/components/filters/__tests__/FlawFilterControl.test.tsx
  - tests/services/test_flaws_service.py
  - tests/repositories/test_library_repository.py
  - tests/repositories/test_game_flaws_repository.py
  - tests/services/test_library_service.py
  - app/models/game.py
  - app/models/game_position.py
  - app/repositories/flaws_repository.py
  - frontend/src/components/library/TagChip.tsx
  - frontend/src/lib/tagDefinitions.ts
  - frontend/src/components/filters/FlawFilterControl.tsx
  - frontend/src/components/filters/__tests__/FlawFilterControl.test.tsx
findings:
  critical: 0
  warning: 4
  info: 3
  total: 7
status: issues_found
---

# Phase 110: Code Review Report

**Reviewed:** 2026-06-08T09:00:00Z
**Depth:** standard
**Files Reviewed:** 35
**Status:** issues_found

## Summary

Phase 110 replaces the outcome-dependent impact family (while-ahead / result-changing) with an outcome-independent two-rung ladder (reversed / squandered) and renames tempo tags (impatient→hasty, considered→unrushed). The core classification logic in `_classify_impact`, the column mapping in `flaw_record_to_row`, the 12-tuple order alignment between `fetch_stats_aggregates` and `library_service.py`, the Alembic migration pattern, the filter clause wiring in `build_flaw_filter_clauses`, and the CI drift gate for `flawThresholds.ts` are all correct.

Four issues require attention before this ships:

- Two instances of the same hover-to-content popover flicker bug affect both TagChip and FlawFilterControl: moving the mouse from the trigger element into the popover content closes the popover immediately because `handleMouseLeave` calls `setOpen(false)` directly, and the content's `onMouseEnter` handler does not reopen it.
- The loading skeleton in FlawStatsPanel renders 4 placeholder cells but the data state renders 3 severity cells, producing a visible layout shift.
- A stale docstring in `apply_game_filters` misstates the semantics of `flaw_severity` filtering.

---

## Warnings

### WR-01: Hover-to-content popover immediately closes on mouse transition (TagChip)

**File:** `frontend/src/components/library/TagChip.tsx:115-117`

**Issue:** `handleMouseLeave` on the trigger `<span>` calls `setOpen(false)` unconditionally. When the mouse moves from the trigger into the portal-rendered `PopoverPrimitive.Content`, the span fires `onMouseLeave` first, closing the popover immediately. The content's `onMouseEnter` handler (line 150-152) only clears the pending open-timeout; it does not call `setOpen(true)`, so the popover cannot recover. The net effect: users who try to read the definition popover by hovering over it see it flash closed as soon as they leave the chip boundary.

**Fix:** Introduce a `closeTimeout` ref to defer the close, and cancel it when the mouse enters the content:

```tsx
const hoverTimeout = React.useRef<ReturnType<typeof setTimeout> | null>(null);
const closeTimeout = React.useRef<ReturnType<typeof setTimeout> | null>(null);

const handleMouseEnter = () => {
  if (closeTimeout.current) clearTimeout(closeTimeout.current);
  hoverTimeout.current = setTimeout(() => setOpen(true), 100);
};

const handleMouseLeave = () => {
  if (hoverTimeout.current) clearTimeout(hoverTimeout.current);
  closeTimeout.current = setTimeout(() => setOpen(false), 80);
};

// In PopoverPrimitive.Content:
onMouseEnter={() => {
  if (hoverTimeout.current) clearTimeout(hoverTimeout.current);
  if (closeTimeout.current) clearTimeout(closeTimeout.current);
}}
onMouseLeave={handleMouseLeave}
```

---

### WR-02: Hover-to-content popover immediately closes on mouse transition (FlawFilterControl)

**File:** `frontend/src/components/filters/FlawFilterControl.tsx:109-112`

**Issue:** Identical root cause to WR-01. In `TagFilterButton`, `handleMouseLeave` on the `<button>` calls `setOpen(false)` directly (line 111). When the mouse moves from the button into the portal-rendered `PopoverPrimitive.Content`, the button fires `onMouseLeave`, closing the popover. The content's `onMouseEnter` (line 141-143) clears the open-timeout but cannot reopen the popover. Same user-visible flicker as WR-01.

**Fix:** Same deferred-close pattern as WR-01: add a `closeTimeout` ref, defer `setOpen(false)` by ~80ms in `handleMouseLeave`, and cancel it in the content's `onMouseEnter`.

```tsx
const closeTimeout = React.useRef<ReturnType<typeof setTimeout> | null>(null);

const handleMouseLeave = (): void => {
  if (hoverTimeout.current) clearTimeout(hoverTimeout.current);
  closeTimeout.current = setTimeout(() => setOpen(false), 80);
};

// In PopoverPrimitive.Content:
onMouseEnter={() => {
  if (hoverTimeout.current) clearTimeout(hoverTimeout.current);
  if (closeTimeout.current) clearTimeout(closeTimeout.current);
}}
onMouseLeave={handleMouseLeave}
```

---

### WR-03: Loading skeleton renders 4 cells; data state renders 3 severity cells

**File:** `frontend/src/components/library/FlawStatsPanel.tsx:152`

**Issue:** The loading skeleton uses `[...Array(4)].map(...)` to render 4 placeholder cells at line 152. When data loads, `FlawStatsBand` renders exactly 3 severity cells (Blunders, Mistakes, Inaccuracies — confirmed in `FlawStatsBand.tsx:30-44`). The skeleton is therefore one cell wider than the content it represents, producing a visible layout shift when data arrives and making the skeleton's width an inaccurate affordance for the loaded content.

**Fix:** Change the skeleton array size from 4 to 3:

```tsx
{[...Array(3)].map((_, i) => (
  <div
    key={i}
    className="flex-1 min-w-[120px] h-16 rounded border border-border"
    style={{ background: 'var(--color-charcoal)' }}
  />
))}
```

---

### WR-04: `apply_game_filters` docstring misstates `flaw_severity` semantics

**File:** `app/repositories/query_utils.py:46-50`

**Issue:** The docstring for the `flaw_severity` parameter (lines 46-50) states:

> "restrict to games containing >=1 flaw in game_flaws at that severity or worse (MIN-threshold)"

The actual implementation uses set-membership via an `IN` operator (through `build_flaw_filter_clauses`): games are included if they contain at least one flaw whose severity is in the provided set. There is no "worse than" escalation — passing `["mistake"]` does not also include blunders. The "MIN-threshold" description is a holdover from an earlier design and is factually wrong for the current code. A developer reading only the docstring would write incorrect callers.

**Fix:** Replace the stale docstring text:

```python
flaw_severity: When set (e.g. ["blunder"] or ["mistake"]), restrict to games
                 containing >=1 flaw in game_flaws with severity in the provided set
                 (exact membership — passing ["mistake"] does NOT include blunders).
                 None (default) leaves the statement unchanged —
                 all existing callers are unaffected.
                 Requires user_id (T-108-07: EXISTS must be user-scoped).
```

---

## Info

### IN-01: Wrong threshold comparison in test comment

**File:** `tests/services/test_flaws_service.py:1047`

**Issue:** The docstring comment states "0.78 < WINNING_LINE_ES (0.70) fails reversed entry." This is factually wrong on two levels: 0.78 is greater than 0.70, not less; and the test is correctly placed in the gap between `WINNING_LINE_ES` (0.70) and `FROM_WINNING_ES` (0.85). The line 1048 comment is correct ("0.78 < FROM_WINNING_ES (0.85) fails squandered entry"). The test logic itself passes correctly — only the comment at line 1047 is wrong.

**Fix:**

```python
# es_before=0.78 > WINNING_LINE_ES (0.70) passes reversed entry threshold,
# but es_after=0.45 > LOSING_LINE_ES (0.30), so reversed exit fails.
# es_before=0.78 < FROM_WINNING_ES (0.85) also fails squandered entry.
```

---

### IN-02: `# noqa: F401` on an import that IS used

**File:** `app/services/library_service.py:33`

**Issue:** Line 33 imports `_TEMPO_INT_TO_TAG` from `library_repository` with `# noqa: F401`, which suppresses the "imported but unused" warning. However, `_TEMPO_INT_TO_TAG` is used at line 269 in `_curate_chips_from_rows`. The suppression comment is misleading: it implies the import is dead code kept for a side-effect reason, when in fact it is a live, used import. This is likely a stale comment from a refactor that moved the usage into the file.

**Fix:** Remove the `# noqa: F401` comment:

```python
from app.repositories.library_repository import _TEMPO_INT_TO_TAG
```

---

### IN-03: Phase tags silently fall back to 'impact' color family in TagChip

**File:** `frontend/src/components/library/TagChip.tsx:37-41`

**Issue:** `getTagFamily` handles `'opening'`, `'middlegame'`, and `'endgame'` with a fallback `return 'impact'` (lines 37-41). The comment says "Phase tags are excluded by upstream curation (Phase 106)" — if that guarantee holds, this code is never reached. But if a phase tag does arrive (e.g., a regression in curation, a direct API call), the chip renders with impact family colors (orange/amber) and no icon error, silently producing a wrong visual. There is no assertion, log, or Sentry capture to signal the invariant violation.

**Fix:** Replace the silent fallback with an explicit unreachable assertion so violations are caught in development and Sentry in production:

```tsx
case 'opening':
case 'middlegame':
case 'endgame':
  // Phase tags are excluded by upstream curation (Phase 106).
  // If this branch is reached, the invariant has been violated.
  console.error(`TagChip: unexpected phase tag '${tag}' — curation failed`);
  return 'impact'; // safe visual fallback
```

---

_Reviewed: 2026-06-08T09:00:00Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
