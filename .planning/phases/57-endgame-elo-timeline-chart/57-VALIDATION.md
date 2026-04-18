---
phase: 57
slug: endgame-elo-timeline-chart
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-04-18
---

# Phase 57 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.x (backend) + vitest (frontend) |
| **Config file** | pyproject.toml (pytest) / vitest.config.ts |
| **Quick run command** | `uv run pytest tests/test_endgame_service.py -x` |
| **Full suite command** | `uv run pytest && cd frontend && npm test && npm run lint && cd .. && uv run ruff check . && uv run ty check app/ tests/` |
| **Estimated runtime** | ~90 seconds |

---

## Sampling Rate

- **After every task commit:** Run `{quick run command}` scoped to the module touched (pytest path filter or `npm test -- path/to/file`)
- **After every plan wave:** Run the full suite command
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 120 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 57-01-XX | 01 | 1 | ELO-05 | — | User scoping: timeline query must filter by current_user.id | unit | `uv run pytest tests/test_endgame_service.py -k timeline -x` | ❌ W0 | ⬜ pending |
| 57-02-XX | 02 | 2 | ELO-05 | — | No PII leakage; aggregate metrics only | unit+component | `cd frontend && npm test -- EndgameEloTimeline` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_endgame_service.py` — stubs for ELO-05 (timeline computation, cold-start handling, rolling window, clamp boundaries)
- [ ] `frontend/src/components/charts/__tests__/EndgameEloTimelineSection.test.tsx` — stubs for chart render, legend toggle, empty-state
- [ ] Existing pytest + vitest infra already installed — no framework install needed

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Visual hue/contrast of paired bright/dark lines | ELO-05 SC-1 | Color perception / accessibility is subjective; theme-level concern | Load /endgames on real account, toggle combos in legend, verify bright/dark distinction is visible on both light/dark themes |
| Mobile legend wrap / collapse behavior | ELO-05 SC-1 | Responsive layout visual check | Open /endgames on iPhone viewport (Chrome devtools), confirm legend does not overflow and chart remains readable |
| Cold-start empty state copy readability | ELO-05 SC-3 | Prose/UX review | Create test account with 0 games, navigate to Endgames tab, verify empty-state message appears instead of chart |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 120s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
