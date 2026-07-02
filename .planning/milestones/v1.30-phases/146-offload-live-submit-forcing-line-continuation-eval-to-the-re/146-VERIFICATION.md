---
phase: 146-offload-live-submit-forcing-line-continuation-eval-to-the-re
verified: 2026-07-01T08:00:00Z
status: human_needed
score: 8/8 must-haves verified
behavior_unverified: 0
overrides_applied: 0
human_verification:
  - test: "Run a live game submission against the dev server, then run `scripts/backfill_multipv.py --db dev --status` to confirm the game shows up in the tier-4 backlog. Start the fleet worker (`uv run python scripts/remote_eval_worker.py --base-url http://localhost:8000 --workers 4 --once`) and verify the submitted game's `allowed_pv_lines`/`missed_pv_lines` transition from NULL to filled values after the worker drains it."
    expected: "After tier-4 drain: game_flaws rows for the freshly-submitted game have non-NULL allowed_pv_lines and missed_pv_lines; tactic tags are gated (denoised) vs the raw tags visible during the NULL-blob window."
    why_human: "Requires a running fleet worker and live dev server. Automated tests mock both the HTTP layer and EnginePool; the actual DB state transition (NULL blobs → filled blobs → gated retag via _classify_tactic_gated) cannot be verified without a real drain cycle. Documented as Manual-Only/HUMAN-UAT in 146-VALIDATION.md."
---

# Phase 146: Offload Live-Submit Forcing-Line Continuation Eval to Remote Worker — Verification Report

