---
phase: 106-games-surface-backend-mistake-filter-per-game-counts-stats-a
reviewed: 2026-06-05T00:00:00Z
depth: standard
files_reviewed: 9
files_reviewed_list:
  - app/services/mistakes_service.py
  - app/repositories/query_utils.py
  - app/repositories/library_repository.py
  - app/schemas/library.py
  - app/services/library_service.py
  - app/routers/library.py
  - app/main.py
  - tests/test_library_repository.py
  - tests/services/test_library_service.py
findings:
  critical: 0
  warning: 4
  info: 5
  total: 9
status: issues_found
---

# Phase 106: Code Review Report

**Reviewed:** 2026-06-05
**Depth:** standard
**Files Reviewed:** 9
**Status:** issues_found

## Summary

Phase 106 adds the Games-surface backend: a boolean mistake-severity `EXISTS` filter, per-game B/M/I counts + curated chips, and a stats-panel aggregate, all derived on-the-fly by re-calling the Phase 105 kernel. The architecture is clean and the security posture is sound: every query is user-scoped (base WHERE + EXISTS subquery + `fetch_game_positions_ordered` + the `_load_analyzed_flaws` ownership re-assert), responses expose FEN/usernames only (no `*_hash`), all SQL uses parameterized binds (no f-string interpolation), the kernel re-call loops are sequential (no `asyncio.gather` on the session), constants are imported (no hard-coded thresholds/K), and the two endpoints are `current_active_user`-gated with bounded `Query` params and a `from_date > to_date` 422 guard.

No Critical defects were found. The most consequential finding is a **genuine SQL/Python divergence on the mate Option-B branch for `eval_mate == 0`** (WR-01) — exactly the class of drift the phase's load-bearing cross-check fixture exists to prevent, yet the SQL mate path has **zero test coverage** (WR-02). The remaining warnings concern a defensive-but-unreachable branch masking a real inconsistency risk and a whole-user coverage aggregate that is not intersected before grouping. The structural seam (user-color scoping, eval-AFTER LAG pairing, interior-null exclusion, inaccuracy-count separation) is correct.

No structural pre-pass (`<structural_findings>`) was provided.

## Narrative Findings (AI reviewer)

## Warnings

### WR-01: SQL mate Option-B diverges from the kernel when `eval_mate == 0`

**File:** `app/repositories/library_repository.py:75-81` (vs `app/services/mistakes_service.py:147-149`)
**Issue:** The SQL `_cp_equiv` transcription and the Python kernel `_ply_to_es` disagree on the boundary value `eval_mate == 0`, breaking the "one source of truth" parity the whole phase is built around.

- Kernel: `cp_equiv = MATE_CP_EQUIVALENT if pos.eval_mate > 0 else -MATE_CP_EQUIVALENT`. For `eval_mate == 0`, the `else` branch fires → `-1000` → mover-POV ES ≈ 0.0.
- SQL: `func.sign(eval_mate) * MATE_CP_EQUIVALENT`. For `eval_mate == 0`, `sign(0) == 0` → `0` → mover-POV ES == 0.5.

`eval_mate` originates from python-chess `score.white().mate()` (`app/services/zobrist.py:189`), which returns `0` for a mate-in-0 / already-mated position (`Mate(0)`). When such a row exists, the SQL `EXISTS` filter and the per-ply flag would compute a materially different drop than the kernel that produces the card counts and chips — so a game could be selected by the filter but show 0 flags on its card (or vice versa), the exact contradiction the cross-check is meant to forbid.

**Fix:** Mirror the kernel's `> 0 / else` split rather than `sign()`:
```python
def _cp_equiv(eval_cp: Any, eval_mate: Any) -> ColumnElement[Any]:
    return case(
        (eval_mate > 0, MATE_CP_EQUIVALENT),
        (eval_mate.isnot(None), -MATE_CP_EQUIVALENT),  # eval_mate <= 0 (incl. 0)
        else_=eval_cp,
    )
```
Then extend the cross-check fixture (WR-02) to seed `eval_mate` rows including `0`, `+N`, and `-N`.

### WR-02: The SQL mate Option-B path has zero test coverage

**File:** `tests/test_library_repository.py:225-261` (and all seed helpers, e.g. `:79-111`)
**Issue:** RESEARCH Pitfall 1 names mate handling as the single highest-risk divergence, and the cross-check fixture (`test_cross_check_sql_equals_kernel_subset`) is documented as "the load-bearing seam guard." But every seeded position across both test files uses `eval_mate=None` (`tests/test_library_repository.py:102`, `tests/services/test_library_service.py:81,324,425`). The mate branch of `_cp_equiv` (`library_repository.py:76-79`) is therefore never executed, so the guard cannot catch WR-01 or any future mate-transcription regression. The cross-check passes only because it exercises the `eval_cp`-only path.

**Fix:** Add a mate variant to the cross-check: seed a game with `eval_mate` values (`+3`, `-3`, and crucially `0`) on user plies, run both `_run_all_moves_pass` and `flagged_plies_for_severity`, and assert the `(ply, severity)` sets match. This is the test that would have surfaced WR-01.

### WR-03: Defensive `isinstance(..., list)` fallback can silently mask a coverage-gate divergence

