---
phase: 109-per-card-expected-score-eval-chart-games-subtab
reviewed: 2026-06-07T14:30:00Z
depth: standard
files_reviewed: 10
files_reviewed_list:
  - app/repositories/library_repository.py
  - app/schemas/library.py
  - app/services/flaws_service.py
  - app/services/library_service.py
  - frontend/src/components/library/EvalChart.tsx
  - frontend/src/components/results/LibraryGameCard.tsx
  - frontend/src/lib/theme.ts
  - frontend/src/types/library.ts
  - tests/services/test_eval_chart_service.py
  - tests/test_library_router.py
findings:
  critical: 0
  warning: 3
  info: 2
  total: 5
status: issues_found
---

# Phase 109: Code Review Report

**Reviewed:** 2026-06-07T14:30:00Z
**Depth:** standard
**Files Reviewed:** 10
**Status:** issues_found

## Summary

The Phase 109 implementation is structurally sound. The key design contracts are honored: the chart line uses white-perspective ES via `eval_mate_to_expected_score`/`eval_cp_to_expected_score("white")`, flaw detection uses mover-POV drops via `_run_all_moves_pass` (D-01/D-04 separation correct), and mate handling in drop math follows `_ply_to_es`'s `MATE_CP_EQUIVALENT` path rather than the hard 1.0/0.0 path (Pitfall 3 correct). IDOR scoping in `fetch_page_eval_positions` applies `user_id` correctly (T-109-01). Opponent tag stripping (`miss`, `lucky-escape`) works through `_USER_FRAMED_TAGS`. Phase-transition logic (D-06 — no ply-0 line, at most two lines) is correct. All theme colors are imported from `theme.ts` with no hex/oklch literals in components. `noUncheckedIndexedAccess` narrowing is present where needed.

Three warnings and two info items were found: a dead prop in `EvalChart.tsx` that is declared, passed, but never read; silent last-write-wins collision behavior in `markerMap`; a dead import masked by `# noqa: F401`; an unsuppressed `as` type assertion on `user_color`; and a debug `print` left in a test.

## Warnings

### WR-01: `userColor` prop declared and passed to `EvalChart` but never read

**File:** `frontend/src/components/library/EvalChart.tsx:38`, `frontend/src/components/results/LibraryGameCard.tsx:290,327`

**Issue:** `EvalChartProps` declares `userColor: 'white' | 'black'` and both the desktop and mobile render paths in `LibraryGameCard` pass it:

```tsx
userColor={game.user_color as 'white' | 'black'}
```

However the `EvalChart` component destructures its props without including `userColor`:

```tsx
export function EvalChart({
  gameId,
  evalSeries,
  flawMarkers,
  phaseTransitions,
  heightClass = 'h-24',
}: EvalChartProps) {
```

The prop is silently discarded. `noUnusedParameters` does not catch props interface fields, so TypeScript will not surface this. The tooltip already determines "You/Opponent" from `marker.is_user` (which does not need `userColor`), so the prop genuinely has no current consumer. Callers incur a type-assertion cost (`as 'white' | 'black'`) for a prop that does nothing.

**Fix:** Either remove `userColor` from `EvalChartProps` and the two call sites in `LibraryGameCard.tsx` (simpler), or destructure and use it (e.g., for a future axis label). If removing, also remove the `as 'white' | 'black'` casts at lines 290 and 327 of `LibraryGameCard.tsx`.

```tsx
// EvalChartProps — remove the unused field:
interface EvalChartProps {
  gameId: number;
  evalSeries: EvalPoint[];
  flawMarkers: FlawMarker[];
  phaseTransitions: PhaseTransitions;
  heightClass?: string;
  // userColor removed — resolved from FlawMarker.is_user in tooltip
}

// LibraryGameCard.tsx — remove the prop and the unsafe cast:
<EvalChart
  gameId={game.game_id}
  evalSeries={game.eval_series}
  flawMarkers={game.flaw_markers}
  phaseTransitions={game.phase_transitions}
  // no userColor
/>
```

---

### WR-02: `markerMap` silently drops a marker when the same ply has two entries

**File:** `frontend/src/components/library/EvalChart.tsx:174`

**Issue:**

```tsx
const markerMap = new Map(flawMarkers.map((m) => [m.ply, m]));
```

