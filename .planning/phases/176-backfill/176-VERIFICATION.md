---
phase: 176-backfill
verified: 2026-07-17T00:00:00Z
status: passed
score: 5/5 must-haves verified
behavior_unverified: 0
overrides_applied: 0
---

# Phase 176: Backfill Verification Report

**Phase Goal:** The existing analyzed corpus gains best-move rows opportunistically, without a deterministic sweep or an ETA promise, so historical games gradually become eligible for gem/great markers and filtering.
**Verified:** 2026-07-17
**Status:** passed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | A PV-complete, best-move-incomplete, non-lichess-eval, non-guest game is periodically selected by the tier-4b lottery and drained through the Phase 174 best-move pipeline (SC1, BACK-01). | ✓ VERIFIED | `_claim_tier4_bestmove` (`app/services/eval_queue_service.py:666-743`) implements the two-stage ES-weighted pick with predicate `full_pv_completed_at IS NOT NULL AND best_moves_completed_at IS NULL AND lichess_evals_at IS NULL` in both Stage-1 EXISTS and Stage-2 WHERE. `test_backfill_pick_drains_and_stamps_best_moves_completed_at` runs a real `_full_drain_tick()`, verifies exactly 1 `game_best_moves` row is created at the correct ply and `best_moves_completed_at`/`full_pv_completed_at` are stamped. Test passes (ran live). |
| 2 | The tier-4b lottery uses the same plain-SELECT/no-lock concurrency shape as the existing tier-4 blob rung and is ordered after it in the bundled scope=None ladder (SC2, D-02). | ✓ VERIFIED | Source read confirms `_claim_tier4_bestmove` has no `FOR UPDATE SKIP LOCKED` / no `eval_jobs` row, identical to `_claim_tier4_blob` (code review IN-01 independently confirms this). `claim_eval_job` (`eval_queue_service.py:852-874`) calls `_claim_tier4_blob` first; only when `blob_pick is None` does it check `BEST_MOVE_BACKFILL_ENABLED` and call `_claim_tier4_bestmove` — confirmed ordering by source read. |
| 3 | A game that has been through the best-move pass gets `best_moves_completed_at` stamped and is never re-selected by tier-4b (self-termination, D-01). | ✓ VERIFIED | Same end-to-end test asserts the stamp is set AND separately re-queries the tier-4b predicate after the tick to confirm the game no longer matches (self-termination). Column is excluded from the lottery predicate once non-NULL by construction. |
| 4 | A Maia-absent backend never stamps `best_moves_completed_at` — no permanent lockout of any game from the backfill lottery (guardrail). | ✓ VERIFIED | `test_maia_absent_never_stamps_best_moves_completed_at` forces `maia_engine._session = None` while mocking `score_move` to SUCCEED (so `best_move_rows` would be non-empty if row-count alone gated the stamp) and asserts `best_moves_completed_at` stays NULL. **Mutation-tested during this verification**: temporarily removed the `if maia_available:` guard around the Path-A `_mark_best_moves_completed` call in `app/services/eval_apply.py` — the test immediately failed (as expected); restored the guard and the test passed again. This proves the guardrail is behaviorally load-bearing, not merely present. |
| 5 | tier-4b runs only when BOTH `BEST_MOVE_BACKFILL_ENABLED` and `EVAL_AUTO_DRAIN_ENABLED` are true (D-05). | ✓ VERIFIED | `claim_eval_job` checks `EVAL_AUTO_DRAIN_ENABLED` at the top of the bundled-flow branch (line 829) and `BEST_MOVE_BACKFILL_ENABLED` again immediately before the tier-4b DB round-trip (line 861), before either the tier-3 or tier-4-blob rungs are even considered for tier-4b dispatch. `test_gated_off` (in `TestTier4bBestMoveBackfill`) confirms `BEST_MOVE_BACKFILL_ENABLED=False` with `EVAL_AUTO_DRAIN_ENABLED=True` suppresses tier-4b. Test passes. |

