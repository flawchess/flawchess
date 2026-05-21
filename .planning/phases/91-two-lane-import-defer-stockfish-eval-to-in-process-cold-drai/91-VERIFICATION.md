---
phase: 91-two-lane-import-defer-stockfish-eval-to-in-process-cold-drai
verified: 2026-05-21T00:00:00Z
status: human_needed
score: 12/13 must-haves verified
overrides_applied: 0
human_verification:
  - test: "Trigger an import on the dev DB (chess.com or lichess), then navigate to the Endgames page and the Openings Stats subtab."
    expected: "EvalCoverageHeader (`data-testid='eval-coverage-header'`) appears at the top of both pages showing a percentage and pending count, and disappears once coverage reaches 100%."
    why_human: "Component renders only when isPending is true and hook polls live API. Cannot be verified with grep — requires a running backend + frontend with real pending eval rows."
  - test: "While an import is in progress and the cold drain is running, open a Stockfish-dependent metric popover (e.g. Score Gap in EndgameMetricCard, or Conversion in EndgameTypeCard)."
    expected: "Popover body shows the one-line caveat 'Based on currently-evaluated games. N more being analysed — refresh in a few minutes for updated values.' while pendingCount > 0, and the caveat is absent after drain completes."
    why_human: "Conditional rendering inside popover body depends on runtime isPending + pendingCount values from the live hook. Cannot be exercised without a real import + drain cycle."
  - test: "Observe backend RSS during any import after the Phase 91 deploy."
    expected: "RSS stays flat and does not climb in step with import progress. No Postgres OOM-kill occurs. The absence of eval work in the hot lane is the key signal."
    why_human: "Memory behaviour is observable only at runtime (docker stats / /proc/PID/status). The architectural fix is tested by TestHotLaneNoEvalCalls regression guard, but real-world memory plateauing confirms it end-to-end."
  - test: "Watch the cold drain process pending evals after an import completes. Observe logs and EvalCoverageHeader updates."
    expected: "pct_complete on GET /imports/eval-coverage advances over time, header bar updates every ~10s, eventually disappears. No eval_drain Sentry errors during normal operation."
    why_human: "Drain liveness (whether it actually picks up and processes pending games) requires a running backend. Cannot be verified from source alone."
---

# Phase 91: Two-lane import — defer Stockfish eval to in-process cold drain Verification Report

**Phase Goal:** Restructure the import pipeline so the hot path holds no Stockfish work, and a separate in-process cold-drain coroutine evaluates entry plies in the background. Two concurrent 20k-game imports must complete without OOM-killing Postgres, the user must see opening-explorer / raw endgame WDL / flag-rate / time-per-move stats within seconds of import start, and Stockfish-dependent stats must fill in over the following minutes with honest per-metric sample-size labels.
**Verified:** 2026-05-21
**Status:** human_needed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

