---
phase: 116-all-ply-engine-core
fixed_at: 2026-06-12T14:30:00Z
review_path: .planning/phases/116-all-ply-engine-core/116-REVIEW.md
iteration: 1
findings_in_scope: 9
fixed: 9
skipped: 0
status: all_fixed
---

# Phase 116: Code Review Fix Report

**Fixed at:** 2026-06-12T14:30:00Z
**Source review:** .planning/phases/116-all-ply-engine-core/116-REVIEW.md
**Iteration:** 1

**Summary:**
- Findings in scope: 9 (1 Critical, 8 Warning; fix_scope=critical_warning, 6 Info findings out of scope)
- Fixed: 9
- Skipped: 0

Verification: `ty check app/ tests/` clean, `ruff check` clean, `ruff format --check app/ tests/` clean, and all touched test suites pass (tests/services/test_full_eval_drain.py, tests/services/test_engine_nodes.py, tests/test_migration_116_full_evals.py, plus sibling suites tests/services/test_eval_drain.py, test_engine.py, test_eval_drain_stage_b.py — 45 passed, 4 skipped).

Note on apply order: WR-05 was applied after WR-07 (out of document order) because its circuit breaker changes the semantics of `test_marker_set_with_holes`, which WR-07 first converts to deterministic tick-based form. All other findings were applied in severity/document order.

## Fixed Issues

### CR-01: Migration backfill marks zero games — terminal-position row always has NULL evals

**Files modified:** `alembic/versions/20260612_120000_add_full_evals_completed_at.py`, `tests/test_migration_116_full_evals.py`
**Commit:** 19a375a7
**Status:** fixed: requires human verification
**Applied fix:** Added `AND gp.move_san IS NOT NULL` to the backfill anti-join (move_san IS NULL is the per-row terminal marker) with an in-code bug-fix comment, and updated the migration docstring (the 798ms EXPLAIN claim is flagged as predating the new predicate). Both backfill tests now insert a terminal row (move_san NULL, NULL evals) plus move_san on non-terminal rows so fixtures match real `process_game_pgn` output; `_insert_game_position` requires an explicit `move_san` argument.
**Human verification needed:** (a) the SQL predicate is a logic fix — confirm intent; (b) the review's residual caveat stands: lichess typically emits no `%eval` on a game-ending mating move, so decisive analyzed games may still have a NULL at the last non-terminal ply and stay unmarked (conservative under-marking — the drain fills them, but it shrinks the seeded dedup set). Decide explicitly whether that is acceptable, ideally by probing real lichess-analyzed games on dev/prod. Also consider re-running EXPLAIN on dev to refresh the cost estimate for a now-nonzero-row UPDATE.

### WR-01: Drain evaluates plies whose results are deterministically discarded for is_analyzed games

**Files modified:** `app/services/eval_drain.py`
**Commit:** c871074f
**Applied fix:** `_FullPlyEvalTarget` now carries the row's current `eval_cp`/`eval_mate`; `_collect_full_ply_targets` populates them. For `is_analyzed` games, covered plies are filtered out of `targets` BEFORE dedup partitioning and the gather, so no 1M-node calls are burned on results the D-116-04 gate would discard. The write-time preservation check remains as a belt-and-braces guard, now using the carried values (no `gp_rows` re-scan — this incidentally resolves IN-04 as the review anticipated).

### WR-02: Dedup transplants post-move lichess evals onto pre-move position hashes

**Files modified:** `app/services/eval_drain.py`, `tests/services/test_full_eval_drain.py`
**Commit:** 584bc399
**Applied fix:** `_fetch_dedup_evals` now adds `Game.white_blunders.is_(None)` to the source-set predicate, restricting dedup sources to engine-written rows (position-keyed by construction). Docstring documents the post-move vs pre-push hash mismatch rationale. Added regression test `test_dedup_excludes_analyzed_source`.

### WR-03: ruff format --check fails on 4 of 9 reviewed files

**Files modified:** `app/services/engine.py`, `app/services/eval_drain.py`, `tests/services/test_engine_nodes.py`, `tests/services/test_full_eval_drain.py`, `tests/test_migration_116_full_evals.py`
**Commit:** 83db4c8a
**Applied fix:** Ran `ruff format` over the phase files (applied last, after all code fixes). `ruff format --check app/ tests/` is now clean. Note: 46 pre-existing "would reformat" files remain under `alembic/versions/` from earlier migrations — outside both the project's CI gate scope (`app/ tests/`) and this review's scope; the Phase 116 migration itself is format-clean.

