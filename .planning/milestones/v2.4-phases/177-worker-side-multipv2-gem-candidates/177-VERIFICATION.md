---
phase: 177-worker-side-multipv2-gem-candidates
verified: 2026-07-17T21:10:00Z
status: passed
score: 20/20 must-haves verified
behavior_unverified: 0
overrides_applied: 0
---

# Phase 177: Worker-side MultiPV-2 gem-candidate searches, protocol v2 Verification Report

**Phase Goal:** Shift the gem-candidate MultiPV-2 runner-up search off the server's engine pool onto the remote worker fleet (protocol v2), add an isolated tier-4b lease/submit lane to backfill best-move data for already-analyzed games, give the server drain a tier-aware minimal path, and record the D-07 post-deploy before/after measurement.
**Verified:** 2026-07-17T21:10:00Z
**Status:** passed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

Merged from all 5 plans' `must_haves.truths` (20 total, no roadmap-level `success_criteria` block exists for this phase — narrative Goal + `Requirements` list in ROADMAP.md is the contract).

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | A v1 worker (or one omitting `worker_schema_version`) gets 204 on `/atomic-lease` for BOTH `scope=explicit` and `scope=idle` (D-01/S-03) | ✓ VERIFIED | `app/routers/eval_remote.py:424-466` — gate is the first statement before `claim_eval_job`; `test_atomic_lease_v1_worker_204` PASSED (ran live) |
| 2 | A v2 worker's `/atomic-submit second_best` entries populate `second_best_map` so the server runs ZERO fallback Stockfish searches for those plies (S-04/PROTO-03) | ✓ VERIFIED | `app/routers/eval_remote.py:1234-1236`; `test_build_best_move_candidates_uses_submitted_second_best`, `test_no_fallback_when_second_best_present` PASSED (spy on `evaluate_nodes_multipv2` asserts zero calls) |
| 3 | A `second_best` entry with ply outside `[0, game_length)` is rejected 422 before any DB write (S-02) | ✓ VERIFIED | `app/routers/eval_remote.py:1205-1210`; `test_atomic_submit_second_best_out_of_range_422` PASSED |
| 4 | `/atomic-lease` response carries `move_uci` per position so the worker can compare its own MultiPV-1 best against the played move | ✓ VERIFIED | `app/schemas/eval_remote.py:37`; `test_atomic_lease_v2_worker_carries_move_uci`, `test_lease_position_move_uci_defaults_none` PASSED |
| 5 | `_build_best_move_candidates` fallback branch emits a Sentry tag naming its source (D-06/OBS-01) | ✓ VERIFIED | `app/services/eval_apply.py:1910` `sentry_sdk.set_tag("source", source)`; `test_best_move_candidates_fallback_source_tag` PASSED |
| 6 | `/bestmove-lease` returns ONLY server-recomputed candidate plies (out-of-book, played == stored best_move) (S-05) | ✓ VERIFIED | `app/services/eval_apply.py:2047-2128` `_build_bestmove_lease_positions`; `test_bestmove_lease_candidate_plies` PASSED |
| 7 | Candidate inaccuracy gate reads eval-of-position(ply) from stored row (ply-1); ply=0 resolves to (None, None) without crashing (Pitfall 1) | ✓ VERIFIED | `app/services/eval_apply.py:2024-2044` `_eval_of_position_map` — dict never populates key 0, `.get(ply, (None, None))` used by callers; `TestEvalOfPositionMap` tests referenced in 177-02-SUMMARY.md coverage table |
| 8 | `/bestmove-submit` writes ONLY `game_best_moves` rows + stamps `best_moves_completed_at`; never calls `apply_full_eval` / `_classify_and_fill_oracle` (S-06/D-02) | ✓ VERIFIED | `app/services/eval_apply.py:2152-2269` — isolated write session, no shared call; `test_bestmove_submit_minimal_write_no_reclassify`, `test_bestmove_submit_existing_flaws_unchanged` PASSED |
| 9 | A tier-4b pick with zero candidate plies (or over `MAX_SUBMIT_EVALS`) stamps `best_moves_completed_at` directly and 204s (Pitfall 2, ES-lottery self-termination) | ✓ VERIFIED | `app/routers/eval_remote.py:1387-1391`; `test_bestmove_lease_zero_candidates_stamps_completed` PASSED |
| 10 | The submit recomputes the candidate-ply set server-side and drops/422s any submitted ply outside it (D-03 stateless recompute) | ✓ VERIFIED | `app/services/eval_apply.py:2236-2250`; `test_bestmove_submit_out_of_range_ply_422`, `test_bestmove_submit_foreign_ply_dropped` PASSED |
| 11 | `_full_drain_tick` on a `TIER_BESTMOVE_BACKFILL` claim runs the minimal candidate-only path, not the full every-ply gather + `apply_full_eval` reclassify (fixes `_ = tier` no-op, Pitfall 3) | ✓ VERIFIED | `app/services/eval_drain.py:861-865` branch is before Step 2/3; `test_full_drain_tick_tier4b_minimal_path` PASSED (asserts `apply_full_eval` NOT called, exactly 2 engine calls) |
| 12 | Tier-4b drain path writes only `game_best_moves` + `best_moves_completed_at`, reusing the same server-side candidate/writer helper as `/bestmove-submit` (D-05) | ✓ VERIFIED | `app/services/eval_drain.py:664-819` `_tier4b_minimal_drain_tick` reuses `_build_bestmove_lease_positions`/`_eval_of_position_map`/`_stamp_best_moves_completed_directly`; same test as #11 |
| 13 | Drain-local candidate fallback is Sentry-tagged `source='drain-local'`, distinguishable from `worker-submit-fallback` (D-06) | ✓ VERIFIED | `app/services/eval_drain.py:799` `source="drain-local"`; `test_tier4b_drain_local_fallback_tagged_source` PASSED |
| 14 | `WORKER_SCHEMA_VERSION == 2` and is sent as a query param on the `/atomic-lease` call (not just in the submit body) (PROTO-01/Pitfall 4) | ✓ VERIFIED | `scripts/remote_eval_worker.py:110,717,734`; `test_worker_schema_version_is_2` PASSED |
| 15 | After its MultiPV-1 full pass, the worker runs a targeted `evaluate_nodes_multipv2` ONLY for plies where its own best move == the leased `move_uci`; the full-ply pass stays MultiPV-1 (S-01, Phase 146 D-03 invariant) | ✓ VERIFIED | `scripts/remote_eval_worker.py:339-395` `_eval_targeted_second_best`; `test_eval_atomic_game_targeted_second_best_only_played_best` PASSED; pre-existing `test_eval_positions_uses_multipv1_no_second_best` still green in full suite run |
| 16 | Worker's rung-5 handler leases `/bestmove-lease`, evaluates candidate FENs at MultiPV-2 only (no full pass, no blob walk), and submits to `/bestmove-submit` | ✓ VERIFIED | `scripts/remote_eval_worker.py:903-975` `_eval_bestmove_positions`/`_handle_bestmove_response`; `test_handle_bestmove_response_submits_n_entries_no_atomic_submit` PASSED |
| 17 | Rung 5 is placed AFTER rung 4 (`/flaw-blob-lease`), preserving `TIER_BLOB_BACKFILL(4) < TIER_BESTMOVE_BACKFILL(5)` (Pitfall 6) | ✓ VERIFIED | `scripts/remote_eval_worker.py:737-751` — bestmove-lease call is nested inside the `blob_resp.status_code == 204` branch; `test_ladder_bestmove_lease_only_after_flaw_blob_204` PASSED |
| 18 | A post-deploy before/after comparison is recorded against the SEED-111 2026-07-17 baseline (games/h, worker busy %, server pool %, worker-submit fallback count, double-claim rate) | ✓ VERIFIED | `177-MEASUREMENT.md` — full before/after table with 6 figures, each traced to a named instrument (prod DB, access logs, `/proc`-tick CPU samples, Sentry) |
| 19 | worker-submit-fallback Sentry dimension confirmed ~zero steady-state; sustained non-zero flagged as D-06 regression signal | ✓ VERIFIED | `177-MEASUREMENT.md` §"Fallback verdict": 0 events recorded, with an honestly-documented instrument caveat (only errored fallbacks captured) and one flagged-for-watch anomaly (single unrelated 422) |
| 20 | Double-claim rate recorded so D-08 (deferred TTL-lease escalation) can be decided on real data | ✓ VERIFIED | `177-MEASUREMENT.md` §"Double-claim / D-08 recommendation": not measurable in the single-active-host window, explicit "defer" recommendation recorded with reasoning |

