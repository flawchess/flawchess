---
phase: 150
slug: consolidate-write-path
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-07-04
---

# Phase 150 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.x (async, per-run DB isolation) |
| **Config file** | `pyproject.toml` / `tests/conftest.py` |
| **Quick run command** | `uv run pytest tests/services/test_full_eval_drain.py tests/test_eval_worker_endpoints.py` |
| **Full suite command** | `uv run pytest -n auto` |
| **Estimated runtime** | ~90s (full suite, parallel) |

---

## Sampling Rate

- **After every task commit:** Run the quick command for the touched write-path suites
- **After every plan wave:** Run `uv run pytest -n auto`
- **Before `/gsd-verify-work`:** Full suite + `uv run ty check app/ tests/` must be green
- **Max feedback latency:** ~90 seconds

---

## Per-Task Verification Map

The full task map is finalized by the planner; the requirement→validation strategy is:

| Requirement | Validation Type | Automated Command |
|-------------|-----------------|-------------------|
| WRITE-01 (apply_completion_decision) | existing-suite regression + targeted unit | `uv run pytest tests/test_eval_worker_endpoints.py tests/services/test_full_eval_drain.py` |
| WRITE-02 (shared classify preamble) | existing-suite regression (lichess-flaw-PV coverage guard) | `uv run pytest tests/services/test_full_eval_drain.py -k "flaw or preamble or lichess"` |
| WRITE-03 (diff/upsert) | **golden-snapshot equivalence test** across 7 D-02 scenarios + committed reproducible generator | `uv run pytest tests/services/test_flaw_upsert_equivalence.py` |
| WRITE-04 (eval_apply.py split) | existing-suite regression + import-boundary assertion | `uv run pytest -n auto` |
| WRITE-05 (EnginePool generic method) | targeted unit test | `uv run pytest tests/services/test_engine.py` |
| WRITE-06 (ES-lottery parameterization) | targeted unit + existing lottery tests | `uv run pytest -k lottery` |

*Status tracked in PLAN.md `must_haves`; this table is the strategy, not the per-task checklist.*

---

## Wave 0 Requirements

- [ ] `tests/services/test_flaw_upsert_equivalence.py` — NEW golden-snapshot equivalence test for WRITE-03 (7 D-02 scenarios)
- [ ] Committed reproducible generator (script or pytest regen mode) that captures `game_flaws` state from current HEAD (no `bin/reset_db.sh`)

*Existing infrastructure (per-run DB isolation, `tests/test_eval_worker_endpoints.py`, `tests/services/test_full_eval_drain.py`) covers R1/R4/R7 regression.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| — | — | — | All phase behaviors have automated verification (structure-only refactor, no behavior change). |

*Frontend gate is a no-op (backend-only phase) but still runs per the pre-merge gate.*

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references (golden-snapshot equivalence test)
- [ ] No watch-mode flags
- [ ] Feedback latency < 90s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
