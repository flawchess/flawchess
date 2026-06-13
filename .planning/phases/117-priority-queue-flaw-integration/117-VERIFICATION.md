---
phase: 117-priority-queue-flaw-integration
verified: 2026-06-13T11:30:00Z
status: human_needed
score: 14/14
overrides_applied: 0
human_verification:
  - test: "Post-deploy: fire the internal tier-1 trigger on an idle prod pool and measure wall-clock from enqueue to all-plies-evaluated"
    expected: "~10s total (spike 003 measured; one game's ~60 plies fanned across 6-8 workers)"
    why_human: "Wall-clock latency depends on real prod pool (6-8 workers, 1M nodes/ply); not deterministic in CI and cannot be measured without a live Stockfish pool"
  - test: "Observe progressive flaw appearance and per-user cache update after a chess.com import on prod"
    expected: "game_flaws rows appear without manual refresh after full eval completes; no invalidation storm in logs"
    why_human: "Cross-surface UX timing; _signal_flaw_completion is a Phase 117 no-op stub (D-117-11); Phase 118 wires real cache invalidation — so the 'cache refresh' part is intentionally deferred. Verifier must confirm that the stub has no adverse side-effects visible in prod logs"
---

# Phase 117: Priority Queue + Flaw Integration — Verification Report

**Phase Goal:** A tiered priority queue replaces the current LIFO id-DESC game pick, serving explicit requests first, then automatic windows, then idle backlog, with round-robin per-user fairness, tier-1 fan-out across the full worker pool, and newly analyzed games flowing automatically into game_flaws.

**Verified:** 2026-06-13T11:30:00Z
**Status:** human_needed
**Re-verification:** No — initial verification

