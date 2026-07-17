---
phase: 174-backend-maia-inference-best-move-storage-spike-gated
reviewed: 2026-07-16T00:00:00Z
depth: standard
files_reviewed: 6
files_reviewed_list:
  - app/services/eval_drain.py
  - app/services/eval_apply.py
  - app/routers/eval_remote.py
  - app/services/eval_queue_service.py
  - app/models/game.py
  - alembic/versions/20260716_171823_1eda5daba951_phase_174_07_lichess_best_move_backfill_.py
findings:
  critical: 0
  warning: 3
  info: 2
  total: 5
resolved: [WR-01, WR-02]
resolved_in: 5f0c42aa
open: [WR-03, IN-01, IN-02]
status: issues_found
---

# Phase 174: Code Review Report (Plans 06 + 07 gap-closure)

**Reviewed:** 2026-07-16
**Depth:** standard
**Files Reviewed:** 6
**Status:** issues_found (no Critical/BLOCKER findings; 3 Warnings, 2 Info)
**Resolved:** WR-01, WR-02 fixed in `5f0c42aa` (2026-07-16). WR-03, IN-01, IN-02 remain open.

## Summary

Reviewed the diff introduced by 174-06 (retire the lichess-eval targets filter,
route lichess-eval games through the unified full-ply MultiPV-2 pass, fix the
CR-01 book-depth bug) and 174-07 (broaden the tier-3 residual-fallback
predicate from `full_evals_completed_at IS NULL` to `full_pv_completed_at IS
NULL`, backed by a renamed/broadened partial index) against baseline
`dd7c018b`. This is a re-review scoped strictly to these two gap-closure
plans; a prior 174-REVIEW.md covered the earlier best-move-storage
implementation and is superseded by this one per the workflow's request.

Verified directly rather than taking the plan summaries at face value:

- `uv run alembic check` reports "No new upgrade operations detected" — the
  model's `Index()` declaration and the new migration's predicate/name agree
  exactly; the migration's `upgrade()`/`downgrade()` round-trip is symmetric.
- The CR-01 `_contiguous_san_prefix` rewrite is correct: it reconstructs the
  SAN prefix from the deepest target's `board.move_stack` (which always
  carries the true, complete push history regardless of which other targets
  are present) rather than depending on ply 0 being present in a possibly
  sparse `targets` list. Confirmed both real call sites (`_full_drain_tick`,
  `_apply_atomic_submit`) now always pass the full contiguous targets list
  post-174-06, so the fix is defense-in-depth today, matching the plan's own
  framing.
- The hole-counting parity fix for lichess-eval games (`_apply_full_eval_results`)
  is directionally correct, and the dedup-bypass (`dedup_map` always empty for
  lichess games) that makes "NULL best_move ⇒ genuine engine failure" a valid
  premise is real and consistently threaded through both `eval_drain.py` and
  `eval_remote.py`.
- The 174-07 predicate broadening is a true superset (an eval-incomplete
  lichess game is necessarily pv-incomplete too), precedence is unchanged, and
  the new partial index matches the broadened predicate exactly in both the
  migration and the ORM model.
- Ran the full affected test suite (`test_eval_apply.py`, `test_full_eval_drain.py`,
  `test_eval_queue.py`, `test_eval_worker_endpoints.py` together): 3 tests fail
  in that combined run (`TestGuestExclusion::test_guest_exclusion`,
  `TestTier3Lottery::test_tier3_guest_excluded_from_lottery`,
  `TestTier3Lottery::test_residual_fallback_excludes_guest_backlog_game`) but
  pass in isolation. Reproduced the same two pre-existing failures against the
  `dd7c018b` baseline in an isolated git worktree — this is inherited
  shared-DB test-isolation debt (already documented in the project's own
  memory notes), not a regression introduced by 174-06/07. See WR-03 below for
  the residual concern this still leaves.

No Critical/BLOCKER-level defects found: no SQL injection, no hardcoded
secrets, no data-loss risk, and the migration is schema-consistent both ways.
The Warnings below are real robustness/documentation gaps worth fixing before
174-07's backfill lottery runs unattended against ~43k games for an extended
period, but none block shipping this diff.

## Warnings

### WR-01: `preserve_existing_evals` is silently ignored in the lichess-eval hole-counting branch — ✅ RESOLVED (5f0c42aa)

