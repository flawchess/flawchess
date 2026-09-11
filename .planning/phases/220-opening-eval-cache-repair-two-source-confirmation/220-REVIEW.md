---
phase: 220-opening-eval-cache-repair-two-source-confirmation
reviewed: 2026-09-11T00:00:00Z
depth: standard
files_reviewed: 17
files_reviewed_list:
  - alembic/env.py
  - alembic/versions/20260909_120000_a1c2e3f40001_phase_220_opening_cache_audit.py
  - alembic/versions/20260912_120000_b7d4f5a60002_phase_220_cache_provenance.py
  - app/models/__init__.py
  - app/models/opening_cache_audit.py
  - app/models/opening_position_eval.py
  - app/routers/eval_remote.py
  - app/services/engine.py
  - app/services/eval_apply.py
  - app/services/eval_drain.py
  - scripts/backfill_flaws.py
  - scripts/opening_cache_repair.py
  - tests/models/test_opening_cache_audit_models.py
  - tests/scripts/test_opening_cache_repair.py
  - tests/services/test_eval_drain.py
  - tests/services/test_full_eval_drain.py
  - tests/test_backfill_flaws.py
  - tests/test_eval_worker_endpoints.py
findings:
  critical: 0
  warning: 6
  info: 0
  total: 6
status: issues_found
---

# Phase 220: Code Review Report

**Reviewed:** 2026-09-11
**Depth:** standard
**Files Reviewed:** 17
**Status:** issues_found

## Summary

Traced the two-source-confirmation write path end to end: `_upsert_opening_cache` →
`_partition_cache_writes` → `_apply_cache_writes` (insert / skip-pv-heal / promote /
replace) in `app/services/eval_drain.py`, the confirmed-only read gate in
`app/services/eval_apply.py::_fetch_dedup_evals`, its delegate in
`app/routers/eval_remote.py::_fetch_cached_opening_hashes`, the Release-2 migration's
batched status-derived marking (`b7d4f5a60002`), and the repair pipeline's `orphans`/
`propagate`/`demote`/`rederive` stages in `scripts/opening_cache_repair.py`.

The core algorithm is sound. `_cache_values_agree`'s mate/non-mate + expected-score-delta
comparison is correct; the D-13 same-source guard (`existing.source_game_id ==
source_game_id`) correctly special-cases `IS NOT DISTINCT FROM` for legacy NULL-source
rows; the optimistic-concurrency `WHERE confirmed = false AND source_game_id IS NOT
DISTINCT FROM :expected_source` guards on `_promote_cache_rows`/`_replace_cache_rows`
correctly no-op (rather than corrupt) a write raced by a concurrent lane; `_fetch_dedup_evals`
is genuinely the only confirmed-filter site, and its only caller for lease-omission
(`_fetch_cached_opening_hashes`) delegates rather than re-implementing the gate, so the two
read paths cannot drift as the docstring claims. The migration's keyset walk (`cursor`
advances to `max(marked_hashes)` each pass, terminates when a pass returns nothing) is
correct given the repair pipeline's actual data shape — `orphans` only ever deletes
`opening_position_eval` rows for still-`pending` audit rows, which the migration's
`status IN ('screened_clean','confirmed_clean','repaired')` filter already excludes, so
the migration's implicit "every selected audit row still has a matching position_eval
row" assumption holds today.

The issues below are real but all WARNING-tier: a stale docstring that flatly
contradicts the actual (correct) CACHEFIX-12 wiring in exactly the area this review was
asked to scrutinize (the drain-tick vs. atomic-submit race), a provenance-metadata bug
that undermines the `demote` operator escape hatch, a non-transactional Sentry side
effect that can fire without a matching commit, a documented-but-unmonitored silent data
loss path on the insert race, and two coverage gaps in the exact mechanisms (migration
loop, optimistic-concurrency guards) this review was asked to verify.

## Warnings

### WR-01: `apply_full_eval` docstring flatly contradicts the actual CACHEFIX-12 wiring it documents

**File:** `app/services/eval_apply.py:2868-2874`
**Issue:** The docstring for `apply_full_eval` states:

> `update_opening_cache` / `upsert_opening_cache_fn` (Pitfall 4): `_full_drain_tick`
> passes `update_opening_cache=True` with `_upsert_opening_cache` ... `_apply_atomic_submit`
> leaves `update_opening_cache=False` (its current behavior — **the opening cache is NOT
> populated from atomic-submit workers**). This is a deliberate, explicit parameter (not
> silently unified) per RESEARCH.md Pitfall 4 / D-05.

This is false for the code as written today. `app/routers/eval_remote.py:1405-1483`
(CACHEFIX-12, per its own inline comments) builds `_cache_targets` and calls
`apply_full_eval(..., update_opening_cache=bool(_cache_targets),
upsert_opening_cache_fn=_upsert_opening_cache, engine_targets_for_cache=_cache_targets)`
— the atomic-submit lane genuinely does write to `opening_position_eval` through the
exact same `_upsert_opening_cache` the drain tick uses (confirmed independently by
`app/services/eval_drain.py:888` and `:1522`, which both correctly describe the
"one function, two call sites" reality). The docstring predates CACHEFIX-12 and was never
updated.

