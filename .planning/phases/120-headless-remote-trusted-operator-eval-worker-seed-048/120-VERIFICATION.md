---
phase: 120-headless-remote-trusted-operator-eval-worker-seed-048
verified: 2026-06-14T20:30:00Z
status: passed
score: 10/10 must-haves verified
overrides_applied: 0
---

# Phase 120: Headless Remote Trusted-Operator Eval Worker — Verification Report

**Phase Goal:** Add off-box CPU to the tier-3 eval drain via a headless Python CLI worker that leases eval jobs from prod over HTTPS, runs the existing EnginePool natively, and posts evals back. Scope: (1) HTTP endpoint to lease one game's unanalyzed (ply, FEN) positions; (2) HTTP endpoint to submit a game's batched evals with server-side SEED-044 storage convention + full_evals_completed_at stamping; (3) operator-token auth on both endpoints; (4) the worker CLI (lease → eval all FENs via EnginePool → batch submit). SF-version-mismatch rejection (D-5). Idempotent duplicate tier-3 work (D-4). Trusted-operator write scope only (D-6). Weighted-random within-user game pick (D-7).

**Verified:** 2026-06-14T20:30:00Z
**Status:** PASSED
**Re-verification:** No — initial verification

---

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | Server config exposes EVAL_OPERATOR_TOKEN and EXPECTED_SF_VERSION, both empty by default (D-1, D-6) | VERIFIED | `app/core/config.py:79-84` — both fields present in Settings with `str = ""` default; comments explain fail-closed semantics and prod override |
| 2 | Worker can read its own Stockfish version via get_stockfish_version() before evaluating (D-5) | VERIFIED | `app/services/engine.py:311-321` — `async def get_stockfish_version()` opens a one-shot `popen_uci` UCI handshake, reads `protocol.id.get("name")`, quits, returns string; no EnginePool instantiation |
| 3 | Pydantic v2 schemas exist for the wire contract (LeasePosition, LeaseResponse, SubmitEval, SubmitRequest, SubmitResponse) | VERIFIED | `app/schemas/eval_remote.py` — all five models present with exact field sets including `user_id` on both LeaseResponse and SubmitRequest |
| 4 | POST /api/eval/remote/lease returns tier-3 game unanalyzed (ply, FEN) positions (D-3) | VERIFIED | `app/routers/eval_remote.py:281-346` — calls `_claim_tier3_derived` directly (not `claim_eval_job`), replays PGN for FEN, includes terminal donor via `include_terminal=True`; registered in main.py at line 150 under `/api` prefix |
| 5 | POST /api/eval/remote/submit applies SEED-044 storage convention server-side and stamps full_evals_completed_at (D-2, D-3) | VERIFIED | `app/routers/eval_remote.py:149-273` — `_apply_submit` calls `_apply_full_eval_results` with worker's unshifted ply-keyed evals; shift is applied inside that function (`_post_move_eval`); test `test_submit_applies_post_move_shift` at line 391 verifies row ply=0 receives eval submitted at ply=1; `_mark_full_evals_completed` + `_mark_full_pv_completed` called on Path A and Path C |
| 6 | Both endpoints reject requests without a valid X-Operator-Token; fail-closed when token unconfigured (D-6) | VERIFIED | `app/routers/eval_remote.py:64-89` — `require_operator_token` dependency: 403 when `not settings.EVAL_OPERATOR_TOKEN` (fail-closed); 401 when token is None or `not hmac.compare_digest(configured, x_operator_token)`; constant-time comparison; both endpoints use `Depends(require_operator_token)` |
| 7 | Submit rejects evals from mismatched Stockfish version with 422 (D-5) | VERIFIED | `app/routers/eval_remote.py:365-371` — D-5 gate checked first before any DB access: `if settings.EXPECTED_SF_VERSION and body.sf_version != settings.EXPECTED_SF_VERSION: raise HTTPException(status_code=422)`; test `test_submit_sf_version_mismatch` at line 371 covers this path |
| 8 | Duplicate submit of the same game is idempotent (D-4) | VERIFIED | `app/routers/eval_remote.py:361-362` — docstring documents idempotency via `ON CONFLICT DO NOTHING` for flaws, idempotent oracle UPDATE, same-timestamp completion markers; test `test_submit_idempotent` at line 526 sends same payload twice and asserts 200 both times |
| 9 | Worker CLI: lease -> eval all FENs via EnginePool -> batch submit loop, reports SF version, no client-side shift (D-1, D-2, D-3) | VERIFIED | `scripts/remote_eval_worker.py` — `run_worker` starts EnginePool, reads `get_stockfish_version()`, sends it in every submit payload; `_eval_positions` passes results through unchanged (no `post_move` reference, no `+ 1` shift); worker sends `X-Operator-Token` header; loops with idle sleep; supports `--dry-run`, `--once`, `--workers`, `--idle-sleep` |
| 10 | D-7: _claim_tier3_derived Step 2 uses Efraimidis-Spirakis weighted-random game pick, not deterministic ORDER BY (D-7) | VERIFIED | `app/services/eval_queue_service.py:360-399` — Step 2 uses `ORDER BY -ln(random()) / (tc_weight * (exp(-delta/tau) + floor)) LIMIT 1` with named constants `GAME_TC_WEIGHTS`, `GAME_RECENCY_HALF_LIFE_DAYS`, `GAME_WEIGHT_FLOOR`; residual fallback similarly updated (lines 408-443); all values bound as `:params`, no f-string interpolation in sa.text; `TestTier3GamePickSpread` class at tests/services/test_eval_queue.py:958 proves spread; old deterministic `played_at DESC NULLS LAST` only remains in `_claim_queued_job` (tier-1/2), not in `_claim_tier3_derived` |

