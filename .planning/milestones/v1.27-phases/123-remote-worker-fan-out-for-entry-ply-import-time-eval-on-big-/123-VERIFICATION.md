---
phase: 123-remote-worker-fan-out-for-entry-ply-import-time-eval-on-big
verified: 2026-06-16T00:00:00Z
status: human_needed
score: 12/12 must-haves verified
overrides_applied: 0
human_verification:
  - test: "End-to-end big-first-import latency reduction"
    expected: "evals_completed_at populates faster than server-pool-only for a >= 300-game import with an entry-capable worker running; entry_eval_leased_by shows distinct worker IDs in the DB"
    why_human: "Requires a real >= 300-game import against a live worker fleet; not reproducible in unit tests"
  - test: "Mixed-fleet backward compat"
    expected: "An old worker (no scope param, no X-Worker-Id header) still drains full-ply, never touches entry-ply, and leased_by falls back to 'remote-worker'"
    why_human: "Needs an un-upgraded worker binary running against the new server side by side; can't be simulated in unit tests"
---

# Phase 123: Remote-Worker Fan-out for Entry-Ply Verification Report

**Phase Goal:** Extend the headless remote eval worker pool to also drain entry-ply (import-time, depth-15) eval in parallel on big first imports. The worker gains a second, higher-priority work type via a three-rung priority ladder: tier-1 single-game > entry-ply fresh-import drain > tier-3 idle backlog. Delivered as: (1) lease column + migration + SKIP-LOCKED LIFO claim; (2) batched /entry-lease endpoint with D-5 gate; (3) batched /entry-submit endpoint with no-shift path; (4) worker CLI D-06 ladder + depth-15 mode; (5) D-5 backlog-depth gate.

**Verified:** 2026-06-16
**Status:** human_needed
**Re-verification:** No — initial verification