**Score:** 20/20 truths verified (0 present-but-behavior-unverified)

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `app/schemas/eval_remote.py` | `move_uci` on `LeasePosition`, `AtomicSecondBestEval`, `second_best[]`, `BestMove*` schema pair | ✓ VERIFIED | All present; `BestMoveLeasePosition` correctly omits `move_uci` per plan |
| `app/routers/eval_remote.py` | `worker_schema_version` gate on `/atomic-lease`; `/bestmove-lease` + `/bestmove-submit` endpoints | ✓ VERIFIED | `WORKER_SCHEMA_VERSION_MIN=2` gate at line 465-466; endpoints at 1349-1426 |
| `app/services/eval_apply.py` | `_build_lease_positions` emits `move_uci`; `_build_best_move_candidates(source=...)`; `_eval_of_position_map`; `_build_bestmove_lease_positions`; `_apply_bestmove_submit`; `_stamp_best_moves_completed_directly` | ✓ VERIFIED | All symbols present and wired |
| `app/services/eval_drain.py` | Early `if tier == TIER_BESTMOVE_BACKFILL:` branch before Step 3; `_tier4b_minimal_drain_tick` | ✓ VERIFIED | Branch at line 864-865, before PGN load (Step 2) and gather (Step 3) |
| `app/core/config.py` | Corrected `BEST_MOVE_BACKFILL_ENABLED` comment | ✓ VERIFIED | No longer states "cannot be shed to the remote worker fleet" |
| `scripts/remote_eval_worker.py` | `WORKER_SCHEMA_VERSION=2`; targeted second-best re-search; `_handle_bestmove_response`; rung-5 in `_run_cycle` | ✓ VERIFIED | All present and correctly ordered |
| `.planning/phases/177-.../177-MEASUREMENT.md` | Before/after table with 6 D-07 figures | ✓ VERIFIED | Present, committed (6921a4b1), non-fabricated per its own self-check |