**File:** `app/services/library_service.py:111-114` and `:283-284`
**Issue:** After `count_game_severities` returns analyzed (the `"reason" in counts_result` branch is false), the code calls `classify_game_mistakes` and then guards `flaws = flaws_result if isinstance(flaws_result, list) else []`. The comment asserts the two kernel entry points "share the identical coverage gate," which is true today — meaning the `else []` branch is unreachable. But if that invariant ever drifts (one gate changes, or a future positions-mutation between the two calls), this fallback would **silently emit an analyzed card with empty chips** instead of failing loudly, hiding the inconsistency. Same pattern at `:283-284` in `_load_analyzed_flaws`.

**Fix:** Replace the silent fallback with an assertion that documents and enforces the invariant, so a regression raises (and is Sentry-captured by the surrounding `try/except`) rather than degrading data:
```python
assert isinstance(flaws_result, list), "coverage gate divergence: count says analyzed, classify says not"
flaws = flaws_result
```

### WR-04: Whole-user coverage aggregate is grouped before intersection with the filtered set

**File:** `app/repositories/library_repository.py:318-338` (`_analyzed_game_ids_subquery`), used at `:386-388` and `:428-433`
**Issue:** `_analyzed_game_ids_subquery(user_id)` runs `GROUP BY game_id ... HAVING coverage >= EVAL_COVERAGE_MIN` over **all** of the user's `game_positions`, and only afterwards is it intersected (`IN (...)`) with the bounded filtered game-id set. The 106-03 SUMMARY's own EXPLAIN documents the isolated whole-user aggregate at ~1.7s (vs ~11ms for the intersected nested-loop), and relies on the planner not being able to push the `IN` predicate into the GROUP BY. Whether Postgres pushes the filter down is plan-dependent; for a power user with many games this aggregate can dominate the request. (Performance is out of v1 scope, but this is a correctness-adjacent robustness concern: the query's cost is unbounded by the filter the user actually applied.)

**Fix:** Scope the coverage aggregate to the filtered game-ids before grouping, e.g. add `.where(GamePosition.game_id.in_(select(base_subq.c.id)))` inside `_analyzed_game_ids_subquery` (pass the filtered base in), so the GROUP BY only ever touches plies of games already in scope. This makes the nested-loop plan the only plan, independent of the optimizer.

## Info

### IN-01: `false()` branch in `mistake_exists_subquery` is unreachable from the live path

**File:** `app/repositories/library_repository.py:176-178`
**Issue:** `if not severities: return false()` is dead from the HTTP path — the router constrains severity to a non-empty `list[Literal["mistake","blunder"]]` and the service converts empty/None to `None` before `apply_game_filters` (which only calls the subquery when `mistake_severity` is truthy). It is reasonable defensive code for direct callers, but worth a one-line comment noting it is not reachable via the endpoints.
**Fix:** Keep it; add `# defensive: live callers never pass empty (router Literal + service None-coalesce)`.

### IN-02: Trend per-date dedup keeps the last game's window, dropping intra-day points

**File:** `app/services/library_service.py:368-384`
**Issue:** `data_by_date` is keyed by `"%Y-%m-%d"`, so multiple analyzed games on the same date collapse to a single point (the last game's rolling window). This faithfully copies the `get_time_series` precedent, so it is intentional and consistent — but for a user who plays many games per day the trend resolution is coarse, and the behavior is not documented in the schema field. Not a bug.
**Fix:** Add a one-line note to `MistakeTrendPoint.date` (`app/schemas/library.py:111`) that same-day games are collapsed to the most recent window, matching the openings time-series convention.

### IN-03: `eval_mate == 0` handling in the kernel is itself questionable (upstream, not 106)

**File:** `app/services/mistakes_service.py:147-149`
**Issue:** The kernel maps `eval_mate == 0` to `-MATE_CP_EQUIVALENT` (the `else` of `> 0`), i.e. "black has mate now" regardless of whose move it is. A mate-in-0 is an already-terminal position and arguably should not feed drop math at all. This predates Phase 106 (Phase 105 kernel) and is out of this phase's scope, but the WR-01 SQL fix should match whatever the kernel does, and this is the value it must match.
**Fix:** Out of scope for 106; flag as a follow-up seed if mate-in-0 rows are observed in prod data.

### IN-04: `_PER_100` magic-number constant is fine; `100.0` label could be clearer

**File:** `app/services/library_service.py:210`
**Issue:** `_PER_100 = 100.0` is correctly extracted per CLAUDE.md "no magic numbers." Minor: the name describes the value, not the intent (per-100-user-moves normalization factor). Purely cosmetic.
**Fix:** Optional rename to `_PER_100_MOVES_FACTOR` or add a comment; not required.

### IN-05: Kernel list-index-as-ply assumption is relied on by both paths but unstated here

**File:** `app/services/library_service.py:237-252` (`_count_user_moves`) and `app/repositories/library_repository.py:106,148-158`
**Issue:** The Python kernel computes mover parity from the list index `n` (`_run_all_moves_pass`), while the SQL computes it from the actual `ply` column. These agree only because plies are stored contiguous from 0 at import time. `_count_user_moves` here correctly uses `pos.ply % 2` (the real ply), aligning with SQL rather than the kernel's index. The assumption is sound for current data but is load-bearing and undocumented at these sites.
**Fix:** Add a brief comment at `_count_user_moves` noting it keys on the real `ply` (contiguous-from-0 invariant) so parity matches both the kernel and the SQL `_user_ply_filter`.

---

_Reviewed: 2026-06-05_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
