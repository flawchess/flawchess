---
phase: "242"
slug: "openings-stats-insights-rework"
# status lifecycle: draft (seeded by plan-phase) → validated (set by validate-phase §6)
# audit-milestone §5.5 distinguishes NOT-VALIDATED (draft) from PARTIAL (validated + nyquist_compliant: false) (#2117)
status: validated
nyquist_compliant: true
wave_0_complete: true
created: "2026-10-17"
---

# Phase 242 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.
> Source: `242-RESEARCH.md` § Validation Architecture.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest + pytest-asyncio (backend); vitest + Testing Library (frontend) |
| **Config file** | `pyproject.toml [tool.pytest.ini_options]`; `frontend/vite.config.ts` test block + `frontend/src/vitest.setup.ts` |
| **Quick run command** | backend: `uv run pytest <touched test files> -x`; frontend: `cd frontend && npx vitest run <touched test files>` |
| **Full suite command** | `uv run pytest -n auto -x` and `( cd frontend && npm run lint && npm run build && npm test -- --run && npm run knip )` |
| **Estimated runtime** | quick ~30 s; full ~6 min |

---

## Sampling Rate

- **After every task commit:** Run the quick-run command for the touched side
- **After every plan wave:** Full backend suite (`-n auto`) after the backend wave; full frontend gate after each frontend wave
- **Before `/gsd-verify-work`:** Full CLAUDE.md pre-merge gate must be green
- **Max feedback latency:** 60 seconds (quick run)

---

## Per-Task Verification Map

Filled by the planner per task (`<automated>` + `<fails_when>`). Decision → test map from research:

| Decision | Behavior | Test Type | Automated Command | File Exists | Status |
|----------|----------|-----------|-------------------|-------------|--------|
| D-00/D-13 | finalizer centres on ±25 cp; raw avg eval unchanged | unit | `uv run pytest tests/services/test_opening_eval.py -x` | ✅ | ✅ green |
| D-16 | toggle retired, stale keys swept once (plan 242-05) | unit/component | `npm --prefix frontend test -- src/lib/__tests__/retiredLocalStorage.test.ts src/components/position-bookmarks` | ✅ | ✅ green |
| D-00 switch | colour switch tracks only changing clicks (plan 242-05) | component | `npm --prefix frontend test -- src/components/openings/__tests__/OpeningColorSwitch.test.tsx` | ✅ | ✅ green |
| D-13 | all 4 Openings call sites centred | integration | `uv run pytest tests/services/test_stats_service_phase_entry.py tests/test_openings_service.py tests/services/test_opening_insights_service.py -x` | ✅ | ✅ green |
| D-13 guard | endgame eval unchanged | regression | `uv run pytest tests/test_endgame_service.py -x` | ✅ | ✅ green |
| D-01..D-03 | current/past cutoff (200 games OR 60 d, filters, now_utc) | unit/integration | `uv run pytest tests/test_repertoire_recency.py -x` | ✅ | ✅ green |
| D-05/D-06 | fetch → dedupe → bookmark twin drop → split → cap 10/10 | integration | `uv run pytest tests/test_stats_service.py -k "dedupe or twin or split or most_played" -x` | ✅ | ✅ green |
| D-05 (clarified) | cutoff-restricted second fetch fills current rows when fewer than 10 survive; nominees carry unrestricted counts; none when cutoff is None (plan 242-01 Task 3, mutation-proven) | unit/integration | `uv run pytest tests/test_stats_service.py -k recent_fallback -x` | ✅ | ✅ green |
| D-09..D-11 | findings high ≤5, medium ≤10, counts, low dropped | unit | `uv run pytest tests/services/test_opening_insights_service.py -x` | ✅ | ✅ green |
| D-00 series / D-18 | weekly points + per-week games; bookmark score p + 99% CI | integration | `uv run pytest tests/test_openings_time_series.py tests/test_aggregation_sanity.py -x` | ✅ | ✅ green |
| D-03 | routers inject `dev_now_utc` (plans 242-01/02/03) | router | `uv run pytest tests/test_stats_router.py tests/routers/test_insights_openings.py tests/routers/test_openings_time_series_router.py -x` | ✅ | ✅ green |
| D-15 | `/openings/insights` redirects to `/openings/stats`; Insights triggers gone on both strips (plan 242-08) | component | `cd frontend && npx vitest run src/pages/__tests__/Openings.render.test.tsx` | ✅ | ✅ green |
| D-00 layout | board hidden on lg for Stats only; Insights case removed (plan 242-08) | unit | `cd frontend && npx vitest run src/pages/__tests__/Openings.statsBoard.test.tsx` | ✅ | ✅ green |
| D-00 verdicts | opening verdict rules (n<20 neutral, band, 99%) | unit | `cd frontend && npx vitest run src/lib/__tests__/openingVerdict.test.ts` | ✅ | ✅ green |
| D-00 table / D-16 | repertoire table, "Played before (n)", chips, fades; toggle gone (plan 242-06; row expansion + bookmark link extended in plan 242-09) | component | `cd frontend && npx vitest run src/components/openings/__tests__/RepertoireTable.test.tsx` | ✅ | ✅ green |
| D-08..D-11 | findings Show more, Not clear yet, empty state (plan 242-07) | component | `cd frontend && npx vitest run src/components/openings/__tests__/OpeningFindings.test.tsx` | ✅ | ✅ green |
| D-14 | single-series ScoreChart with volume bars (plan 242-09) | component | `cd frontend && npx vitest run src/components/charts/__tests__/ScoreChart.test.tsx` | ✅ | ✅ green |
| D-17 | Moves/Games verdict bar for opening-end; endgame-entry unchanged (plan 242-04) | component | `npm --prefix frontend test -- src/components/charts/__tests__/PositionResultsPanel.test.tsx src/pages/__tests__/Endgames.readinessGate.test.tsx` | ✅ | ✅ green |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [x] `tests/services/test_opening_eval.py` — centred finalizer
- [x] `tests/test_repertoire_recency.py` — cutoff helper (>200 and <200 game fixtures, injected `now_utc`)
- [x] dedupe/split cases in `tests/test_stats_service.py`
- [x] `frontend/src/lib/__tests__/openingVerdict.test.ts`
- [x] `frontend/src/components/openings/__tests__/RepertoireTable.test.tsx`, `OpeningFindings.test.tsx`
- [x] Delete tests with their components (`OpeningStatsCard` in plan 242-06; `OpeningFindingCard`, `OpeningInsightsBlock` in plan 242-08); adjust `EvalCpuPlaceholder.test.tsx` (plan 242-06), `openingStatsZones.test.ts`

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Sticky colour switch + sticky table header on scroll; phone row stacking | D-00 | layout/scroll behaviour not observable in jsdom | Browser UAT at phone/tablet/desktop widths (run it yourself via Chrome) |
| Owner data: Queen's Gambit (280 games, Oct 2023) in "Played before"; Caro-Kann Advance duplicate collapsed | D-01, D-06 | needs real data | Browser UAT on dev with owner's games |

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references
- [x] No watch-mode flags
- [x] Feedback latency < 60s
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** approved 2026-10-17 (validate-phase audit: 18/18 rows green, 0 gaps)

## Validation Audit 2026-10-17

| Metric | Count |
|---|---|
| Gaps found | 0 |
| Resolved | 0 |
| Escalated | 0 |