**Phase Goal:** Stop the live `/eval/remote/submit` path from running server-side Stockfish. Move the MultiPV-2 forcing-line continuation eval onto the remote fleet — the live submit applies evals + classifies flaws + fills flaw PVs + stamps BOTH completion markers (`full_evals_completed_at` and `full_pv_completed_at`) leaving `allowed_pv_lines`/`missed_pv_lines` NULL (matching the existing tier-4 backfill predicate); the freshly-submitted game then drains through the existing Phase-145 flaw-blob lease/submit + D-07 gated retag path. Server runs zero Stockfish on the live path; live and backfill unify. Recency-prioritize tier-4 so fresh games gate promptly (D-01). Upgrade the fleet worker to drain tier-4 (D-04).
**Verified:** 2026-07-01T08:00:00Z
**Status:** human_needed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | POST /eval/remote/submit applies per-ply evals, classifies flaws, stamps BOTH full_evals_completed_at and full_pv_completed_at, and leaves allowed_pv_lines/missed_pv_lines NULL (D-03). | VERIFIED | `_apply_submit` (eval_remote.py line 261): `blob_map: dict[int, tuple[list[PvNode], list[PvNode]]] = {}` unconditional. Line 282: `_classify_and_fill_oracle(..., blob_map if blob_map else None)` — empty dict evaluates to None → raw classify, gate skipped. Lines 290-291 (Path A): `_mark_full_evals_completed` + `_mark_full_pv_completed`; lines 308-309 (Path C) same. No `_run_multipv2_pass` call anywhere in the function. Tests: `test_submit_phase146_blobs_null_both_markers_stamped` (test_eval_worker_endpoints.py). |
| 2 | The live submit path invokes zero Stockfish/EnginePool — no call to `_build_flaw_multipv2_blobs` and no `_run_multipv2_pass` engine work (D-03). | VERIFIED | `grep -n "_build_flaw_multipv2_blobs\|_run_multipv2_pass" app/routers/eval_remote.py` returns zero non-comment lines. Neither function appears in the import block (lines 62-84 of eval_remote.py). Test: `test_submit_phase146_build_blob_not_called` patches `app.services.eval_drain._build_flaw_multipv2_blobs` to raise and asserts the submit endpoint succeeds without triggering it. |
| 3 | SubmitEval parses a payload WITHOUT second-best fields, and still parses an old-worker payload that includes second_cp/second_mate/second_uci without a 422 (D-03, backward-compatible narrowing). | VERIFIED | `app/schemas/eval_remote.py` SubmitEval (lines 30-40): fields are `ply`, `eval_cp`, `eval_mate`, `best_move`, `pv` only. Comment documents the Phase 146 D-03 removal and Pydantic v2 extra-fields behavior. `FlawBlobSubmitEval` (lines 125-135) retains `second_cp/second_mate/second_uci` — unchanged. Tests: `test_submit_eval_schema_phase146_no_second_best_fields` and `test_submit_eval_accepts_second_best_fields` (the latter now asserts old-worker fields are silently ignored). |
| 4 | `_claim_tier4_blob` selects among the most-recently-analyzed games (favoring fresh games), not uniformly across the entire backlog (D-01). | VERIFIED | `app/services/eval_queue_service.py` line 101: `TIER4_RECENCY_WINDOW: int = 50`. Lines 491-510: CTE `WITH recent AS (... ORDER BY g.full_evals_completed_at DESC LIMIT :recency_window)` followed by `SELECT game_id, user_id FROM recent ORDER BY random() LIMIT 1`. `:recency_window` bound via params dict (`{"recency_window": TIER4_RECENCY_WINDOW}`). No f-string interpolation (confirmed with grep). Test: `test_claim_tier4_blob_recency_favors_fresh_game` — monkeypatches `TIER4_RECENCY_WINDOW=1`, asserts all 20 draws return the freshest game. |
| 5 | After tier-1/2/3 (/lease, /entry-lease, /lease?scope=idle) all return 204, the worker leases tier-4 flaw-blob positions, evaluates them at MultiPV-2, and submits to /flaw-blob-submit (D-04). | VERIFIED | `scripts/remote_eval_worker.py` `_run_cycle` (lines 231-288): after tier-3 `idle_resp.status_code == 204` at line 279, POSTs `/api/eval/remote/flaw-blob-lease` (line 281); 200 → `_handle_flaw_blob_response` (line 286). `_handle_flaw_blob_response` (lines 370-407): reads `game_id`, calls `_eval_flaw_blob_positions` at MultiPV-2, submits to `/api/eval/remote/flaw-blob-submit`. Test: `test_ladder_flaw_blob_on_all_tier123_204` asserts both URLs appear in client.post call list. |
| 6 | When all four rungs return 204, the worker sleeps exactly once (no double sleep). | VERIFIED | `_run_cycle` lines 282-285: `if blob_resp.status_code == 204:` → `_log(...)` + `await asyncio.sleep(idle_sleep)` + `return not loop`. No sleep in any other rung path — sleeping only when the tier-4 204 is reached. Test: `test_ladder_all_queues_empty_sleeps_once` (mock_sleep.assert_awaited_once_with). |
| 7 | The full-ply pass evaluates at MultiPV-1 (evaluate_nodes_with_pv) — no second-best on the /submit wire (D-03 consequence, RESEARCH-confirmed safe). | VERIFIED | `_eval_positions` (lines 96-125): `asyncio.gather(*(pool.evaluate_nodes_with_pv(b) for b in boards))`, output dict has only `{ply, eval_cp, eval_mate, best_move, pv}`. `grep -c "evaluate_nodes_multipv2" scripts/remote_eval_worker.py` returns 1 — only in `_eval_flaw_blob_positions`. Test: `test_eval_positions_uses_multipv1_no_second_best`. |
| 8 | HTTP_TIMEOUT_S is 30.0 (the SEED-071 120s stopgap removed). | VERIFIED | `scripts/remote_eval_worker.py` line 61: `HTTP_TIMEOUT_S: float = 30.0`. No stopgap comment. Test: `test_http_timeout_s_restored_to_30`. |

**Score:** 8/8 truths verified (0 present, behavior-unverified)

### SCOPE Verification (nothing should have changed)

