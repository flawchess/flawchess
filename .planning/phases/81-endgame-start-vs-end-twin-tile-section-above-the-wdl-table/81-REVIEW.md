---
phase: 81-endgame-start-vs-end-twin-tile-section-above-the-wdl-table
reviewed: 2026-05-09T00:00:00Z
depth: standard
files_reviewed: 12
files_reviewed_list:
  - app/schemas/endgames.py
  - app/services/endgame_service.py
  - frontend/src/components/charts/EndgamePerformanceSection.tsx
  - frontend/src/components/charts/EndgameStartVsEndSection.tsx
  - frontend/src/components/charts/__tests__/EndgameStartVsEndSection.test.tsx
  - frontend/src/lib/endgameEntryEvalZones.ts
  - frontend/src/lib/__tests__/endgameEntryEvalZones.test.ts
  - frontend/src/pages/Endgames.tsx
  - frontend/src/pages/__tests__/Endgames.startVsEnd.test.tsx
  - frontend/src/types/endgames.ts
  - tests/test_endgame_service.py
  - tests/test_endgames_router.py
findings:
  blocker: 0
  warning: 6
  info: 4
  total: 10
status: issues_found
---

# Phase 81: Code Review Report

**Reviewed:** 2026-05-09
**Depth:** standard
**Files Reviewed:** 12
**Status:** issues_found

## Summary

The Phase 81 changes are tightly scoped and well-documented:

- Schema: 6 new optional fields on `EndgamePerformanceResponse` with sensible defaults.
- Service: a new entry-eval aggregation block in `_get_endgame_performance_from_rows` plus a Wilson p-value test on `endgame_wdl`. Aggregation correctly consumes `bucket_rows` (one row per game) so `entry_eval_n` lines up with `endgame_wdl.total`.
- Frontend: a clean `EndgameStartVsEndSection` reusing existing primitives (`MiniBulletChart`, `BulletConfidencePopover`, `ScoreConfidencePopover`) with confidence buckets derived locally from the wire-format p-value.
- Tests: solid coverage of the new aggregation and component behavior.

No BLOCKER findings — the math is sound, the n-gates are consistent (n=10 across backend + frontend), and the user-color sign flip is explicit. The findings below are correctness-adjacent quality issues (mostly around documented invariants that don't quite hold, redundant/dead code, and a couple of minor comment inaccuracies). Nothing prevents this from shipping.

## Warnings

### WR-01: Docstring invariant `entry_eval_n + mate_excluded == endgame_wdl.total` is incomplete

**File:** `app/services/endgame_service.py:1652-1659`
**Issue:** The docstring asserts that "`entry_eval_n + mate_excluded == endgame_wdl.total` by construction." This ignores **NULL-eval** rows (`eval_cp IS NULL AND eval_mate IS NULL` — engine errors or not-yet-backfilled positions), which `_get_endgame_performance_from_rows` also drops at line 1679. The same NULL-exclusion is repeated in `tests/test_endgame_service.py::test_null_eval_row_excluded_from_aggregation`. The accurate invariant is:

```
entry_eval_n + mate_excluded + null_eval_excluded == endgame_wdl.total
```

This matters because the Phase 81 plan and PR may be claiming an invariant that won't hold in production until eval-backfill is 100% complete (the same risk that motivated REFAC-02's NULL→parity routing in `_classify_endgame_bucket`). A reader trusting the docstring will be surprised when `entry_eval_n` lags `endgame_wdl.total` for a freshly imported user.

**Fix:**
```python
# In docstring:
# so `entry_eval_n + mate_excluded + null_excluded == endgame_wdl.total` by
# construction. NULL evals (engine errors / not-yet-backfilled spans) are
# excluded from the entry-eval mean even though they are counted toward
# endgame_wdl.total — they would bias the mean toward 0 if routed there.
```

Also update the analogous comment block in `get_endgame_overview` (line 2082-2085) which makes the same incomplete claim.

---

### WR-02: `_get_endgame_performance_from_rows` accepts `Sequence[Row | tuple]` but unconditionally uses attribute access

**File:** `app/services/endgame_service.py:1648, 1674-1687`
**Issue:** The function signature declares `bucket_rows: Sequence[Row[Any] | tuple[Any, ...]]`, but the loop body accesses `row.eval_mate`, `row.eval_cp`, `row.user_color` via attribute access (with `# ty: ignore[unresolved-attribute]` suppressions on every line). Attribute access on a plain `tuple` would raise `AttributeError` at runtime, so the declared union is a lie — only labeled `Row` and `NamedTuple` actually work.

This is the same shape problem `_compute_score_gap_material` already has at line 752 (it carries the same suppressions), so the pattern is consistent — but it's still a type lie that ty has to be told to ignore. If a future caller hands in a real `tuple`, the failure mode is a runtime error, not a type error.