---

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | Tier-1 > tier-2 > tier-3 claim priority exists in eval_queue_service | VERIFIED | `eval_queue_service.py:127-159` — CTE orders by `ej.tier ASC`; `claim_eval_job` falls through to tier-3 derived only when no tier-1/2 row exists; `test_tier_priority` PASSES |
| 2 | Round-robin per-user (oldest-pending-user first) and TC-weighted ordering within user (D-117-04) | VERIFIED | `eval_queue_service.py:136-148` — CTE `ORDER BY MIN(j2.created_at) ASC, CASE time_control_bucket WHEN 'classical' THEN 0 WHEN 'rapid' THEN 1 WHEN 'blitz' THEN 2 WHEN 'bullet' THEN 3 END ASC, g.played_at DESC NULLS LAST`; `test_round_robin` and `test_tc_ordering` PASS |
| 3 | Tier-3 is a derived pick (no pre-populated eval_jobs rows; job_id=None) | VERIFIED | `eval_queue_service.py:177-221` — `_claim_tier3_derived` queries `games WHERE full_evals_completed_at IS NULL AND NOT is_guest`; returns `(game_id, user_id, is_analyzed)` with no eval_jobs insert; `ClaimedJob.job_id=None`; `test_tier3_derived` PASSES |
| 4 | Lease/report contract: claim sets status=leased; report_job_complete sets completed; expired lease requeued | VERIFIED | `eval_queue_service.py:276-306` — `report_job_complete` sets `status='completed'`; `_sweep_expired_leases` resets `status='pending'` for `lease_expiry < now()`; `test_lease_expiry` PASSES |
| 5 | Guest exclusion on every tier path AND enqueue_tier1_game guard (QUEUE-08) | VERIFIED | CTE: `AND u.is_guest = false` (line 134); tier-3: `User.is_guest == False` (line 200); enqueue: `if is_guest: return False` (lines 323-325); `test_guest_exclusion` PASSES |
| 6 | best_move (UCI) written for every evaluated non-dedup'd ply; transplanted via dedup in opening region gated on lichess_evals_at IS NULL (D-117-07) | VERIFIED | `eval_drain.py:318` — `stmt.values(eval_cp=eval_cp, eval_mate=eval_mate, best_move=best_move)`; `_fetch_dedup_evals:205` — selects `GamePosition.best_move`; WR-02 gate at line 213: `Game.lichess_evals_at.is_(None)`; `test_best_move_written_after_tick` and `test_dedup_best_move_transplanted` PASS |
| 7 | Full PV (~12-ply cap) written only at ply N+1 for each flaw at ply N (D-117-02) | VERIFIED | `eval_drain.py:442-458` — `_classify_and_fill_oracle` loops `flaw_list`, writes `pv=pv_string` at `ply == flaw_ply + 1`; `engine_result_map.get(pv_ply)` where `pv_ply = flaw_ply + 1`; `test_flaw_pv_written_at_ply_n_plus_one` PASSES |
| 8 | evaluate_nodes_with_pv returns 4-tuple (eval_cp, eval_mate, best_move, pv_string) from the same 1M-node search (zero extra compute) | VERIFIED | `engine.py:486-507` — `EnginePool.evaluate_nodes_with_pv` calls `_analyse_with_pv` once with `Limit(nodes=_NODES_BUDGET)`; applies `_score_to_cp_mate` + `_pv_to_best_move` + `_pv_to_uci_string` to the same `InfoDict`; `PV_CAP_PLIES=12` caps the string |
| 9 | classify_game_flaws runs automatically on full-eval completion; oracle count columns filled (D-117-08); full_pv_completed_at marker set (D-117-12) | VERIFIED | `eval_drain.py:1218-1225` — write session calls `_classify_and_fill_oracle`, then `_mark_full_evals_completed`, then `_mark_full_pv_completed` atomically; oracle fills at lines 425-436; `test_classify_hook_inserts_game_flaws` and `test_oracle_counts_filled_and_match_game_flaws` PASS |
| 10 | The LIFO id-DESC pick is replaced by queue lease in the Phase 116+ full drain | VERIFIED | `eval_drain.py:1117` — `_full_drain_tick` calls `claimed = await claim_eval_job(worker_id=WORKER_ID_SERVER_POOL)`; the old LIFO `_pick_pending_game_ids` is only used by the Phase 91 entry-ply drain (`run_eval_drain`), which is a separate coroutine intentionally untouched |
| 11 | D-117-07: WR-02 gate repointed from white_blunders to lichess_evals_at; white_blunders is now the oracle write target only | VERIFIED | `grep -vn '^#' eval_drain.py | grep -c "white_blunders.is_(None)"` returns 0; `lichess_evals_at.is_(None)` at line 213 is the sole WR-02 discriminator; `white_blunders` appears only as a write target at line 432; `TestWr02Repointed::test_wr02_engine_source_included` and `test_wr02_lichess_source_excluded` PASS |
| 12 | Superuser-gated POST /admin/eval/enqueue-tier1/{game_id} trigger exists (D-117-05) | VERIFIED | `admin.py:86-126` — `@router.post("/eval/enqueue-tier1/{game_id}")` gated by `Depends(current_superuser)`; delegates to `enqueue_tier1_game`; 404 on missing game; `import-time route assertion` confirms `/api/admin/eval/enqueue-tier1/{game_id}` registered |
| 13 | _signal_flaw_completion is a Phase 117 no-op stub (D-117-11 intentional; Phase 118 wires cache) | VERIFIED | `eval_drain.py:495-503` — `_recently_flaw_completed_users.add(user_id)`; docstring explicitly states "Phase 117: no-op beyond a set insert. Phase 118 will wire cache invalidation here." CONTEXT.md D-117-11 scopes this as a stub; not a gap |
| 14 | D-117-10 backfill sets lichess_evals_at only for white_blunders IS NOT NULL games | VERIFIED | `migration:158-160` — `SET lichess_evals_at = COALESCE(imported_at, NOW()) WHERE white_blunders IS NOT NULL AND lichess_evals_at IS NULL`; `test_backfill_sets_lichess_evals_at_for_analyzed_game` and `test_backfill_leaves_lichess_evals_at_null_for_unanalyzed_game` PASS |

**Score:** 14/14 truths verified

