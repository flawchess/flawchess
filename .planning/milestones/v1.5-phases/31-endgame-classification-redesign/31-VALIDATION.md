---
phase: 31
slug: endgame-classification-redesign
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-26
---

# Phase 31 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x (backend) |
| **Config file** | pyproject.toml |
| **Quick run command** | `uv run pytest tests/test_endgame_repository.py tests/test_endgame_service.py -x` |
| **Full suite command** | `uv run pytest` |
| **Estimated runtime** | ~30 seconds |

---

## Sampling Rate

- **After every task commit:** Run `uv run pytest tests/test_endgame_repository.py tests/test_endgame_service.py -x`
- **After every plan wave:** Run `uv run pytest`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 30 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 31-01-01 | 01 | 1 | Schema | unit | `uv run pytest tests/test_endgame_repository.py -x` | ✅ | ⬜ pending |
| 31-01-02 | 01 | 1 | Backfill | integration | `uv run pytest tests/test_endgame_repository.py -x` | ✅ | ⬜ pending |
| 31-02-01 | 02 | 2 | Query redesign | unit | `uv run pytest tests/test_endgame_repository.py tests/test_endgame_service.py -x` | ✅ | ⬜ pending |
| 31-02-02 | 02 | 2 | Import wiring | integration | `uv run pytest tests/test_endgame_repository.py -x` | ✅ | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] Update `_seed_game_position()` fixture in `tests/test_endgame_repository.py` to include `endgame_class` values

*Existing test infrastructure covers all phase requirements.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Endgame stats show correct multi-class counts | D-02, D-03 | Requires visual verification of UI | Check Endgames tab with a user who has games spanning multiple endgame types |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 30s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