### Key Link Verification

| From | To | Via | Status | Details |
|------|-----|-----|--------|---------|
| `worker_schema_version` Query param | 204 gate | applied to BOTH scopes before `claim_eval_job` | ✓ WIRED | Confirmed first statement in `atomic_lease_eval_game` (line 465-466), before any claim logic |
| `body.second_best` | `second_best_map` | dict → `_build_best_move_candidates(..., second_best_map, source='worker-submit-fallback')` | ✓ WIRED | `app/routers/eval_remote.py:1234-1237` |
| `/bestmove-lease` | `_claim_tier4_bestmove(session)` | DIRECT call, mirroring `flaw_blob_lease` → `_claim_tier4_blob` | ✓ WIRED | `app/routers/eval_remote.py:1377` |
| `_apply_bestmove_submit` | `best_move_candidates` pure fns | reused via `_build_best_move_candidates` (no re-derivation) | ✓ WIRED | `app/services/eval_apply.py:2252-2254` |
| `_tier4b_minimal_drain_tick` | Plan 02's `_build_bestmove_lease_positions` + minimal writer + `_stamp_best_moves_completed_directly` | reused (not re-derived) | ✓ WIRED | `app/services/eval_drain.py` imports and calls all three |
| Drain's fresh-lane candidate call | `_build_best_move_candidates` | `source='drain-local'` | ✓ WIRED | `app/services/eval_drain.py:799` |
| leased `move_uci` per position | fresh-lane targeted re-search | drives played==best comparison | ✓ WIRED | `scripts/remote_eval_worker.py:368-376` |
| worker `_run_cycle` rung 5 | `/bestmove-lease` → `/bestmove-submit` | strictly after rung 4 (`/flaw-blob-lease`) | ✓ WIRED | `scripts/remote_eval_worker.py:737-751` |
| Sentry source tags (`worker-submit-fallback` vs `drain-local`) | regression-watch instrument | read in D-07 measurement | ✓ WIRED | `177-MEASUREMENT.md` §5 explicitly reads the `worker-submit-fallback` dimension |

