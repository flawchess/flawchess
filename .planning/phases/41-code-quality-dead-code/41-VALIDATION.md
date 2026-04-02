---
phase: 41
slug: code-quality-dead-code
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-04-02
---

# Phase 41 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework (backend)** | pytest with asyncio_mode=auto |
| **Framework (frontend)** | Vitest 4.1.1 |
| **Config file (backend)** | pyproject.toml |
| **Config file (frontend)** | Embedded in `vite.config.ts` |
| **Quick run command** | `uv run pytest && cd frontend && npm run build && npm test` |
| **Full suite command** | `uv run pytest && cd frontend && npm run knip && npm run build && npm test` |
| **Estimated runtime** | ~30 seconds |

---

## Sampling Rate

- **After every task commit:** Run `uv run ruff check app/ && cd frontend && npm run build && npm test`
- **After every plan wave:** Run `uv run pytest && cd frontend && npm run knip && npm run build && npm test`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 30 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 41-01-01 | 01 | 1 | TOOL-03 | smoke | `cd frontend && npm run knip` | :x: W0 | :white_large_square: pending |
| 41-01-02 | 01 | 1 | D-09 | CI | CI workflow after PR | :white_check_mark: | :white_large_square: pending |
| 41-02-01 | 02 | 1 | QUAL-01 | integration | `uv run pytest tests/test_*_router.py` | :white_check_mark: | :white_large_square: pending |
| 41-03-01 | 03 | 2 | QUAL-02 | integration | `uv run pytest` | :white_check_mark: | :white_large_square: pending |
| 41-03-02 | 03 | 2 | QUAL-02 | build | `cd frontend && npm run build` | :white_check_mark: | :white_large_square: pending |
| 41-04-01 | 04 | 2 | QUAL-03 | lint | `uv run ruff check app/` | :white_check_mark: | :white_large_square: pending |
| 41-04-02 | 04 | 2 | QUAL-03 | lint | `cd frontend && npm run knip` | :x: W0 | :white_large_square: pending |
| 41-05-01 | 05 | 1 | D-08 | type check | `cd frontend && npm run build` | :white_check_mark: | :white_large_square: pending |

*Status: :white_large_square: pending · :white_check_mark: green · :x: red · :warning: flaky*

---

## Wave 0 Requirements

- [ ] `npm install -D knip` — Knip package must be installed
- [ ] `frontend/knip.json` — Knip config with entry points (`src/main.tsx`, `src/prerender.tsx`)
- [ ] `frontend/package.json` — Add `"knip": "knip"` script

*Existing backend infrastructure (pytest, ruff) covers all backend requirements.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| CI pipeline runs frontend steps | D-09 | Requires GitHub Actions execution | Push branch, verify CI runs `npm run build`, `npm test`, `npm run knip` |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 30s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
