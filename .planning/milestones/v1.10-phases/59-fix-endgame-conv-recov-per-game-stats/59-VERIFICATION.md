---
phase: 59-fix-endgame-conv-recov-per-game-stats
verified: 2026-04-13T20:30:00Z
status: passed
score: 4/4 must-haves verified
overrides_applied: 0
---

# Phase 59: Fix Endgame Conv/Even/Recov per-game stats Verification Report

**Phase Goal:** The "Endgame Conversion & Recovery" section counts each endgame game exactly once across Conv/Even/Recov buckets so the sum equals the "Games with Endgame" total; obsolete admin-gated gauges + timeline are removed.

**Verified:** 2026-04-13T20:30:00Z
**Status:** PASSED
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths (ROADMAP Success Criteria)

| #   | Truth | Status | Evidence |
| --- | ----- | ------ | -------- |
| 1   | `sum(material_rows.games)` equals `performance.endgame_wdl.total` for any filter combination | VERIFIED | `_compute_score_gap_material` rewritten with group-then-pick + NULL→even routing (app/services/endgame_service.py:546-599); 8 invariant tests in `TestScoreGapMaterialInvariant` all assert sum equality across single-span, multi-span, NULL, NULL-after, empty, mixed-10-games, and deterministic-ordering cases — all passing. |
| 2   | "Results by Endgame Type" table is unchanged (stays sequence-based with the 6-ply threshold) | VERIFIED | `_aggregate_endgame_stats` and `EndgameConvRecovChart` untouched in this phase per Plan 59-03 SUMMARY ("Left ... `_aggregate_endgame_stats`, `_compute_score_gap_material`, and `get_endgame_performance` untouched"). `MATERIAL_ADVANTAGE_POINTS`/`PERSISTENCE_MOVES` exports preserved (verified via grep). |
| 3   | Admin-gated "Conversion and Recovery" section (gauges + timeline) is removed along with its backend query, schemas, and frontend components | VERIFIED | `EndgameConvRecovTimelineChart.tsx`, `EndgameGauge.tsx`, `EndgameGaugesSection` all gone; `Endgames.tsx` no longer references any of them; backend `query_conv_recov_timeline_rows`, `_compute_conv_recov_rolling_series`, `get_conv_recov_timeline`, `ConvRecovTimelinePoint`, `ConvRecovTimelineResponse`, and 9 `EndgamePerformanceResponse` fields all deleted. Grep across `app/`, `frontend/src`, `tests/` returns ZERO matches. |
| 4   | Backend unit test asserts the Conv+Even+Recov == Games-with-Endgame invariant | VERIFIED | `class TestScoreGapMaterialInvariant(TestScoreGapMaterial)` in tests/test_endgame_service.py:900 with 8 `test_invariant_*` methods. Each asserts `sum(row.games for row in result.material_rows) == endgame_wdl.total`. |

**Score:** 4/4 truths verified

### Required Artifacts

| Artifact | Expected | Status | Details |
| -------- | -------- | ------ | ------- |
| `app/services/endgame_service.py` | `_compute_score_gap_material` rewritten with group-then-pick dedupe, NULL→even, conversion-over-recovery tiebreak | VERIFIED | All required patterns present: `rows_by_game` (3 occurrences L546-550), `Conversion-over-recovery` doc comment (L534), no `seen_game_ids` or `if user_material_imbalance is None:` matches. Old `_compute_conv_recov_rolling_series` and `get_conv_recov_timeline` deleted. |
| `tests/test_endgame_service.py` | `TestScoreGapMaterialInvariant` class with 8 invariant tests + renamed none-imbalance test | VERIFIED | `class TestScoreGapMaterialInvariant` at L900; 8 `test_invariant_*` methods at L906-1004; renamed `test_score_gap_material_none_imbalance_bucketed_as_even` at L801; old `test_score_gap_material_none_imbalance_excluded` removed. |
| `app/schemas/endgames.py` | `EndgamePerformanceResponse` slimmed to 3 fields; `ConvRecov*` schemas deleted; `conv_recov_timeline` removed from `EndgameOverviewResponse` | VERIFIED | `EndgamePerformanceResponse` (L102-114) only declares `endgame_wdl`, `non_endgame_wdl`, `endgame_win_rate` with explicit Phase 59 docstring. No grep matches for `ConvRecov*` or removed fields anywhere in `app/`. |
| `app/repositories/endgame_repository.py` | `query_conv_recov_timeline_rows` deleted; `query_endgame_timeline_rows` 3-tuple shape preserved | VERIFIED | Grep for `query_conv_recov_timeline_rows` returns zero matches in production code. |
| `frontend/src/components/charts/EndgameConvRecovTimelineChart.tsx` | Deleted | VERIFIED | File no longer exists (`ls` returns "No such file"). |
| `frontend/src/components/charts/EndgameGauge.tsx` | Deleted (orphaned by Plan 59-02 cleanup) | VERIFIED | File no longer exists. |
| `frontend/src/components/charts/EndgamePerformanceSection.tsx` | `EndgameGaugesSection` removed; `EndgamePerformanceSection` + `MATERIAL_ADVANTAGE_POINTS`/`PERSISTENCE_MOVES` preserved | VERIFIED | Only one stale grep match: a JSDoc memorial line ("the associated EndgameGaugesSection ... were deleted"). The function/code is gone. |
| `frontend/src/pages/Endgames.tsx` | No references to `EndgameGaugesSection`, `EndgameConvRecovTimelineChart`, `showConvRecovTimeline`, `convRecovData`, `Conversion and Recovery`, `conv_recov_timeline` | VERIFIED | Combined grep returns ZERO matches. |
| `frontend/src/types/endgames.ts` | TS mirrors of removed schemas deleted | VERIFIED | No TS references to `ConvRecovTimelinePoint`, `ConvRecovTimelineResponse`, or removed `EndgamePerformance*` fields. |

