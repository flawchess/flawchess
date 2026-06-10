---
phase: 114
slug: benchmark-flaw-delta-zone-computation
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-06-10
---

# Phase 114 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.
> Source: RESEARCH.md §"Validation Architecture".

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest (asyncio) |
| **Config file** | `pyproject.toml` (addopts `--ignore=tests/scripts/benchmarks` — benchmark gates excluded from default run) |
| **Quick run command** | `uv run pytest tests/scripts/benchmarks/test_chapter5_diff.py -q` |
| **Full suite command** | `uv run pytest -n auto -x` (standard suite; benchmark gate run separately with explicit path) |
| **Estimated runtime** | ~standard-suite + benchmark gate on demand |

---

## Sampling Rate

- **After every task commit:** Run `uv run ruff check app/ tests/ && uv run ty check app/ tests/`
- **After every plan wave:** Run `uv run pytest -n auto -x` (standard suite; benchmark gates run separately on demand)
- **Before `/gsd-verify-work`:** Standard suite green + benchmark chapter-diff gate green + generator smoke run
- **Max feedback latency:** ~standard-suite runtime

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 114-01-xx | 01 | 1 | FLAWBMK-01 | — | N/A (read-only benchmark gen) | unit (DB) | `uv run pytest tests/scripts/benchmarks/test_chapter5_diff.py` | ❌ W0 | ⬜ pending |
| 114-01-xx | 01 | 1 | FLAWBMK-02 | — | N/A | unit (DB) | `uv run pytest tests/scripts/benchmarks/test_chapter5_diff.py` | ❌ W0 | ⬜ pending |
| 114-01-xx | 01 | 1 | FLAWBMK-03 | — | N/A | unit (DB) | `uv run pytest tests/scripts/benchmarks/test_chapter5_diff.py` | ❌ W0 | ⬜ pending |
| 114-01-xx | 01 | 1 | FLAWBMK-04 | — | N/A | integration | generator smoke run + SKILL.md narration | N/A | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

*Exact task IDs assigned by the planner; this map is the requirement→test contract the plan must honor.*

---

## Wave 0 Requirements

- [ ] `scripts/benchmarks/chapter5.py` — new chapter module (the primary deliverable; `build()`/`compute()`/`render()` per the chapter3.py analog)
- [ ] `tests/scripts/benchmarks/test_chapter5_diff.py` — numeric-diff gate for all 15 metrics, following the `test_chapter3_diff.py` pattern

*Existing test infrastructure (pytest + benchmark DB fixtures) covers the standard suite; only the benchmark-specific chapter module and its diff gate are new.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Report artifact reads correctly (quartiles + marginals + verdicts + viability diagnostics narrated) | FLAWBMK-04 | Code/LLM seam — SKILL.md narrates the generated numbers into prose; final report quality is editorial | Run the generator against the benchmark DB, then have `/benchmarks` narrate the new chapter; review `reports/benchmark/benchmarks-latest.md` §flaw-delta for completeness of all 15 metrics, marginals, verdicts, and viability columns |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency acceptable for benchmark-gen phase
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
