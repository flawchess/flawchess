---
phase: "220"
slug: "opening-eval-cache-repair-two-source-confirmation"
# status lifecycle: draft (seeded by plan-phase) → validated (set by validate-phase §6)
# audit-milestone §5.5 distinguishes NOT-VALIDATED (draft) from PARTIAL (validated + nyquist_compliant: false) (#2117)
status: draft
nyquist_compliant: false
wave_0_complete: false
created: "2026-09-09"
---

# Phase 220 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.
> Detail source: `220-RESEARCH.md` §"Validation Architecture" (per-requirement test map,
> 14-step dev-smoke procedure, 14 prod acceptance queries). The planner fills the
> Per-Task Verification Map from that section.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest (asyncio, PostgreSQL template clone per session via `tests/conftest.py`) |
| **Config file** | `pyproject.toml` (`[tool.pytest.ini_options]`) |
| **Quick run command** | `uv run pytest tests/<target_file>.py -x -q` |
| **Full suite command** | `uv run pytest -n auto -x` |
| **Estimated runtime** | ~5-20 s per target file; full suite several minutes |

---

## Sampling Rate

- **After every task commit:** Run the task's `<automated>` command (target test file)
- **After every plan wave:** Run `uv run pytest -n auto -x` plus `uv run ruff check .` and `uv run ty check app/ tests/ scripts/`
- **Before `/gsd-verify-work`:** Full pre-merge gate green (CLAUDE.md §"Pre-merge gate")
- **Max feedback latency:** 60 seconds for a single target file

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| (filled by planner from RESEARCH.md §Validation Architecture) | | | CACHEFIX-01..12 | — | N/A | unit / integration / operator | see PLAN.md `<verify>` | | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/scripts/test_opening_cache_repair.py` — stubs for CACHEFIX-02..07, CACHEFIX-10 (status transitions, old-value predicate, hash-mismatch skipping, out-of-order refusal, resume-after-kill)
- [ ] `tests/services/test_full_eval_drain.py` — extended for CACHEFIX-08 (candidate -> promote, candidate -> replace + Sentry, confirmed never overwritten) and the `OPENING_CACHE_BACKFILL_SQL` fix
- [ ] `tests/test_eval_worker_endpoints.py` — extended for CACHEFIX-12 (submit writes cache; second game's lease omits cached hashes) and the D-04 no-resurrect test
- [ ] Alembic migration tests use the existing template-refresh mechanism (no new fixture needed)

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Prod repair run (all stages) and report | CACHEFIX-07, CACHEFIX-11 | Operator stage against prod through `bin/prod_db_tunnel.sh` on the local 4-worker box; ~2 days wall clock | Run stages in order with `--db prod`; paste the 14 acceptance queries' results into the SUMMARY |
| Legacy-cohort sample decision | CACHEFIX-10 | ~25 min engine time against prod; decision rule D-07 | Run `legacy-sample --db prod`; record rates and the build/no-build decision |
| Benchmark-lane lease shrinks after submit-path cache writes | CACHEFIX-12 | Requires a live benchmark-DB worker lane | Observe `opening_position_eval` row count growing and leased target counts falling |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 60s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
