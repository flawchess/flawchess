---
phase: 88
slug: time-pressure-stats-rework
status: planned
nyquist_compliant: true
wave_0_complete: false
created: 2026-05-17
updated: 2026-05-17
---

# Phase 88 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.x (backend) + vitest (frontend) |
| **Config file** | `pyproject.toml` (backend), `frontend/vitest.config.ts` (frontend) |
| **Quick run (backend)** | `uv run pytest tests/services/test_score_confidence.py tests/services/test_endgame_zones.py tests/services/test_time_pressure_service.py -x -q` |
| **Quick run (frontend)** | `cd frontend && npm test -- --run src/components/charts/__tests__/EndgameTimePressureCard.test.tsx src/components/charts/__tests__/EndgameTimePressureSection.test.tsx` |
| **Full suite command** | `uv run ty check app/ tests/ && uv run pytest -x -q && cd frontend && npx tsc --noEmit && npm run lint && npm run knip && npm test -- --run` |
| **Codegen drift gate** | `uv run python scripts/gen_endgame_zones_ts.py && git diff --exit-code frontend/src/generated/endgameZones.ts` |
| **Estimated runtime** | ~60-90 seconds full suite |

---

## Sampling Rate

- **After every task commit:** run quick command for the touched layer (backend OR frontend test file).
- **After every plan wave:** full suite.
- **Before `/gsd:verify-work`:** full suite green + ty zero errors + codegen drift-clean.
- **Max feedback latency:** 60 seconds.

---

## Per-Task Verification Map

One row per planned task across all 8 plans. Status updated by executor.

| Task ID | Plan | Wave | Decision Refs | Threat Ref | Secure Behavior | Test Type | Automated Command | Status |
|---------|------|------|---------------|------------|-----------------|-----------|-------------------|--------|
| 88-01-01 | 01 | 1 | D-04 | T-88-01, T-88-02 | Wilson-vs-arbitrary-ref math correctness, division-by-zero guard | source-grep + ty | `uv run ty check app/services/score_confidence.py && grep -c "def compute_score_delta_vs_reference\|def _wilson_score_test_vs_ref" app/services/score_confidence.py` | ⬜ pending |
| 88-01-02 | 01 | 1 | D-04 | T-88-01 | Wilson-transplant invariant; n-gate enforcement | unit | `uv run pytest tests/services/test_score_confidence.py::TestComputeScoreDeltaVsReference -x -q` | ⬜ pending |
| 88-02-01 | 02 | 1 | D-03 | T-88-02-01 | Skill docs include per-quintile collapse verdict pattern | source-grep | `grep -c "### §3.3.3 chess-score-per-pressure-bin\|PRESSURE_BIN_SCORE_NEUTRAL_ZONES\|PRESSURE_BIN_NEUTRAL_CAP" .claude/skills/benchmarks/SKILL.md` | ⬜ pending |
| 88-02-02 | 02 | 1 | D-03 | T-88-02-01 | clock-gap-% submetric documented under §3.3.1 | source-grep | `grep -c "clock-gap-%\|clock_gap_pct\|CLOCK_GAP_NEUTRAL" .claude/skills/benchmarks/SKILL.md` | ⬜ pending |
| 88-03-01 | 03 | 1 | D-02, D-03 | T-88-03-02 | PressureBinBand + 4x5 ZONES + clock_gap_pct MetricId added; LLM-finding scope checked | source-grep + ty | `uv run ty check app/services/endgame_zones.py && python -c "from app.services.endgame_zones import PRESSURE_BIN_SCORE_NEUTRAL_ZONES; assert len(PRESSURE_BIN_SCORE_NEUTRAL_ZONES) == 4"` | ⬜ pending |
| 88-03-02 | 03 | 1 | D-02, D-03 | T-88-03-01 | Codegen emits new constants drift-clean | drift-gate | `uv run python scripts/gen_endgame_zones_ts.py && git diff --exit-code frontend/src/generated/endgameZones.ts` | ⬜ pending |
| 88-03-03 | 03 | 1 | D-02 | T-88-03-01 | 4x5 shape + lower<upper + half-width <= cap invariants | unit | `uv run pytest tests/services/test_endgame_zones.py -x -q` | ⬜ pending |
| 88-04-01 | 04 | 2 | D-03 (research Q3) | T-88-04-03 | Pydantic models created; legacy models deleted; ty clean | source-grep + ty | `uv run ty check app/schemas/endgames.py && grep -c "class TimePressureCardsResponse" app/schemas/endgames.py` | ⬜ pending |
| 88-04-02 | 04 | 2 | D-04, D-05, D-06 | T-88-04-01, T-88-04-02, T-88-04-03 | New service function; mirror-bucket extended with quintile; legacy functions removed | source-grep + ty | `uv run ty check app/services/endgame_service.py && grep -c "def _compute_time_pressure_cards\|def _compute_clock_pressure\|def _compute_time_pressure_chart" app/services/endgame_service.py` (expect: 1 0 0) | ⬜ pending |
| 88-04-03 | 04 | 2 | D-01 (sparse), D-04, D-05 | T-88-04-02 | Quintile bucketing math; sparse handling; mirror-bucket cohort; clock-gap CI | unit | `uv run pytest tests/services/test_time_pressure_service.py -x -q` | ⬜ pending |
| 88-05-01 | 05 | 2 | D-01 (color zones) | T-88-05-01 | Config module exports + types compile | source-grep + tsc | `cd frontend && npx tsc --noEmit src/lib/pressureBulletConfig.ts && grep -c "PRESSURE_DELTA_CENTER\|PRESSURE_DELTA_DOMAIN\|CLOCK_GAP_DOMAIN\|clampDeltaCi\|pressureDeltaZoneColor" src/lib/pressureBulletConfig.ts` | ⬜ pending |
| 88-06-01 | 06 | 3 | D-03 (research Q3) | T-88-06-01 | TS types mirror backend schemas; legacy types removed | source-grep | `grep -c "TimePressureCardsResponse\|ClockPressureResponse" frontend/src/types/api.ts` (expect: 1+, 0) | ⬜ pending |
| 88-06-02 | 06 | 3 | D-01 (sparse, dimming), D-04 (triple-gate) | T-88-06-01, T-88-06-02 | Card component renders 6 bullets; sparse + triple-gate; data-testid coverage | source-grep + tsc | `cd frontend && npx tsc --noEmit src/components/charts/EndgameTimePressureCard.tsx` | ⬜ pending |
| 88-06-03 | 06 | 3 | D-01 (n=0 row preservation, dimming, triple-gate) | T-88-06-02 | TC hide; n=0 dash; dim opacity; n-chip; triple-gate font | component-test | `cd frontend && npm test -- --run src/components/charts/__tests__/EndgameTimePressureCard.test.tsx` | ⬜ pending |
| 88-07-01 | 07 | 4 | D-01 (responsive grid) | T-88-07-02 | Section orchestrator: grid xl 4-col / lg 2-col / base 1-col; legacy code overwritten | source-grep + tsc | `cd frontend && npx tsc --noEmit src/components/charts/EndgameTimePressureSection.tsx && grep -c "xl:grid-cols-4\|lg:grid-cols-2" src/components/charts/EndgameTimePressureSection.tsx` | ⬜ pending |
| 88-07-02 | 07 | 4 | D-01 | T-88-07-01, T-88-07-02 | Grid + visibility tests; legacy testid absent | component-test | `cd frontend && npm test -- --run src/components/charts/__tests__/EndgameTimePressureSection.test.tsx` | ⬜ pending |
| 88-07-03 | 07 | 4 | (phase final sweep) | T-88-07-01, T-88-07-03 | Page wiring; legacy deleted; knip/ty/lint/tests/codegen all green | full-suite | `test ! -f frontend/src/components/charts/EndgameClockPressureSection.tsx && cd frontend && npm run lint && npm run knip && npx tsc --noEmit && npm test -- --run && cd .. && uv run ty check app/ tests/ && uv run pytest -x -q && uv run python scripts/gen_endgame_zones_ts.py && git diff --exit-code frontend/src/generated/endgameZones.ts` | ⬜ pending |
| 88-08-01 | 08 | 5 | D-02, D-03 | T-88-08-02 | /benchmarks §3.3.3 + clock-gap-% run; calibrated tables recorded | source-grep | `grep -c "§3.3.3 chess-score-per-pressure-bin\|clock-gap-%" reports/benchmarks-latest.md` | ⬜ pending |
| 88-08-02 | 08 | 5 | D-02 | (checkpoint) | Collapse-verdict decision recorded | checkpoint:decision | resume-signal: collapse-clean / accept-pooled-with-caveat / promote-to-elo-faceting | ⬜ pending |
| 88-08-03 | 08 | 5 | D-02, D-03 | T-88-08-01, T-88-08-03 | Calibrated values; codegen drift-clean; tests still green | drift-gate + unit | `uv run python scripts/gen_endgame_zones_ts.py && git diff --exit-code frontend/src/generated/endgameZones.ts && uv run pytest tests/services/test_endgame_zones.py -x -q` | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements (test files MUST exist before/with task implementation)

