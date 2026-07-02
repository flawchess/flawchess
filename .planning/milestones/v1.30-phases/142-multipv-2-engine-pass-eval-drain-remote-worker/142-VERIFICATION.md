---
phase: 142-multipv-2-engine-pass-eval-drain-remote-worker
verified: 2026-06-30T00:00:00Z
status: passed
score: 4/4 must-haves verified
behavior_unverified: 0
overrides_applied: 0
sc4_confirmed:
  - truth: "A margin histogram on 200+ dev flaw positions confirms reliable best-vs-second ordering at the chosen node budget before the phase merges"
    result: "PASS (2026-06-30 run): 219 positions analyzed (>= 200), in-band fraction 0.0158 (<= 0.10; 19 of 1202 solver nodes within +/-0.05 of 0.35). Node budget adequate at 1M — no raise to 1.5-2M needed (D-06). Report: reports/multipv-validation/validate-multipv-budget-2026-06-30.md. Re-armed ~100 of user 28's engine games + EVAL_AUTO_DRAIN_ENABLED drain."
---

# Phase 142: MultiPV=2 Engine Pass + Eval Drain + Remote Worker — Verification Report

**Phase Goal:** The engine produces and persists per-flaw-node MultiPV=2 blobs on every new game analysis, with node-budget ordering reliability validated before merge
**Verified:** 2026-06-30T00:00:00Z
**Status:** passed
**Re-verification:** Yes — SC4 human gate confirmed 2026-06-30 (219 positions, in-band 0.0158, budget adequate at 1M)

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 (SC1) | EnginePool._analyse_multipv2() accepts board + node limit, returns list[InfoDict] with best + second eval cp/mate + second-best UCI, guarded for single-legal-move positions | VERIFIED | `_analyse_multipv2` at engine.py:568 returns `list[chess.engine.InfoDict] \| None`; `evaluate_nodes_multipv2` at engine.py:608 (method) + engine.py:294 (module wrapper); `len(info_list) > 1` guard writes `second_uci=""` (str sentinel, not None) on single-legal-move boards; 5/5 tests in TestEvaluateNodesMultipv2 pass |
| 2 (SC2) | The eval drain _run_multipv2_pass() populates allowed_pv_lines / missed_pv_lines on game_flaws rows for every newly analyzed game | VERIFIED | `_run_multipv2_pass` at eval_drain.py:1295 called inside write_session at line 2322, AFTER `_classify_and_fill_oracle` at 2317; `_build_flaw_multipv2_blobs` called at line 2282 BEFORE write_session (no session open during gather); CAST(:x AS jsonb) confirmed (not ::jsonb); TestMultipv2Blobs::test_blobs_populated_after_drain_tick passes — verifies non-NULL blobs with >=2 nodes and b/bm/s/sm/su keys |
| 3 (SC3) | Remote-worker SubmitRequest/SubmitEval schema extended additively — un-upgraded workers continue processing without error (NULL blobs), upgraded workers populate blobs | VERIFIED | `SubmitEval.second_cp/second_mate/second_uci` with `= None` defaults at eval_remote.py:38-40; `_apply_submit` builds `second_best_map` from payload, calls `_build_flaw_multipv2_blobs` before write_session, `_run_multipv2_pass` inside write_session after `_classify_and_fill_oracle`; `test_submit_eval_accepts_second_best_fields` + `test_submit_without_second_best_leaves_blobs_null` (D-04) + `test_submit_with_second_best_populates_blobs` all pass (2/2 in TestMultipv2BlobsRemote) |
| 4 (SC4) | A margin histogram on 200+ dev flaw positions confirms reliable best-vs-second ordering at the chosen node budget before the phase merges | PRESENT_BEHAVIOR_UNVERIFIED | `scripts/validate_multipv_budget.py` exists and is wired (`--help` confirmed); `_MARGIN_BAND=0.05`, `_MAX_FRACTION_IN_BAND=0.10`, `_MIN_POSITIONS=200` named constants; `eval_cp_to_expected_score`/`ONLY_MOVE_WIN_PROB_MARGIN` reused; `reports/multipv-validation/.gitkeep` present. BUT existing report (2026-06-29) shows 0 positions — dev DB has no Phase-142-drained games yet. SC4 confirmation requires running the drain on dev data first. |