---

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `alembic/versions/20260613_120000_phase_117_queue_pv.py` | Migration adding 4 columns, eval_jobs table, indexes, D-117-10 backfill | VERIFIED | `down_revision="20260612120000"`; all 5 upgrade steps confirmed; `alembic current` = `20260613120000 (head)` |
| `app/models/eval_jobs.py` | EvalJob ORM with tier constants, FK cascade, partial indexes | VERIFIED | `class EvalJob(Base)` with `BigInteger PK`, `SmallInteger tier`, `ForeignKey("users.id", ondelete="CASCADE")`, `ForeignKey("games.id", ondelete="CASCADE")`, 3 partial indexes in `__table_args__`; `TIER_EXPLICIT=1`, `TIER_AUTO_WINDOW=2`, `TIER_IDLE_BACKLOG=3` |
| `app/models/game.py` | lichess_evals_at + full_pv_completed_at mapped columns | VERIFIED | Lines 165, 172; `is_analyzed` hybrid unchanged (D-117-09 — still `white_blunders IS NOT NULL`) |
| `app/models/game_position.py` | best_move String(5) + pv Text mapped columns | VERIFIED | Lines 179, 183; `Text` import added |
| `app/services/eval_queue_service.py` | claim_eval_job (SKIP LOCKED), report_job_complete, requeue_expired_leases, enqueue_tier1_game | VERIFIED | All 4 public functions present; `SKIP LOCKED` CTE at lines 127-159; `LEASE_TTL_SECONDS=120`; `WORKER_ID_SERVER_POOL="server-pool"`; no f-strings in sa.text |
| `app/services/engine.py` | evaluate_nodes_with_pv (4-tuple), _pv_to_best_move, _pv_to_uci_string, PV_CAP_PLIES | VERIFIED | Lines 246-507; `PV_CAP_PLIES=12`; `_analyse_with_pv` on EnginePool; 4-tuple `(eval_cp, eval_mate, best_move, pv_string)` |
| `app/services/eval_drain.py` | Queue-lease pick, best_move threading, WR-02 repoint, _classify_and_fill_oracle, _mark_full_pv_completed, _signal_flaw_completion stub | VERIFIED | All 6 components present and wired; gather outside session (structural + AST test) |
| `app/routers/admin.py` | POST /admin/eval/enqueue-tier1/{game_id} superuser-gated | VERIFIED | Line 86-126; `Depends(current_superuser)`; `enqueue_tier1_game` called; registered at `/api/admin/eval/enqueue-tier1/{game_id}` |
| `app/repositories/game_repository.py` | POSITION_COPY_COLUMNS includes best_move and pv | VERIFIED | Lines 44-45; bulk COPY path covers new columns (Rule 1 fix from 03-SUMMARY) |
| `tests/test_migration_117.py` | Migration test covering columns, eval_jobs table, indexes, D-117-10 backfill | VERIFIED | 5/5 tests PASS |
| `tests/services/test_eval_queue.py` | 6 queue behavior tests (QUEUE-01/02/05/06/08) | VERIFIED | 6/6 tests PASS: tier_priority, round_robin, tc_ordering, tier3_derived, lease_expiry, guest_exclusion |
| `tests/services/test_full_eval_drain.py` | EVAL-04/EVAL-06/D-117-07/QUEUE-03 drain tests | VERIFIED | All 21 tests in file PASS including TestBestMove (best_move, dedup_best_move), TestFlawPv (flaw_pv), TestClassifyHook (classify_hook), TestOracleCounts (oracle_counts), TestWr02Repointed, TestGatherOutsideSession |

---

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `eval_queue_service.py` | `eval_jobs` table | `sa.text CTE with FOR UPDATE OF ej SKIP LOCKED` | VERIFIED | Line 127: `SELECT ... FOR UPDATE OF ej SKIP LOCKED`; parameterized `:worker_id` and `:ttl` (no f-strings) |
| `admin.py` | `eval_queue_service.enqueue_tier1_game` | superuser-gated endpoint | VERIFIED | Line 105: `from app.services.eval_queue_service import enqueue_tier1_game`; called at line 111 |
| `eval_queue_service.py` | `users.is_guest` | guest exclusion join/filter | VERIFIED | CTE line 134 `AND u.is_guest = false`; tier-3 line 200 `User.is_guest == False`; enqueue lines 322-325 |
| `eval_drain.py` | `eval_queue_service.claim_eval_job` | queue lease replaces LIFO pick | VERIFIED | Line 62 import; line 1117 `claimed = await claim_eval_job(...)` |
| `eval_drain.py` | `engine.evaluate_nodes_with_pv` | PV-carrying engine call in gather | VERIFIED | Line 1173 `engine_service.evaluate_nodes_with_pv(t.board)` in `asyncio.gather` |
| `eval_drain.py` | `classify_game_flaws + count_game_severities` | `_classify_and_fill_oracle` post-game hook | VERIFIED | Lines 394, 411-418; `_classify_and_fill_oracle` called at line 1218 |
| `eval_drain.py` | `game_positions.pv` | flaw PV write at ply N+1 | VERIFIED | Lines 444-458: `pv_ply = flaw_ply + 1`; `update(GamePosition).values(pv=pv_string)` |
| `eval_jobs.py` | `users.id` | `ForeignKey ondelete=CASCADE` | VERIFIED | Line 67: `ForeignKey("users.id", ondelete="CASCADE")` |
| `migration` | `20260612120000` | down_revision chain to Phase 116 head | VERIFIED | Line 46: `down_revision: Union[str, None] = "20260612120000"` |