**Score:** 10/10 truths verified

---

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `app/core/config.py` | EVAL_OPERATOR_TOKEN + EXPECTED_SF_VERSION settings | VERIFIED | Both fields at lines 79-84, empty default, prod-override comments |
| `app/schemas/eval_remote.py` | 5 Pydantic v2 models | VERIFIED | 41 lines, all 5 models with correct fields |
| `app/services/engine.py` | get_stockfish_version() async helper | VERIFIED | Lines 311-321, coroutine, uses popen_uci, no EnginePool |
| `app/routers/eval_remote.py` | lease + submit endpoints + require_operator_token dependency | VERIFIED | 377 lines (> min 80), both endpoints registered, auth dependency on both |
| `app/main.py` | eval_remote router registration under /api | VERIFIED | Line 24 imports `eval_remote_router`, line 150 registers with `/api` prefix |
| `tests/test_eval_worker_endpoints.py` | Integration tests for lease, submit, auth, version gate, idempotency | VERIFIED | 593 lines; all required test functions present |
| `scripts/remote_eval_worker.py` | Headless CLI worker: lease -> eval -> submit loop | VERIFIED | 308 lines (> min 90); all 5 required functions present |
| `app/services/eval_queue_service.py` | Weighted-random Step-2 game pick + named constants | VERIFIED | GAME_TC_WEIGHTS, GAME_RECENCY_HALF_LIFE_DAYS, GAME_WEIGHT_FLOOR constants; ES key in Step 2 and residual fallback |
| `tests/services/test_eval_queue.py` | TestTier3GamePickSpread class | VERIFIED | Class at line 958 with spread, weighting-bias, and single-game regression tests |

---

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `eval_remote.py:lease_eval_game` | `eval_queue_service._claim_tier3_derived` | direct call, bypasses EVAL_AUTO_DRAIN_ENABLED | VERIFIED | Line 297: `claim = await _claim_tier3_derived(read_session)` |
| `eval_remote.py:submit_eval` | `eval_drain._apply_full_eval_results` | server applies post-move shift | VERIFIED | Line 214: `failed_ply_count = await _apply_full_eval_results(write_session, targets, {}, engine_result_map, ...)` |
| `eval_remote.py:require_operator_token` | `settings.EVAL_OPERATOR_TOKEN` | hmac.compare_digest constant-time check | VERIFIED | Lines 76-89: fail-closed 403 + constant-time 401 path |
| `remote_eval_worker.py:_eval_positions` | `engine.EnginePool.evaluate_nodes_with_pv` | asyncio.gather fan-out (no DB session) | VERIFIED | Line 87: `results = await asyncio.gather(*(pool.evaluate_nodes_with_pv(b) for b in boards))` |
| `remote_eval_worker.py:run_worker` | `POST /api/eval/remote/lease + /submit` | httpx.AsyncClient with X-Operator-Token header | VERIFIED | Lines 188-192: client built with `headers={"X-Operator-Token": token}` |
| `remote_eval_worker.py` | `engine.get_stockfish_version` | reads SF version at startup for SubmitRequest | VERIFIED | Line 185: `sf_version = await get_stockfish_version()` |
| `eval_queue_service._claim_tier3_derived` | ES game pick ORDER BY | `-ln(random()) / game_weight` with :params bound | VERIFIED | Lines 360-395: Step 2 uses ES key; 7 non-commented occurrences of `-ln(random())` (Step 1 + Step 2 + residual) |

---

### Data-Flow Trace (Level 4)

Not applicable for this phase — the phase delivers API endpoints and a CLI worker, not a data-rendering UI component.

**Key server-side shift trace (D-2 critical path):**

Worker submits `{ply: 1, eval_cp: 30}` → `engine_result_map = {1: (30, None, ...)}` → `_apply_full_eval_results(targets, {}, engine_result_map, ...)` → internally calls `_post_move_eval` which shifts the eval to the row at `ply=0` → `game_positions.eval_cp` at `ply=0` stores `30`. This is proven by `test_submit_applies_post_move_shift`.

