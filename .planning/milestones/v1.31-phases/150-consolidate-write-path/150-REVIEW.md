---
phase: 150-consolidate-write-path
reviewed: 2026-07-04T00:00:00Z
depth: standard
files_reviewed: 9
files_reviewed_list:
  - app/services/eval_apply.py
  - app/services/eval_drain.py
  - app/services/eval_entry.py
  - app/routers/eval_remote.py
  - app/repositories/game_flaws_repository.py
  - app/services/engine.py
  - app/services/eval_queue_service.py
  - app/services/import_service.py
  - scripts/gen_write_path_golden.py
findings:
  critical: 0
  warning: 4
  info: 2
  total: 6
status: issues_found
---

# Phase 150: Code Review Report

**Reviewed:** 2026-07-04
**Depth:** standard
**Files Reviewed:** 9
**Status:** issues_found

## Summary

This is a structure-only refactor (R1/R3/R4/R7) of the eval write path: extracting
`apply_completion_decision` (R1), unifying the classify preamble with an `overlay`
parameter (R4), replacing `_classify_and_fill_oracle`'s delete-then-insert with a
4-way diff/upsert (R3), and splitting `eval_drain.py`/`eval_remote.py` into
`eval_apply.py` (shared leaf) + `eval_entry.py` (entry-lane primitives), plus two
smaller R2 refactors (`EnginePool._acquire_and_analyse`, the ES-lottery shared
helpers in `eval_queue_service.py`).

I traced the specific landmines called out in the review brief and did not find
any of them realized:

- **No `ON CONFLICT DO UPDATE ... COALESCE(...)` over a JSONB blob column anywhere**
  in the reviewed files. The only `COALESCE` in a write statement
  (`best_move = COALESCE(v.best_move, game_positions.best_move)`,
  `eval_apply.py:413`) is over a `varchar` column and pre-dates this phase
  (FLAWCHESS-6B) — the asyncpg `null::jsonb` blob-wipe landmine this phase set
  out to avoid is genuinely absent.
- **Preservation-by-omission is real**: `FLAW_BLOB_COLUMNS` is defined exactly
  once (`game_flaws_repository.py:171`) and consumed exactly once
  (`eval_apply.py:881`, filtering `preserve_rows`). Both `fresh_rows` and
  `preserve_rows` are internally key-homogeneous per
  `bulk_update_game_flaw_rows`'s stated invariant (every dict built from the
  same `flaw_record_to_row` shape, filtered identically), so the ORM
  bulk-update-by-PK compiles one consistent `SET` clause per call.
- **Fail-closed contract intact**: the delete/insert/update statements and the
  oracle-count `UPDATE` inside `_classify_and_fill_oracle` are not wrapped in
  try/except; only the flaw-adjacent `game_positions.pv` write is
  individually fault-tolerant, exactly as documented.
- **Post-move off-by-one preserved**: `_post_move_eval` remains the single `+1`
  site; the diff/upsert and R4 overlay refactors don't touch it.
- **R4 overlay parameter correct**: `_flaw_engine_plies` is the only call site
  using `overlay=False`; `_missing_flaw_pv_targets`, `_build_flaw_multipv2_blobs`,
  and `_derive_atomic_sentinel_lines` all use `overlay=True`, matching the
  documented lichess-%eval-must-not-be-zeroed contract.
- **R1 completion decision**: the `WHERE status = 'leased'` guard on the
  `eval_jobs` stamp is present, and the injectable Path-C callback is wired
  identically for both lanes.
- **No circular imports**: `eval_apply.py` is a genuine leaf (no import of
  `eval_drain`/`eval_remote`); `eval_drain.py` imports `eval_apply` +
  `eval_entry`; `eval_remote.py` imports all three but nothing imports back
  into it. `ruff check` and `ty check` both pass clean on all 9 files.

The findings below are secondary maintainability issues (parameter-list bloat,
a type-safety gap on one callback, dead branching in a pre-existing but
in-scope function, and a stale comment left behind by the R7 module split) —
none rise to a correctness or security defect.

## Warnings

### WR-01: `apply_full_eval`'s signature has 12 optional keyword parameters, several silently-coupled

**File:** `app/services/eval_apply.py:1677-1711`
**Issue:** `apply_full_eval` (the new shared write-session body, R7) takes 20
parameters, 12 of them optional keyword flags/callbacks:
`preserve_existing_evals`, `blobs_pending`, `update_opening_cache`,
`upsert_opening_cache_fn`, `engine_targets_for_cache`, `count_flaws_written`,
`record_heartbeat`, `heartbeat_worker_id`, `heartbeat_last_ip`,
`heartbeat_sf_version`, `heartbeat_worker_schema_version`, `heartbeat_n_evals`.
Three of these (`update_opening_cache`, `upsert_opening_cache_fn`,
`engine_targets_for_cache`) are correlated but not enforced together: a future
caller could pass `update_opening_cache=True` while forgetting
`engine_targets_for_cache`, and the code silently no-ops
(`list(engine_targets_for_cache or [])` → `[]`) instead of erroring — it would
quietly skip populating the opening cache rather than surfacing the mistake.
Both current call sites (`eval_drain.py`, `eval_remote.py`) pass them
correctly, so there's no live bug today, but the shape invites a future
silent-miss.
**Fix:** Group the 5 `heartbeat_*` params into a small dataclass
(`HeartbeatContext`) passed as one optional argument, and/or assert
`upsert_opening_cache_fn is not None and engine_targets_for_cache is not None`
when `update_opening_cache=True` so a future caller mistake fails loudly
instead of silently skipping the cache write.