---

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | A new big-import game can be atomically leased by exactly one claimer (server or remote); a second concurrent claim returns a disjoint set (no double-lease) | VERIFIED | `_claim_entry_eval_games` in `eval_drain.py:1032-1067` uses `UPDATE ... WHERE id IN (SELECT ... FOR UPDATE SKIP LOCKED) RETURNING id` with all values bound as `:params`. `test_lease_partition` inserts > batch_size pending games and asserts two sequential claims with different worker_ids return disjoint sets. |
| 2 | The in-process server drain `_pick_pending_game_ids` claims through the lease column and sets the lease when it picks (D-01) | VERIFIED | `eval_drain.py:1070-1092`: `_pick_pending_game_ids` calls `_claim_entry_eval_games(session, WORKER_ID_SERVER_POOL, limit, ENTRY_LEASE_TTL_SECONDS)` and commits before engine work. |
| 3 | A crashed/stale lease (`entry_eval_lease_expiry < now()`) is reclaimable by the next claimer (TTL reclaim) | VERIFIED | Claim predicate at `eval_drain.py:1058`: `AND (entry_eval_lease_expiry IS NULL OR entry_eval_lease_expiry < now())`. `test_lease_reclaim` in `test_eval_worker_endpoints.py:1178` sets a past-expiry lease and asserts re-claim succeeds; a future-expiry game is not re-claimed. |
| 4 | The migration adds two nullable columns to games with no data loss and no backfill | VERIFIED | `alembic/versions/20260616_120000_phase_123_entry_eval_lease.py`: `entry_eval_lease_expiry` (`DateTime(timezone=True)`, nullable) and `entry_eval_leased_by` (`String(16)`, nullable) added via `op.add_column`. No backfill, no index. `down_revision = "7d5a4aa09a47"`. |
| 5 | POST /eval/remote/entry-lease (operator-token auth) returns `{game_id, ply, fen}[]` for pending big-import games, gated by the D-5 backlog existence probe (204 when backlog < threshold) | VERIFIED | `eval_remote.py:474-542`: endpoint behind `Depends(require_operator_token)`. D-5 probe at line 492-508: `SELECT 1 FROM games WHERE evals_completed_at IS NULL ORDER BY id DESC LIMIT 1 OFFSET :offset` with `offset = ENTRY_LEASE_BACKLOG_THRESHOLD - 1` (299). Returns 204 when probe finds nothing. Returns `EntryLeaseResponse` with `positions: list[EntryLeasePosition]`. Gate tests `test_entry_lease_gate_below_threshold` (THRESHOLD-1 -> 204) and `test_entry_lease_gate_at_threshold` (THRESHOLD -> 200) both pass. |
| 6 | POST /eval/remote/entry-submit applies entry evals at the correct ply with NO +1 shift, classifies flaws, stamps evals_completed_at, and is idempotent on double-submit | VERIFIED | `eval_remote.py:552, 599-604`: explicitly uses `_apply_eval_results` (no shift), NOT `_apply_full_eval_results`. Calls `_classify_and_insert_flaws` then `_mark_evals_completed`. `test_entry_submit_no_shift` (passes), `test_entry_submit_stamps_evals_completed_at` (passes), `test_entry_submit_idempotent` (passes). |
| 7 | GET/POST /eval/remote/lease accepts an optional scope param: absent = bundled (backward-compat); scope=explicit = tier-1/2 only; scope=idle = tier-3 only | VERIFIED | `eval_remote.py:356`: `scope: Annotated[Literal["explicit", "idle"] \| None, Query()] = None`. Passed to `claim_eval_job(worker_id=worker_id, scope=scope)` at line 383. `eval_queue_service.py:458-527`: scope=None (bundled), scope="explicit" (early return after `_claim_queued_job`), scope="idle" (skips to `_claim_tier3_derived`). Tests `test_scope_explicit_returns_only_tier1_2`, `test_scope_idle_skips_tier1_2`, `test_scope_absent_is_bundled` all pass. |
| 8 | X-Worker-Id header (advisory only) populates leased_by / entry_eval_leased_by; absent header falls back to "remote-worker" | VERIFIED | `eval_remote.py:335-344`: `worker_id_label` dependency reads `Header(alias="X-Worker-Id")`, returns `x_worker_id or _WORKER_ID_REMOTE`. Wired to `/lease` (line 355, 383) and `/entry-lease` (line 477, 513). Tests `test_worker_id_header_populates_leased_by_on_entry_lease` and `test_worker_id_absent_falls_back_to_remote_worker_on_entry_lease` pass. |
| 9 | Both new endpoints reject missing/invalid operator token | VERIFIED | `eval_remote.py:476`: `_auth: Annotated[None, Depends(require_operator_token)]`; same on `/entry-submit` at line 548. Tests `test_entry_lease_auth_missing_token`, `test_entry_lease_auth_wrong_token`, `test_entry_submit_auth_missing_token` all pass. |
| 10 | The worker per-cycle runs the D-06 ladder: POST /lease?scope=explicit -> if 204, POST /entry-lease -> if 204/empty, POST /lease?scope=idle | VERIFIED | `remote_eval_worker.py:200-244`: `_run_cycle` implements the three-rung ladder. POST to `/api/eval/remote/lease?scope=explicit` at line 221; if 204 falls to `/api/eval/remote/entry-lease` at line 228; if 204 falls to `/api/eval/remote/lease?scope=idle` at line 235. Tests `test_ladder_explicit_first_skips_entry_lease`, `test_ladder_entry_ply_on_explicit_204`, `test_ladder_falls_to_idle_when_entry_lease_204` all pass. |
| 11 | Entry-ply positions are evaluated with EnginePool.evaluate (depth-15), NOT evaluate_nodes_with_pv (1M-node), and submitted as {game_id, ply, eval_cp, eval_mate} | VERIFIED | `remote_eval_worker.py:123-150`: `_eval_entry_positions` calls `pool.evaluate(b)` (depth-15) in `asyncio.gather`. Return dict contains `game_id, ply, eval_cp, eval_mate` — no `best_move/pv`. `evaluate_nodes_with_pv` only appears in the docstring warning comment, not in the function body. `test_entry_eval_uses_depth15_not_evaluate_nodes_with_pv` asserts `evaluate_nodes_with_pv.assert_not_called()`. |
| 12 | Each worker self-assigns a distinctive ID (random ~8-char base36; --worker-id override validated < 10 chars) sent via X-Worker-Id header on every call | VERIFIED | `remote_eval_worker.py:81-90`: `_generate_worker_id()` uses `secrets.randbelow` to produce 8 chars from `_WORKER_ID_ALPHABET` (base36). `parse_args` at line 429 adds `--worker-id` flag; validation at line 444: `len(args.worker_id) >= 10` triggers `parser.error`. X-Worker-Id set on `httpx.AsyncClient` constructor at line 355. Tests `test_worker_id_default_length`, `test_worker_id_override_too_long_raises`, `test_worker_id_override_exactly_ten_chars_raises` all pass. |

