---
phase: 94-backend-frontend-percentile-annotations
plan: 01
subsystem: api
tags: [backend, endgame, percentile, pydantic, fastapi, reliability-gate]

# Dependency graph
requires:
  - phase: 93-global-percentile-benchmark-artifact
    provides: interpolate_percentile helper + GLOBAL_PERCENTILE_CDF registry (4 in-scope metrics, 99 breakpoints each)
provides:
  - "ScoreGapMaterialResponse.score_gap_percentile (float | None)"
  - "ScoreGapMaterialResponse.section2_score_gap_conv_percentile (float | None)"
  - "ScoreGapMaterialResponse.section2_score_gap_parity_percentile (float | None)"
  - "EndgamePerformanceResponse.achievable_score_gap_percentile (float | None)"
  - "Service-layer dual-N + single-N reliability gates layered on top of interpolate_percentile, reusing PVALUE_RELIABILITY_MIN_N=10"
affects: [94-02-frontend, 94-03-frontend, 95-llm-payload]

# Tech tracking
tech-stack:
  added: []  # no new packages — Phase 93 helper is the only new dep, already in app/services/
  patterns:
    - "Gate-then-compute pattern: gate on N first, only call interpolate_percentile if floor cleared (Pitfall 6)"
    - "Per-bucket mean-not-None guard: helper is NaN-safe but not None-safe; explicit guard on conv/parity mean"
    - "Field-name divergence by design: score_gap_percentile mirrors MetricId, not the wire sibling score_difference (D-11)"

key-files:
  created: []
  modified:
    - "app/schemas/endgames.py (4 new nullable Pydantic fields with gate-semantics docstrings)"
    - "app/services/endgame_service.py (1 import + 4 gated interpolate_percentile calls + 4 new kwargs on response constructors)"
    - "tests/schemas/test_endgames_schema.py (TestPercentileFieldsPresent class — 2 methods, 4 positive + 1 negative assertion)"
    - "tests/test_endgame_service.py (TestPercentileGates class — 11 gate tests across both sites)"

key-decisions:
  - "Reuse PVALUE_RELIABILITY_MIN_N = 10 for all 4 metrics (D-10 default). No per-metric override: Phase 93 CDF inclusion floors (≥30/≥20 spans) are already stricter than the chip gate, so the N=10 gate only fires when CDF interpolation is itself well-supported."
  - "Dual-N gate confirmed for Endgame Score Gap: min(endgame_wdl.total, non_endgame_wdl.total) >= PVALUE_RELIABILITY_MIN_N. Mirrors the existing score_difference_p_value gate."
  - "Explicit `mean is not None` guard added to conv/parity percentile gates: _compute_per_bucket_score_gap returns mean=None on empty cohorts and interpolate_percentile raises on None."
  - "Recovery percentile field NOT added anywhere (D-12). Comment in endgames.py rephrased to avoid the literal field-name string so the recovery-absent grep guard returns 0."

patterns-established:
  - "Gate-then-compute: cheaper than compute-then-gate and makes the gate semantics legible at the call site"
  - "Structural recovery exclusion: defensive negative assertions in both schema and service tests guard against future symmetry-driven re-introduction"

requirements-completed: [PCTL-02, PCTL-06]

# Metrics
duration: 12min
completed: 2026-05-23
---

# Phase 94 Plan 01: Backend percentile field emission Summary

**4 nullable `*_percentile` fields wired into the endgame API response, computed from the Phase 93 global CDF and reliability-gated at PVALUE_RELIABILITY_MIN_N=10 (dual-N for Endgame Score Gap, single-N for the other 3).**

## Performance

- **Duration:** ~12 min
- **Started:** 2026-05-23T06:19:40Z (phase execution start per STATE.md)
- **Completed:** 2026-05-23T06:31:11Z
- **Tasks:** 2 (both TDD: RED then GREEN)
- **Files modified:** 4

## Accomplishments

- 4 additive nullable Pydantic v2 fields on the existing endgame response schemas — non-breaking, default `None`, value range `[0, 100]`.
- 4 gated `interpolate_percentile` calls at the 2 service-layer compute sites (`_get_endgame_performance_from_rows` and `_compute_score_gap_material`), all reusing the existing `PVALUE_RELIABILITY_MIN_N` constant.
- 11 new gate-semantics tests covering both wings of the dual-N gate, the at-floor and below-floor edges of all 3 single-N gates, the empty-cohort mean-None guard for conv/parity, and a structural recovery-exclusion guard.
- Full backend suite still green: 1642 passed, 6 skipped.

## Task Commits

1. **Task 1 RED: failing schema-presence tests** — `aa2260bf` (test)
2. **Task 1 GREEN: 4 nullable Pydantic fields with gate-semantics docstrings** — `1d9087c4` (feat)
3. **Task 2 RED: failing percentile gate tests for service layer** — `225ecbf6` (test)
4. **Task 2 GREEN: wire interpolate_percentile into 2 compute sites with N gates** — `5a965f20` (feat)

_TDD discipline maintained: each GREEN commit follows a RED commit whose tests fail without the feature._

## Files Created/Modified