### Key Link Verification

| From | To | Via | Status | Details |
| ---- | -- | --- | ------ | ------- |
| `_compute_score_gap_material` | `endgame_wdl.total` | `sum(material_rows.games)` invariant | WIRED | `material_rows` constructed in fixed order conversion/even/recovery (L601-603); `bucket_games` accumulator increments exactly once per game in `rows_by_game.items()` loop (L593); test class proves `sum == endgame_wdl.total` across 8 distinct scenarios. |
| `Endgames.tsx` | `EndgamePerformanceSection` | Named import | WIRED | Import line preserved in `Endgames.tsx`; component still renders with `endgame_wdl` + `non_endgame_wdl` props which remain in slimmed schema. |
| `EndgameConvRecovChart` | `MATERIAL_ADVANTAGE_POINTS` / `PERSISTENCE_MOVES` | Named import from `EndgamePerformanceSection.tsx` | WIRED | Both constants explicitly preserved by Plan 59-02 (verified via grep — exactly 2 export lines remain). |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
| -------- | ------- | ------ | ------ |
| Backend type check zero errors | `uv run ty check app/ tests/` | "All checks passed!" | PASS |
| Targeted invariant tests pass | `uv run pytest tests/test_endgame_service.py::TestScoreGapMaterial tests/test_endgame_service.py::TestScoreGapMaterialInvariant` | 42 passed in 0.29s | PASS |
| Full backend suite passes | `uv run pytest -x -q` | 672 passed, 139 warnings in 6.95s | PASS |
| Frontend production build succeeds | `cd frontend && npm run build` | PWA v1.2.0 generated, 11 precache entries | PASS |
| Frontend dead-code check | `cd frontend && npm run knip` | clean exit | PASS |
| No orphan refs to removed entities | `grep -rn "aggregate_conversion\|aggregate_recovery\|endgame_skill\|relative_strength\|overall_win_rate\|conv_recov_timeline\|ConvRecovTimeline*\|query_conv_recov_timeline_rows\|_compute_conv_recov_rolling_series\|get_conv_recov_timeline" app/ frontend/src tests/` | Only 1 hit in `tests/test_endgames_router.py:319` for `test_conv_recov_timeline_returns_404` (intentionally preserved per Plan 59-03 — asserts the legacy HTTP route returns 404, removed in Phase 52) | PASS |

### Requirements Coverage

No `requirements:` IDs declared in any of the three plan frontmatters (`requirements: []`). Phase has no formal REQUIREMENTS.md entries — verification driven by ROADMAP success criteria, all of which are satisfied above.

### Anti-Patterns Found

None. Pre-existing F841 ruff errors at `app/services/endgame_service.py:857` and `:860` (unused `time_control_seconds`, `termination` locals) confirmed pre-existing in Phase 55 commit `0a21775e` per Plan 59-03 SUMMARY — explicitly out of scope for this phase. They do not affect ty, tests, or builds.

### Human Verification Required

None. The phase is fully verifiable from the codebase and test suite:
- The invariant is asserted by 8 unit tests covering single-span, multi-span tiebreaks, NULL handling, empty input, and deterministic ordering.
- The UI removal is verifiable structurally (files deleted, JSX block stripped, no grep hits).
- The backend cleanup is verifiable structurally (schemas slimmed, functions deleted, ty + tests green).
- A post-deploy smoke check by the user (e.g., load /endgames page and confirm no "Conversion and Recovery" heading) would be a nice-to-have but is fully implied by the build + grep evidence.

### Gaps Summary

No gaps. Phase 59 fully achieves its stated goal. The `_compute_score_gap_material` algorithm now provably accounts for every endgame game exactly once across the three buckets. The obsolete admin-gated "Conversion and Recovery" UI is removed end-to-end across frontend components, backend service helpers, repository functions, response schemas, and TypeScript type mirrors. All quality gates (ty, pytest 672/672, frontend lint/build/knip) pass.

---

_Verified: 2026-04-13T20:30:00Z_
_Verifier: Claude (gsd-verifier)_