---

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
|----------|---------------|--------|--------------------|--------|
| `_classify_and_fill_oracle` | `flaw_list` | `classify_game_flaws(game, positions)` — reads real `eval_cp` from DB | Yes — `eval_cp` written in same transaction before classify runs | FLOWING |
| `_apply_full_eval_results` | `eval_cp, eval_mate, best_move` | `evaluate_nodes_with_pv(board)` via asyncio.gather | Yes — Stockfish 1M-node search; dedup from DB | FLOWING |
| `_fetch_dedup_evals` | dedup map | `GamePosition.eval_cp + best_move` WHERE `lichess_evals_at IS NULL` | Yes — queries real DB rows | FLOWING |
| `_claim_queued_job` | `ClaimedJob` | `eval_jobs` table via SKIP LOCKED | Yes — real DB rows; job_id=None for tier-3 derived | FLOWING |

---

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| Queue tests (tier priority, round-robin, TC ordering, tier-3 derived, lease expiry, guest exclusion) | `uv run pytest tests/services/test_eval_queue.py -q` | 6 passed | PASS |
| Migration test (columns, eval_jobs table, indexes, D-117-10 backfill) | `uv run pytest tests/test_migration_117.py -q` | 5 passed | PASS |
| Drain tests (best_move, dedup, flaw PV, classify hook, oracle counts, WR-02, gather discipline) | `uv run pytest tests/services/test_full_eval_drain.py -q` | 21 passed | PASS |
| Admin endpoint registered | `python -c "from app.main import app; assert any('enqueue-tier1' in p for p in [r.path for r in app.routes])"` | `/api/admin/eval/enqueue-tier1/{game_id}` | PASS |
| Type check | `uv run ty check app/ tests/` | All checks passed | PASS |
| Lint | `uv run ruff check app/ tests/` | All checks passed | PASS |
| WR-02 gate repoint (no white_blunders.is_ in non-comment drain code) | `grep -vn '^#' eval_drain.py \| grep -c "white_blunders.is_(None)"` | 0 | PASS |
| Full suite (no regressions) | `uv run pytest -n auto -q` | 2586 passed, 10 skipped | PASS |

---

### Probe Execution

Step 7c: SKIPPED (no probe scripts declared in PLAN.md; phase is service/migration work verified by the test suite above)

---

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|-------------|-------------|--------|----------|
| EVAL-04 | 117-01, 117-03 | best_move (PV[0] UCI) every ply; full PV only at flaw-adjacent ply N+1; opening dedup transplant | SATISFIED | `engine.py:246-507`; `eval_drain.py:205,318,442-458`; `TestBestMove`, `TestFlawPv` PASS |
| EVAL-06 | 117-01, 117-03 | classify_game_flaws auto on completion; oracle count columns filled | SATISFIED | `eval_drain.py:1218`; `_classify_and_fill_oracle:355-468`; `TestClassifyHook`, `TestOracleCounts` PASS |
| QUEUE-01 | 117-02 | Tiered priority queue: tier-1 > tier-2 > tier-3 | SATISFIED | `eval_queue_service.py:127-159,258-273`; `test_tier_priority` PASSES |
| QUEUE-02 | 117-02 | Round-robin per user + TC-weighted within user (D-117-04) | SATISFIED | CTE lines 136-148; `test_round_robin`, `test_tc_ordering` PASS |
| QUEUE-03 | 117-02, 117-03 | Tier-1 fan-out all plies across pool (~10s); superuser trigger | SATISFIED (automated portion) | `eval_drain.py:1172-1174` gather of all plies; `admin.py:86`; AST test `TestGatherOutsideSession` PASSES. Wall-clock ~10s requires human prod verification |
| QUEUE-05 | 117-02 | Idle backlog tier-3 derived pick (no pre-populated rows) | SATISFIED | `_claim_tier3_derived:177-221`; `test_tier3_derived` PASSES |
| QUEUE-06 | 117-01, 117-02 | Lease/report contract; expired lease requeue | SATISFIED | `claim_eval_job` sets status=leased; `_sweep_expired_leases` requeues; `report_job_complete`; `test_lease_expiry` PASSES |
| QUEUE-08 | 117-02, 117-03 | Guest exclusion on every tier + enqueue | SATISFIED | CTE `AND u.is_guest = false`; tier-3 `User.is_guest == False`; enqueue `if is_guest: return False`; `test_guest_exclusion` PASSES |

