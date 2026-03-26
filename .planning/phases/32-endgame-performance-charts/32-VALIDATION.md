---
phase: 32
slug: endgame-performance-charts
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-26
---

# Phase 32 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x (backend), vitest (frontend) |
| **Config file** | `pyproject.toml`, `frontend/vitest.config.ts` |
| **Quick run command** | `uv run pytest tests/test_endgame_service.py -x -q` |
| **Full suite command** | `uv run pytest -x && cd frontend && npm test` |
| **Estimated runtime** | ~15 seconds |

---

## Sampling Rate

- **After every task commit:** Run `uv run pytest tests/test_endgame_service.py -x -q`
- **After every plan wave:** Run `uv run pytest -x && cd frontend && npm test`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 15 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 32-01-* | 01 | 1 | Performance endpoint | unit | `uv run pytest tests/test_endgame_service.py -x` | ❌ W0 | ⬜ pending |
| 32-02-* | 02 | 1 | Timeline endpoint | unit | `uv run pytest tests/test_endgame_service.py -x` | ❌ W0 | ⬜ pending |
| 32-03-* | 03 | 2 | Frontend charts | build | `cd frontend && npm run build` | ✅ | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_endgame_performance.py` — tests for performance endpoint (WDL comparison, gauge metrics)
- [ ] `tests/test_endgame_timeline.py` — tests for timeline endpoint (rolling window, per-type series)

*Existing test infrastructure (pytest, fixtures, async session) covers framework needs.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Semicircle gauge renders correctly | SC-2 | Visual SVG rendering | Open /endgames/statistics, verify two semicircle gauges appear with correct values |
| Timeline chart date axis | SC-3, SC-4 | Visual date formatting | Verify X-axis shows calendar dates, lines plot correctly |
| Mobile layout adaptation | SC-5 | Responsive layout | Resize browser to 375px, verify charts stack and remain usable |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 15s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