| Constraint | Status | Evidence |
|------------|--------|----------|
| No DB schema/migration | VERIFIED | Newest alembic/versions/ file is `20260630_220000_c3f5d1e8a092_ix_game_flaws_blob_backfill.py` — predates phase 146 commits. No new migration created. |
| No blob-shape change | VERIFIED | `FlawBlobLeaseResponse`, `FlawBlobSubmitEval`, `FlawBlobSubmitRequest` schemas in eval_remote.py unchanged. |
| No gate-logic / ONLY_MOVE_WIN_PROB_MARGIN change | VERIFIED | `forcing_line_gate.py` line 62: `ONLY_MOVE_WIN_PROB_MARGIN: float = 0.35` — unchanged. Not in any phase 146 commit diff. |
| No STOCKFISH_POOL_SIZE change | VERIFIED | Remains an env var in engine.py; no modification in phase 146. |

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `app/routers/eval_remote.py` | `_apply_submit` with unconditional `blob_map = {}`, removed `_build_flaw_multipv2_blobs`/`_run_multipv2_pass` imports and calls | VERIFIED | Line 261: unconditional assignment. Import block (lines 62-84): neither function imported. grep returns 0 non-comment matches. |
| `app/schemas/eval_remote.py` | `SubmitEval` without `second_cp/second_mate/second_uci`; `FlawBlobSubmitEval` unchanged | VERIFIED | Lines 30-40: SubmitEval has 5 fields (ply, eval_cp, eval_mate, best_move, pv). Lines 125-135: FlawBlobSubmitEval retains all second-best fields. |
| `app/services/eval_queue_service.py` | `TIER4_RECENCY_WINDOW: int = 50` + recency CTE in `_claim_tier4_blob` with bound param | VERIFIED | Line 101: constant defined. Lines 490-511: CTE with `:recency_window` bound via params dict. |
| `scripts/remote_eval_worker.py` | `_eval_flaw_blob_positions`, `_handle_flaw_blob_response`, rung-4 in `_run_cycle`, `_eval_positions` MultiPV-1, `HTTP_TIMEOUT_S=30.0` | VERIFIED | Lines 61, 96-125, 128-159, 231-288, 370-407. All present and substantive. |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `blob_map = {}` in `_apply_submit` | `_classify_and_fill_oracle` receives `None` | `blob_map if blob_map else None` (line 282) | VERIFIED | Empty dict is falsy in Python; gate is skipped; raw tactic classify (D-02 behavior during NULL-blob window). |
| `allowed_pv_lines/missed_pv_lines NULL` | Game matches tier-4 predicate | No `_run_multipv2_pass` called; blobs never written on live path | VERIFIED | `_claim_tier4_blob` CTE predicate: `gf.allowed_pv_lines IS NULL` — newly submitted game satisfies this immediately. |
| `:recency_window` in CTE | Bound SQL parameter | `sa.text(...)` params dict `{"recency_window": TIER4_RECENCY_WINDOW}` (line 510) | VERIFIED | No f-string usage confirmed by grep returning 0 results on `f".*recency_window`. |
| `_handle_flaw_blob_response` reads `data["game_id"]` | Included in `/flaw-blob-submit` body | Lines 386 (`game_id = data["game_id"]`) and 402 (`json={"game_id": game_id, ...}`) | VERIFIED | `FlawBlobSubmitRequest` requires `game_id`; worker correctly reads and echoes it. |
| `_eval_flaw_blob_positions` r[0]/r[1]/r[4]/r[5]/r[6] | Output dict fields `best_cp/best_mate/second_cp/second_mate/second_uci` | Explicit index mapping lines 153-157 | VERIFIED | r[2] (best_move) and r[3] (pv) intentionally absent. Token echoed unchanged (`str(pos["token"])` line 151). |
| Rung-4 `/flaw-blob-lease` 204 | Single `asyncio.sleep(idle_sleep)` | Lines 282-285: `if blob_resp.status_code == 204: ... await asyncio.sleep(idle_sleep)` | VERIFIED | No second sleep in any other rung 4 path. `test_ladder_all_queues_empty_sleeps_once` asserts `assert_awaited_once_with`. |

### Data-Flow Trace (Level 4)