### WR-02: `Callable[..., Any]` return type on an awaited async callback

**File:** `app/services/eval_apply.py:1693-1703`
**Issue:** `upsert_opening_cache_fn`'s type is
`Callable[[AsyncSession, list[_FullPlyEvalTarget], dict[...]], Any]`, but the
callable is `await`ed at the call site (`eval_apply.py:1785`:
`await upsert_opening_cache_fn(...)`), i.e. it's actually an async function
returning `Coroutine[Any, Any, None]`. Typing the return as bare `Any` is
exactly the pattern CLAUDE.md's "Type safety" section calls out to avoid
(`Avoid any, prefer explicit types for function signatures ... and return
values`), and it silently accepts a non-awaitable callable at the type level.
**Fix:**
```python
from collections.abc import Coroutine

upsert_opening_cache_fn: (
    Callable[
        [AsyncSession, list[_FullPlyEvalTarget], dict[int, tuple[int | None, int | None, str | None, str | None]]],
        Coroutine[Any, Any, None],
    ]
    | None
) = None,
```

### WR-03: Dead branching in `_apply_flaw_blob_submit`'s token-tamper guard

**File:** `app/routers/eval_remote.py:846-866`
**Issue:** Both branches of the `if not in_null_plies: raise ... / raise ...`
structure raise the identical `HTTPException(422, "Unknown or foreign token: ...")`.
The `in_null_plies` variable (computed via `_parse_token` + a set-membership
check) is never used to alter control flow — every token not in
`valid_tokens` is rejected unconditionally regardless of its value. This
doesn't cause a behavior bug (the net effect matches the intended "reject any
non-issued token" contract), but it's misleading: the code and its comments
read as if there are two distinct rejection paths (foreign-ply vs.
issued-but-not-leased sentinel-line token) when there is only one. Pre-dates
Phase 150 (introduced in Phase 145) but is in the reviewed file set.
**Fix:** Collapse to a single unconditional raise (the `_parse_token`
try/except and `in_null_plies` computation can be dropped entirely), or if the
distinction is intended to matter for future diagnostics, actually branch on
it (e.g. a different `detail` message per case) instead of computing an
unused value.

### WR-04: Deeply nested boolean/None-hole branching in `_apply_full_eval_results`

**File:** `app/services/eval_apply.py:507-539`
**Issue:** The per-target write-row classification loop reaches nesting depth
4 (`for target` → `if eval_cp is None` → `if/elif/else` → `if best_move is not
None`), at the hard limit CLAUDE.md sets for function nesting. This is
pre-existing structure carried through the refactor rather than something R7
introduced, but since the review brief calls out "functions exceeding
nesting/LOC limits introduced by the refactor," flagging it here as a
borderline case worth a follow-up extraction (e.g. a small helper that
resolves `(is_hole, should_write_bm)` per target) if this function is touched
again.
**Fix:** Extract the `if target.ends_game / elif preserve_existing_evals /
else` block into a small pure helper returning a decision enum, dropping one
nesting level.

## Info

### IN-01: Stale cross-reference comment after the R7 module split

**File:** `app/services/import_service.py:33-39`
**Issue:** The import block reads:
```python
from app.services.eval_entry import (
    _classify_and_insert_flaws,
    _collect_endgame_span_eval_targets,
    _collect_midgame_eval_targets,
)  # Phase 91: cross-module use of eval_drain internals is intentional — see SEED-023.

# Phase 150 R7 Task 2: these moved from eval_drain.py to eval_entry.py.
```
The trailing comment on the import statement still says "eval_drain internals"
even though the import is now from `eval_entry`, and the newer Phase 150
comment explaining the move sits below the (now half-stale) older comment
rather than replacing it. Purely cosmetic, but it will confuse the next
reader trying to trace which module actually owns these symbols.
**Fix:** Delete or update the Phase-91 comment to say `eval_entry` (not
`eval_drain`) internals, or fold both comments into one accurate note.

### IN-02: Router private-helper import breadth (acknowledged, still worth tracking)

**File:** `app/routers/eval_remote.py:81-115`
**Issue:** `eval_remote.py` imports 10 underscore-prefixed symbols from
`eval_apply`, 5 from `eval_entry`, and 1 (`_load_pgns_for_games`) plus 3
constants from `eval_drain`. The module docstrings for both `eval_apply.py`
and `eval_drain.py` explicitly flag this as "the phase's one flagged,
deliberate residual private import" (documented in 150-05-SUMMARY.md), so this
isn't a surprise regression — but it's still a genuine encapsulation gap: a
router reaching into three services' private (`_`-prefixed) namespaces makes
it easy for a future edit to one of those modules to silently break the
router without any public-API contract to hold onto. Not asking for a fix
given the documented, deliberate tradeoff — flagging for visibility only, in
case a future phase wants to promote the genuinely-shared subset
(`_collect_full_ply_targets`, `_fetch_dedup_evals`, `apply_full_eval`, etc.)
to non-underscore public names.
**Fix (optional, not required):** If this file is touched again, consider a
small `eval_apply.__all__` / public re-export shim for the symbols the router
actually needs, so the router's imports read as "the public surface of the
write path" rather than "everything eval_apply happens to define."