**Score:** 5/5 truths verified

### Note on SC3 (coverage-growth over time)

ROADMAP SC3 ("Best-move-row coverage across the analyzed corpus visibly increases over time") is explicitly scoped in `176-VALIDATION.md` as **Manual-Only** — an operational, snapshot-diff observation made after `BEST_MOVE_BACKFILL_ENABLED` is flipped to `true` in production (D-05: the flag stays `False` in this merge by design). This mirrors the accepted precedent from Phase 174-07's tier-4 blob backfill (see `174-VERIFICATION.md`: "expected for an opportunistic, no-ETA backfill... not counted as a gap"). The *mechanism* that would produce this growth (the tier-4b lottery + self-terminating stamp) is fully verified above (Truths 1/3); the growth itself cannot be observed at merge time because the kill-switch is intentionally off. Not treated as a gap or a human-verification blocker — it is a deliberate, documented post-rollout operational check, consistent with the phase's own design.

### Required Artifacts

| Artifact | Expected | Status | Details |
|---|---|---|---|
| `app/models/game.py` | `best_moves_completed_at` column + `ix_games_bestmove_backfill_pending` partial index | ✓ VERIFIED | Column at line 222; index at lines 97-104. `postgresql_where` text: `"full_pv_completed_at IS NOT NULL AND best_moves_completed_at IS NULL AND lichess_evals_at IS NULL"`. |
| `alembic/versions/20260717_035706_939c3d99868d_...py` | Column + partial index + D-04 one-time stamp, byte-identical index predicate to the model | ✓ VERIFIED | `create_index` predicate text is byte-identical to the model's. `alembic check` reports "No new upgrade operations detected." **WR-01 fix confirmed**: the D-04 `UPDATE` now requires `full_pv_completed_at IS NOT NULL` and stamps that value directly (no `now()` fallback) — commit `83fe9dde` verified present in the current file. |
| `app/services/eval_queue_service.py` | `_claim_tier4_bestmove` rung wired into `claim_eval_job` after the blob pick | ✓ VERIFIED | Lines 666-743 (function), 855-874 (wiring). |
| `app/models/eval_jobs.py` | `TIER_BESTMOVE_BACKFILL` constant | ✓ VERIFIED | `TIER_BESTMOVE_BACKFILL: int = 5` at line 26. |
| `app/services/maia_engine.py` | `is_maia_available()` public accessor | ✓ VERIFIED | Line 121, returns `_session is not None`. |
| `app/services/eval_apply.py` | `_mark_best_moves_completed` + `maia_available` param threaded into `apply_completion_decision` | ✓ VERIFIED | `_mark_best_moves_completed` at line 687; `maia_available` param at line 714, used on Path A (773-774) and Path C (790-791); single call site (`apply_full_eval` line 2100/2137) computes it via `maia_engine.is_maia_available()`, never inferred from row count. |
| `app/core/config.py` | `BEST_MOVE_BACKFILL_ENABLED` bool (default False) | ✓ VERIFIED | Line 96. |
| `tests/services/test_eval_queue.py` / `test_full_eval_drain.py` | `TestTier4bBestMoveBackfill`; `TestBestMoveBackfill` | ✓ VERIFIED | 9 tests + 2 tests, both classes present and collected; all 11 pass (ran live: `11 passed in 4.19s`). |

### Key Link Verification

