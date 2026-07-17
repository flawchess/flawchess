---
phase: 174-backend-maia-inference-best-move-storage-spike-gated
verified: 2026-07-16T20:15:00Z
status: passed
score: 5/5 must-haves verified
behavior_unverified: 0
overrides_applied: 0
re_verification:
  previous_status: gaps_found
  previous_score: 4/5
  gaps_closed:
    - "Every newly analyzed game stores a candidate row for each out-of-book ply where played == Stockfish best AND the inaccuracy gate passes (ROADMAP SC2 / GEMS-01/02/03) — now closed for lichess-eval games via Plans 06 (unified full MultiPV-2 pass, CR-01 book-depth fix, hole-counting parity, /atomic-lease skip removed) and 07 (broadened residual PV-backfill predicate + supporting partial index)."
  gaps_remaining: []
  regressions: []
---

# Phase 174: Backend Maia Inference + Best-Move Storage (spike-gated) Verification Report

**Phase Goal:** Every newly analyzed game automatically stores per-ply Maia-3 probability + Stockfish best/runner-up eval for out-of-book best-move plies that clear the inaccuracy gate, computed once during eval-apply from a Python port of the client's board→tensor encoding, validated against client output.
**Verified:** 2026-07-16T20:15:00Z
**Status:** passed
**Re-verification:** Yes — after gap closure (Plans 06 + 07 addressing the prior `174-VERIFICATION.md` gaps_found report)

## Goal Achievement

### Observable Truths

| # | Truth (ROADMAP Success Criteria) | Status | Evidence |
|---|-----------------------------------|--------|----------|
| 1 | A fixture-based parity test proves the Python port of the 12-plane encoding + onnxruntime Maia-3 inference matches the client's onnxruntime-web output within an agreed tolerance, gating all further work (D-01/D-02). | ✓ VERIFIED (regression-checked) | Re-ran live: `uv run --group maia-inference python scripts/maia_parity_spike.py` exits 0. All 11 fixture plies tier-match; measured max drift 0.003844 vs `PARITY_EPSILON=0.01`. Unaffected by the 06/07 diff (neither plan touches `maia_encoding.py`/`maia_engine.py`/the spike script). |
| 2 | Every newly analyzed game stores a candidate row (`game_best_moves`) for each out-of-book ply where played == Stockfish best AND `best_es − second_es ≥ INACCURACY_DROP` (0.05); rows hold `maia_prob` + best/second eval as floats, unique on `(game_id, ply)`. | ✓ VERIFIED — **prior gap CLOSED** | Was ✗ FAILED (partial) in the prior report for lichess-eval games. Now closed by two independently-verified fixes (see "Gap Closure Verification" below): (a) 174-06 retires the local-drain targets filter so lichess-eval games get the SAME full-ply MultiPV-2 pass as engine games — code-traced in `eval_drain.py` (`dedup_hashes = []` for lichess games, so `engine_targets == targets`, full coverage); (b) the CR-01 book-depth bug is fixed in `_contiguous_san_prefix` (rebuilt from `board.move_stack` instead of a ply-0-anchored walk over a possibly-sparse `targets` list) — **mutation-tested**: reverting the fix locally makes `test_sparse_targets_book_depth_not_collapsed_cr01` fail, confirming the test is not a symbol-presence check; (c) the hole-counting parity fix in `_apply_full_eval_results`'s `is_lichess_eval_game` branch is also **mutation-tested**: reverting it makes `test_lichess_game_forced_null_best_move_is_a_hole_not_false_completion` fail; (d) `/atomic-lease` no longer skips lichess-eval games (204 removed, confirmed via source read); (e) 174-07's broadened residual-fallback predicate (`full_pv_completed_at IS NULL`) was independently confirmed against the LIVE dev DB: `pv_complete=677`, `backfill_eligible=3862` out of `4539` total lichess-eval games — an EXACT match to 174-07-SUMMARY.md's own reported numbers, cross-validating the SUMMARY claim rather than trusting it. |
| 3 | Maia inference runs on the backend during eval-apply (not remote workers, no worker-protocol change) using the mover's pinned lichess-blitz-equivalent rating, clamped to [600, 2600]. | ✓ VERIFIED (regression-checked) | `git diff main..HEAD --stat -- scripts/remote_eval_worker.py app/schemas/eval_remote.py Dockerfile.worker` = empty; `grep -c 'onnxruntime\|maia' scripts/remote_eval_worker.py` = 0. Unaffected by 06/07 (those plans thread `is_lichess_eval_game` through `/atomic-lease`'s existing shape, adding no new worker-side logic). |
| 4 | `onnxruntime` and `numpy` are isolated behind a uv extra/dependency group; installing the worker image's dependency set does not pull them in. | ✓ VERIFIED (regression-checked) | Unaffected by 06/07 diff. `tests/test_dependency_isolation.py` (7 tests) pass in the full suite run below. |
| 5 | Re-querying stored rows against Gem (`maia_prob ≤ 0.20`) / Great (`(0.20, 0.50]`) thresholds and `MISTAKE_DROP` (0.10) reclassifies gems/greats with zero re-analysis. | ✓ VERIFIED (regression-checked) | Unaffected by 06/07 diff (`best_move_candidates.py` untouched). `tests/services/test_best_move_candidates.py` passes in the full suite run below. |

