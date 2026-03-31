---
phase: 40
slug: static-type-checking
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-31
---

# Phase 40 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.x (existing) + ty 0.0.26 (type checking) |
| **Config file** | `pyproject.toml` ([tool.ruff], new [tool.ty]) |
| **Quick run command** | `uv run ty check app/` |
| **Full suite command** | `uv run ty check app/ tests/ && uv run pytest` |
| **Estimated runtime** | ~10 seconds (ty) + ~30 seconds (pytest) |

---

## Sampling Rate

- **After every task commit:** Run `uv run ty check app/`
- **After every plan wave:** Run `uv run ty check app/ tests/ && uv run pytest`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 40 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 40-01-01 | 01 | 1 | TOOL-01 | tool | `uv run ty check app/` | ✅ | ⬜ pending |
| 40-02-01 | 02 | 2 | TOOL-02 | tool | `uv run ty check app/` | ✅ | ⬜ pending |
| 40-CI-01 | 01 | 1 | TOOL-01 | ci | `grep 'ty check' .github/workflows/ci.yml` | ✅ | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [x] `ty>=0.0.26` — already added as dev dependency during research
- [x] `pyproject.toml` — existing config file for tool configuration

*Existing infrastructure covers all phase requirements.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| CI blocks on type errors | TOOL-01 | Requires GitHub Actions run | Push a PR with a type error, verify CI fails |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 40s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
