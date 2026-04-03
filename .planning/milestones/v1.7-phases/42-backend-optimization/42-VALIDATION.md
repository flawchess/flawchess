---
phase: 42
slug: backend-optimization
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-04-03
---

# Phase 42 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest (backend), vitest (frontend — not used this phase) |
| **Config file** | `pyproject.toml` (pytest config) |
| **Quick run command** | `uv run pytest tests/ -x --tb=short` |
| **Full suite command** | `uv run pytest` |
| **Estimated runtime** | ~30 seconds |

---

## Sampling Rate

- **After every task commit:** Run `uv run pytest tests/ -x --tb=short`
- **After every plan wave:** Run `uv run pytest`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 30 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 42-01-01 | 01 | 1 | BOPT-01 | unit/integration | `uv run pytest tests/ -x -k "wdl or openings"` | ✅ | ⬜ pending |
| 42-01-02 | 01 | 1 | BOPT-01 | unit/integration | `uv run pytest tests/ -x -k "endgame"` | ✅ | ⬜ pending |
| 42-02-01 | 02 | 1 | BOPT-02 | schema check | `uv run ty check app/models/` | ✅ | ⬜ pending |
| 42-03-01 | 03 | 1 | BOPT-03 | unit | `uv run pytest tests/ -x -k "auth or users or imports"` | ✅ | ⬜ pending |
| 42-03-02 | 03 | 1 | BOPT-03 | type check | `uv run ty check app/routers/ app/schemas/` | ✅ | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

Existing infrastructure covers all phase requirements. pytest, ty, and ruff are already configured and run in CI.

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| SQL aggregation produces identical results to Python loops | BOPT-01 | Need to compare actual query results against known data | Run openings/endgame API endpoints and verify W/D/L counts match pre-refactor values |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 30s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
