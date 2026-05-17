---
phase: 88
slug: time-pressure-stats-rework
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-05-17
---

# Phase 88 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.x (backend) + vitest (frontend) |
| **Config file** | `pyproject.toml` (backend), `frontend/vitest.config.ts` (frontend) |
| **Quick run command** | `uv run pytest tests/test_endgame_math.py -x` (backend) / `cd frontend && npm test -- --run src/components/charts/__tests__/EndgameTimePressureCard.test.tsx` (frontend) |
| **Full suite command** | `uv run pytest && cd frontend && npm test -- --run && npm run lint && npm run knip` |
| **Estimated runtime** | ~60–90 seconds full suite |

---

## Sampling Rate

- **After every task commit:** Run quick command for the touched layer (backend OR frontend test file).
- **After every plan wave:** Run full suite.
- **Before `/gsd:verify-work`:** Full suite green + `uv run ty check app/ tests/` zero errors + `bin/gen_endgame_zones_ts.py` drift-clean (no uncommitted changes after run).
- **Max feedback latency:** 60 seconds.

---

## Per-Task Verification Map

Filled by the planner during plan generation. Each row maps a task ID to its automated check.

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 88-01-01 | 01 | 1 | D-04 | — | N/A | unit | `uv run pytest tests/test_endgame_math.py::test_compute_score_delta_vs_reference -x` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

*The planner expands this table to cover every task across all plans.*

---

## Wave 0 Requirements

- [ ] `tests/test_endgame_math.py` — `compute_score_delta_vs_reference` boundary tests (n=0, all-wins, all-losses, user==cohort, wilson CI invariants)
- [ ] `tests/test_endgame_zones.py` — `PRESSURE_BIN_SCORE_NEUTRAL_ZONES` registry shape test (4 TC × 5 quintile keys, p25 ≤ p75, half-width ≤ cap)
- [ ] `tests/services/test_time_pressure_service.py` — service-level test for the new card payload (mirror-bucket cohort_score lookup, sparse-bin handling)
- [ ] `frontend/src/components/charts/__tests__/EndgameTimePressureCard.test.tsx` — card render test (4 TC, sparse-bin dimming, n=0 row preservation, sig-gating)
- [ ] `frontend/src/components/charts/__tests__/EndgameTimePressureSection.test.tsx` — section orchestrator test (TC-card hide at MIN_GAMES_PER_TC_CARD, grid breakpoints)

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Card grid renders at xl (4-col), lg (2-col), md and below (1-col) | UI doctrine | Visual regression not yet automated | Open Endgames page at 1440px / 1024px / 375px, confirm column counts and equal card heights |
| Popover content readable and not clipped on mobile | UI doctrine | Radix popover positioning is responsive | Open card popovers at 375px, confirm no overflow |
| /benchmarks §3.3.3 produces 4×5 IQR table with collapse verdicts | D-03 | Skill output reviewed by user before zone constants commit | Run `/benchmarks chess-score-per-pressure-bin` against benchmark DB, review `reports/benchmarks-latest.md` §3.3.3 |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 60s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