Not applicable. Phase 146 modifies routing logic, a database query ordering, and a remote worker protocol. No new components render dynamic data from a new source.

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| `_build_flaw_multipv2_blobs`/`_run_multipv2_pass` absent from eval_remote.py | `grep -n "_build_flaw_multipv2_blobs\|_run_multipv2_pass" app/routers/eval_remote.py` | 0 lines | PASS |
| `HTTP_TIMEOUT_S == 30.0` | `grep -n "^HTTP_TIMEOUT_S" scripts/remote_eval_worker.py` | `61:HTTP_TIMEOUT_S: float = 30.0` | PASS |
| `evaluate_nodes_multipv2` appears exactly once in worker (only in tier-4 blob rung) | `grep -c "evaluate_nodes_multipv2" scripts/remote_eval_worker.py` | `1` | PASS |
| `:recency_window` bound as param, no f-string interpolation | `grep -n "f\".*recency_window\|f'.*recency_window" app/services/eval_queue_service.py` | 0 lines | PASS |
| No TBD/FIXME/XXX debt markers in modified files | grep across 4 modified files | 0 lines | PASS |
| Phase 146 commits exist in git log | `git log --oneline ab47e283 38db8a81 a5adb79a 56f9e32a bc2554ee 20feeae8` | All 6 commits found | PASS |

### Requirements Coverage

No formal REQ-IDs mapped to Phase 146 (authorized per PLAN frontmatter). Coverage tracked via CONTEXT decisions D-01..D-04:

| Decision | Description | Status |
|----------|-------------|--------|
| D-01 | Recency-order `_claim_tier4_blob` — fresh games win | VERIFIED (truth 4) |
| D-02 | Show raw tactic tags during NULL-blob window (no read-path change) | VERIFIED — implicit: `blob_map={}` leaves stored tactic columns as raw tags; read path unchanged |
| D-03 | Live `/submit` unconditionally takes empty-blob_map path; drops second-best from SubmitEval; stamps both markers | VERIFIED (truths 1-3) |
| D-04 | Fleet worker drains tier-4 via /flaw-blob-lease + /flaw-blob-submit | VERIFIED (truth 5) |

### Anti-Patterns Found

No blockers found.

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| — | — | No TBD/FIXME/XXX markers, no stubs, no hardcoded empty returns in new code paths | — | Clean |

### Human Verification Required

#### 1. End-to-End Dev Drain: live submit → NULL blobs → tier-4 drain → gated retag

**Test:** Submit a game via the live `/eval/remote/submit` endpoint on the dev server (or use `backfill_multipv.py --dev-validate`). Confirm `allowed_pv_lines`/`missed_pv_lines` are NULL immediately after submit. Then run the fleet worker once (`uv run python scripts/remote_eval_worker.py --base-url http://localhost:8000 --workers 4 --once`). Check DB via `scripts/backfill_multipv.py --db dev --status`.

**Expected:** Immediately post-submit: the game's `game_flaws` rows show `allowed_pv_lines IS NULL` and `missed_pv_lines IS NULL`; both `full_evals_completed_at` and `full_pv_completed_at` are stamped. After worker drains tier-4: `allowed_pv_lines`/`missed_pv_lines` are non-NULL, tactic tags are gated (denoised). No EnginePool calls observed on the server during `/submit` (latency evidence: p99 drops from the pre-phase worker ReadTimeout levels).

**Why human:** Requires a running fleet worker and dev server. All automated tests mock both HTTP and EnginePool. The DB state transition (NULL → filled blobs → gated retag via `_classify_tactic_gated`) cannot be verified without a real drain cycle. Explicitly documented as Manual-Only/HUMAN-UAT in 146-VALIDATION.md per plan design.

### Gaps Summary

No gaps. All 8 must-haves are VERIFIED in the codebase. SCOPE constraints (no migration, no blob-shape change, no gate-logic change, no STOCKFISH_POOL_SIZE change) are satisfied. The single human verification item (end-to-end drain) was pre-authorized as HUMAN-UAT in 146-VALIDATION.md and is not a blocker.

---

_Verified: 2026-07-01T08:00:00Z_
_Verifier: Claude (gsd-verifier)_