`Map` constructed from an iterable of `[key, value]` pairs uses last-write-wins when the same key appears more than once. In chess, only one side moves per ply, so the backend should never emit two `FlawMarker` entries for the same ply. But the frontend silently trusts this invariant without any guard. If the backend ever emits a duplicate ply (e.g., a future schema change, an off-by-one in `_run_all_moves_pass`, or data corruption), one dot is silently lost with no error, no warning, and no visible symptom.

This is not a current correctness bug — the backend invariant holds — but the silent data-loss failure mode is concerning given the ply key is also used for tooltip lookup.

**Fix:** Add a defensive check so the invariant violation is observable:

```tsx
const markerMap = new Map<number, FlawMarker>();
for (const m of flawMarkers) {
  if (import.meta.env.DEV && markerMap.has(m.ply)) {
    console.warn(`EvalChart: duplicate FlawMarker at ply ${m.ply} — last entry wins`);
  }
  markerMap.set(m.ply, m);
}
```

This preserves the O(n) construction and surfaces invariant violations in development without impacting production.

---

### WR-03: `game.user_color as 'white' | 'black'` unsafe type assertion

**File:** `frontend/src/components/results/LibraryGameCard.tsx:290,327`

**Issue:** `GameFlawCard.user_color` is typed as `string` (matching the backend's untyped `str` field). The call sites cast it:

```tsx
userColor={game.user_color as 'white' | 'black'}
```

A type assertion (`as`) silences the compiler but does not validate at runtime. If the API ever returns an unexpected string (e.g., `"WHITE"`, `"w"`, or an empty string), the assertion succeeds silently and the prop receives a value outside the union — which would confuse any perspective-sensitive code. This is compounded by WR-01: the prop is currently discarded, so the faulty value is not reachable. If WR-01 is fixed and `userColor` is actually used, the unsafe assertion becomes an active bug path.

**Fix:** Narrow with a runtime guard rather than a bare assertion:

```tsx
const userColor = game.user_color === 'black' ? 'black' : 'white';
// then pass userColor to EvalChart
```

Alternatively, tighten `GameFlawCard.user_color` in `frontend/src/types/library.ts` to `'white' | 'black'` (the backend `user_color` column only ever holds those two values):

```ts
user_color: 'white' | 'black';
```

This makes the `as` cast unnecessary and catches mismatches at the API boundary.

---

## Info

### IN-01: Dead import `_PHASE_INT_TO_TAG` masked by `# noqa: F401`

**File:** `app/services/library_service.py:32`

**Issue:**

```python
from app.repositories.library_repository import _PHASE_INT_TO_TAG, _TEMPO_INT_TO_TAG  # noqa: F401
```

`_TEMPO_INT_TO_TAG` is legitimately used at line 244 (`_curate_chips_from_rows`). `_PHASE_INT_TO_TAG` is never referenced anywhere in `library_service.py` — the `# noqa: F401` silences ruff's "unused import" warning for both names in the same statement, hiding the dead import. The import comment is inherited from before Phase 109 (the line pre-existed), but the Phase 109 addition of `_build_eval_series` did not add any phase-int-to-tag usage. Dead code should not be masked by suppression comments.

**Fix:** Split the import so the suppression covers only the legitimately re-exported name, or remove `_PHASE_INT_TO_TAG` from the import entirely since it is unused:

```python
from app.repositories.library_repository import _TEMPO_INT_TO_TAG
```

If `_PHASE_INT_TO_TAG` is intentionally re-exported from this module for external callers, add a comment explaining the consumer; a grep of the codebase shows no such consumer currently exists.

---

### IN-02: Intentional `print()` instrumentation left in test

**File:** `tests/test_library_router.py:1383`

**Issue:**

```python
print(f"\n[D-05] Gzipped payload size: {compressed_size} bytes (ceiling: {_EVAL_PAYLOAD_GZIP_CEILING_BYTES})")
```

The comment acknowledges this is intentional D-05 documentation instrumentation. However, `print` in a pytest test produces output only when `-s` / `--capture=no` is passed; the default capture mode suppresses it. The documented intent ("so the SUMMARY can record it") was already fulfilled in `109-03-SUMMARY.md`. Keeping a `print` in a committed test file violates the project's no-debug-artifact convention and will cause noise if `-s` is ever used.

**Fix:** Remove the `print` call. The D-05 size figure is already captured in the plan summary; the test assertion on `compressed_size < _EVAL_PAYLOAD_GZIP_CEILING_BYTES` is sufficient ongoing enforcement.

---

_Reviewed: 2026-06-07T14:30:00Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