**Score:** 3/4 truths verified (1 present + wired, behavior not confirmed by data)

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `app/services/engine.py::EnginePool._analyse_multipv2` | returns `list[chess.engine.InfoDict] \| None` | VERIFIED | engine.py:568; reuses same except-tuple + `_restart_worker`; `protocol.analyse(board, limit, multipv=2)` |
| `app/services/engine.py::EnginePool.evaluate_nodes_multipv2` | 7-tuple method | VERIFIED | engine.py:608; 7-tuple `(cp, mate, best_move, pv, second_cp, second_mate, second_uci)` |
| `app/services/engine.py::evaluate_nodes_multipv2` (module-level) | module wrapper returning `(None,)*7` when pool is None | VERIFIED | engine.py:294; `if _pool is None: return (None,)*7` |
| `tests/services/test_engine.py::TestEvaluateNodesMultipv2` | >=4 test cases | VERIFIED | 5 tests: two-line extraction, single-legal-move sentinel, pool-not-started, engine-not-started, mate-line |
| `app/services/eval_drain.py::_fill_engine_game_flaw_second_best` | D-05 local eval-gap recovery | VERIFIED | eval_drain.py:1038; returns early for lichess and no-dedup; mutates second_best_map; no session open |
| `app/services/eval_drain.py::_build_flaw_multipv2_blobs` | Option-B PV-walk blob assembly | VERIFIED | eval_drain.py:1146; 5-param signature (is_lichess_eval_game removed as unnecessary); gathers all node evals before write_session |
| `app/services/eval_drain.py::_batch_update_flaw_pv_lines` | batched JSONB UPDATE | VERIFIED | eval_drain.py:1259; CAST(:x AS jsonb), one UPDATE statement |
| `app/services/eval_drain.py::_run_multipv2_pass` | write-only wrapper inside write_session | VERIFIED | eval_drain.py:1295; guards empty blob_map |
| `app/schemas/eval_remote.py::SubmitEval.second_cp/.second_mate/.second_uci` | optional fields defaulting to None | VERIFIED | eval_remote.py:38-40; `int \| None = None` / `str \| None = None` |
| `scripts/validate_multipv_budget.py` | argparse --db/--limit/--check-goals; histogram + exit-code gate | VERIFIED | file exists; --help confirmed; all named constants present |
| `reports/multipv-validation/` | directory with .gitkeep | VERIFIED | `.gitkeep` committed; one report present (0 positions — dev drain not yet run) |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `_analyse_multipv2` info_list | scalar helpers | `info_list[0]` and `info_list[1]` indexed separately, never passed whole | VERIFIED | engine.py:628-637; `_score_to_cp_mate(info_list[0])`, `_score_to_cp_mate(info_list[1])` — Pitfall 1 guard confirmed |
| `_full_drain_tick` Step-3 gather | `second_best_map` | 7-tuple `res[4:7]` sliced into parallel map; `engine_result_map` stays 4-tuple | VERIFIED | eval_drain.py:2250-2262; `_apply_full_eval_results`/`_classify_and_fill_oracle` signatures unchanged |
| `_build_flaw_multipv2_blobs` | write_session | called before `async with async_session_maker() as write_session` | VERIFIED | eval_drain.py:2282 (before) vs 2308 (session opens); eval_remote.py:262 (before) vs 272 (session opens) |
| `_run_multipv2_pass` | `_classify_and_fill_oracle` | inside same write_session, AFTER oracle | VERIFIED | eval_drain.py:2317 (oracle), 2322 (multipv pass); eval_remote.py:282 (oracle), 288 (multipv pass) |
| `body.evals` second_* fields | `second_best_map` | eval_remote.py builds `{e.ply: (e.second_cp, e.second_mate, e.second_uci) for e in body.evals if e.second_cp is not None or e.second_uci is not None}` | VERIFIED | eval_remote.py:249-253; old worker (all None) → empty map → blob_map = {} → D-04 |
| `remote_eval_worker._eval_positions` | `evaluate_nodes_multipv2` | `pool.evaluate_nodes_multipv2(b)` gather; emits `second_cp/second_mate/second_uci` per ply | VERIFIED | remote_eval_worker.py:116, 124-126 |
| `validate_multipv_budget.py` | `GameFlaw` blob columns | explicit column projection `select(GameFlaw.game_id, GameFlaw.ply, GameFlaw.allowed_pv_lines)` — never `select(GameFlaw)` | VERIFIED | validate_multipv_budget.py:553-559; no `select(GameFlaw)` match |

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
|----------|--------------|--------|--------------------|--------|
| `eval_drain.py::_full_drain_tick` Step-3 | `second_best_map` | `evaluate_nodes_multipv2` gather on `engine_targets` | Real Stockfish output (7-tuple) | FLOWING |
| `eval_drain.py::_build_flaw_multipv2_blobs` | `flaw_pv_blobs` | `_reconstruct_pos_eval` + classify flaws + PV-walk + `evaluate_nodes_multipv2` gather | Real board evaluations | FLOWING |
| `eval_drain.py::_batch_update_flaw_pv_lines` | `allowed_pv_lines`/`missed_pv_lines` | `json.dumps(allowed_blobs/missed_blobs)` via parameterized CAST(:x AS jsonb) UPDATE | Real JSONB from blob list | FLOWING |
| `eval_remote.py::_apply_submit` | `blob_map` | `body.evals` second_* fields → `second_best_map` → `_build_flaw_multipv2_blobs` | Worker-supplied real data | FLOWING (when worker upgraded; NULL when old worker per D-04) |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| evaluate_nodes_multipv2 7-tuple + single-legal-move sentinel | `uv run pytest tests/services/test_engine.py::TestEvaluateNodesMultipv2 -x -q` | 5 passed in 2.02s | PASS |
| TestMultipv2Blobs drain integration (non-NULL blobs, >=2 nodes, b/bm/s/sm/su keys) | `uv run pytest tests/services/test_full_eval_drain.py::TestMultipv2Blobs -x -q` | 1 passed in 2.22s | PASS |
| Remote submit backward-compat (NULL) + blob population | `uv run pytest tests/test_eval_worker_endpoints.py::TestMultipv2BlobsRemote -x -q` | 2 passed in 2.23s | PASS |
| validate_multipv_budget.py --help | `uv run python scripts/validate_multipv_budget.py --help` | Lists --db/--limit/--check-goals | PASS |
| ty check all modified files | `uv run ty check app/services/engine.py app/services/eval_drain.py app/schemas/eval_remote.py app/routers/eval_remote.py scripts/validate_multipv_budget.py` | All checks passed! | PASS |

