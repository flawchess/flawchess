---
phase: 28
slug: engine-analysis-import
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-25
---

# Phase 28 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x |
| **Config file** | pyproject.toml |
| **Quick run command** | `uv run pytest tests/ -x --timeout=30` |
| **Full suite command** | `uv run pytest` |
| **Estimated runtime** | ~15 seconds |

---

## Sampling Rate

- **After every task commit:** Run `uv run pytest tests/ -x --timeout=30`
- **After every plan wave:** Run `uv run pytest`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 15 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 28-01-01 | 01 | 1 | ENGINE-02, ENGINE-03 | unit | `uv run pytest tests/test_normalization.py -x` | pending | pending |
| 28-02-01 | 02 | 2 | ENGINE-01, ENGINE-03 | unit | `uv run pytest tests/test_import_service.py -x` | pending | pending |
| 28-03-01 | 03 | 2 | ENGINE-01, ENGINE-02, ENGINE-03 | unit+integration | `uv run pytest tests/test_reimport.py -x` | pending | pending |

*Status: pending / green / red / flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_normalization.py` — existing file, add stubs for chess.com accuracy extraction (ENGINE-02, ENGINE-03)
- [ ] `tests/test_import_service.py` — stubs for eval extraction from PGN (ENGINE-01, ENGINE-03)
- [ ] `tests/test_reimport.py` — stubs for CLI argument parsing + eval population integration test (ENGINE-01, ENGINE-02, ENGINE-03)
- [ ] Test fixtures for lichess PGN with %eval annotations and chess.com game JSON with accuracies

*Existing test infrastructure (conftest.py, test DB) covers framework needs.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Re-import script deletes and re-imports correctly against live APIs | D-11, D-12 | Requires live platform API access (chess.com rate limits, lichess auth) | Run `uv run python scripts/reimport_games.py --user-id 1` against dev DB with seeded data |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 15s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
