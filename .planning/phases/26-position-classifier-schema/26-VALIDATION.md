---
phase: 26
slug: position-classifier-schema
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-23
---

# Phase 26 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.x |
| **Config file** | pyproject.toml `[tool.pytest.ini_options]` |
| **Quick run command** | `uv run pytest tests/test_position_classifier.py -x` |
| **Full suite command** | `uv run pytest` |
| **Estimated runtime** | ~5 seconds |

---

## Sampling Rate

- **After every task commit:** Run `uv run pytest tests/test_position_classifier.py -x`
- **After every plan wave:** Run `uv run pytest`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 10 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 26-01-01 | 01 | 1 | PMETA-01 | unit | `uv run pytest tests/test_position_classifier.py -x` | ❌ W0 | ⬜ pending |
| 26-01-02 | 01 | 1 | PMETA-02 | unit | `uv run pytest tests/test_position_classifier.py -x` | ❌ W0 | ⬜ pending |
| 26-01-03 | 01 | 1 | PMETA-03 | unit | `uv run pytest tests/test_position_classifier.py -x` | ❌ W0 | ⬜ pending |
| 26-01-04 | 01 | 1 | PMETA-04 | unit | `uv run pytest tests/test_position_classifier.py -x` | ❌ W0 | ⬜ pending |
| 26-02-01 | 02 | 1 | PMETA-01 | integration | `uv run alembic upgrade head` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_position_classifier.py` — stubs for PMETA-01 through PMETA-04
- [ ] `app/services/position_classifier.py` — module under test

*Existing `tests/conftest.py` with board fixtures is reusable.*

---

## Manual-Only Verifications

*All phase behaviors have automated verification.*

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 10s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