**Score:** 12/12 truths verified

---

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `alembic/versions/20260616_120000_phase_123_entry_eval_lease.py` | Migration adding `entry_eval_lease_expiry` + `entry_eval_leased_by VARCHAR(16)` to games | VERIFIED | File exists. `op.add_column("games", sa.Column("entry_eval_lease_expiry", sa.DateTime(timezone=True), nullable=True))` and `sa.Column("entry_eval_leased_by", sa.String(16), nullable=True)`. `down_revision = "7d5a4aa09a47"`. Proper `downgrade()` drops columns in reverse order. No backfill, no new index. |
| `app/models/game.py` | `entry_eval_lease_expiry` + `entry_eval_leased_by` mapped_columns | VERIFIED | Lines 190-196: `entry_eval_lease_expiry: Mapped[datetime.datetime \| None]` and `entry_eval_leased_by: Mapped[str \| None]` with `sa.String(16)` in the eval-marker block. |
| `app/services/eval_drain.py` | Shared `_claim_entry_eval_games` SKIP-LOCKED LIFO helper + `ENTRY_LEASE_*` constants + D-01 server lease | VERIFIED | Lines 118-132: three named constants with rationale comments (`ENTRY_LEASE_TTL_SECONDS=20`, `ENTRY_LEASE_BATCH_SIZE=50`, `ENTRY_LEASE_BACKLOG_THRESHOLD=300`). Lines 1032-1067: `_claim_entry_eval_games` with `FOR UPDATE SKIP LOCKED`, all values bound as `:params` (no f-string interpolation). Lines 1070-1092: `_pick_pending_game_ids` delegates to `_claim_entry_eval_games(session, WORKER_ID_SERVER_POOL, ...)`. |
| `app/schemas/eval_remote.py` | `EntryLeasePosition / EntryLeaseResponse / EntrySubmitEval / EntrySubmitRequest / EntrySubmitResponse` | VERIFIED | Lines 60-85: all five schemas present. `EntryLeasePosition` has `game_id`, `ply: int = Field(ge=0)`, `fen`. `EntrySubmitRequest.evals` has `Field(max_length=MAX_SUBMIT_EVALS)`. |
| `app/routers/eval_remote.py` | `/entry-lease` + `/entry-submit` endpoints, scope param on `/lease`, `X-Worker-Id` label dependency | VERIFIED | Lines 474-542: `/entry-lease` with D-5 probe and `require_operator_token`. Lines 545-626: `/entry-submit` with no-shift path and `require_operator_token`. Line 356: `scope` query param on `/lease`. Lines 335-344: `worker_id_label` dependency reading `X-Worker-Id`. |
| `app/services/eval_queue_service.py` | `scope: Literal["explicit","idle"] \| None` param on `claim_eval_job` | VERIFIED | Line 458: `scope: Literal["explicit", "idle"] \| None = None`. Three branches verified at lines 473-527. |
| `scripts/remote_eval_worker.py` | D-06 ladder in `_run_cycle`, `_eval_entry_positions` depth-15, `--worker-id` flag, `X-Worker-Id` header, random worker-id generator | VERIFIED | All present and substantive (lines 81-150, 200-244, 329-358, 429-447, 480-486). |
| `tests/test_remote_eval_worker.py` | Worker-id generation/validation + ladder-sequencing tests | VERIFIED | File exists (283 lines). 11 tests: `test_worker_id_default_length`, `test_worker_id_uniqueness`, `test_worker_id_override_too_long_raises`, `test_worker_id_override_exactly_ten_chars_raises`, `test_worker_id_override_nine_chars_accepted`, `test_worker_id_override_short_accepted`, `test_worker_id_max_len_constant`, `test_ladder_explicit_first_skips_entry_lease`, `test_ladder_entry_ply_on_explicit_204`, `test_ladder_falls_to_idle_when_entry_lease_204`, `test_entry_eval_uses_depth15_not_evaluate_nodes_with_pv`. All 11 pass. |
| `tests/test_eval_worker_endpoints.py` | 21 new Phase 123 tests (lease claim + entry endpoints + scope + worker-id) | VERIFIED | Tests enumerated and confirmed present: 4 lease-helper tests (partition, LIFO, reclaim, leased_by_set), 9 entry endpoint tests, 3 scope tests, 4 worker-id tests, plus SF version gate test = 21 total. All listed in `--collect-only` output. |