**Score:** 5/5 truths verified (prior partial failure now closed)

### Gap Closure Verification (the prior report's single failing truth)

The prior `174-VERIFICATION.md` (gaps_found, 4/5) failed Truth 2 specifically for lichess-eval games processed via the local full-drain lane: the out-of-book gate silently collapsed (book_plies≈0) and candidate coverage was reduced to holes + flaw-adjacent plies only. Plans 06 and 07 targeted this gap directly. Re-verified below — not by trusting SUMMARY prose, but by reading the actual code and, for the two most safety-critical fixes, reverting them locally and confirming the regression tests fail (mutation testing per project convention):

| Fix | File | Verification method | Result |
|---|---|---|---|
| Retire lichess-eval `targets` filter — full MultiPV-2 pass for every ply | `app/services/eval_drain.py` (`_full_drain_tick`, `dedup_hashes`/`engine_targets` construction) | Source read: `dedup_hashes = []` for `is_lichess_eval_game`, so every non-terminal ply falls into `engine_targets` unconditionally | ✓ Confirmed in code |
| CR-01 book-depth fix (`_contiguous_san_prefix` rebuilt from `board.move_stack`) | `app/services/eval_apply.py:1692-1732` | **Mutation test**: swapped in the pre-fix (`fb1bd216^`) implementation, re-ran `test_sparse_targets_book_depth_not_collapsed_cr01` → FAILED (produces the bogus row exactly as the pre-fix bug would). Restored the fix, test passes again. | ✓ Behaviorally proven, not just present |
| Hole-counting parity for lichess-eval games (`_apply_full_eval_results`) | `app/services/eval_apply.py:556-573` | **Mutation test**: removed the `else: failed_ply_count += 1` branch, re-ran `test_lichess_game_forced_null_best_move_is_a_hole_not_false_completion` → FAILED. Restored, test passes again. | ✓ Behaviorally proven, not just present |
| `/atomic-lease` no longer skips lichess-eval games | `app/routers/eval_remote.py` | Source read: no 204-skip remains for `is_lichess_eval_game`; `_build_lease_positions` bypasses the SEED-076 redundancy filter for these games | ✓ Confirmed in code + `test_atomic_lease_lichess_eval_game_returns_full_positions` / `test_atomic_submit_lichess_eval_game_produces_best_move_candidate_row` pass (realistic HTTP-endpoint-level integration tests, not stubs — read in full) |
| 174-07 broadened residual-fallback predicate + partial index | `app/services/eval_queue_service.py`, `app/models/game.py`, migration `1eda5daba951` | `uv run alembic check` → "No new upgrade operations detected"; live dev-DB query independently reproduced the SUMMARY's own numbers (677 pv-complete / 3862 backfill-eligible / 4539 total lichess-eval games) — exact match | ✓ Confirmed in code + live data cross-check |