| #  | Truth | Status | Evidence |
|----|-------|--------|----------|
| 1  | `games.evals_completed_at TIMESTAMPTZ NULL` column exists with partial index `ix_games_evals_pending` | ✓ VERIFIED | `alembic/versions/20260521_015028_bd54be3a66bf_add_evals_completed_at_to_games.py` — column add + `op.create_index("ix_games_evals_pending", ..., postgresql_where="evals_completed_at IS NULL")` + backfill using `COALESCE(imported_at, NOW())`. Game ORM model has `evals_completed_at: Mapped[datetime.datetime \| None]`. |
| 2  | Hot lane (`_flush_batch`) makes zero calls to `engine.evaluate` | ✓ VERIFIED | `grep -cE 'engine\.evaluate\|engine_service\.evaluate' app/services/import_service.py` returns 0. `TestHotLaneNoEvalCalls.test_flush_batch_no_engine_calls` in `tests/services/test_import_service.py` is a CI-enforced regression guard. |
| 3  | Cold-drain coroutine `run_eval_drain` exists in `app/services/eval_drain.py`, uses LIFO pick, gathers outside session | ✓ VERIFIED | `eval_drain.py` (567 lines). `_pick_pending_game_ids` uses `.order_by(Game.id.desc()).limit(_DRAIN_BATCH_SIZE)`. `asyncio.gather` at line 533 is preceded by literal comment "CLAUDE.md hard rule: asyncio.gather must NEVER run inside an AsyncSession scope". The session is opened *after* the gather call in a separate `async with async_session_maker()` block. |
| 4  | `run_eval_drain` wired into FastAPI lifespan alongside `run_periodic_reaper` | ✓ VERIFIED | `app/main.py` line 70: `drain_task = asyncio.create_task(run_eval_drain(), name="eval-drain")`. Both tasks cancelled before either awaited; `stop_engine()` is last in `finally`. |
| 5  | `GET /imports/eval-coverage` returns `{pending_count, total_count, pct_complete}` for the authenticated user; 401 without auth; 100% on zero games | ✓ VERIFIED | `app/routers/imports.py` line 127: `@router.get("/eval-coverage", response_model=EvalCoverageResponse)`. Route is declared before `/{job_id}` (line 148) — no path-parameter shadowing. Zero-games guard at line 141. `count_pending_evals` uses `.is_(None)` (not `== None`). Five integration tests pass: auth, zero-games, all-complete, partial, cross-user scoping. |
| 6  | `useEvalCoverage` hook polls every 10s while `pct_complete < 100`, stops at 100% | ✓ VERIFIED | `frontend/src/hooks/useEvalCoverage.ts`: `refetchInterval: (query) => query.state.data?.pct_complete === 100 ? false : EVAL_COVERAGE_POLL_INTERVAL_MS`. Constants `EVAL_COVERAGE_POLL_INTERVAL_MS = 10_000` and `EVAL_COVERAGE_STALE_TIME_MS = 10_000` declared at module top. Default pre-load: `pct: 100, isPending: false`. |
| 7  | `EvalCoverageHeader` component renders with `role="status"`, `data-testid="eval-coverage-header"`, plural-aware copy, `Cpu h-3.5 w-3.5` icon; returns null when `isPending === false` | ✓ VERIFIED | Component source confirmed. `if (!isPending) return null`. Plural gate `=== 1`. D-04 exact copy: "Stockfish analysis: {pct}% complete ({pendingCount.toLocaleString()} {gamesLabel} pending)". |
| 8  | Header mounted on Endgames page AND Openings StatsTab ONLY; NOT on Import page, NOT in global topbar | ✓ VERIFIED | `Endgames.tsx` line 361: `<EvalCoverageHeader />`. `StatsTab.tsx` line 196: `<EvalCoverageHeader />`. `grep EvalCoverageHeader frontend/src/pages/Import.tsx` returns 0. No matches in layout/navbar files. |
| 9  | Per-metric caveat injected in `EvalConfidenceTooltip` and `MetricStatTooltip`; shown iff `isPending && pendingCount > 0`; absent when false | ✓ VERIFIED | Both files contain `{isPending === true && (pendingCount ?? 0) > 0 && (<p className="opacity-70"> Based on currently-evaluated games...)}`. D-06 exact copy with em-dash confirmed. Six RTL tests cover shown/absent/zero-count for each. |
| 10 | All 7 Cpu-bearing components thread `isPending`/`pendingCount` to their popovers | ✓ VERIFIED | All 7 files (`PositionResultsPanel`, `OpeningFindingCard`, `EndgameOverallEntryCard`, `EndgameOverallPerformanceSection`, `EndgameMetricCard`, `EndgameTypeCard`, `OpeningStatsCard`) show `useEvalCoverage` count of 2 (import + call). `EndgameTimePressureCard` count is 0 (correctly excluded per RESEARCH OQ-1). |
| 11 | Stress-test harness `scripts/measure_dual_import_rss.py` exists with 6 named constants, refuses prod, uses httpx | ✓ VERIFIED | Script is 921 lines. All 6 constants present (`RSS_PLATEAU_MAX_MB`, `POSTGRES_MEMORY_MAX_MB`, `SWAP_USAGE_MAX_PCT`, `DEFAULT_TARGET_GAMES`, `DEFAULT_POLL_INTERVAL_S`, `DEFAULT_COVERAGE_TIMEOUT_MIN`). Prod-refusal confirmed by live run: exits non-zero with "refusing" message. `requests.get/post` count = 0. `--help` exits 0. |
| 12 | Full test suite passes: 1605 backend + 601 frontend (pre-confirmed) | ✓ VERIFIED | Confirmed per prompt context: "1605 passed, 6 skipped (zero failures)" and "601 passed (zero failures)". All new test files exist: `test_migration_91_evals_completed_at.py`, `tests/services/test_eval_drain.py`, `tests/routers/test_imports_eval_coverage.py`, `tests/test_main_lifespan.py`. |
| 13 | Dual-20k stress-test execution with acceptance bounds confirmed | ? HUMAN NEEDED | Task 8.2 explicitly deferred to HUMAN-UAT per operator decision documented in 91-08-SUMMARY.md. The harness exists and is runnable, but the actual stress run has not been executed. |