> **Resolved 2026-07-16 (`5f0c42aa`):** Took the first fix option (thread an explicit
> "already has best_move" signal). Added `_FullPlyEvalTarget.stored_best_move` and a new
> `_is_lichess_best_move_hole()` helper mirroring `_is_engine_hole()`; the lichess branch
> now routes its hole decision through it (`elif` instead of an unconditional `else`). The
> stored best_move is threaded only by the atomic-submit path (the sole `preserve_existing_evals=True`
> caller) via a new optional `stored_best_move_by_ply` param and a `GamePosition.best_move`
> column added to that path's SELECT; the drain leaves it `None` (no-op). Proven by
> `test_lichess_preserve_existing_evals_skips_already_resolved_hole` — reverting the guard
> to an unconditional `else` fails it (`assert 1 == 0`).

**File:** `app/services/eval_apply.py:556-573`
**Issue:** The engine-game branch (`app/services/eval_apply.py:579-591`) uses
`_is_engine_hole(target, preserve_existing_evals)` to avoid double-counting a
hole when an incremental re-lease (SEED-076) legitimately omitted an
already-resolved position and the worker simply didn't resend it. The new
`is_lichess_eval_game` branch added in 174-06 has no equivalent guard — it
increments `failed_ply_count` on any `best_move is None`, unconditionally,
even though `atomic_submit_eval`'s caller passes `preserve_existing_evals=True`
for every game (`app/routers/eval_remote.py:1201`) regardless of
`is_lichess_eval_game`.

In practice this is masked today because `_build_lease_positions` now bypasses
the SEED-076 redundancy filter entirely for lichess-eval games (`is_lichess_eval_game
or not _lease_position_redundant(...)`, `app/routers/eval_remote.py:345`) — every
position is always re-leased on every retry, so the incremental-omission case
that `preserve_existing_evals` exists to protect against cannot occur through
the *cache-aware-omission* path. But it CAN occur through ordinary flakiness: on
a Path-B retry, a ply whose `best_move` was already successfully written in a
prior attempt can still be re-leased, re-submitted, and legitimately fail again
(transient worker/engine hiccup) on the SAME ply that already has a good value
stored. Because the `_FullPlyEvalTarget` dataclass carries no "does this row
already have a best_move" signal for lichess games (unlike `eval_cp`/`eval_mate`,
which the engine-game branch uses as that signal — and which is *useless* here
since lichess rows always have a non-NULL `eval_cp`/`eval_mate` from import),
this branch cannot distinguish "already resolved, not a real failure" from "genuinely
failed this attempt." The result: `failed_ply_count` is overcounted in that
scenario, forcing an unnecessary extra Path-B retry cycle for a game that
already has complete best-move coverage at that ply. Bounded by
`MAX_EVAL_ATTEMPTS` (Path C eventually completes), so this is a robustness/test-
coverage gap, not a data-loss or correctness bug — but it's an inconsistency
with the pattern the engine-game branch just fixed for the exact same reason,
and it is completely untested (`preserve_existing_evals` never appears in a
lichess-branch test in `tests/services/test_eval_apply.py` or
`tests/test_eval_worker_endpoints.py`).
**Fix:** Either thread an explicit "already has best_move" signal into
`_FullPlyEvalTarget` for lichess-eval games (mirroring `_is_engine_hole`'s
existing-eval check), or document explicitly that `preserve_existing_evals` is
a no-op for lichess-eval games and accept the retry-churn tradeoff. A one-line
comment noting this is a deliberate simplification (with the tradeoff spelled
out) would at least prevent a future reader from assuming the parameter is
honored uniformly.

### WR-02: Stale `_flaw_engine_plies` reference left in a docstring after the function was deleted — ✅ RESOLVED (5f0c42aa)

> **Resolved 2026-07-16 (`5f0c42aa`):** Rewrote the stale comment to describe the current
> mechanism (post-174-06 lichess games run the full MultiPV-2 pass, so ply N is
> engine-evaluated like every other ply; the `_flaw_engine_plies` selective path is
> retired). The other two references (`eval_drain.py`, `eval_apply.py`) already described it
> as retired and were left unchanged.

**File:** `app/services/eval_apply.py:996-998`
**Issue:** `_classify_and_fill_oracle`'s flaw-PV-write comment still reads:
"Each pv_string comes from engine_result_map at its OWN ply. For lichess games
ply N is engine-evaluated thanks to `_flaw_engine_plies` (SEED-054 Part 1); for
chess.com every ply already ran." `_flaw_engine_plies` was deleted in this same
plan's Task 1 (confirmed: zero remaining references anywhere in `app/` other
than two other, already-updated docstrings that correctly describe it as
retired — `app/services/eval_drain.py:498` and `app/services/eval_apply.py:1063`).
This one comment was missed and now describes a mechanism that no longer
exists; the underlying claim ("lichess ply N is engine-evaluated") is still
true, but for a different reason (the full MultiPV-2 pass, not the deleted
pre-classification helper). CLAUDE.md's own "Comment bug fixes" convention
explicitly asks future readers not to have to dig through git history to
understand non-obvious code — a stale reference to a deleted symbol does the
opposite.
**Fix:**
```python
# Each pv_string comes from engine_result_map at its OWN ply. For lichess games
# every non-terminal ply is engine-evaluated directly (Phase 174-06 — the full
# MultiPV-2 pass, no pre-classification helper); for chess.com every ply already
# ran.
```

