---
phase: 90
slug: import-pipeline-memory-leak-fix-resilience
status: draft
nyquist_compliant: true
wave_0_complete: false
created: 2026-05-20
---

# Phase 90 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.x (asyncio) |
| **Config file** | `pyproject.toml` (`[tool.pytest.ini_options]`) |
| **Quick run command** | `uv run pytest tests/test_import_service.py -x -q` |
| **Full suite command** | `uv run pytest -x` |
| **Estimated runtime** | ~30s quick · ~3 min full |

---

## Sampling Rate

- **After every task commit:** Run quick `pytest tests/test_import_service.py -x -q`
- **After every plan wave:** Run full `uv run pytest -x`
- **Before `/gsd:verify-work`:** Full suite green + manual RSS-flat verification (see Manual-Only)
- **Max feedback latency:** 60s

---

## Per-Task Verification Map

> Populated by the planner from PLAN.md `<task>` blocks. Filled rows are seeded from the research's planning-ready partition (90-01 Stage 5 rewrite, 90-02 session-recycle, 90-03 reaper + retry). Planner replaces these with the actual task IDs.

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 90-01-* | 01 | 1 | (defect-fix) | T-90-01 | Stage 5 UPDATE never silently NULLs `result_fen`; bound-param SQL identical across batches | unit | `uv run pytest tests/test_import_service.py::TestFlushBatchStage5 -x` | ❌ W0 | ⬜ pending |
| 90-02-* | 02 | 2 | (defect-fix) | — | Per-batch session recycled; `previous_job.last_synced_at` scalar survives bootstrap close | unit | `uv run pytest tests/test_import_service.py::TestRunImportSessionPerBatch -x` | ❌ W0 | ⬜ pending |
| 90-03-* | 03 | 2 | (defect-fix) | T-90-02, T-90-03 | Periodic reaper respects orphan-age threshold; failure-state UPDATE retries on `OperationalError` | unit | `uv run pytest tests/test_import_service.py::TestFailOrphanedJobsAgeThreshold tests/test_import_service.py::TestPeriodicReaper tests/test_import_service.py::TestRecordFailureWithRetry -x` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_import_service.py` — extend with `_flush_batch` Stage 5 fixtures (mixed None / non-None `result_fen`, idempotency across two batches)
- [ ] `tests/test_import_service.py` — fixtures asserting one session per batch (count `async_sessionmaker` calls)
- [ ] `tests/test_import_service.py` — fixture simulating `OperationalError` on first N attempts then success, to exercise the failure-state retry
- [ ] `tests/test_import_service.py` — async task fixture for the periodic reaper, asserts orphan-age threshold is honored
- [ ] No framework install needed (pytest already configured)

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Backend RSS stays flat across a real ~5k+ game import (vs linear climb today) | Phase goal — leak elimination | Real OOM repro requires live chess.com/lichess API fetch + Stockfish eval pool — too heavy for CI | 1. `bin/run_local.sh` 2. Import a real ~5k+ game user 3. `docker stats flawchess-backend` (or `ps -o rss= -p $(pgrep -f uvicorn)` in a 5s loop) 4. RSS must stay within ±15% of baseline across the import (not climb linearly with batch count) |
| Sentry FLAWCHESS-56 (120262007) and FLAWCHESS-3Q (115610288) do not recur in prod after deploy | Phase goal — OOM elimination | Production-only signal | After `bin/deploy.sh`, monitor Sentry for 48h with a representative-account import; resolve both issues if clean |
| Reaper fires after Postgres-only restart without backend restart | Reaper scope (item 3) | Requires SIGKILL of Postgres container while backend stays up | 1. Start an import, let it begin processing batches 2. `docker compose -f docker-compose.dev.yml -p flawchess-dev kill postgres && docker compose -f docker-compose.dev.yml -p flawchess-dev up -d postgres` 3. Wait for the next reaper tick 4. Confirm the stranded job transitions to `failed` (or similar terminal state) within the reaper cadence |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 60s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