---

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| `eval_drain.py` | 85 | `_DRAIN_BATCH_SIZE = 10` comment says "D-11 (LIFO id-DESC pick size)" | Info | Dead constant — still used by Phase 91 `run_eval_drain` entry-ply pick, not by the Phase 117 `_full_drain_tick`. No functional issue; minor documentation drift from Phase 117's perspective |

No blockers. No TBD/FIXME/XXX markers in any Phase 117 files. The `_signal_flaw_completion` stub is intentional per D-117-11 and explicitly scoped to Phase 118.

---

### Human Verification Required

#### 1. Tier-1 Fan-Out Wall-Clock (~10s on prod pool)

**Test:** Fire `POST /api/admin/eval/enqueue-tier1/{game_id}` (with a superuser JWT) against a prod game that has `full_evals_completed_at IS NULL`. Measure wall-clock from insert to `full_evals_completed_at` being set.

**Expected:** ~10s total (spike 003 measured: ~60 plies / 6 workers x 0.98 s/ply = ~10s). All plies gathered in parallel via `asyncio.gather` across the pool.

**Why human:** Wall-clock latency depends on prod Stockfish pool size (currently 6 workers, possibly raised to 8). No live engine in CI.

#### 2. Progressive Flaw Appearance After Import (No Invalidation Storm)

**Test:** Import a fresh chess.com account, watch the flaw-dependent surfaces (game_flaws rows, oracle count columns) populate progressively. Check backend logs for any invalidation storm or errors from `_signal_flaw_completion`.

**Expected:** Flaws appear game-by-game as `full_evals_completed_at` is set; `_signal_flaw_completion` inserts user_id into `_recently_flaw_completed_users` set silently (no errors, no cache invalidation in Phase 117 — that is Phase 118's job).

**Why human:** Cross-surface UX timing; stub behavior in prod logs; real cache invalidation is a Phase 118 deliverable.

---

### Gaps Summary

No gaps. All 14 must-haves are VERIFIED against the codebase with test evidence. The only human verification items are:

1. Prod wall-clock for tier-1 fan-out (purely a perf sanity check — the structural code is correct).
2. Prod log inspection for `_signal_flaw_completion` stub (it is intentionally a no-op per D-117-11; the check is that it causes no errors).

Both are operational/perf checks, not correctness gaps.

---

### Notable Implementation Decisions Honored

- **D-117-07 (WR-02 repoint):** `white_blunders.is_(None)` completely removed as a gate; `lichess_evals_at.is_(None)` is the sole discriminator. `grep` confirms 0 non-comment occurrences.
- **D-117-09 (is_analyzed intentional):** `Game.is_analyzed` hybrid still uses `white_blunders IS NOT NULL` — correct; engine-filled oracle counts now set `white_blunders`, so engine-analyzed games also return `is_analyzed=True`.
- **D-117-11 (_signal_flaw_completion stub):** Correctly implemented as a set insert, not a real cache invalidation. Phase 118 wires the real logic.
- **D-117-12 (full_pv_completed_at):** Second completion marker set atomically with `full_evals_completed_at` and flaws in the same write transaction.
- **VALIDATION.md naming:** `wr02_repointed` in VALIDATION.md maps to class `TestWr02Repointed` with methods `test_wr02_engine_source_included` / `test_wr02_lichess_source_excluded` — both PASS. The `-k wr02_repointed` filter does not collect them (method names don't contain "wr02_repointed"), but the behavior is fully covered.
- **Rule 1 fix (POSITION_COPY_COLUMNS):** `best_move` and `pv` correctly added to bulk COPY columns in `game_repository.py`.
- **asyncio.gather outside session:** Structurally enforced in `_full_drain_tick` and confirmed by AST-based `TestGatherOutsideSession` test.

---

_Verified: 2026-06-13T11:30:00Z_
_Verifier: Claude (gsd-verifier)_