### WR-03: New guest-exclusion regression test inherits pre-existing shared-DB test-isolation flakiness

**File:** `tests/services/test_eval_queue.py:1205-1250` (`test_residual_fallback_excludes_guest_backlog_game`, added by 174-07)
**Issue:** Confirmed by direct reproduction: running
`test_eval_apply.py + test_full_eval_drain.py + test_eval_queue.py +
test_eval_worker_endpoints.py` together in one pytest session fails 3
guest-exclusion-related tests (including the new 174-07 test) that all pass
individually and pass when `test_eval_queue.py` runs alone (31/31, 3 repeated
runs). Reproduced the same failure pattern (2 of the 3 tests — the third is
new to this plan) against the `dd7c018b` baseline in an isolated git worktree,
confirming this is *inherited* test-isolation debt from the shared,
session-scoped test DB (already documented in the project's own memory notes
on eval-lottery test isolation), not something 174-06/07 introduced. Flagging
because the new test rides on top of a known-fragile shared-state pattern
without adding any isolation of its own — though to be fair, it DOES clean up
its own inserted row via `finally: await _delete_games(...)`, so the fragility
comes entirely from OTHER tests' leaked rows polluting the shared DB within the
same pytest session, not from this test's own hygiene.
**Fix:** Not blocking for this plan (pre-existing, out of 174-06/07's declared
scope), but worth a follow-up: either give the eval-lottery test classes a
per-test-scoped Postgres schema/transaction rollback instead of a shared
session-scoped DB, or audit every test in this file (not just the new one)
for the `finally`-cleanup discipline the project's own memory note already
prescribes.

## Info

### IN-01: `_classify_with_overlay`'s `overlay=False` mode is dead code with zero test coverage, contradicting its own docstring

**File:** `app/services/eval_apply.py:1042-1072`
**Issue:** The updated docstring claims `overlay=False` is "kept as a
documented, tested mode for a future direct-classify caller, not dead weight."
Verified: after deleting `_flaw_engine_plies` (its only caller), there are
exactly 3 remaining call sites of `_classify_with_overlay` in the entire
codebase (`app/services/eval_apply.py:1232`, `:1355`, `app/services/eval_drain.py:521`)
and all 3 pass `overlay=True`. No test anywhere calls `_classify_with_overlay`
with `overlay=False`. The branch is therefore genuinely dead and untested today
— the docstring's "tested" claim is inaccurate. This is a minor inconsistency
with the same plan's own stated rationale for deleting `_flaw_engine_plies`
("a genuinely dead, untestable helper... which the plan's own acceptance
criteria implicitly requires cleaning up").
**Fix:** Either add a small unit test exercising `overlay=False` directly (cheap,
since the function is already structured to support it) so the docstring's
claim is true, or soften the docstring to say "currently untested, kept for a
future caller" rather than "tested."

### IN-02: Migration's `drop_index(..., postgresql_where=...)` predicate is inert but harmless

**File:** `alembic/versions/20260716_171823_1eda5daba951_phase_174_07_lichess_best_move_backfill_.py:54-61`, `:74-79`
**Issue:** `op.drop_index()` is passed a `postgresql_where=` kwarg for both the
old-index drop in `upgrade()` and the new-index drop in `downgrade()`. Postgres's
`DROP INDEX` statement takes no `WHERE` clause — Alembic accepts and stores the
kwarg for metadata/reflection purposes only; it has no effect on the emitted
DDL. Not a bug (correctly drops by name either way, confirmed by the clean
`alembic check` + `upgrade`/`downgrade`/`upgrade` round-trip), and it does match
the project's documentation-heavy migration style, but a future reader might
reasonably (and incorrectly) assume the predicate is load-bearing for the drop.
**Fix:** No action required; optional — a one-line comment noting `postgresql_where`
here is documentation-only (the DROP INDEX statement ignores it) would prevent
a future reader from assuming it changes drop behavior.

---

_Reviewed: 2026-07-16_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