**Note on live dev-DB state:** `game_best_moves` currently has 0 rows in the dev DB, and no full-drain activity has occurred since 2026-07-14 (before Plans 06/07 shipped) — the local drain loop is simply idle (no new game imports triggering it), not broken. This is expected for an opportunistic, no-ETA backfill (by design, per 174-07's own framing) and is not counted as a gap: the code path that would produce these rows is proven correct by the mutation-tested unit/integration tests above, which exercise the exact production code (not fixtures divorced from it).

### Required Artifacts

| Artifact | Expected | Status | Details |
|---|---|---|---|
| `app/services/eval_drain.py` | Lichess-eval targets filter retired; unified full-ply pass | ✓ VERIFIED | Confirmed via source read; `dedup_hashes`/`engine_targets` always full for lichess games. |
| `app/services/eval_apply.py` | CR-01 book-depth fix; hole-counting parity for lichess-eval games | ✓ VERIFIED | Both mutation-tested (see table above). |
| `app/routers/eval_remote.py` | `/atomic-lease` skip removed; lease-redundancy bypass for lichess games | ✓ VERIFIED | Source read + passing integration tests. |
| `app/services/eval_queue_service.py` | Residual fallback predicate broadened (`full_pv_completed_at IS NULL`) | ✓ VERIFIED | Source read + 8 passing unit tests + live dev-DB cross-check. |
| `app/models/game.py` + migration `1eda5daba951` | `ix_games_lichess_pv_backfill_pending` partial index, supersedes old index | ✓ VERIFIED | `alembic check` clean; migration up/down round-trip verified by the plan executor and reconfirmed via `alembic check` here. |
| All Phase 174-01..05 artifacts (encoding, engine, candidates, table, isolation) | Unaffected by 06/07 | ✓ VERIFIED (regression) | Full suite green; parity spike re-run green; `ty check` clean. |

### Key Link Verification

| From | To | Via | Status | Details |
|---|---|---|---|---|
| `eval_drain.py::_full_drain_tick` | `eval_apply.py::_build_best_move_candidates` | Unified full MultiPV-2 pass feeds a complete `engine_result_map`/`second_best_map` | ✓ WIRED | Confirmed no targets-filter remains before the builder call. |
| `eval_remote.py::/atomic-lease` → `/atomic-submit` | `eval_apply.py::apply_full_eval` (`best_move_rows=`) | Remote lane now covers lichess-eval games too | ✓ WIRED | `test_atomic_submit_lichess_eval_game_produces_best_move_candidate_row` proves the full round trip. |
| `eval_queue_service.py::_claim_tier3_derived` residual fallback | `eval_drain.py::_full_drain_tick` | Broadened predicate selection → drain → `full_pv_completed_at` stamp → self-termination | ✓ WIRED | `test_backfill_pick_drains_gets_best_moves_and_self_terminates` (real, unmocked `claim_eval_job` selection routed through one drain tick) passes. |

### Behavioral Spot-Checks / Probe Execution

| Behavior | Command | Result | Status |
|---|---|---|---|
| Parity spike gate (regression) | `uv run --group maia-inference python scripts/maia_parity_spike.py` | Exit 0; "PARITY GATE PASSED" | ✓ PASS |
| CR-01 mutation test | Revert `_contiguous_san_prefix` fix, run named test | Test FAILS (as expected) | ✓ PASS (proves fix is load-bearing) |
| Hole-counting mutation test | Revert `failed_ply_count` increment, run named test | Test FAILS (as expected) | ✓ PASS (proves fix is load-bearing) |
| Named regression tests (post-restore) | `uv run pytest tests/services/test_eval_apply.py::TestCandidateGate::test_sparse_targets_book_depth_not_collapsed_cr01 tests/services/test_full_eval_drain.py::TestLichessBestMoveBackfill tests/services/test_eval_queue.py::TestTier3Lottery` | 15 passed | ✓ PASS |
| Full backend suite | `uv run pytest -n auto` | 3380 passed, 18 skipped | ✓ PASS |
| Type check | `uv run ty check app/ tests/` | "All checks passed!" | ✓ PASS |
| Alembic drift check | `uv run alembic check` | "No new upgrade operations detected" | ✓ PASS |
| Live dev-DB predicate cross-check | Direct SQL against `flawchess` dev DB | `total_lichess=4539, pv_complete=677, backfill_eligible=3862` (exact match to 174-07-SUMMARY.md) | ✓ PASS |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|---|---|---|---|---|
| GEMS-01 | 174-03, 174-07 | `game_best_moves` sibling table + broadened backfill selection | ✓ SATISFIED | Model/migration verified; 174-07 predicate broadening confirmed live. |
| GEMS-02 | 174-04, 174-05, 174-06 | Candidate gate: out-of-book + played==best + inaccuracy margin | ✓ SATISFIED — **upgraded from PARTIALLY SATISFIED** | CR-01 book-depth fix + unified full-ply pass close the lichess-eval coverage gap; mutation-tested. |
| GEMS-03 | 174-04, 174-05, 174-06, 174-07 | Backend scores candidates with Maia-3 during eval-apply; workers stay pure Stockfish | ✓ SATISFIED — **upgraded from PARTIALLY SATISFIED** | Backend-only inference unaffected; `/atomic-lease` no longer skips lichess games; worker protocol still untouched (`git diff` empty). |
| GEMS-04 | 174-01 | Python port passes fixture-based parity check | ✓ SATISFIED | Spike re-run, still passes. |
| GEMS-05 | 174-04 | Pinned lichess-blitz-equivalent rating, clamped [600, 2600] | ✓ SATISFIED | Unaffected; regression-checked via full suite. |
| GEMS-06 | 174-02 | onnxruntime/numpy isolated behind a uv dependency group | ✓ SATISFIED | Unaffected; regression-checked. |
| GEMS-07 | 174-04 | Query-time Gem/Great classification, zero re-analysis | ✓ SATISFIED | Unaffected; regression-checked. |

No orphaned requirements — all 7 GEMS IDs declared across the 7 plans map 1:1 to `REQUIREMENTS.md` entries (lines 14-20), and its Phase 174 mapping table (lines 60-66) lists all 7 as Complete with no additional IDs.

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|---|---|---|---|---|
| `app/services/eval_apply.py` | 556-573 | `preserve_existing_evals` silently ignored in the new `is_lichess_eval_game` hole-counting branch (WR-01, 174-REVIEW.md) | ⚠️ Warning | Robustness/retry-churn gap, not data loss: a Path-B retry can over-count a ply that already has a good stored `best_move` as a "failure," forcing an extra bounded retry cycle (Path C eventually completes via `MAX_EVAL_ATTEMPTS`). Does not defeat any must-have truth. |
| `app/services/eval_apply.py` | 996-998 | Stale docstring reference to deleted `_flaw_engine_plies` helper (WR-02) | ℹ️ Info | Documentation staleness only; underlying claim is still true for a different reason. |
| `tests/services/test_eval_queue.py` | 1205-1250 | New guest-exclusion test inherits pre-existing shared-DB test-isolation flakiness when run in combination with 3 other test files (WR-03) | ℹ️ Info | Confirmed by the code reviewer to reproduce against the pre-174-06/07 baseline too (inherited, not introduced). Does not manifest under this project's mandated `-n auto` invocation (full suite green, 3380 passed). |
| — | — | No `TBD`/`FIXME`/`XXX` debt markers found in any file touched by Plans 06/07. | — | Debt-marker gate clean. |

## Gaps Summary

None. The single failing truth from the prior verification (out-of-book candidate coverage for lichess-eval games) is now closed, independently re-verified through source reads, a live dev-DB cross-check of the SUMMARY's own numbers, and — for the two safety-critical fixes (CR-01 book-depth, hole-counting parity) — mutation testing that proves the regression tests are load-bearing rather than symbol-presence checks. The three Warnings from the fresh `174-REVIEW.md` (WR-01/02/03) are real but non-blocking: WR-01 is a bounded retry-churn robustness gap (not data loss), WR-02 is a stale comment, and WR-03 is inherited, pre-existing test-isolation debt that does not manifest under the project's own `-n auto` test invocation.

The full backend suite (3380 passed, 18 skipped), `ty check` (clean), and `alembic check` (clean) all pass. The parity spike (Truth 1's own gate) was re-run live and still passes with tier-stability. Phase 174 goal is achieved: every newly analyzed game — across the local-drain lane, remote-worker lane, and the opportunistic 43k-game lichess-eval backlog — now flows through a unified path capable of storing best-move candidate rows for every out-of-book played==best ply that clears the inaccuracy gate.

---

_Verified: 2026-07-16T20:15:00Z_
_Verifier: Claude (gsd-verifier)_