| From | To | Via | Status | Details |
|---|---|---|---|---|
| `claim_eval_job` | `_claim_tier4_bestmove` | Called only after `blob_pick is None`, gated by `settings.BEST_MOVE_BACKFILL_ENABLED` checked before the DB round-trip | ✓ WIRED | Source-confirmed at `eval_queue_service.py:855-864`. |
| `apply_completion_decision` Path A/C | `_mark_best_moves_completed` | `if maia_available:` guard | ✓ WIRED (mutation-tested) | Confirmed present in code AND confirmed load-bearing by temporarily removing the guard and observing the guardrail test fail, then restoring it and observing the test pass again. |
| `app/models/game.py` index `postgresql_where` | Migration `create_index` `postgresql_where` | Byte-identical text | ✓ WIRED | Both read: `"full_pv_completed_at IS NOT NULL AND best_moves_completed_at IS NULL AND lichess_evals_at IS NULL"`. `alembic check` clean. |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|---|---|---|---|
| New tier-4b + backfill tests pass | `uv run pytest tests/services/test_eval_queue.py::TestTier4bBestMoveBackfill tests/services/test_full_eval_drain.py::TestBestMoveBackfill -q` | `11 passed in 4.19s` | ✓ PASS |
| maia_engine tests unaffected | `uv run pytest tests/services/test_maia_engine.py -q` | `4 passed, 2 skipped` | ✓ PASS |
| Migration round-trip / drift-free | `uv run alembic current` (dev DB at `939c3d99868d (head)`) + `uv run alembic check` | "No new upgrade operations detected." | ✓ PASS |
| Guardrail mutation test | Removed `if maia_available:` guard around Path-A stamp in `eval_apply.py`, re-ran `test_maia_absent_never_stamps_best_moves_completed_at` | Test FAILED (`MissingGreenlet`/assertion path hit as expected) — restored, test passed again | ✓ PASS (proves the guardrail is behaviorally load-bearing) |
| ty check on modified files | `uv run ty check app/models/game.py app/models/eval_jobs.py app/core/config.py app/services/eval_apply.py app/services/eval_queue_service.py app/services/maia_engine.py` | 3 pre-existing `onnxruntime`/`numpy` unresolved-import errors (confirmed present before this phase via `git show 4b7291c4:app/services/maia_engine.py`), zero new errors | ✓ PASS |
| ruff format/check | `uv run ruff check` + `uv run ruff format --check` on all 9 modified files | "All checks passed!" / "9 files already formatted" | ✓ PASS |
| Anti-pattern scan | `grep -E "TBD|FIXME|XXX|TODO|HACK|PLACEHOLDER"` on all modified files | No matches | ✓ PASS |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|---|---|---|---|---|
| BACK-01 | 176-01-PLAN.md | The existing analyzed corpus gains best-move rows opportunistically via the tier-4 lottery pattern (global + random, no deterministic sweep, no ETA); backfill lottery keying decided at phase planning. | ✓ SATISFIED | Parallel tier-4b rung (D-02 decision) implemented, tested, mutation-verified for the correctness-critical guardrail. REQUIREMENTS.md traceability table shows `BACK-01 \| Phase 176 \| Complete`, no orphans (11/11 requirements mapped per REQUIREMENTS.md footer). |

No orphaned requirements — BACK-01 is the only requirement mapped to Phase 176 and it is fully accounted for.

### Anti-Patterns Found

None. Code review (`176-REVIEW.md`) found 1 warning (WR-01, a real D-04 migration-stamp defect) which was fixed in commit `83fe9dde` and independently re-verified above by reading the current migration file. The 2 remaining info-level findings (IN-01: inherited no-lock concurrency shape — accepted, matches existing tier-3/4 pattern; IN-02: missing symmetric gate-independence test) are non-blocking and do not affect goal achievement.

### Human Verification Required

None. All must-haves are verified via code, live test execution, and one mutation test on the safety-critical guardrail. SC3 (coverage-growth-over-time) is a documented, by-design post-rollout operational observation (see note above) — not a merge-time gap and not routed to human verification, consistent with the accepted Phase 174-07 precedent.

### Gaps Summary

No gaps. All 5 must-have truths verified, all 8 required artifacts verified at exists/substantive/wired levels, both key links verified (one via mutation test), 11/11 new tests pass live, migration round-trips cleanly with zero alembic drift, WR-01 fix from code review confirmed present in the current codebase, requirements traceability clean with no orphans, and no anti-patterns or debt markers in any modified file.

---

*Verified: 2026-07-17*
*Verifier: Claude (gsd-verifier)*