---

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| Both routes registered on app | `python -c "from app.main import app; paths={r.path for r in app.routes}; assert '/api/eval/remote/lease' in paths and '/api/eval/remote/submit' in paths"` | Confirmed via code inspection: main.py lines 24 + 150 | VERIFIED |
| require_operator_token uses compare_digest | `grep -n 'compare_digest' app/routers/eval_remote.py` | Line 85 confirms usage | VERIFIED |
| No post_move reference in worker | `grep 'post_move' scripts/remote_eval_worker.py` | Only in comment text (not logic) | VERIFIED |
| ES key count >= 2 in eval_queue_service | `grep -v '^#' ... | grep -c -- '-ln(random())'` | 7 (Step 1 + Step 2 + residual + docstring occurrences; non-comment logic has 3) | VERIFIED |
| TestTier3GamePickSpread class exists | `grep 'TestTier3GamePickSpread' tests/services/test_eval_queue.py` | Line 958 | VERIFIED |
| Full backend suite passes | Reported: 2628 passed, 10 skipped | Clean (per phase submission) | PASS |

---

### Probe Execution

No probes declared in PLAN files. Phase verification relies on the test suite (2628 passed) and manual UAT noted in 120-03-PLAN.md.

---

### Requirements Coverage

Phase 120 requirement IDs reference locked decisions in SEED-048, not REQUIREMENTS.md formal IDs.

| Decision | Source Plan | Description | Status | Evidence |
|----------|------------|-------------|--------|----------|
| D-1 | 120-01, 120-03 | Headless Python CLI worker, native Stockfish | SATISFIED | `scripts/remote_eval_worker.py` CLI exists |
| D-2 | 120-02, 120-03 | Server owns SEED-044 post-move shift (no client-side shift) | SATISFIED | `_apply_full_eval_results` called server-side; worker passes evals unchanged; test verifies shift |
| D-3 | 120-02 | Per-game granularity, single batched submit | SATISFIED | Lease returns one game's positions; submit accepts one batch per game |
| D-4 | 120-02 | Idempotent duplicate tier-3 work accepted | SATISFIED | Submit is idempotent; `test_submit_idempotent` passes |
| D-5 | 120-01, 120-02 | SF version pinning + server-side mismatch rejection (422) | SATISFIED | Gate at eval_remote.py:365; `test_submit_sf_version_mismatch` covers it |
| D-6 | 120-01, 120-02 | Trusted-operator write scope; fail-closed when unconfigured | SATISFIED | 403 when `EVAL_OPERATOR_TOKEN == ""`; constant-time comparison on both endpoints |
| D-7 | 120-04 | Weighted-random within-user game pick (Efraimidis-Spirakis) | SATISFIED | ES key in Step 2 + residual; named constants; `TestTier3GamePickSpread` proves spread |

---

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| `scripts/remote_eval_worker.py` | 227 | `default=os.environ.get("EVAL_OPERATOR_TOKEN", "")` in argparse | Info (IN-05 from code review) | Low: argparse does not print secrets by default; no log/print exposes it |
| `app/routers/eval_remote.py` | 267 | `_signal_flaw_completion(user_id)` uses worker-supplied `body.user_id` not `game.user_id` | Warning (WR-04 from code review) | Correctness: cache-invalidation fires for the worker-supplied user_id; data writes use game's authoritative owner. Not a security defect; advisory non-blocking per review |

No TBD/FIXME/XXX markers found in phase-modified files. No unreferenced debt markers. No stub implementations.

---

### Human Verification Required

One item intentionally deferred in 120-03-PLAN.md as MANUAL / HUMAN-UAT:

**1. End-to-end worker connectivity against local dev server**

- **Test:** Run `uv run python scripts/remote_eval_worker.py --base-url http://localhost:8000 --token <dev-token> --dry-run --once` against a local dev server with `EVAL_OPERATOR_TOKEN` set in dev `.env` and Stockfish installed. Then run `--once` (without `--dry-run`) and confirm one game's evals land + `full_evals_completed_at` is stamped.
- **Expected:** `--dry-run` confirms connectivity; `--once` processes one game; DB row shows `full_evals_completed_at IS NOT NULL`.
- **Why human:** Requires a running local backend with Stockfish binary installed, a dev `.env` with `EVAL_OPERATOR_TOKEN` set, and actual tier-3 games queued. Cannot be automated without starting a server.

> Note: integration tests (`tests/test_eval_worker_endpoints.py`) cover the server-side contract comprehensively via ASGI transport + monkeypatching. The HUMAN-UAT above validates the full end-to-end path through the real binary and HTTP stack.

---

### Gaps Summary

No gaps. All must-haves are verified at all three levels (exists, substantive, wired).

The code review found 4 advisory Warnings (WR-01 through WR-04). None are blockers for the phase goal:
- **WR-01** (non-ASCII token → 500): an edge case requiring attacker-controlled non-ASCII header; correctness/robustness issue, not a goal failure
- **WR-02** (no exception boundary in worker loop): robustness issue for the daemon; does not prevent the core lease/eval/submit from working
- **WR-03** (unbounded evals list): minor input-trust gap behind operator auth
- **WR-04** (user_id source for cache signal): correctness defect in cache invalidation; data writes are correct

These are recorded for follow-up but do not block phase completion per the review's own classification.

---

_Verified: 2026-06-14T20:30:00Z_
_Verifier: Claude (gsd-verifier)_