---

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `eval_drain.py::_pick_pending_game_ids` | `eval_drain.py::_claim_entry_eval_games` | server-side lease claim (D-01) | VERIFIED | Line 1088: `game_ids = await _claim_entry_eval_games(session, WORKER_ID_SERVER_POOL, limit, ENTRY_LEASE_TTL_SECONDS)` |
| `eval_drain.py::_claim_entry_eval_games` | `games.entry_eval_lease_expiry` | `UPDATE ... FOR UPDATE SKIP LOCKED RETURNING id` | VERIFIED | Lines 1050-1066: `sa.text(""" UPDATE games SET entry_eval_lease_expiry = ... WHERE id IN (SELECT id ... FOR UPDATE SKIP LOCKED) RETURNING id """)` |
| `eval_remote.py::entry_lease` | `eval_drain.py::_claim_entry_eval_games` | shared claim helper from Plan 01 | VERIFIED | Line 512-515: `game_ids = await _claim_entry_eval_games(claim_session, worker_id, ENTRY_LEASE_BATCH_SIZE, ENTRY_LEASE_TTL_SECONDS)` |
| `eval_remote.py::entry_submit` | `eval_drain.py::_apply_eval_results` | NO-shift entry-ply write path (NOT `_apply_full_eval_results`) | VERIFIED | Line 602: `await _apply_eval_results(write_session, eval_targets, eval_results)`. Confirmed `_apply_full_eval_results` does NOT appear in the `entry_submit_eval` function body (only in module imports and comments). |
| `eval_remote.py::lease` | `eval_queue_service.py::claim_eval_job` | scope param pass-through | VERIFIED | Line 383: `claim = await claim_eval_job(worker_id=worker_id, scope=scope)` |
| `remote_eval_worker.py::_run_cycle` | `/api/eval/remote/entry-lease` | D-06 ladder, fired when scope=explicit returns 204 | VERIFIED | Line 228: `entry_resp = await client.post("/api/eval/remote/entry-lease")` |
| `remote_eval_worker.py::_eval_entry_positions` | `EnginePool.evaluate` | depth-15 eval (NOT `evaluate_nodes_with_pv`) | VERIFIED | Line 141: `results = await asyncio.gather(*(pool.evaluate(b) for b in boards))`. `evaluate_nodes_with_pv` absent from function body. |
| `remote_eval_worker.py::httpx.AsyncClient` | `X-Worker-Id` header | set once on client alongside `X-Operator-Token` | VERIFIED | Lines 354-355: `headers={"X-Operator-Token": token, "X-Worker-Id": worker_id}` on `httpx.AsyncClient` constructor. |

