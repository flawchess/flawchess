---
phase: 97
slug: endgame-metrics-by-time-control
status: planned
nyquist_compliant: true
wave_0_complete: false
created: 2026-05-29
---

# Phase 97 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.x (backend) + vitest (frontend) |
| **Config file** | `pyproject.toml` (pytest) / `frontend/vitest.config.ts` |
| **Quick run command** | `uv run pytest tests/test_endgame_service.py -x` |
| **Full suite command** | `uv run pytest -x && ( cd frontend && npm test -- --run )` |
| **Estimated runtime** | ~90 seconds |

---

## Sampling Rate

- **After every task commit:** Run the relevant quick command (backend `uv run pytest <file> -x`, frontend `npm test -- --run <file>`)
- **After every plan wave:** Run the full suite command
- **Before `/gsd-verify-work`:** Full suite must be green + `uv run ty check app/ tests/` + `cd frontend && npm run lint && npm run knip`
- **Max feedback latency:** 90 seconds

---

## Per-Task Verification Map

> One row per task across the four phase plans.

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| P01-T1 | 97-01 | 1 | SC-3 | T-97-01 | N/A (build-time const) | unit/source | `uv run python -c "from app.services.endgame_zones import TC_METRIC_BANDS; assert TC_METRIC_BANDS['bullet'].conv_rate==(0.588,0.719)"` | app/services/endgame_zones.py | ⬜ pending |
| P01-T2 | 97-01 | 1 | SC-5 | T-97-01 | drift gate | drift | `uv run python scripts/gen_endgame_zones_ts.py && git diff --exit-code frontend/src/generated/endgameZones.ts` | scripts/gen_endgame_zones_ts.py, frontend/src/generated/endgameZones.ts | ⬜ pending |
| P02-T1 | 97-02 | 1 | SC-5 | T-97-05 | Literal-typed TC field | source/type | `uv run python -c "from app.schemas.endgames import EndgameOverviewResponse; assert 'endgame_metrics_cards' in EndgameOverviewResponse.model_fields"` + `uv run ty check` | app/schemas/endgames.py, app/repositories/endgame_repository.py | ⬜ pending |
| P02-T2 | 97-02 | 1 | SC-4, SC-5 | T-97-03 | V4 pre-scoped rows, no gather | unit/integration | `uv run pytest tests/services/test_endgame_service.py::test_compute_per_tc_metric_cards -x && uv run pytest tests/test_endgame_service.py -x` | app/services/endgame_service.py, tests/services/test_endgame_service.py | ⬜ pending |
| P03-T1 | 97-03 | 2 | SC-2 | T-97-06 | N/A | type | `cd frontend && npx tsc --noEmit` | frontend/src/types/endgames.ts | ⬜ pending |
| P03-T2 | 97-03 | 2 | SC-2, SC-3 | T-97-07 | bands from codegen, not API | unit | `cd frontend && npm test -- --run EndgameMetricsByTcCard` | frontend/src/components/charts/EndgameMetricsByTcCard.tsx | ⬜ pending |
| P03-T3 | 97-03 | 2 | SC-1, SC-6 | T-97-06 | N/A | unit | `cd frontend && npm test -- --run EndgameMetricsByTcSection && npm run lint` | frontend/src/components/charts/EndgameMetricsByTcSection.tsx, frontend/src/pages/Endgames.tsx | ⬜ pending |
| P04-T1 | 97-04 | 3 | SC-1, SC-7 | T-97-08 | grep-guard scope | source/regression | `! grep -rq "score_gap_conv_percentile\|score_gap_conv_per_tc" app/ && uv run pytest tests/test_endgame_service.py tests/services/test_endgame_service_chip_decoupling.py tests/schemas/test_endgames_schema.py -x` | app/schemas/endgames.py, app/services/endgame_service.py | ⬜ pending |
| P04-T2 | 97-04 | 3 | SC-1, SC-5, SC-7 | T-97-09 | knip dead-export gate | knip/lint/test | `cd frontend && npm run knip && npm run lint && npm test -- --run && npx tsc --noEmit` | (deletions) frontend/src/components/charts/EndgameMetricsSection.tsx, EndgameMetricCard.tsx | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- Existing infrastructure (pytest + vitest) covers all phase verification. No new framework install required.
- New test files to create during execution (counted as in-task scaffolding, not a separate Wave 0):
  - `tests/services/test_endgame_service.py::test_compute_per_tc_metric_cards` (Plan 02 Task 2)
  - `frontend/src/components/charts/__tests__/EndgameMetricsByTcCard.test.tsx` (Plan 03 Task 2)
  - `frontend/src/components/charts/__tests__/EndgameMetricsByTcSection.test.tsx` (Plan 03 Task 3)

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Per-TC cards render responsively on desktop + mobile | SC-6 | Visual layout parity is hard to assert automatically | Load Endgames page at desktop + mobile widths; confirm one full-width card per eligible TC in bullet/blitz/rapid/classical order, metric blocks side-by-side on desktop and stacked on mobile; confirm Conv/Recov gauge bands shift per TC and Parity band is constant |
| Overall Performance section chips/tooltips still render after removal | SC-7 | Confirms the surgical removal did not drop the kept score_gap / achievable chips | Load Endgames page; confirm the Overall Performance "Endgame Score Gap" and "Achievable Score Gap" percentile chips + per-TC tooltips still render |

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 scaffolding within the task
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references (new test files created in-task)
- [x] No watch-mode flags
- [x] Feedback latency < 90s
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** ready for execution
