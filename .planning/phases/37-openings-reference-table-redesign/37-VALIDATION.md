---
phase: 37
slug: openings-reference-table-redesign
status: draft
nyquist_compliant: true
wave_0_complete: true
created: 2026-03-28
---

# Phase 37 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest (backend) + vitest (frontend) |
| **Config file** | pyproject.toml / frontend/vitest.config.ts |
| **Quick run command** | `uv run pytest tests/test_stats_repository.py tests/test_stats_router.py -x` |
| **Full suite command** | `uv run pytest && cd frontend && npm run build` |
| **Estimated runtime** | ~30 seconds |

---

## Sampling Rate

- **After every task commit:** Run `uv run pytest tests/test_stats_repository.py tests/test_stats_router.py -x`
- **After every plan wave:** Run `uv run pytest && cd frontend && npm run build`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 30 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 37-01-01 | 01 | 1 | ORT-01, ORT-02 | unit + migration | `uv run pytest tests/test_seed_openings.py -x` | ✅ (created by Plan 37-01 Task 2) | ⬜ pending |
| 37-02-01 | 02 | 2 | ORT-03 | unit + integration | `uv run pytest tests/test_stats_repository.py tests/test_stats_router.py -x` | ✅ | ⬜ pending |
| 37-03-01 | 03 | 2 | ORT-04, ORT-05 | build | `cd frontend && npm run build` | ✅ | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

*Existing infrastructure covers all phase requirements. Plan 37-01 Task 2 creates `tests/test_seed_openings.py` for ORT-01/ORT-02. Existing `tests/test_stats_repository.py` and `tests/test_stats_router.py` cover ORT-03.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Opening table renders correctly with ECO/name/PGN columns | ORT-04 | Visual layout verification | Navigate to Opening Statistics subtab, verify table structure |
| Minimap popover shows correct position on hover/tap | ORT-05 | Visual + interaction verification | Hover over a row, verify chessboard shows opening position |
| Mobile responsive table layout | ORT-04 | Device-specific layout | Test on 375px viewport width |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 30s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
