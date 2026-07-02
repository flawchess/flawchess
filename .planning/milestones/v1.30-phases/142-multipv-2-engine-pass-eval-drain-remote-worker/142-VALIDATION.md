---
phase: 142
slug: multipv-2-engine-pass-eval-drain-remote-worker
status: draft
nyquist_compliant: true
wave_0_complete: false
created: 2026-06-29
---

# Phase 142 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.x (async via per-run cloned PostgreSQL template) |
| **Config file** | `pyproject.toml` / `tests/conftest.py` |
| **Quick run command** | `uv run pytest tests/services/test_engine.py tests/services/test_eval_drain.py -x` |
| **Full suite command** | `uv run pytest -n auto -x` |
| **Estimated runtime** | ~120–240 seconds (full suite) |

---

## Sampling Rate

- **After every task commit:** Run the quick run command for the touched module
- **After every plan wave:** Run `uv run pytest -n auto -x`
- **Before `/gsd-verify-work`:** Full suite + `uv run ty check app/ tests/` must be green
- **Max feedback latency:** 240 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 142-01-* | 01 | 1 | MPV-01 | — | N/A | unit | `uv run pytest tests/services/test_engine.py -x` | ✅ | ⬜ pending |
| 142-02-* | 02 | 2 | MPV-02 | — | N/A | unit/integration | `uv run pytest tests/services/test_eval_drain.py tests/services/test_full_eval_drain.py -x` | ✅ | ⬜ pending |
| 142-03-* | 03 | 1 | MPV-02 (SC3) | — | un-upgraded worker omits second-best → None, no error | integration | `uv run pytest tests/test_eval_worker_endpoints.py -x` | ✅ | ⬜ pending |
| 142-04-* | 04 | 3 | MPV-03 | — | N/A | script + report | `uv run python scripts/validate_multipv_budget.py --db dev --check-goals` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/services/test_engine.py` — add `_analyse_multipv2()` cases (best+second extraction, single-legal-move guard → `su=""`, `s/sm=None`)
- [ ] `scripts/validate_multipv_budget.py` — new committed histogram/margin tool (modeled on `scripts/tactic_tagger_report.py`), with `--check-goals` exit-code gate
- [ ] Existing `tests/conftest.py` per-run-DB fixtures cover eval_drain / eval_remote integration tests

*Existing infrastructure covers engine, eval_drain, and eval_remote module tests.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Margin histogram ordering reliability (SC4) | MPV-03 | Requires ≥200 real dev flaw positions + visual histogram read; gating decision (raise budget to 1.5–2M if >10% within ±0.05) is a human merge gate | Run `scripts/validate_multipv_budget.py --db dev` against ≥200 dev flaw positions; inspect generated `reports/multipv-validation/*.md`; confirm <10% of positions within ±0.05 margin or raise budget |
| PV1-drift spot-check (RESEARCH FLAG) | MPV-01/MPV-02 | Confirms multipv=2 doesn't systematically shift PV1 eval/best-move vs multipv=1 | Spot-check eval delta of PV1 under multipv=2 vs multipv=1 on the same positions; confirm drift is within accepted non-determinism (not a systematic flaw-boundary shift) |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references (`scripts/validate_multipv_budget.py`)
- [ ] No watch-mode flags
- [ ] Feedback latency < 240s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