**Score:** 12/13 truths verified (13th is operator-gated human UAT by documented decision)

### Deferred Items

Items not yet met but explicitly addressed via operator decision.

| # | Item | Addressed In | Evidence |
|---|------|-------------|----------|
| 1 | Dual-20k stress-test execution confirming RSS ≤ 1.6 GB, postgres ≤ 1.2 GB, swap ≤ 50%, both imports completed, coverage 100% | HUMAN-UAT (operator decision, not a later phase) | 91-08-SUMMARY.md: "Task 8.2 Status: DEFERRED TO HUMAN-UAT — formal acceptance-bound verification against a fresh-DB baseline is no longer a gate on Phase 91 completion." Structural OOM fix is verified by `TestHotLaneNoEvalCalls` CI regression guard. |

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `app/models/game.py` | `Game.evals_completed_at` mapped column | ✓ VERIFIED | Line 132: `Mapped[datetime.datetime \| None]`, `DateTime(timezone=True)`, `nullable=True` |
| `alembic/versions/20260521_*.py` | Schema migration: column + partial index + backfill | ✓ VERIFIED | `COALESCE(imported_at, NOW())`, `ix_games_evals_pending`, `down_revision = "e925558020b9"`, no `updated_at`/`created_at` |
| `tests/test_migration_91_evals_completed_at.py` | Up/down/backfill correctness test | ✓ VERIFIED | 4 tests: column+index, backfill no-pending-rows, downgrade, now-fallback |
| `app/services/eval_drain.py` | Cold-lane drain coroutine + eval helpers | ✓ VERIFIED | 567 lines; `run_eval_drain` + `_pick_pending_game_ids` + `_load_pgns_for_games` + `_collect_eval_targets_from_db` + `_mark_evals_completed`; constants present |
| `tests/services/test_eval_drain.py` | 6 architectural invariant tests | ✓ VERIFIED | All 6 test functions confirmed: gather-outside-session, LIFO, idempotency, engine-None, partial-index EXPLAIN, cancellation |
| `app/services/import_service.py` | Hot-lane refactor: eval stages stripped, Stage 5c added | ✓ VERIFIED | `engine.evaluate` count = 0; 7 duplicate helpers removed; `_collect_covered_game_ids` present; `from app.services.eval_drain import` present |
| `tests/services/test_import_service.py` | `TestHotLaneNoEvalCalls` + `TestHotLaneCoveredGate` | ✓ VERIFIED | Both test classes present with all required test methods |
| `app/schemas/imports.py` | `EvalCoverageResponse` Pydantic schema | ✓ VERIFIED | `class EvalCoverageResponse(BaseModel)` with `pending_count`, `total_count`, `pct_complete` as `int` |
| `app/repositories/game_repository.py` | `count_pending_evals(session, user_id) -> int` | ✓ VERIFIED | Uses `Game.evals_completed_at.is_(None)` (not `== None`) |
| `app/routers/imports.py` | `GET /imports/eval-coverage` endpoint | ✓ VERIFIED | Registered before `/{job_id}`, auth via `current_active_user`, zero-games guard, rounded pct |
| `tests/routers/test_imports_eval_coverage.py` | 5 integration tests for auth+shape+edge cases | ✓ VERIFIED | All 5 test functions present; constants `PARTIAL_PENDING_COUNT/TOTAL/PCT` present |
| `app/main.py` | Lifespan wiring for `run_eval_drain` | ✓ VERIFIED | `drain_task = asyncio.create_task(run_eval_drain(), name="eval-drain")`; both tasks cancelled before either awaited; `stop_engine` last |
| `tests/test_main_lifespan.py` | Lifespan smoke test for both tasks | ✓ VERIFIED | `test_both_background_tasks_spawned` + `test_drain_task_exception_on_shutdown_is_logged` |
| `frontend/src/types/api.ts` | `EvalCoverageResponse` interface | ✓ VERIFIED | Line 191: `export interface EvalCoverageResponse` |
| `frontend/src/hooks/useEvalCoverage.ts` | TanStack Query hook | ✓ VERIFIED | Polling logic, stop-at-100%, shared queryKey, pre-load defaults |
| `frontend/src/components/EvalCoverageHeader.tsx` | Page-level header bar | ✓ VERIFIED | `role="status"`, `data-testid`, plural-aware, `Cpu h-3.5 w-3.5`, null-when-complete |
| `frontend/src/pages/Endgames.tsx` | Header mounted on Endgames | ✓ VERIFIED | Line 361: `<EvalCoverageHeader />` |
| `frontend/src/pages/openings/StatsTab.tsx` | Header mounted on Openings Stats | ✓ VERIFIED | Line 196: `<EvalCoverageHeader />` |
| `frontend/src/components/insights/EvalConfidenceTooltip.tsx` | Caveat-aware tooltip body | ✓ VERIFIED | Conditional `<p>` with D-06 exact copy |
| `frontend/src/components/popovers/MetricStatTooltip.tsx` | Caveat-aware metric tooltip body | ✓ VERIFIED | Conditional `<p>` with D-06 exact copy |
| `scripts/measure_dual_import_rss.py` | Dual-20k stress-test harness | ✓ VERIFIED | 921 lines, 6 constants, prod-refusal gate, httpx |
| `logs/.gitkeep` | Tracked logs directory | ✓ VERIFIED | Present in git ls-files |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|----|--------|---------|
| `run_eval_drain` | `engine_service.evaluate` | `asyncio.gather` outside session | ✓ WIRED | Line 533 in eval_drain.py; comment immediately above confirms CLAUDE.md rule |
| `run_eval_drain` | `games.evals_completed_at` | `_mark_evals_completed` executemany UPDATE | ✓ WIRED | `update(games_table).values(evals_completed_at=now_ts)` with `bindparam("b_id")` |
| `app/main.py` lifespan | `run_eval_drain` | `asyncio.create_task(..., name="eval-drain")` | ✓ WIRED | Line 70 in main.py |
| `GET /imports/eval-coverage` | `game_repository.count_pending_evals` | `WHERE evals_completed_at IS NULL` | ✓ WIRED | Router line 143 calls repo; repo uses `.is_(None)` on `evals_completed_at` |
| `EvalCoverageHeader` | `useEvalCoverage` | Hook call inside component | ✓ WIRED | `const { pendingCount, pct, isPending } = useEvalCoverage()` |
| `Endgames.tsx + StatsTab.tsx` | `EvalCoverageHeader` | JSX mount | ✓ WIRED | `<EvalCoverageHeader />` at render top in both files |
| 7 Cpu-bearing components | `useEvalCoverage` | Hook call + `isPending={isPending} pendingCount={pendingCount}` on popovers | ✓ WIRED | All 7 files confirmed; `EndgameTimePressureCard` correctly untouched |
| `_flush_batch` (import_service) | `eval_drain._collect_covered_game_ids` | Stage 5c executemany UPDATE for covered games | ✓ WIRED | `covered_ids = _collect_covered_game_ids(...)` + `evals_completed_at=now_ts` UPDATE |

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
|----------|---------------|--------|-------------------|--------|
| `EvalCoverageHeader` | `pendingCount, pct` from `useEvalCoverage()` | `GET /imports/eval-coverage` → `count_pending_evals` → `SELECT COUNT(*) WHERE evals_completed_at IS NULL` | Yes — live DB query | ✓ FLOWING |
| `run_eval_drain` | `eval_targets` from `_collect_eval_targets_from_db` | Reads `GamePosition` rows (game_id, ply, phase, endgame_class, eval_cp, eval_mate) from DB | Yes — real DB query then `engine_service.evaluate()` | ✓ FLOWING |
| `EvalConfidenceTooltip` / `MetricStatTooltip` caveat | `isPending, pendingCount` | Same `useEvalCoverage()` hook; TanStack Query deduplicates on `['imports', 'eval-coverage']` | Yes — same DB query shared | ✓ FLOWING |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| Stress test script refuses prod API base | `uv run python scripts/measure_dual_import_rss.py --api-base https://flawchess.com ...` | Exit 1, "ERROR: refusing to run stress test against non-localhost API base" | ✓ PASS |
| Stress test script `--help` exits cleanly | `uv run python scripts/measure_dual_import_rss.py --help` | Exit 0, displays all CLI args | ✓ PASS |
| `engine.evaluate` absent from import_service.py | `grep -cE 'engine\.evaluate\|engine_service\.evaluate' app/services/import_service.py` | 0 | ✓ PASS |
| Duplicate helpers removed from import_service.py | `grep -c "^def _board_at_ply\|^class _EvalTarget..." app/services/import_service.py` | 0 | ✓ PASS |
| Lifespan drain_task created with correct name | `grep -c 'name="eval-drain"' app/main.py` | 1 | ✓ PASS |
| Route ordering: `/eval-coverage` before `/{job_id}` | `grep -n "@router.get" app/routers/imports.py` | `/eval-coverage` at line 127, `/{job_id}` at line 148 | ✓ PASS |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|------------|------------|-------------|--------|----------|
| Phase 91 Scope #1 (schema + partial index + backfill) | 91-01 | `games.evals_completed_at` column, `ix_games_evals_pending` partial index, backfill via `COALESCE(imported_at, NOW())` | ✓ SATISFIED | Migration file confirmed; Game ORM model confirmed |
| Phase 91 Scope #2 (hot-lane refactor) | 91-03 | Strip Stages 3a/4/eval-UPDATE from `_flush_batch`; add Stage 5c covered-game gate | ✓ SATISFIED | engine.evaluate count = 0; 7 helpers gone; `_collect_covered_game_ids` present |
| Phase 91 Scope #3 (cold-lane drain + eval-coverage endpoint) | 91-02, 91-04, 91-05 | `run_eval_drain` coroutine + `GET /imports/eval-coverage` + lifespan wiring | ✓ SATISFIED | eval_drain.py + router endpoint + main.py lifespan all confirmed |
| Phase 91 Scope #4 (frontend header bar) | 91-06 | `EvalCoverageHeader` on Endgames + Openings/Stats, polling hook | ✓ SATISFIED | Both mount sites confirmed; hook polling logic confirmed |
| Phase 91 Scope #5 (per-metric pending caveat) | 91-07 | Caveat in EvalConfidenceTooltip + MetricStatTooltip; 7 Cpu-bearing components threaded | ✓ SATISFIED | Both tooltip bodies confirmed; all 7 components confirmed |
| Phase 91 Scope #6 (stress-test harness) | 91-08 | `scripts/measure_dual_import_rss.py` + operator-gated run | ✓ SATISFIED (harness) / HUMAN-UAT (execution) | Script confirmed; execution deferred per operator decision |
| CONTEXT D-01 | 91-04 | Dedicated `/imports/eval-coverage` endpoint, not extending `/imports/active` | ✓ SATISFIED | Separate route confirmed |
| CONTEXT D-02 | 91-06 | Header on Endgames + Openings/Stats only, not global topbar | ✓ SATISFIED | Only two mount sites found |
| CONTEXT D-03 | 91-06 | 10s staleTime + 10s refetchInterval; stops at 100% | ✓ SATISFIED | Confirmed in useEvalCoverage.ts |
| CONTEXT D-04 | 91-06 | Exact copy "Stockfish analysis: N% complete (M games pending)", plural-aware, `Cpu h-3.5 w-3.5` | ✓ SATISFIED | Confirmed in EvalCoverageHeader.tsx |
| CONTEXT D-05 | 91-06, 91-07 | Centralised `useEvalCoverage` hook with shared queryKey | ✓ SATISFIED | All consumers use same hook + queryKey |
| CONTEXT D-06 | 91-07 | One-line addendum in existing popover bodies, no new component family | ✓ SATISFIED | Conditional `<p>` in existing bodies confirmed |
| CONTEXT D-08 / RESEARCH OQ-3 | 91-01 | Backfill uses `COALESCE(imported_at, NOW())` not `updated_at`/`created_at` | ✓ SATISFIED | Migration grep for `updated_at`/`created_at` returns 0 |
| CONTEXT D-11 | 91-02 | LIFO id-DESC pick, batch=10 | ✓ SATISFIED | `.order_by(Game.id.desc()).limit(_DRAIN_BATCH_SIZE)` confirmed |
| CONTEXT D-13 | 91-02 | Drain idle sleep = 5s | ✓ SATISFIED | `_DRAIN_IDLE_SLEEP_SECONDS = 5` confirmed |

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| None found | — | — | — | Scan of key Phase 91 files produced no TBD/FIXME/XXX/HACK/PLACEHOLDER markers. The only "TODO"-like comment in eval_drain.py is a forward-refactor note (lines 384-391) referencing a future improvement to `_collect_eval_targets_for_games` — this is informational and correctly references in-file context, not an unresolved debt marker. |