### WR-04: run_full_eval_drain breaches the hard nesting limit and inlines the write stage

**Files modified:** `app/services/eval_drain.py`
**Commit:** 3ca231d2
**Applied fix:** Extracted the write stage into `_apply_full_eval_results(session, targets, dedup_map, engine_result_map, is_analyzed)` (mirroring `_apply_eval_results`) and the per-ply resolution priority (dedup > engine > hole) into the pure function `_resolve_full_eval`. Combined with the WR-07 tick extraction, the coroutine's nesting is back within CLAUDE.md limits and the resolution priority is unit-testable.

### WR-05: Per-ply Sentry messages + no circuit breaker for a dead engine pool

**Files modified:** `app/services/eval_drain.py`, `tests/services/test_full_eval_drain.py`
**Commit:** 8a3aca8b
**Applied fix:** (a) `_apply_full_eval_results` no longer emits per-ply Sentry messages; it returns a `failed_ply_count` and the tick emits ONE aggregated event per game with `failed_ply_count` in context. (b) Circuit breaker in `_full_drain_tick`: when engine targets exist and EVERY result is `(None, None)`, the game is NOT marked complete — one Sentry event is emitted and the tick returns False (game stays pending; loop sleeps and retries). Per-position holes remain mark-and-continue per D-116-07. `test_marker_set_with_holes` was reworked to a partial-failure scenario (the all-fail case now legitimately trips the breaker) and `test_all_fail_keeps_game_pending` covers the breaker. Behavior change to D-116-07's "mark unconditionally" semantics is deliberate per the review; flagging for awareness.

### WR-06: EnginePool.evaluate_nodes duplicates evaluate wholesale

**Files modified:** `app/services/engine.py`
**Commit:** 1765ce11
**Applied fix:** Extracted the shared worker-acquisition / analyse / restart-on-failure / slot-release path into `EnginePool._analyse(board, limit, timeout)`. `evaluate()` and `evaluate_nodes()` are now one-line wrappers passing `Limit(depth=_DEPTH), _TIMEOUT_S` and `Limit(nodes=_NODES_BUDGET), _NODES_TIMEOUT_S` respectively. The `_NODES_TIMEOUT_S` monkeypatch in test_engine_nodes.py still works (module global read at call time); all engine tests pass.

### WR-07: Marker tests run the real drain loop against shared per-run DB state

**Files modified:** `app/services/eval_drain.py`, `tests/services/test_full_eval_drain.py`
**Commit:** 618c3d10
**Applied fix:** Extracted the tick body into `_full_drain_tick() -> bool` (True = game processed); `run_full_eval_drain` is now a thin loop that sleeps only when the tick processed nothing. Marker tests call `_full_drain_tick()` directly via a shared `_patch_drain_for_tick_tests` helper that also forces the yield gate to False (eliminating the ordering-dependent flake; the gate itself stays covered by TestYieldGate). Removes ~6s of guaranteed wall-clock sleep per run. The QUEUE-07 AST regression test now scans `_full_drain_tick` (where the gather lives post-extraction).

### WR-08: ply <= 20 coupling invariant maintained by comments in three places

**Files modified:** `app/models/game_position.py`, `app/services/eval_drain.py`
**Commit:** 6ed83540
**Applied fix:** Defined `DEDUP_MAX_PLY: int = 20` next to `MAX_EXPLORER_PLY` in the model with a coupling-invariant docstring; the `ix_gp_full_hash_opening` predicate now interpolates it (`text(f"ply <= {DEDUP_MAX_PLY}")`, following the file's established MAX_EXPLORER_PLY pattern). `eval_drain.py` imports it and aliases `_DEDUP_MAX_PLY = DEDUP_MAX_PLY` (no separate literal). The migration keeps its literal `20` (frozen history, per the review).

## Skipped Issues

None — all in-scope findings were fixed. Info findings (IN-01 through IN-06) were out of scope (fix_scope=critical_warning); note IN-04 was incidentally resolved by the WR-01 fix.

---

_Fixed: 2026-06-12T14:30:00Z_
_Fixer: Claude (gsd-code-fixer)_
_Iteration: 1_
