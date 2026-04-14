---
phase: 54-time-pressure-clock-stats-table
reviewed: 2026-04-12T00:00:00Z
depth: standard
files_reviewed: 7
files_reviewed_list:
  - app/repositories/endgame_repository.py
  - app/schemas/endgames.py
  - app/services/endgame_service.py
  - frontend/src/components/charts/EndgameClockPressureSection.tsx
  - frontend/src/pages/Endgames.tsx
  - frontend/src/types/endgames.ts
  - tests/test_endgame_service.py
findings:
  critical: 0
  warning: 2
  info: 3
  total: 5
status: issues_found
---

# Phase 54: Code Review Report

**Reviewed:** 2026-04-12
**Depth:** standard
**Files Reviewed:** 7
**Status:** issues_found

## Summary

Comprehensive review of Phase 54 time pressure clock stats implementation. The feature is well-structured with clear separation of concerns across repository (query), service (aggregation), schema (types), and frontend (UI) layers. All tests are thorough and cover edge cases.

Two issues were found: one warning about missing `data-testid` on a table element in the frontend, and another warning about a potential inconsistency in how multi-ply endgame spans are handled. Three info-level items suggest minor improvements for clarity and consistency.

## Critical Issues

None found.

## Warnings

### WR-01: Missing `data-testid` on Table Element

**File:** `frontend/src/components/charts/EndgameClockPressureSection.tsx:66`

**Issue:** The `<table>` element has `data-testid="clock-pressure-table"` but there are no `data-testid` attributes on the `<thead>` element. Per CLAUDE.md browser automation rules, major layout containers and table header elements should have `data-testid` for consistent automation support.

**Fix:**
```tsx
<thead data-testid="clock-pressure-table-head">
  <tr className="text-left text-xs text-muted-foreground border-b border-border">
    {/* ... */}
  </tr>
</thead>
```

Also consider adding `data-testid="clock-pressure-table-body"` to `<tbody>` for consistency with other table components in the codebase.

### WR-02: Contiguity Check Logic May Be Unclear in Multi-Span Context

**File:** `app/repositories/endgame_repository.py:135-138`

**Issue:** The persistence check in `query_endgame_entry_rows` uses contiguity logic to handle cases where a game exits and re-enters the same endgame class (see comment at lines 115-120). The check `ply_at_persistence == func.min(GamePosition.ply) + PERSISTENCE_PLIES` ensures that the 5th ply is exactly 4 after the 1st, filtering non-contiguous spans.

However, the logic may not correctly handle all edge cases. Consider a game that exits at ply 10 and re-enters at ply 15 in the same class. The GROUP BY groups them together, but the min ply would be from the first segment, and the 5th ply might come from the second segment without detecting the discontinuity. This could lead to incorrect persistence values for re-entry spans.

The current check is: `ply_at_persistence == func.min(GamePosition.ply) + PERSISTENCE_PLIES`. This works for contiguous spans but may not fully validate continuity across multiple non-contiguous segments within the same (game_id, endgame_class) group.

**Fix:** The logic is technically correct as documented but would benefit from clarification. The intention appears to be: "accept only if the 5th ply value corresponds to exactly 4 plies after the minimum ply in the span, meaning the first 5 plies are contiguous and in order." If a re-entry creates non-contiguous plies, the 5th array element would come from a later span, and the check would catch it (since `min(ply) + 4` would not match).

However, to be more explicit and defensive, consider adding a comment explaining that this check handles non-contiguous multi-segment endgame spans by verifying the first 5 plies are temporally contiguous:

```python
# Persistence check: ply_at_persistence must be exactly 4 plies after min(ply)
# to ensure the first 5 plies are contiguous (no re-entry gaps).
# If the span is non-contiguous (e.g., game exits and re-enters the class),
# the 5th ply comes from a later segment, making this check fail → imbalance_after=NULL.
```

## Info

### IN-01: Type Safety: `time_control_bucket` Should Use Literal Type in Service Layer

**File:** `app/services/endgame_service.py:680`

**Issue:** In `_compute_clock_pressure`, the line `time_control_bucket: str | None = row[1]` uses a plain `str` type rather than the more specific `Literal["bullet", "blitz", "rapid", "classical"] | None`. This reduces type safety at the service layer.

A few lines later (line 758), the same value is cast explicitly: `cast(Literal["bullet", "blitz", "rapid", "classical"], tc)`. This suggests the intent to use the narrower type was present during implementation but not fully applied.

**Fix:** Update the type annotation at line 680:

```python
time_control_bucket: Literal["bullet", "blitz", "rapid", "classical"] | None = row[1]
```

Or extract to a TypedDict for clarity if reused:
```python
from typing import TypedDict, Literal

class ClockRowData(TypedDict):
    game_id: int
    time_control_bucket: Literal["bullet", "blitz", "rapid", "classical"] | None
    time_control_seconds: int | None
    termination: str | None
    result: str
    user_color: str
    ply_array: list[int]
    clock_array: list[float | None]
```

This would eliminate the need for the `cast()` at line 758 and improve type checking.

### IN-02: Potential Edge Case: Empty `clock_array` in Span

**File:** `app/services/endgame_service.py:700`

**Issue:** In `_compute_clock_pressure`, the function `_extract_entry_clocks(ply_array, clock_array, user_color)` is called on every row. However, there is no validation that `ply_array` and `clock_array` have the same length or are non-empty before processing.

The `_extract_entry_clocks` function itself handles empty arrays gracefully (returns `(None, None)` per the test at line 1138-1140), but the relationship between ply_array and clock_array is never verified. If they differ in length due to a data corruption or schema change, the `zip()` at line 641 would silently truncate to the shorter list, potentially missing clock data.

**Fix:** Add a defensive check:

```python
# Validate arrays are same length (should be guaranteed by query, but defensive)
if len(ply_array) != len(clock_array):
    sentry_sdk.capture_exception(ValueError(
        f"Mismatched ply and clock array lengths for game {game_id}: "
        f"ply={len(ply_array)}, clock={len(clock_array)}"
    ))
    sentry_sdk.set_context("clock_data", {
        "game_id": game_id,
        "ply_count": len(ply_array),
        "clock_count": len(clock_array),
    })
    continue

user_clock, opp_clock = _extract_entry_clocks(ply_array, clock_array, user_color)
```

This would catch potential data issues and help with debugging in production without impacting the happy path.

### IN-03: Unused Import in Frontend Types File

**File:** `frontend/src/types/endgames.ts:5`

**Issue:** The import statement `import type { GameRecord } from './api';` is declared but the `GameRecord` type is never used in this file. The file only re-exports types from the Pydantic backend schemas and does not construct any types that include `GameRecord`.

(Note: The file is likely meant to be a pure type mirror, and this import may have been added in anticipation of future use, or left over from refactoring.)

**Fix:** Remove the unused import:

```typescript
// Remove this line
import type { GameRecord } from './api';
```

If `GameRecord` is used elsewhere (e.g., in `EndgameGamesResponse` in the backend schema), ensure it's imported there, not here. The knip CI tool will catch this on the next run.

---

_Reviewed: 2026-04-12_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