Note: `_collect_eval_targets_for_games` (lines 334-393) contains a "pure-function stub" comment but this function is NOT called in the hot path. The actual drain uses `_collect_eval_targets_from_db` (line 421) which performs real DB queries. The stub exists only as a test helper for signature testing — this is acceptable.

### Human Verification Required

#### 1. EvalCoverageHeader render with live import

**Test:** Trigger an import on the dev DB (chess.com or lichess) and navigate to the Endgames page and Openings Stats subtab while the import is in progress.
**Expected:** `EvalCoverageHeader` (with `data-testid="eval-coverage-header"`) appears at the top of both pages displaying a percentage and pending game count. The count decreases as the cold drain processes pending games, and the header disappears entirely when `pct_complete` reaches 100.
**Why human:** Component renders only when `isPending` is true and polling the live API. Cannot be verified from source code alone — requires a running backend + frontend with actual pending `evals_completed_at IS NULL` rows.

#### 2. Per-metric popover caveat visibility

**Test:** While pending evals exist (during or after import), open a Stockfish-dependent metric popover — e.g. Score Gap in `EndgameMetricCard`, Conversion in `EndgameTypeCard`, or Entry Eval in `EndgameOverallEntryCard`.
**Expected:** Popover body shows: "Based on currently-evaluated games. N more being analysed — refresh in a few minutes for updated values." After the cold drain completes and the page is refreshed, the caveat is absent.
**Why human:** Conditional rendering inside existing popover bodies requires a live running instance with real pending eval state to observe the caveat appearing and disappearing.