This is exactly the area the review brief flagged ("race conditions between the drain
tick and the atomic submit lane writing the same full_hash") — a maintainer who trusts
this docstring will conclude no such race exists and skip reasoning about it, when in
fact both lanes genuinely write to the same table concurrently (correctly, via the
optimistic-concurrency guards — see the Summary — but the docstring denies the premise
entirely).

**Fix:**
```python
# app/services/eval_apply.py, apply_full_eval docstring
update_opening_cache / upsert_opening_cache_fn (Pitfall 4, CACHEFIX-12): both
_full_drain_tick (eval_drain.py) and the router's _apply_atomic_submit
(eval_remote.py) pass update_opening_cache=True with _upsert_opening_cache as
upsert_opening_cache_fn -- the SAME two-source-confirmation write path handles
concurrent writes from both lanes to the same full_hash via the optimistic-
concurrency guards in _promote_cache_rows/_replace_cache_rows (see their
docstrings). The atomic-submit lane scopes engine_targets_for_cache to
_cache_targets (plies the worker itself evaluated, excluding dedup hits) --
see eval_remote.py's own CACHEFIX-12 comments for that derivation.
```

### WR-02: `engine_version` on cache writes always records the server's local Stockfish, not the remote worker's

**File:** `app/services/eval_drain.py:263-268, 691, 774`; called from `app/routers/eval_remote.py:1451-1482`
**Issue:** `_insert_cache_candidates` and `_replace_cache_rows` both stamp
`engine_version = await _get_cached_engine_version()`, which memoizes
`engine_service.get_stockfish_version()` — a UCI handshake against the **server's own
local** Stockfish binary (`app/services/engine.py:391-401`). This function is invoked
identically regardless of whether the eval it is stamping came from the drain tick's own
local engine call or from a **remote worker's** submitted result via
`_apply_atomic_submit` (`app/routers/eval_remote.py:1451-1482`, `update_opening_cache=bool(_cache_targets)`).

A remote worker's actual Stockfish build is `body.sf_version`, already available at the
call site and used for the SF-version gate (`app/routers/eval_remote.py:1533`,
`settings.EXPECTED_SF_VERSION`) and the heartbeat (`heartbeat_sf_version=body.sf_version`).
When `settings.EXPECTED_SF_VERSION` is unset (no gate configured — fully legal per the
gate's own `if settings.EXPECTED_SF_VERSION and ...` guard), a worker on a different
Stockfish build than the server's own local process can still submit, and its cache
writes get silently mislabeled with the server's version string.

This directly undermines the one place `engine_version` is actually read:
`scripts/opening_cache_repair.py`'s `demote` operator escape hatch
(`_demote_affected_count`/`_demote_apply`, lines 1777-1832), whose entire purpose
(per its own docstring at 1846-1854) is to let an operator selectively un-confirm rows
"recorded against `engine_version`" after "a bump that changes the eval SCALE (a new NNUE
net)". If a fleet of remote workers ran a stale/different engine build, `demote` cannot
find those rows by their true engine version — they are all mislabeled with whatever the
server process's local binary reports.

**Fix:** Thread the true source engine version through `_upsert_opening_cache` instead of
re-deriving it from the local process:
```python
async def _upsert_opening_cache(
    session: AsyncSession,
    engine_targets: list[_FullPlyEvalTarget],
    engine_result_map: dict[int, tuple[int | None, int | None, str | None, str | None]],
    source_game_id: int,
    source_engine_version: str | None = None,  # None -> fall back to local (drain tick)
) -> None:
    ...
    engine_version = source_engine_version or await _get_cached_engine_version()
```
and pass `source_engine_version=body.sf_version` from `_apply_atomic_submit`'s
`upsert_opening_cache_fn` call site (threading it through `apply_full_eval`'s existing
`upsert_opening_cache_fn` callback signature).

### WR-03: D-12 Sentry disagreement alert fires as a non-transactional side effect before commit

**File:** `app/services/eval_drain.py:641-676, 796-809`
**Issue:** `_replace_cache_rows` calls `_capture_opening_cache_disagreement` (which calls
`sentry_sdk.capture_message`) immediately after `session.execute(...)`, i.e. **inside**
the caller's still-open write transaction (`apply_full_eval`'s `write_session`,
committed only later — see the sequencing in `eval_apply.py`'s `apply_full_eval`
docstring: opening-cache upsert runs before `apply_completion_decision` and the
worker-heartbeat upsert, both of which can still raise). If any later step in the same
`write_session` raises (e.g. `apply_completion_decision`, the heartbeat upsert, or a
concurrent advisory-lock/deadlock issue), the whole transaction rolls back — including
this cache write — but the Sentry "two consecutive evaluations disagreed" alert has
already fired unconditionally and cannot be un-fired. This produces a phantom alert for a
disagreement that was never actually persisted, undermining exactly the signal D-12 is
designed to be trustworthy for (a genuine misalignment-pattern detector, not noise).