**Fix:** Either narrow the param type to `Sequence[Row[Any]]` (the only shape that actually works in prod) and let the test fixture's `_FakeRow` continue to satisfy it via NamedTuple's attribute access, or define a `Protocol` / `TypedDict` covering the labeled columns and type the param to that. The four `# ty: ignore` comments would all go away.

---

### WR-03: `get_endgame_performance` is now an unreachable code path that still runs a redundant DB query

**File:** `app/services/endgame_service.py:1729-1775`
**Issue:** `tests/test_endgames_router.py:TestLegacyEndpointsRemoved::test_performance_returns_404` confirms that `GET /api/endgames/performance` returns 404. The only consumer of `get_endgame_performance` is now... nothing in the router layer. It is reachable only through the test suite.

Phase 81 wired it to `query_endgame_bucket_rows` (correct change for the test path) but the orchestrator `get_endgame_overview` already independently fetches `bucket_rows`. So at runtime this function is dead code, and at test time it's adding maintenance burden (mocks for both `query_endgame_performance_rows` and `query_endgame_bucket_rows`).

This is not a Phase 81 regression — Phase 52 created the dead-code situation — but Phase 81 expanded what the dead function does without removing it. Worth flagging while you're in this file.

**Fix:** Either remove `get_endgame_performance` and its tests in a follow-up cleanup quick-task, or annotate it `# Internal: kept for direct unit-testing of _get_endgame_performance_from_rows; not reached via /api/endgames/performance (404 since Phase 52)` so the next reader doesn't search for the missing route binding.

---

### WR-04: Comment at `EndgameStartVsEndSection.tsx:88-91` mischaracterizes BulletConfidencePopover's null handling

**File:** `frontend/src/components/charts/EndgameStartVsEndSection.tsx:88-91`
**Issue:** The comment says:

> ScoreConfidencePopover.pValue is non-nullable; coerce null to 1.0 (the popover's "no signal" baseline — same coercion BulletConfidencePopover does internally).

`BulletConfidencePopover` does NOT do "the same coercion" — its prop type is `pValue: number | null | undefined` (see `BulletConfidencePopover.tsx:11`), and it handles null via `pValue ?? 1` only when forwarding to `EvalConfidenceTooltip`. The interfaces are not symmetric. A future reader will see this comment, decide "well if Bullet does it internally, Score should too" and waste time before realizing the discrepancy.

**Fix:**
```tsx
// ScoreConfidencePopover.pValue is non-nullable (unlike BulletConfidencePopover,
// which accepts number | null | undefined). Coerce null to 1 — under the gate
// `showTile2Chart = totalGames >= 10`, the backend always ships a non-null
// p-value, so this branch is defensive only.
const scorePValueForPopover = data.endgame_score_p_value ?? 1;
```

---

### WR-05: `EndgameStartVsEndSection` recomputes `score` locally but uses the backend `endgame_wdl.total` as the n-gate — value can drift from `endgame_score_p_value`

**File:** `frontend/src/components/charts/EndgameStartVsEndSection.tsx:75-86`
**Issue:** The component recomputes `score = (wins + 0.5 * draws) / totalGames` from the raw counts on the wire, which is good. But the backend's `endgame_score_p_value` was computed by `compute_confidence_bucket(wins, draws, losses, total)` against H0=0.5 using the *same* counts, so the score the user sees and the p-value the popover advertises are mathematically tied — that's the intent.

However, `wilsonBounds(score, totalGames)` is also computed locally from the same counts. Both backend and frontend use the same Wilson formula (verified — `score_confidence.py::wilson_bounds` and `frontend/src/lib/scoreConfidence.ts::wilsonBounds`), so the CI bounds match. **No correctness bug here.**

The risk is durability: if a future change sends `endgame_score_p_value` computed against a different `total` (e.g. recency-filtered on the backend, but frontend renders the broader counts), the displayed score / CI / p-value triple would silently disagree. Worth a brief comment locking in the assumption.

**Fix:**
```tsx
// `score`, the Wilson CI bounds, and `endgame_score_p_value` are all derived
// from `endgame_wdl.{wins,draws,losses,total}` — the backend Wilson p-value
// formula matches `wilsonBounds` here (see scoreConfidence.ts header). Do not
// substitute a different score source without re-deriving the p-value too.
const totalGames = data.endgame_wdl.total;
```

---

### WR-06: `endgame_wdl.win_pct` is rounded; using it as `endgame_win_rate` ships a ~0.05 pp rounding error to consumers

**File:** `app/services/endgame_service.py:1719`
**Issue:** Pre-existing (not introduced in Phase 81), but worth flagging while reviewing this surface:

```python
endgame_win_rate=endgame_wdl.win_pct,
```

`endgame_wdl.win_pct` is `round(wins / total * 100, 1)` (line 531). The schema docstring claims `endgame_win_rate` is "wins / total for endgame games only, 0-100" — implying unrounded. Any consumer comparing `endgame_win_rate` against another raw percentage could disagree by up to 0.05 pp.

This is downstream of Phase 81 (no consumer outside the dashboard appears to read `endgame_win_rate` today), but Phase 81 added new sibling fields with their own precision contracts, so consistency matters.

**Fix:** Compute the unrounded win rate explicitly:
```python
endgame_win_rate = (
    endgame_wdl.wins / endgame_wdl.total * 100 if endgame_wdl.total > 0 else 0.0
)
return EndgamePerformanceResponse(..., endgame_win_rate=endgame_win_rate, ...)
```

If the rounding behavior is intentional and consumers depend on it, document it on the schema field instead.

## Info

### IN-01: `EndgameStartVsEndSection` uses `MIN_GAMES_FOR_RELIABLE_STATS` from `@/lib/theme` for a non-presentation purpose

**File:** `frontend/src/components/charts/EndgameStartVsEndSection.tsx:43,59,72,86`
**Issue:** `MIN_GAMES_FOR_RELIABLE_STATS = 10` lives in `theme.ts` alongside colors and zone constants. Importing it for the n-gate check is fine, but the constant is doing double duty: it's both a presentation threshold (when to dim/mute UI) AND a statistical threshold (when to suppress p-values). The backend uses a separate `OPENING_INSIGHTS_CONFIDENCE_MIN_N` for the latter. Keeping both names in sync depends on a comment in `eval_confidence.py:8` ("matches the unreliable-stats UI dim").

Not a Phase 81 issue — this duality predates the phase — but the new component is now another consumer that quietly assumes they'll always equal 10. A future bump of `MIN_GAMES_FOR_RELIABLE_STATS` from 10 to e.g. 20 (for visual reasons) would silently change confidence bucketing here.

**Fix:** Consider re-exporting a `MIN_GAMES_FOR_CONFIDENCE_GATE` from `scoreConfidence.ts` (currently a private `CONFIDENCE_MIN_N`) and using that for the gate, leaving `MIN_GAMES_FOR_RELIABLE_STATS` purely for presentation. Out of phase scope; flag for follow-up.

---

### IN-02: Magic number `1` in `data.endgame_score_p_value ?? 1`

**File:** `frontend/src/components/charts/EndgameStartVsEndSection.tsx:91`
**Issue:** The fallback `1` (representing p-value 1.0 = no signal) is duplicated across the codebase: `BulletConfidencePopover.tsx:83` does `pValue ?? 1`, `scoreConfidence.ts:70` returns `pValue: 1`, etc. Each site is a magic number.

**Fix:** Either inline a constant `const NO_SIGNAL_P_VALUE = 1` in the relevant tooltip/popover module and import it, or accept this as established convention and leave it. Low priority.

---

### IN-03: TODO/FIXME-style "Phase X" comments accumulating

**File:** `app/services/endgame_service.py` (multiple) and `app/schemas/endgames.py`
**Issue:** The endgame service file is now a heritage layer of "Phase X added Y" comments referencing Phases 32, 52, 53, 54, 55, 57, 57.1, 59, 60, 65, 68, 75, 76, 80, 81. Each comment was useful at the time it landed; collectively they're hard to follow because the reader has to keep a phase-history in their head. Many of the older comments are about removed features ("Phase 59 removed the aggregate ... fields").

**Fix:** Out of phase scope, but a future cleanup task could prune historical phase markers — keep only the ones explaining *current* behavior, drop the ones about what was removed.

---

### IN-04: `bucket_rows` parameter in `_compute_score_gap_material` shape comment is now misleading post-Phase 81

**File:** `app/services/endgame_service.py:746-749`
**Issue:** The comment says:

> rows carry labeled columns in prod (see query_endgame_bucket_rows / query_endgame_entry_rows) and a matching NamedTuple stand-in in tests, so attribute access is valid in both cases even though the declared parameter type unions in plain tuple for backward-compat.

Phase 81 widened the consumers of `bucket_rows` (now also fed through `_get_endgame_performance_from_rows`) without consolidating the row-shape contract. The "backward-compat" framing is stale: there's no longer any caller passing a plain `tuple`. Same as WR-02 — narrow the union.

**Fix:** Drop the `tuple[Any, ...]` arm of the union in both `_compute_score_gap_material` (line 684) and `_get_endgame_performance_from_rows` (line 1648). Remove the four `# ty: ignore[unresolved-attribute, invalid-argument-type]` lines that follow.

---

_Reviewed: 2026-05-09_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
