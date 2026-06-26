---
phase: 126-comparison-stats-frontend
reviewed: 2026-06-18T00:00:00Z
depth: standard
files_reviewed: 18
files_reviewed_list:
  - app/repositories/library_repository.py
  - app/repositories/query_utils.py
  - app/routers/library.py
  - app/schemas/library.py
  - app/services/library_service.py
  - frontend/src/api/client.ts
  - frontend/src/components/filters/FilterPanel.tsx
  - frontend/src/components/filters/LibraryFilterPanel.tsx
  - frontend/src/components/library/FlawCard.tsx
  - frontend/src/components/library/FlawStatsPanel.tsx
  - frontend/src/components/library/TacticComparisonGrid.tsx
  - frontend/src/components/library/TacticMotifChip.tsx
  - frontend/src/components/results/LibraryGameCard.tsx
  - frontend/src/hooks/useLibrary.ts
  - frontend/src/lib/tacticComparisonMeta.ts
  - frontend/src/lib/tacticMotifDefinitions.ts
  - frontend/src/lib/theme.ts
  - frontend/src/types/library.ts
findings:
  critical: 0
  warning: 2
  info: 4
  total: 6
status: issues_found
---

# Phase 126: Code Review Report

**Reviewed:** 2026-06-18
**Depth:** standard
**Files Reviewed:** 18
**Status:** issues_found

## Summary

Phase 126 introduces the tactic-motif comparison grid, per-flaw motif chips, and a beta-gated motif family filter. The backend follows the established `flaw-comparison` mirror pattern closely, and the frontend correctly gates all new surfaces on `user?.beta_enabled`. Type safety, sentry capture, and IDOR prevention are all in order.

Two warnings surfaced during the review. One is a defense-in-depth deviation from the established T-108-07 security pattern (missing `user_id` scoping in the tactic EXISTS subquery). The other is a logic inconsistency: the gate counter ignores the `tactic_families` filter, so `analyzed_n` in the response no longer represents the actual game set used to compute the comparison bullets when that filter is active.

No critical issues were found.

## Warnings

### WR-01: tactic_exists in query_utils missing user_id scope (T-108-07 deviation)

**File:** `app/repositories/query_utils.py:216-221`

**Issue:** The correlated EXISTS added for the `tactic_families` filter omits `_GameFlaw.user_id == user_id` from its WHERE clause:

```python
tactic_exists = _exists(
    _select(_GameFlaw.ply).where(
        _GameFlaw.game_id == Game.id,        # present
        _GameFlaw.tactic_motif.in_(motif_ints),
        # _GameFlaw.user_id == user_id       ← missing
    )
)
```

The analogous `flaw_exists_from_table` in `library_repository.py` (line 222-226) explicitly includes `GameFlaw.user_id == user_id` and cites T-108-07 as the rationale ("scoping requires an authenticated user_id").

The missing clause is not an exploitable vulnerability in isolation because `game_id` is a globally unique PK on the `games` table and the outer query is already filtered to `Game.user_id == user_id`. However, it deviates from the established defense-in-depth pattern and could become a real leak if the `game_flaws` table is ever denormalized or the outer query restructured. `user_id` is already available in `apply_game_filters` (passed from `_filtered_games_base`) — the fix is a one-liner.

**Fix:**

```python
tactic_exists = _exists(
    _select(_GameFlaw.ply).where(
        _GameFlaw.game_id == Game.id,
        _GameFlaw.user_id == user_id,   # T-108-07: scope to authenticated user
        _GameFlaw.tactic_motif.in_(motif_ints),
    )
)
```

Note: `user_id` is always provided to `apply_game_filters` via `_filtered_games_base` (line 916 of `library_repository.py`), so a `None` guard is not required here, but adding a guard matching the flaw_exists pattern would be more consistent.

---

### WR-02: analyzed_n in TacticComparisonResponse does not reflect tactic_families filter

**File:** `app/services/library_service.py:1319-1336`

**Issue:** `get_tactic_comparison` builds `_filter_kwargs` without `tactic_families`, then passes it to `count_filtered_and_analyzed` for the gate check. The actual data query (`fetch_tactic_comparison`) does include `tactic_families`. This means:

- When `tactic_families` is set (e.g. only "fork" games), `analyzed_n` in the response reflects the full filtered set (all families), but the CI and rates are computed only over games that also contain a tactic in the selected families.
- The UI renders `GateCTA` based on `analyzed_n`/`analyzed_gate` and the section copy refers to the analyzed_n as the basis for the comparison. Both are misleading when the actual computation basis is smaller.

Contrast with `get_flaw_comparison` (line 1158): `_filter_kwargs` includes `flaw_severity`, ensuring `analyzed_n` matches the exact set used for bullets. The docstring on `count_filtered_and_analyzed` (lines 1035-1038) explicitly says "passes flaw_severity, so analyzed_n matches the set the bullets aggregate over."