---

### Data-Flow Trace (Level 4)

Not applicable — this phase delivers a background evaluation pipeline (no React/frontend components rendering dynamic data). The eval results flow from: remote worker -> `/entry-submit` -> `_apply_eval_results` (writes `eval_cp`/`eval_mate` to `game_positions`) -> `_classify_and_insert_flaws` -> `_mark_evals_completed` (stamps `evals_completed_at`). The data flow is verified by behavioral tests (`test_entry_submit_no_shift`, `test_entry_submit_stamps_evals_completed_at`) rather than a data-flow trace.

---

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| Worker unit tests: ID generation, ladder sequencing, depth-15 assertion | `uv run pytest tests/test_remote_eval_worker.py -x -q` | 11 passed in 6.85s | PASS |
| Entry-submit no-shift assertion | `uv run pytest tests/test_eval_worker_endpoints.py::test_entry_submit_no_shift -x -q` | 1 passed in 4.96s | PASS |
| D-5 gate boundary (THRESHOLD-1 -> 204, THRESHOLD -> 200) | `uv run pytest tests/test_eval_worker_endpoints.py::test_entry_lease_gate_below_threshold tests/test_eval_worker_endpoints.py::test_entry_lease_gate_at_threshold -x -q` | 2 passed in 8.03s | PASS |
| All new Phase 123 tests enumerable | `uv run pytest tests/test_eval_worker_endpoints.py --collect-only -q \| grep "entry\|scope\|lease_partition\|leased_by\|worker_id"` | 21 tests collected | PASS |

---

### Probe Execution

No conventional `scripts/*/tests/probe-*.sh` probes were declared in PLAN files or found in the scripts directory for this phase. Skipped.

---

### Requirements Coverage

Requirements are tracked per-plan via plan frontmatter (not REQUIREMENTS.md, which is absent). All plan-declared requirements have implementation evidence:

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|-------------|-------------|--------|----------|
| SEED-051-D-1 | 01, 03 | Three-rung priority ladder; D-01 server partition | SATISFIED | `_pick_pending_game_ids` uses `_claim_entry_eval_games`; worker `_run_cycle` implements the ladder |
| SEED-051-D-2 | 03 | Server derives FENs; worker stays dumb Stockfish node | SATISFIED | `/entry-lease` calls `_collect_eval_targets_from_db` server-side; worker only passes `eval_cp/eval_mate` |
| SEED-051-D-3 | 01 | Nullable lease column on `games`, SKIP LOCKED LIFO claim | SATISFIED | Migration adds `entry_eval_lease_expiry`, `_claim_entry_eval_games` uses `FOR UPDATE SKIP LOCKED` |
| SEED-051-D-5 | 02 | Backlog existence probe gates `/entry-lease` | SATISFIED | D-5 probe at `OFFSET = THRESHOLD - 1 = 299` with bound `:param`; 204 on shallow backlog |
| D-01 | 01 | Server drain leases via `_claim_entry_eval_games` | SATISFIED | `_pick_pending_game_ids` calls shared claim helper |
| D-02 | 02 | D-5 gate is remote-lease-only; server pool unaffected | SATISFIED | Probe only in `/entry-lease` endpoint; `_pick_pending_game_ids` has no probe |
| D-03 | 01 | Named module-level constants for tuning knobs | SATISFIED | `ENTRY_LEASE_TTL_SECONDS=20`, `ENTRY_LEASE_BATCH_SIZE=50`, `ENTRY_LEASE_BACKLOG_THRESHOLD=300` with rationale comments |
| D-04 | 01 | Entry-ply lease TTL short (20s, well under full-ply 120s) | SATISFIED | `ENTRY_LEASE_TTL_SECONDS: int = 20` |
| D-05 | 02 | `scope` param on `/lease` + `claim_eval_job` | SATISFIED | `Literal["explicit", "idle"] \| None` on both; scope=None is exact backward-compat |
| D-06 | 03 | D-06 three-rung ladder in worker `_run_cycle` | SATISFIED | explicit -> entry-lease -> idle; entry-ply always-on per D-08 |
| D-07 | 02 | Separate `/entry-lease` and `/entry-submit` endpoints | SATISFIED | Both endpoints exist at `POST /eval/remote/entry-lease` and `POST /eval/remote/entry-submit` |
| D-08 | 03 | Entry-ply always-on (no opt-in flag) | SATISFIED | No flag in `parse_args`; server D-5 gate handles the "no big import" case |
| D-09 | 01, 02 | `entry_eval_leased_by` is `VARCHAR(16)`, NOT Text | SATISFIED | Migration uses `sa.String(16)`; model uses `sa.String(16)`; plan rationale documented |
| D-10 | 02, 03 | Distinctive worker IDs via `X-Worker-Id` header; absent -> "remote-worker" | SATISFIED | `worker_id_label` dependency; `_generate_worker_id()` in worker; fallback to `_WORKER_ID_REMOTE` |

