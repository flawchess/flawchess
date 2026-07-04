---
phase: 150-consolidate-write-path
fixed_at: 2026-07-04T18:45:00Z
review_path: .planning/phases/150-consolidate-write-path/150-REVIEW.md
iteration: 1
findings_in_scope: 4
fixed: 4
skipped: 0
status: all_fixed
---

# Phase 150: Code Review Fix Report

**Fixed at:** 2026-07-04T18:45:00Z
**Source review:** .planning/phases/150-consolidate-write-path/150-REVIEW.md
**Iteration:** 1

**Summary:**
- Findings in scope: 4 (Warning only; 2 Critical/0 found, 2 Info out of scope per `fix_scope: critical_warning`)
- Fixed: 4
- Skipped: 0

## Fixed Issues

### WR-03: Dead branching in `_apply_flaw_blob_submit`'s token-tamper guard

**Files modified:** `app/routers/eval_remote.py`
**Commit:** `261ebd30`
**Applied fix:** Collapsed the two-branch token-rejection structure (both branches raised the identical `HTTPException(422, "Unknown or foreign token: ...")`) into a single unconditional raise. Removed the now-unused `_parse_token` try/except and `in_null_plies` computation from this call site (the `_parse_token` import itself stays — it's still used at `eval_remote.py:1119` for a different, real branch). `null_flaw_plies` remains defined and used later in the function's CPU phase. Verified against `test_blob_submit_foreign_token_rejected`, which exercises this exact path and still passes.

### WR-02: `Callable[..., Any]` return type on an awaited async callback

**Files modified:** `app/services/eval_apply.py`
**Commit:** `a4d5342b`
**Applied fix:** Imported `Coroutine` from `collections.abc` and retyped `upsert_opening_cache_fn`'s return annotation from bare `Any` to `Coroutine[Any, Any, None]`, matching how the callable is actually used (`await upsert_opening_cache_fn(...)`). The one real call site, `eval_drain.py`'s `_upsert_opening_cache` (an `async def ... -> None` function), type-checks cleanly against the new signature — verified with `ty check` on both `eval_apply.py` and `eval_drain.py`.

### WR-01: `apply_full_eval`'s signature has 12 optional keyword parameters, several silently-coupled

**Files modified:** `app/services/eval_apply.py`
**Commit:** `b9dd4cb8`
**Applied fix:** Chose the assertion half of the review's "and/or" fix suggestion rather than the `HeartbeatContext` dataclass grouping — grouping the 5 `heartbeat_*` params would ripple through both call sites (`eval_drain.py`, `eval_remote.py`) for a pure style improvement, which the task's critical_reminders flag as unsafe scope creep for a Warning-tier finding. Instead, replaced the silent-no-op guard (`if update_opening_cache and upsert_opening_cache_fn is not None:`) with `if update_opening_cache:` followed by two explicit asserts (`upsert_opening_cache_fn is not None`, `engine_targets_for_cache is not None`). A future caller that sets `update_opening_cache=True` without both companions now fails loudly instead of silently skipping the opening-cache write. Confirmed both current call sites are unaffected: `eval_drain.py` always passes a concrete (never-`None`) `engine_targets` list and `_upsert_opening_cache`; `eval_remote.py` leaves `update_opening_cache` at its default `False`, so the new asserts never execute there.

### WR-04: Deeply nested boolean/None-hole branching in `_apply_full_eval_results`

**Files modified:** `app/services/eval_apply.py`
**Commit:** `727dc594`
**Applied fix:** Extracted the `if target.ends_game / elif preserve_existing_evals / else` block (the source of the depth-4 nesting) into a new pure helper `_is_engine_hole(target, preserve_existing_evals) -> bool`, matching the review's suggested extraction shape. The per-target loop now reads `if _is_engine_hole(target, preserve_existing_evals): failed_ply_count += 1` followed by the unconditional `if best_move is not None: bm_only_rows.append(...)` that was previously duplicated identically across all three original branches — nesting drops from depth 4 to depth 3. Behavior is unchanged: `failed_ply_count` still increments only in the genuine-hole case, and `best_move` is still appended whenever available regardless of hole status, exactly as before.

**Note on this fix's risk tier:** although mechanically a pure extraction, this touches the write path's per-ply hole-classification control flow (feeds `failed_ply_count` -> Path A/B/C completion decision), so per the verification_strategy's logic-bug caveat this is flagged `fixed: requires human verification` rather than plain `fixed`, despite passing the full backend suite (3161 passed, 19 skipped) and the golden equivalence test (`tests/services/test_flaw_upsert_equivalence.py`, 8/8) unchanged.

## Skipped Issues

None — all 4 in-scope findings were fixed.

---

_Fixed: 2026-07-04T18:45:00Z_
_Fixer: Claude (gsd-code-fixer)_
_Iteration: 1_
