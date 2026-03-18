---
phase: 15
slug: enhanced-game-import-data
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-18
---

# Phase 15 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x (backend) / vitest (frontend) |
| **Config file** | `pyproject.toml` (backend) / `frontend/vitest.config.ts` (frontend) |
| **Quick run command** | `uv run pytest tests/ -x --tb=short` |
| **Full suite command** | `uv run pytest tests/ && cd frontend && npm run build` |
| **Estimated runtime** | ~30 seconds |

---

## Sampling Rate

- **After every task commit:** Run `uv run pytest tests/ -x --tb=short`
- **After every plan wave:** Run `uv run pytest tests/ && cd frontend && npm run build`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 30 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 15-01-01 | 01 | 1 | Clock data extraction | unit | `uv run pytest tests/test_zobrist.py -x` | ⬜ W0 | ⬜ pending |
| 15-01-02 | 01 | 1 | Termination normalization | unit | `uv run pytest tests/test_normalization.py -x` | ⬜ W0 | ⬜ pending |
| 15-01-03 | 01 | 1 | Time control bucketing fix | unit | `uv run pytest tests/test_normalization.py -x` | ✅ | ⬜ pending |
| 15-01-04 | 01 | 1 | Multi-username sync fix | unit | `uv run pytest tests/test_import_service.py -x` | ⬜ W0 | ⬜ pending |
| 15-02-01 | 02 | 2 | Data isolation bug | integration | `uv run pytest tests/ -x` | ⬜ W0 | ⬜ pending |
| 15-02-02 | 02 | 2 | last_login SSO fix | unit | `uv run pytest tests/test_auth.py -x` | ⬜ W0 | ⬜ pending |
| 15-02-03 | 02 | 2 | Game card display | build | `cd frontend && npm run build` | ✅ | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_zobrist.py` — tests for clock extraction from PGN annotations
- [ ] `tests/test_normalization.py` — tests for termination normalization mappings
- [ ] `tests/test_import_service.py` — tests for multi-username sync boundary

*Existing test infrastructure covers framework and fixtures.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Data isolation across users | Cross-user visibility bug | Requires two authenticated sessions | Login as user A, import games. Login as user B, verify no games from A visible |
| Google SSO last_login | last_login update on OAuth | Requires Google OAuth flow | Login via Google SSO, verify last_login column updated |
| Game card visual layout | TC + termination display | Visual correctness | Import games, verify game cards show "Blitz · 10+5" and termination reason |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 30s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