The symptom: a user with 25 analyzed games total and 3 games containing fork flaws selects the "fork" family filter. `analyzed_n` shows 25 (above gate), the comparison proceeds, but the CI is computed over 3 game-deltas. The section header shows no indication that the comparison is over a narrow subset.

**Fix:** Include `tactic_families` in `_filter_kwargs`, and add `tactic_families` as an accepted parameter in `count_filtered_and_analyzed` (passing it through to `_filtered_games_base`). This mirrors how `flaw_severity` gates the count to the same set the bullets aggregate over.

```python
# In get_tactic_comparison, include tactic_families in _filter_kwargs:
_filter_kwargs: dict[str, Any] = dict(
    time_control=time_control,
    platform=platform,
    rated=rated,
    opponent_type=opponent_type,
    from_date=from_date,
    to_date=to_date,
    flaw_severity=flaw_severity,
    opponent_gap_min=opponent_gap_min,
    opponent_gap_max=opponent_gap_max,
    color=color,
    tactic_families=tactic_families,   # ← add this
)
```

And add `tactic_families: Sequence[str] | None = None` to `count_filtered_and_analyzed`'s signature, threading it through to `_filtered_games_base`.

---

## Info

### IN-01: test_significant_gap_first does not assert ranking order

**File:** `tests/services/test_tactic_comparison_service.py:239-272`

**Issue:** The test name and docstring claim to verify that "bullets with significant gaps rank before non-significant." The test seeds many fork events on the player side to create a significant gap, then asserts only:

```python
assert len(fork_bullets) <= 1  # at most one fork bullet
```

It never asserts that the fork bullet is at `result.bullets[0]` or that it precedes non-significant bullets. The ranking logic in `_compute_tactic_bullets` (`_sort_key`) is untested.

**Fix:** After seeding significant fork data, assert the fork bullet appears first:

```python
assert result.bullets[0].family == "fork"  # significant gap ranked first
```

Alternatively, also assert `fork_bullet.ci_low is not None and fork_bullet.ci_low > 0`.

---

### IN-02: Redundant falsy check on tactic_by_ply dict

**File:** `app/services/library_service.py:388`

**Issue:** The call site passes `tactic_by_ply=tactic_by_ply if tactic_by_ply else None`. An empty `dict` `{}` is falsy in Python, so when all flaws fall below the confidence threshold `tactic_by_ply={}` is treated as `None`. Both `{}` and `None` produce identical results in `_build_eval_series` (the `if tactic_by_ply is not None:` check returns the same outcome either way), but the conditional conflates two distinct sentinel semantics: "we looked and found nothing" vs "we never looked." This creates a subtle readability trap.

**Fix:** Either pass the dict directly (empty dict is safe) or be explicit:

```python
# Option A: just pass the dict — _build_eval_series handles {} correctly
eval_series_val, flaw_marker_val, phase_transition_val = _build_eval_series(
    game, positions, tactic_by_ply=tactic_by_ply
)

# Option B: explicit None sentinel for the no-qualifying-flaws case (keep current semantics but comment)
eval_series_val, flaw_marker_val, phase_transition_val = _build_eval_series(
    game, positions, tactic_by_ply=tactic_by_ply or None  # {} → None: both mean "no chips to render"
)
```

---

### IN-03: Test fixture for TacticComparisonGrid violates FilterState type contract

**File:** `frontend/src/components/library/__tests__/TacticComparisonGrid.test.tsx:40-49`

**Issue:** `DEFAULT_FILTERS` is annotated as `FilterState` but is missing three required fields (`matchSide`, `customRange`, `color`) and sets `opponentStrength: null` instead of `OpponentStrengthRange`. TypeScript does not catch this because test files are excluded from `tsconfig.app.json` compilation (`"exclude": ["src/**/*.test.ts", "src/**/*.test.tsx"]`). The test passes because `TacticComparisonGrid` only reads `filters.tacticFamilies`, but the fixture silently violates the contract.

**Fix:** Import `DEFAULT_FILTERS` from `FilterPanel` or populate all required fields:

```typescript
import { DEFAULT_FILTERS } from '@/components/filters/FilterPanel';
// or add the missing fields manually
```

---

### IN-04: Duplicate FilterField union type definition in LibraryFilterPanel

**File:** `frontend/src/components/filters/LibraryFilterPanel.tsx:15`

**Issue:** `LibraryFilterPanel.tsx` re-declares `FilterField` locally instead of importing it from `FilterPanel.tsx`. The file comment acknowledges: "Using the same literal type as FilterPanel's internal FilterField union." This phase correctly added `'tacticMotif'` to both copies, but future FilterPanel extensions could silently diverge. This is a pre-existing technical debt that this phase extended.

**Fix:** Export `FilterField` from `FilterPanel.tsx` and import it in `LibraryFilterPanel.tsx`:

```typescript
// FilterPanel.tsx — change from `type` to exported:
export type FilterField = 'timeControl' | ... | 'tacticMotif';

// LibraryFilterPanel.tsx — replace the local re-declaration:
import type { FilterField } from '@/components/filters/FilterPanel';
```

---

_Reviewed: 2026-06-18_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
