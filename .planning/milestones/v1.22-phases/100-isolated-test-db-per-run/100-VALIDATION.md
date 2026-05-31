---
phase: 100
slug: isolated-test-db-per-run
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-05-31
---

# Phase 100 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 9.x + pytest-asyncio 1.4.0 |
| **Config file** | `pyproject.toml` `[tool.pytest.ini_options]` |
| **Quick run command** | `uv run pytest tests/test_zobrist.py -x -q` (fast, no DB) |
| **Full suite command** | `uv run pytest -x --tb=short` |
| **Estimated runtime** | ~41 seconds serial (baseline measured); target faster under `-n auto` |

---

## Sampling Rate

- **After every task commit:** Run `uv run pytest tests/test_zobrist.py -x -q` (fast, DB-free smoke)
- **After every plan wave:** Run `uv run pytest -x --tb=short` (full serial suite must be green)
- **Before `/gsd-verify-work`:** Full suite green serially, then `time uv run pytest -n auto` records SC-3 wall clock
- **Max feedback latency:** ~45 seconds (full serial suite)

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 100-01-T1 | 01 | 1 | SC-3 (xdist dep) | — | N/A | install | `uv run python -c "import xdist"` | ❌ W0 | ⬜ pending |
| 100-01-T2 | 01 | 1 | SC-2 / SC-5 / D-01 | T-100-01 | DB names from trusted sources only | unit/source | `uv run ruff check tests/conftest.py && uv run ty check tests/ && grep -q pg_advisory_lock tests/conftest.py && grep -q "CREATE DATABASE" tests/conftest.py` | ✅ | ⬜ pending |
| 100-01-T3 | 01 | 1 | SC-2 / SC-4 | — | N/A | unit/source | `! grep -q "TRUNCATE" tests/conftest.py && ! grep -q "_truncate_all_tables" tests/conftest.py && uv run ruff check app/ tests/ && uv run ty check app/ tests/ && uv run pytest -x --tb=short` | ✅ | ⬜ pending |
| 100-02-T1 | 02 | 2 | SC-5 | — | N/A | docs/source | `grep -q "flawchess_test_template" CLAUDE.md && uv run ruff check tests/conftest.py && uv run pytest tests/test_zobrist.py -x -q` | ✅ | ⬜ pending |
| 100-02-T2 | 02 | 2 | SC-1 / SC-3 | T-100-02 | N/A | manual + measurement | `time uv run pytest -n auto` (green, vs ~41s baseline) + two concurrent `uv run pytest` runs (HUMAN-UAT) | ✅ | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `uv add --group dev pytest-xdist` — enables `-n auto` (SC-3). Serial runs work without it.

*No new test files needed: Phase 100 modifies `tests/conftest.py` only; its correctness is validated by the existing full suite passing under the new per-run-DB infrastructure.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Two concurrent full `pytest` runs with zero deadlock / cross-run corruption | SC-1 | Requires two simultaneous OS processes; not expressible as a single pytest assertion | Open two terminals, run `uv run pytest` in each at the same time; both must finish green with no deadlock and no shared-state errors |
| `-n auto` wall-clock faster than ~41s serial baseline | SC-3 | Wall-clock measurement, machine-dependent | `time uv run pytest -n auto`; record the number; must be green and < serial baseline |

*All other phase behaviors have automated verification.*

---

## Validation Sign-Off

- [ ] All tasks have automated verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references (pytest-xdist install)
- [ ] No watch-mode flags
- [ ] Feedback latency < 45s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