---

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| None | — | No TBD/FIXME/XXX markers found in phase-modified files | — | — |
| None | — | No unresolved placeholder or stub patterns found | — | — |

Note: The code review (123-REVIEW.md) identified CR-01 (X-Worker-Id length not validated server-side, can cause a 500 if an HTTP client sends > 16 chars) and six warnings. These are advisory findings from the separate code review process. The phase goal is achieved; CR-01 is a robustness hardening item on the trusted-operator surface, not a goal-blocking stub or missing capability. The phase delivers all five ROADMAP scope items with passing tests.

---

### Human Verification Required

The two items below come from VALIDATION.md (manually-only verifications, harvested per Step 8):

#### 1. End-to-end big-first-import latency reduction

**Test:** Trigger a big first import (>= 300 games) in dev or prod with an entry-capable worker (Plan 03 binary) running alongside the server pool.
**Expected:** `evals_completed_at` populates faster than server-pool-only; `entry_eval_leased_by` shows distinct worker IDs in the database (confirming the remote worker is actually claiming and completing entry-ply games).
**Why human:** Requires a real >= 300-game import against a live worker fleet. The D-5 gate threshold of 300 games and the actual throughput split between server pool and remote worker(s) cannot be exercised in unit tests.

#### 2. Mixed-fleet backward compat

**Test:** Run an un-upgraded worker binary (no `--worker-id`, no `scope` param, no `X-Worker-Id` header) against the new server alongside a new binary.
**Expected:** The old worker continues draining full-ply games unchanged (`/lease` with no scope returns bundled tier-1>2>3 as before), never touches `/entry-lease` or `/entry-submit`, and `leased_by` in `eval_jobs` falls back to `"remote-worker"`.
**Why human:** Needs two worker binary versions simultaneously in a real network environment; the zero-coordination rollout contract (D-05/D-10) can only be confirmed with a real mixed fleet.

---

### Gaps Summary

No gaps found. All 12 must-have truths are VERIFIED. All required artifacts exist, are substantive, and are wired. All key links are confirmed. The full backend suite passes (2705 passed, 10 skipped per 123-03-SUMMARY.md). Ruff and ty are clean.

Status is `human_needed` (not `passed`) because two integration behaviors — actual latency reduction on a real big import, and mixed-fleet backward compat — require live infrastructure to confirm. These were documented as manual-only in VALIDATION.md before execution.

---

*Verified: 2026-06-16*
*Verifier: Claude (gsd-verifier)*