- `app/schemas/endgames.py` — added `achievable_score_gap_percentile` on `EndgamePerformanceResponse` and `score_gap_percentile` + `section2_score_gap_conv_percentile` + `section2_score_gap_parity_percentile` on `ScoreGapMaterialResponse`. Each field is `float | None = None` with a docstring documenting the reliability gate and the deliberate `score_gap` name divergence (D-11).
- `app/services/endgame_service.py` — added `from app.services.global_percentile_cdf import interpolate_percentile`; gate-then-compute pattern at site A (`_get_endgame_performance_from_rows`, single-N on `ex_n`) and site B (`_compute_score_gap_material`, dual-N on `min(endgame_wdl.total, non_endgame_wdl.total)` and single-N + mean-not-None on conv/parity).
- `tests/schemas/test_endgames_schema.py` — `TestPercentileFieldsPresent` class with two methods: positive presence assertions for the 4 fields, and a defensive negative assertion that `section2_score_gap_recov_percentile` is forbidden (D-12).
- `tests/test_endgame_service.py` — `TestPercentileGates` class with 11 tests: 2 single-N for achievable, 3 dual-N for score_gap, 4 single-N for conv/parity at n=9 and n=10, 1 empty-cohort mean-None guard, 1 structural recovery-exclusion guard.

## Decisions Made

- **Reliability floor: reuse `PVALUE_RELIABILITY_MIN_N = 10` for all 4 metrics (D-10 default).** No per-metric tightening. Rationale: Phase 93's CDF inclusion floors (≥30 endgame AND ≥30 non-endgame games for score_gap; ≥20 entry spans for achievable; ≥20 spans/bucket for Section 2) are already stricter than the chip gate, so the N=10 gate only fires when the CDF interpolation is itself well-supported. Per-metric overrides would have added 3 unnecessary constants and split the floor-management story.
- **Dual-N gate for Endgame Score Gap confirmed.** Uses `min(endgame_wdl.total, non_endgame_wdl.total) >= PVALUE_RELIABILITY_MIN_N` — mirrors the existing `score_difference_p_value` gate so the percentile absence and CI absence appear together. Both wings of the gap must clear the floor.
- **Explicit `mean is not None` guard on conv/parity gates.** `_compute_per_bucket_score_gap` returns `mean=None` on empty cohorts and `interpolate_percentile` is NaN-safe but not None-safe. The triple guard `mean is not None and n is not None and n >= floor` makes the call-site contract explicit rather than relying on the helper to mask the bug.
- **Recovery percentile is not added anywhere (D-12).** Per the locked decision (opponent-confounded, d=0.95 inverted, no CDF shipped). The comment in `endgames.py` was rephrased so the literal field name `section2_score_gap_recov_percentile` does not appear in either `app/schemas/endgames.py` or `app/services/endgame_service.py`, satisfying the plan's `grep -c` acceptance guard while preserving the D-12 explanatory note.

## Deviations from Plan

None — plan executed exactly as written. All design ambiguities were pre-resolved in `94-CONTEXT.md` (D-10..D-13) and `94-RESEARCH.md` (Pitfalls 1, 6). No Rule 1/2/3 auto-fixes were needed; no Rule 4 architectural escalation.

The only minor textual adjustment was rephrasing a comment in `app/schemas/endgames.py` after the GREEN commit to satisfy the plan's literal `grep -c "section2_score_gap_recov_percentile" ... = 0` acceptance criterion. The original comment used the field name as a self-documenting "NO X field" anchor; the rephrased version says "NO recovery percentile field is emitted for the recovery bucket" which conveys the same intent without tripping the grep guard. This is a Task 2 GREEN refinement, not a deviation.

## Issues Encountered

- **Pydantic v2.11 deprecation warning** on `result.model_fields` (instance access) in the structural recovery-exclusion test. Fixed by reading from the class (`ScoreGapMaterialResponse.model_fields`) and adding a complementary `hasattr` runtime check on the instance. Both assertions strengthen the guard rather than weaken it.

## Verification

All plan acceptance criteria green:

- `uv run pytest tests/schemas/test_endgames_schema.py::TestPercentileFieldsPresent -x` → 2/2 passed.
- `uv run pytest tests/test_endgame_service.py::TestPercentileGates -x` → 11/11 passed.
- `uv run ty check app/ tests/` → All checks passed.
- `uv run ruff format app/ tests/ && uv run ruff check app/ tests/ --fix` → clean.
- `grep -n "from app.services.global_percentile_cdf import interpolate_percentile" app/services/endgame_service.py` → exactly 1 line (line 74).
- `grep -c "section2_score_gap_recov_percentile" app/services/endgame_service.py app/schemas/endgames.py` → 0 + 0 = 0 (D-12 guard).
- `grep -cE 'interpolate_percentile\("(score_gap\|achievable_score_gap\|section2_score_gap_conv\|section2_score_gap_parity)"' app/services/endgame_service.py` → 4 hits.
- `uv run pytest tests/services/test_global_percentile_cdf.py -x` → Phase 93 regression suite still green (11/11).
- `uv run pytest -x` → full backend suite 1642 passed, 6 skipped, 0 failed.

## User Setup Required

None — pure additive backend change, no env vars, no migrations, no external services.

## Next Phase Readiness

- 4 new nullable fields are live on the wire and ready for the Wave 2 frontend to consume.
- TS types need a manual mirror in `frontend/src/types/endgames.ts` — flagged in `94-RESEARCH.md` Pitfall 4; Plan 94-02 task.
- LLM payload integration is Phase 95's job (LLM-05) — Phase 94 explicitly does not touch `app/prompts/endgame_insights.md` or `app/services/insights_llm.py`.

## Threat Flags

None — Phase 94 introduces no new trust boundaries beyond those documented in the plan's `<threat_model>` (T-94-01 / T-94-02 / T-94-03 / T-94-SC). All percentile values are server-derived from existing service computations; reliability gate is enforced at the service layer; no new authorization surface; no new packages installed.

## Self-Check: PASSED

- SUMMARY.md exists at the planned path.
- All 4 modified files exist on disk.
- All 4 commits (`aa2260bf`, `1d9087c4`, `225ecbf6`, `5a965f20`) exist on the worktree branch.

---
*Phase: 94-backend-frontend-percentile-annotations*
*Completed: 2026-05-23*
