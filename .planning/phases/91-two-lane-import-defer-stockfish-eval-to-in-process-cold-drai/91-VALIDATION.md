---
phase: 91
slug: two-lane-import-defer-stockfish-eval-to-in-process-cold-drain
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-05-21
---

# Phase 91 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.x (backend), vitest (frontend) |
| **Config file** | `pyproject.toml` (pytest), `frontend/vitest.config.ts` |
| **Quick run command** | `uv run pytest tests/services/test_eval_drain.py tests/services/test_import_service.py -x` |
| **Full suite command** | `uv run pytest && cd frontend && npm test -- --run` |
| **Estimated runtime** | ~120 seconds (backend ~90s, frontend ~30s) |

---

## Sampling Rate

- **After every task commit:** Run quick run command (eval_drain + import_service tests)
- **After every plan wave:** Run full suite command
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 120 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| TBD | TBD | TBD | Phase 91 scope #1 (schema) | — | Migration up/down idempotent | integration | `uv run pytest tests/test_migration_91_evals_completed_at.py` | ❌ W0 | ⬜ pending |
| TBD | TBD | TBD | Phase 91 scope #1 (partial index) | — | Drain SELECT uses partial index | unit | `uv run pytest tests/test_eval_drain_explain.py::test_partial_index_used` | ❌ W0 | ⬜ pending |
| TBD | TBD | TBD | Phase 91 scope #2 (hot-lane refactor) | — | _flush_batch holds no Stockfish work | unit | `uv run pytest tests/services/test_import_service.py::test_flush_batch_no_engine_calls` | ❌ W0 | ⬜ pending |
| TBD | TBD | TBD | Phase 91 scope #3 (cold-drain) | — | gather happens outside session | unit | `uv run pytest tests/services/test_eval_drain.py::test_gather_outside_session` | ❌ W0 | ⬜ pending |
| TBD | TBD | TBD | Phase 91 scope #3 (cold-drain idempotency) | — | Crash mid-batch leaves rows pickable next pass | integration | `uv run pytest tests/services/test_eval_drain.py::test_idempotent_on_simulated_crash` | ❌ W0 | ⬜ pending |
| TBD | TBD | TBD | Phase 91 scope #3 (LIFO order) | — | LIFO id-DESC picks newest first | unit | `uv run pytest tests/services/test_eval_drain.py::test_lifo_order` | ❌ W0 | ⬜ pending |
| TBD | TBD | TBD | Phase 91 scope #3 (hot-lane RSS) | — | Dual-import RSS plateau ≤ 1.6 GB | manual-instrumented | `python scripts/measure_dual_import_rss.py` | ❌ W0 | ⬜ pending (manual aided) |
| TBD | TBD | TBD | Phase 91 scope #3 (eval-coverage endpoint) | — | Returns {pending_count, total_count, pct_complete} | integration | `uv run pytest tests/routers/test_imports_eval_coverage.py` | ❌ W0 | ⬜ pending |
| TBD | TBD | TBD | Phase 91 scope #4 (header bar render) | — | Hidden when pending == 0 | unit (RTL) | `cd frontend && npm test -- src/components/EvalCoverageHeader.test.tsx` | ❌ W0 | ⬜ pending |
| TBD | TBD | TBD | Phase 91 scope #4 (polling cadence) | — | refetchInterval stops at 100% | unit (RTL) | `cd frontend && npm test -- src/hooks/useEvalCoverage.test.tsx` | ❌ W0 | ⬜ pending |
| TBD | TBD | TBD | Phase 91 scope #5 (per-metric caveat) | — | Conditional <p> appears/disappears | unit (RTL) | `cd frontend && npm test -- src/components/insights/EvalConfidenceTooltip.test.tsx` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

*Task IDs are TBD — planner will assign concrete plan/task numbers and link them to this map.*

---

## Wave 0 Requirements

- [ ] `tests/services/test_eval_drain.py` — new file; tests for gather-outside-session, LIFO order, idempotency on crash, partial index usage
- [ ] `tests/services/test_import_service.py` — extend with `test_flush_batch_no_engine_calls` (regression test for hot-lane refactor)
- [ ] `tests/test_migration_91_evals_completed_at.py` — alembic up/down + backfill correctness against COALESCE(imported_at, NOW())
- [ ] `tests/routers/test_imports_eval_coverage.py` — auth + response shape + plural-aware count
- [ ] `scripts/measure_dual_import_rss.py` — instrumented dual-20k stress harness writing RSS + pg memory traces to logs/
- [ ] `frontend/src/hooks/useEvalCoverage.test.tsx` — new file; RTL test for staleTime/refetchInterval/stops at 100
- [ ] `frontend/src/components/EvalCoverageHeader.test.tsx` — new file; hidden-when-zero render test
- [ ] `frontend/src/components/insights/EvalConfidenceTooltip.test.tsx` — extend with conditional caveat <p>

*Wave 0 installs no new frameworks — pytest and vitest already configured.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Dev 2×20k stress test passes acceptance bounds | Phase 91 verification (ROADMAP) | Requires real DB + real engine pool + 30+ min runtime; not suitable for CI | 1. Reset dev DB (`bin/reset_db.sh` after explicit permission). 2. Run two concurrent 20k-game imports (chess.com + lichess on freshly-cloned test account). 3. Poll `docker stats` and `pg_stat_activity` every 30s. 4. Assert: backend RSS ≤ 1.6 GB, postgres anon+shmem ≤ 1.2 GB, swap ≤ 50% of allocated swap, both imports `status=completed`, eval coverage reaches 100% within N minutes after second import finishes. |
| Production deploy verification | Phase 91 verification (ROADMAP) | Cannot run in CI | After deploy, re-run a real ≥10k-game account import against prod. Watch eval coverage header reach 100%; verify Sentry quiet; verify `pg_stat_activity` shows no held transactions > 1s. |
| Backfill timing on prod-sized data | Risk register | One-shot at deploy; cannot be re-run | `EXPLAIN ANALYZE UPDATE games SET evals_completed_at = COALESCE(imported_at, NOW()) WHERE evals_completed_at IS NULL` against prod-restored dev snapshot; expect < 5s. |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 120s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