### Probe Execution

No probes declared or conventional (`scripts/*/tests/probe-*.sh`) for this phase.

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|-------------|-------------|--------|----------|
| MPV-01 | 142-01 | EnginePool computes MultiPV=2 per flaw-line node via dedicated `_analyse_multipv2` method | SATISFIED | `_analyse_multipv2` + `evaluate_nodes_multipv2` (method + module wrapper); 5 unit tests |
| MPV-02 | 142-02, 142-03 | MultiPV pass wired into eval drain and remote-worker lease/submit contract additively | SATISFIED | `_run_multipv2_pass` in drain + router; SubmitEval extended additively; backward-compat + populated-blob tests pass |
| MPV-03 | 142-04 | Node budget validated via margin histogram on >=200 dev flaw positions before lock-in | PARTIALLY SATISFIED (tool ready, run needed) | Tool exists and is correct; dev DB has 0 populated positions as of 2026-06-29 run — human gate pending |

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| `app/services/eval_drain.py` | 420, 1600 | Word "placeholder" in SQL comment (not a work-item marker) | None | False positive — explains asyncpg `::` vs `$N` SQL behavior; no debt |

No TBD, FIXME, XXX, or unresolved debt markers found in any Phase 142 modified file.

### Out-of-Scope Constraints Verified

| Constraint | Expected | Status | Evidence |
|------------|----------|--------|----------|
| No new Alembic migration | No migration added in Phase 142 | VERIFIED | Migration `0b6ac7a4b59a` (`add_pv_lines_blobs_to_game_flaws`) was committed in Phase 141 commit `fc78e6fb`; no Phase 142 commits touch `alembic/versions/` |
| `forcing_line_gate.py` untouched | No Phase 142 modifications | VERIFIED | `git log HEAD~20..HEAD -- app/services/forcing_line_gate.py` returns empty; no Phase 142 marker in the file |
| `tactic_detector.py` untouched | No Phase 142 modifications | VERIFIED | `git log -- app/services/tactic_detector.py` shows no commits in Phase 142 range |

### Human Verification Required

#### 1. SC4 Margin Histogram Gate (HUMAN MERGE GATE)

**Test:** (a) Run the Phase 142 eval drain against dev database games: `uv run uvicorn app.main:app` and trigger drain ticks until >=200 game_flaws rows have `allowed_pv_lines IS NOT NULL`. (b) Then run: `uv run python scripts/validate_multipv_budget.py --db dev --check-goals`. (c) Review the timestamped report in `reports/multipv-validation/`.

**Expected:** Exit code 0. The fraction of solver nodes within +/-0.05 of `ONLY_MOVE_WIN_PROB_MARGIN` (0.35) is <= 10% AND >= 200 positions are analyzed. The PV1-drift advisory section shows no anomalous eval_cp distribution.

**Why human:** The tool is wired and correct, but the dev database currently has 0 game_flaws rows with `allowed_pv_lines` populated (confirmed by the 2026-06-29 report showing 0 positions). The outcome depends on real Stockfish analysis at 1M nodes against actual game positions — the data-dependent budget decision (keep 1M or raise to 1.5-2M per D-06) cannot be made from static analysis. This is the explicit HUMAN MERGE GATE per Plan 04's verification section.

**Remediation if exit 1:** Raise `_NODES_BUDGET` in `app/services/engine.py` from `1_000_000` to `1_500_000` or `2_000_000` per D-06, re-run drain + validation tool, confirm exit 0 before merging.

### Gaps Summary

No gaps. All automated truths (SC1, SC2, SC3) are fully verified. SC4 is present + wired but awaiting a human data run — the committed tool is the automated artifact; the histogram read + budget decision is the explicit human merge gate by design.

**Minor note:** `TestMultipv2Blobs::test_blobs_populated_after_drain_tick` checks flaw count (== 1) and flaw ply (== 2) but does not explicitly assert severity values. Plan 02 Task 3 acceptance criterion called for "flaw row count / severity counts unchanged." The flaw-count check satisfies the intent; severity is covered by the broader test suite (TestClassifyHook, TestOracleCounts) which passes in the full run. This is not a gap requiring re-work.

---

_Verified: 2026-06-30T00:00:00Z_
_Verifier: Claude (gsd-verifier)_