### Behavioral Spot-Checks

All named tests below were run directly by the verifier (not taken from SUMMARY claims), one test/small group at a time, never the full suite per-check:

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| v1 worker 204 on atomic-lease | `pytest tests/test_eval_worker_endpoints.py::TestAtomicLeaseEndpoint::test_atomic_lease_v1_worker_204` | 1 passed | ✓ PASS |
| move_uci on lease response | `pytest ...::test_lease_position_move_uci_defaults_none ...::test_atomic_lease_v2_worker_carries_move_uci` | 2 passed | ✓ PASS |
| bestmove-lease candidate plies + minimal submit isolation | `pytest ...::TestBestMoveLeaseEndpoint::test_bestmove_lease_candidate_plies ...::TestBestMoveSubmitEndpoint::test_bestmove_submit_minimal_write_no_reclassify` | 2 passed | ✓ PASS |
| Pitfall-1 fallback / source tag | `pytest tests/services/test_eval_apply.py::TestPitfall1Fallback` (4 tests) | 4 passed | ✓ PASS |
| Drain tier branch (minimal path vs full path) | `pytest tests/services/test_full_eval_drain.py::TestBestMoveBackfill::test_full_drain_tick_tier4b_minimal_path ...::test_non_tier4b_claim_still_takes_full_path` | 2 passed | ✓ PASS |
| Worker script v2 (schema version, targeted search, rung ladder) | `pytest tests/test_remote_eval_worker.py -k "bestmove or targeted_second_best or worker_schema_version_is_2 or ladder"` | 11 passed | ✓ PASS |
| Full backend suite (run once) | `pytest -n auto` | 3482 passed, 18 skipped | ✓ PASS |
| Type check | `uv run ty check app/ tests/` | zero errors | ✓ PASS |
| Debt-marker scan (TBD/FIXME/XXX/TODO/HACK/PLACEHOLDER) | `grep` across 6 modified files | none found | ✓ PASS |
| Deployment confirmation | `git log origin/production`, `gh pr view 260` | `3efc7172` on `production`, PR #260 MERGED 2026-07-17T17:42:00Z | ✓ PASS |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|------------|-------------|--------|----------|
| PROTO-01 | 01, 04 | Lease-level version gating, both scopes; worker sends version at lease time | ✓ SATISFIED | Truths #1, #14 |
| PROTO-02 | 04 | Worker-side targeted MultiPV-2 re-search preserving MultiPV-1 full pass | ✓ SATISFIED | Truth #15 |
| PROTO-03 | 01 | Worker second_best eliminates server fallback searches | ✓ SATISFIED | Truth #2 |
| BACK-02 | 02 | `/bestmove-lease` server-recomputed candidate reconstruction | ✓ SATISFIED | Truths #6, #7, #9 |
| BACK-03 | 02 | `/bestmove-submit` minimal isolated write, no reclassify | ✓ SATISFIED | Truths #8, #10 |
| DRAIN-01 | 03 | Tier-aware minimal drain path for tier-4b | ✓ SATISFIED | Truths #11, #12 |
| OBS-01 | 01, 03 | Sentry source-tagged fallback (worker-submit-fallback vs drain-local) | ✓ SATISFIED | Truths #5, #13 |
| MEAS-01 | 05 | D-07 post-deploy before/after measurement | ✓ SATISFIED | Truths #18, #19, #20 |