#### 3. Backend RSS behaviour during import (informal smoke)

**Test:** Watch `/proc/<uvicorn_pid>/status VmRSS` or `docker stats` during a large import (any existing account with 1k+ games).
**Expected:** RSS stays roughly flat across the import, with no monotonic climb associated with Stockfish eval work in the hot lane. No Postgres OOM-kill.
**Why human:** Memory plateauing is a runtime observable. The architectural guarantee is backed by `TestHotLaneNoEvalCalls`, but informal confirmation during real use validates the fix end-to-end.

#### 4. Cold drain liveness verification

**Test:** After an import completes, monitor `GET /imports/eval-coverage` (either via the header bar or direct curl) over several minutes.
**Expected:** `pct_complete` advances in steps as the drain processes batches of 10 games every 5s idle interval. Eventually reaches 100. No `source=eval_drain` Sentry errors appear.
**Why human:** Drain liveness (the loop actually running and picking up pending rows) cannot be asserted from static code analysis. Requires a running backend with a drain-ready workload.

### Gaps Summary

No BLOCKER gaps found. All 12 automatable must-haves are VERIFIED. The 13th (stress-test execution) is correctly held in HUMAN-UAT per documented operator decision — the structural OOM fix is protected by `TestHotLaneNoEvalCalls` CI regression guard, and the harness is ready for future formal runs.

The four human verification items are standard runtime-observable behaviours (UI rendering, memory monitoring, drain liveness) that cannot be verified from source code alone.

---

_Verified: 2026-05-21_
_Verifier: Claude (gsd-verifier)_