**Fix:** Defer the Sentry capture until after `write_session.commit()` succeeds — collect
disagreement events from `_replace_cache_rows` (return them instead of firing inline) and
have the caller (`apply_full_eval`'s caller, after its own commit) fire them, mirroring
how `_apply_atomic_submit` already defers its own "signal after commit" hook
(`app/routers/eval_remote.py:1487-1488`, "Signal after commit so the hook never fires for
a partially-committed game").

### WR-04: Concurrent first-writer race on a brand-new position silently drops the losing write without comparison

**File:** `app/services/eval_drain.py:678-722` (`_insert_cache_candidates`)
**Issue:** When two different games reach the same **not-yet-cached** opening position at
the same time, both read `existing_by_hash` as empty and both route to the `insert`
bucket. `INSERT ... ON CONFLICT (full_hash) DO NOTHING` means only the first committer's
value is stored; the second, independently-computed value is discarded entirely —
never compared via `_cache_values_agree`, never counted as an agreement or a
disagreement. The code comment acknowledges this ("this result becomes the second source
next time this position is reached"), but that framing is imprecise: the second writer's
*specific* result is gone forever, not deferred — a genuinely independent second opinion
on a brand-new position is lost with zero observability (no counter, no Sentry breadcrumb,
no test), silently weakening the two-source guarantee's actual coverage in exactly the
highest-value case (fresh positions with no confirmation history yet). This is a rare race
in absolute terms but the position space is opening moves specifically, which are the most
frequently re-visited (cross-user, high fan-out) positions in the whole cache.

**Fix:** At minimum, add a counter/log line when `_insert_cache_candidates`'s row count
returned by the `ON CONFLICT DO NOTHING` (via `RETURNING full_hash`) is smaller than the
number of rows attempted, so the frequency of this silent drop is observable. Consider
whether the lost write should instead route through the same "read again, then
promote/replace" path used for an existing row, to actually capture the second opinion.

### WR-05: Migration's multi-batch keyset-walk loop is never exercised by a test with >1 iteration

**File:** `alembic/versions/20260912_120000_b7d4f5a60002_phase_220_cache_provenance.py:130-140`
**Issue:** The migration's `upgrade()` runs a `while True` loop with cursor advance
(`cursor = max(marked_hashes)`) and termination-on-empty-batch — this is exactly the
mechanism the review brief asked to verify for "termination, cursor advance, NULL cursor
cast". The only test that exercises `MARK_CONFIRMED_SQL`
(`tests/models/test_opening_cache_audit_models.py::test_migration_marking_matches_status`,
lines 297-345) runs the SQL statement directly, once, with `batch_size=1000` against a
handful of seeded rows — i.e. it validates the SQL predicate's status-filtering
correctness but never drives the Python loop through more than one pass, so the
cursor-advance-and-continue behavior (and the `cursor > :cursor` boundary, and that a
second pass correctly excludes already-marked rows) is entirely untested.

**Fix:** Add a test that seeds more `screened_clean`/`confirmed_clean`/`repaired` rows
than a small `batch_size`, calls the migration's `upgrade()` (or drives the same loop
directly against `MARK_CONFIRMED_SQL` with e.g. `batch_size=2` over 5 qualifying rows),
and asserts all rows end up marked and the loop terminates in the expected number of
passes.

### WR-06: No test proves the optimistic-concurrency guard actually rejects a stale write

**File:** `app/services/eval_drain.py:746-809` (`_promote_cache_rows`, `_replace_cache_rows`)
**Issue:** Both functions rely on `WHERE full_hash = :fh AND confirmed = false AND
source_game_id IS NOT DISTINCT FROM :expected_source` to detect and silently drop a write
built from a stale snapshot (the exact mechanism that makes the drain-tick vs.
atomic-submit race safe — see the Summary). `tests/services/test_eval_drain.py`'s
write-path tests (`test_disagree_replaces_unconfirmed_candidate`,
`test_promote_confirms_on_agreement`, `test_agree_boundary_promotes_exactly_at_constant`,
`test_disagree_second_fires_sentry_at_two`, `test_confirmed_immutable_except_pv_heal`,
`test_self_promotion_guarded_by_source_game_id`) all exercise `_partition_cache_writes`/
`_apply_cache_writes` against a single, uncontested snapshot. None of them construct the
"stale `expected_source`" scenario directly (e.g. call `_promote_cache_rows`/
`_replace_cache_rows` with an `expected_source` that no longer matches the row's actual
`source_game_id`, simulating a concurrent write that landed between the read and this
write) to prove the guard actually causes the write to no-op rather than silently
corrupting/overwriting a row that changed underneath it.

**Fix:** Add a direct unit test: seed a confirmed-false row with `source_game_id=A`, call
`_promote_cache_rows`/`_replace_cache_rows` with an `expected_source=B` (simulating a
stale read), and assert the row is unchanged (still `source_game_id=A`,
`confirmed=false`, `disagreements` unincremented) — proving the WHERE guard's silent-no-op
behavior this review had to verify by code reading alone.

---

_Reviewed: 2026-09-11_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