No orphaned requirements — all 8 requirement IDs in the phase's `Requirements` line are claimed by exactly one plan each (PROTO-01 claimed by both 01 and 04, which is a legitimate split: 01 does the server-side gate, 04 does the worker-side send).

### Anti-Patterns Found

None blocking. No debt markers (TBD/FIXME/XXX/TODO/HACK/PLACEHOLDER) in any of the 6 modified files. No stub returns, no hardcoded-empty data flows, no console.log-only implementations.

**Two advisory findings from `177-REVIEW.md` are carried forward here for visibility (not must-have failures — confirmed present in the codebase during this verification, but not part of any plan's `must_haves`):**

- **CR-01 (critical, review-flagged):** `_apply_bestmove_submit` (`app/services/eval_apply.py:2256-2267`) stamps `best_moves_completed_at` unconditionally, without the Phase 176 D-01 `maia_available` guardrail that its sibling `_tier4b_minimal_drain_tick` (Plan 03) explicitly added. Confirmed present in the current codebase during this verification pass (line-for-line matches the review's finding). On a backend where `maia_engine.is_maia_available()` is `False`, `/bestmove-submit` writes zero `game_best_moves` rows yet still stamps completion — permanently excluding that game from the tier-4b lottery with no resweep path. Per this verification's explicit scope instruction, this is **not** treated as a must-have failure (no plan's `must_haves` names the Maia guardrail for the wire endpoint), but it is a real production data-integrity risk that should be fixed as a fast follow-up before `BEST_MOVE_BACKFILL_ENABLED` is flipped on in prod with a Maia-degraded backend.
- **WR-01 (warning, review-flagged):** `_eval_bestmove_positions` (`scripts/remote_eval_worker.py:903-929`) does not drop engine-failure results (all-`None` 7-tuples) the way its sibling `_eval_targeted_second_best` does — confirmed present. A single transient Stockfish failure on the worker silently and permanently forfeits that gem/great candidate rather than falling through to the server's fallback.

### Human Verification Required

None. MEAS-01's human-verify checkpoint (Plan 05) was already executed and user-approved during phase execution (per task context: "user-approved with a partial-rollout caveat"), and its artifact (`177-MEASUREMENT.md`) is complete and verified above. No further human action is required to close this phase's verification.

### Gaps Summary

No gaps. All 20 must-have truths across the 5 plans are verified true in the codebase, backed by passing named tests (not just symbol presence — spies/monkeypatches confirm the actual eliminated-fallback, isolated-write, and tier-branching behaviors). The full backend suite (3482 tests) passes; `ty` is clean; the phase is deployed to production (`3efc7172`, PR #260, merged 2026-07-17T17:42:00Z) and the D-07 measurement is recorded and human-approved with an honestly-documented partial-rollout caveat (3 of 4 worker hosts still v1 at measurement time — a known, tracked follow-up, not a phase-goal miss, since the mechanism itself is confirmed working on the one upgraded host: local engine busy % rose from ~68% to 90.5%, near the ~95% target).

Two advisory code-review findings (CR-01, WR-01) are carried forward as recommended fast-follow work — see Anti-Patterns section above. Recommend a small follow-up quick-task before `BEST_MOVE_BACKFILL_ENABLED` sees sustained prod traffic, to close CR-01 specifically (the WR-01 gap is lower severity — server fallback already exists as backstop for the fresh lane, but tier-4b has no equivalent retry, so a forfeited candidate there is permanent until a resweep script exists, same conceptual gap as CR-01).

---

_Verified: 2026-07-17T21:10:00Z_
_Verifier: Claude (gsd-verifier)_