- [x] `tests/services/test_score_confidence.py` — existing file; Plan 01 Task 2 appends `TestComputeScoreDeltaVsReference`
- [x] `tests/services/test_endgame_zones.py` — existing file; Plan 03 Task 3 appends `test_pressure_bin_zones_shape`
- [ ] `tests/services/test_time_pressure_service.py` — NEW; created in Plan 04 Task 3
- [ ] `frontend/src/components/charts/__tests__/EndgameTimePressureCard.test.tsx` — NEW; created in Plan 06 Task 3
- [ ] `frontend/src/components/charts/__tests__/EndgameTimePressureSection.test.tsx` — NEW; created in Plan 07 Task 2

All test files are created alongside the production code they test (TDD-style per plan), not in a dedicated Wave 0. The executor MUST write the test first or in the same commit as the implementation.

---

## Manual-Only Verifications

| Behavior | Decision Ref | Why Manual | Test Instructions |
|----------|--------------|------------|-------------------|
| Card grid renders at xl (4-col), lg (2-col), md and below (1-col) | D-01 | Visual regression not yet automated | Open Endgames page at 1440px / 1024px / 375px; confirm column counts and equal card heights |
| Popover content readable and not clipped on mobile | (UI doctrine) | Radix popover positioning is responsive | Open card popovers at 375px; confirm no overflow |
| /benchmarks §3.3.3 produces 4x5 IQR table with collapse verdicts | D-03 | Skill output reviewed by user before zone constants commit | Plan 08 Task 1: run `/benchmarks chess-score-per-pressure-bin` against benchmark DB; review `reports/benchmarks-latest.md` §3.3.3 |
| Per-quintile collapse verdict for ELO axis | D-02 | Decides whether to ship 4x5 or extend to per-ELO faceting | Plan 08 Task 2 checkpoint |

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies
- [x] Sampling continuity: no 3 consecutive tasks without automated verify (every plan ends with a tested step)
- [x] Wave 0 covers all MISSING references (test files created alongside implementation per plan)
- [x] No watch-mode flags (all vitest invocations use `--run`; pytest invocations use `-x -q`)
- [x] Feedback latency < 60s (per-task quick commands are scoped to a single file)
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** ready for execution
</content>
</invoke>