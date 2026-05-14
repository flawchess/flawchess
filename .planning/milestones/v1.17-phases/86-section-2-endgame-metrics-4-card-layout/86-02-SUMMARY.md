---
phase: 86
plan: 02
subsystem: backend-stats
tags: [score-confidence, peer-bullet, wald-z, endgame, sig-test, schema, wire-format]
requires:
  - compute_skill_diff_test
  - compute_per_bucket_diff_test
provides:
  - ScoreGapMaterialResponse.skill
  - ScoreGapMaterialResponse.opp_skill
  - ScoreGapMaterialResponse.skill_diff_p_value
  - ScoreGapMaterialResponse.skill_diff_ci_low
  - ScoreGapMaterialResponse.skill_diff_ci_high
  - MaterialRow.diff_p_value
  - MaterialRow.diff_ci_low
  - MaterialRow.diff_ci_high
affects:
  - app/schemas/endgames.py
  - app/services/endgame_service.py
  - tests/test_endgame_service.py
  - frontend/src/types/endgames.ts
tech-stack:
  added: []
  patterns:
    - Backend-side per-card sig test (D-06 site choice)
    - Mirror identity inversion via dedicated per-bucket helper (NOT chess-score variance)
    - Strict opp-side gating (D-05) — distinct from Phase 85.1 min-of-both gate
key-files:
  created: []
  modified:
    - app/schemas/endgames.py
    - app/services/endgame_service.py
    - tests/test_endgame_service.py
    - frontend/src/types/endgames.ts
decisions:
  - "D-06 site choice: backend, on MaterialRow (single source of truth, no frontend math)"
  - "Per-bucket diff uses compute_per_bucket_diff_test (headline-rate variance), NOT compute_score_difference_test (chess-score variance)"
  - "Strict opp-side gate at per-bucket helper — asymmetric (D-05): opp_row.N >= 10 governs, user_N is allowed below 10"
metrics:
  duration: "~25 min"
  completed: "2026-05-14"
requirements:
  - SEC2-03
  - SEC2-06
  - SEC2-07
  - SEC2-08
---

# Phase 86 Plan 02: Wire Skill + Per-Bucket Diff Helpers Summary

Eight new wire fields (5 top-level Skill + 3 per-MaterialRow diff) populated by
`_compute_score_gap_material` via the Plan 01 math helpers
(`compute_skill_diff_test`, `compute_per_bucket_diff_test`). Frontend TS types
mirror the new shape character-for-character; downstream wave-3..5 frontend
plans consume the wire and never recompute the math.

## What Was Built

- `MaterialRow` (`app/schemas/endgames.py`) gets 3 additive `float | None`
  fields: `diff_p_value`, `diff_ci_low`, `diff_ci_high`. Each defaults to
  `None` so existing fixtures that construct rows without these kwargs keep
  working (mirrors the Phase 85.1 `score_difference_*` additive pattern).
- `ScoreGapMaterialResponse` (`app/schemas/endgames.py`) gets 5 additive
  `float | None` Skill fields: `skill`, `opp_skill`, `skill_diff_p_value`,
  `skill_diff_ci_low`, `skill_diff_ci_high`. Same `= None` default pattern.
- `_compute_score_gap_material` (`app/services/endgame_service.py`) is
  augmented with TWO new helper invocations:
  1. **Aggregate Skill diff** — a single `compute_skill_diff_test(...)` call
     inserted AFTER the `rows_by_game` loop populates the per-bucket W/D/L/N
     accumulators and BEFORE the per-bucket `material_rows` construction
     loop. Opp arguments are the USER's mirror-bucket rows
     (`opp_conv_row = recov_row`, `opp_parity_row = parity_row`,
     `opp_recov_row = conv_row`) — the helper inverts via
     `1 − userRate(opp_row)` internally per Plan 01.
  2. **Per-bucket diff** — a `compute_per_bucket_diff_test(...)` call inside
     the existing `material_rows` loop (3 invocations total, one per
     bucket). User row and opp row are both pulled from the same
     `bucket_wins/draws/losses/games` accumulators using the existing `swap`
     dict. The helper's built-in `opp_row.N < CONFIDENCE_MIN_N (=10)` gate
     enforces D-05 strict-opp-side gating at the call site without an extra
     guard.
- `ScoreGapMaterialResponse(...)` constructor at the end of the function
  appends `skill=skill, opp_skill=opp_skill, skill_diff_p_value=skill_p,
  skill_diff_ci_low=skill_ci_low, skill_diff_ci_high=skill_ci_high`. The
  `MaterialRow(...)` constructor inside the loop appends `diff_p_value=diff_p,
  diff_ci_low=diff_ci_low_v, diff_ci_high=diff_ci_high_v`.
- Existing Phase 85.1 `compute_score_difference_test` call site at lines
  803-812 (SEC1-08 chess-score test on endgame-vs-non-endgame totals) is
  untouched — different accumulator, different math, different semantics.
- `frontend/src/types/endgames.ts` mirrors the new wire shape: `MaterialRow`
  gets 3 `number | null` fields and `ScoreGapMaterialResponse` gets 5
  `number | null` fields. Field names match Python schema
  character-for-character.
- 5 new pytest cases: 2 schema-defaults tests in
  `TestPValueReliabilityMinNConstantAndSchemaDefaults` (`MaterialRow` and
  `ScoreGapMaterialResponse` defaults for the new fields), plus 3 end-to-end
  tests in `TestSkillDiffTestWireFields` covering schema-presence on a
  fully-populated fixture, n_active < 2 gating, and the asymmetric
  strict-opp-side gating behavior at the per-bucket helper.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Extend ScoreGapMaterialResponse + MaterialRow schema | 2f909a0b | app/schemas/endgames.py, tests/test_endgame_service.py |
| 2 | Wire compute_skill_diff_test + compute_per_bucket_diff_test in _compute_score_gap_material | 89bf359e | app/services/endgame_service.py |
| 3 | Add pytest coverage for the 8 new wire fields + gating boundaries | ec0d004d | tests/test_endgame_service.py |
| 4 | Mirror new fields into frontend TS types | b8d8edb1 | frontend/src/types/endgames.ts |

## Verification

- `uv run pytest tests/test_endgame_service.py tests/services/test_score_confidence.py` → 350 passed
- `uv run pytest tests/test_endgame_service.py -k "skill or diff_p_value or diff_ci"` → 26 selected, all pass
- `uv run pytest tests/test_endgame_service.py::TestSkillDiffTestWireFields` → 17 passed (3 new + 14 inherited)
- `uv run pytest tests/test_endgame_service.py::TestPValueReliabilityMinNConstantAndSchemaDefaults` → 5 passed (2 new Phase 86 + 3 Phase 85.1 baseline)
- `uv run ruff check app/schemas/endgames.py app/services/endgame_service.py tests/test_endgame_service.py` → All checks passed
- `uv run ruff format --check app/schemas/endgames.py app/services/endgame_service.py tests/test_endgame_service.py` → 3 files already formatted
- `uv run ty check app/ tests/` → All checks passed
- `cd frontend && npx tsc --noEmit` → exit 0 (no output)

## Deviations from Plan

**Tooling friction (process, not implementation).** Initial attempts to use
the `Edit` tool on `tests/test_endgame_service.py` and `app/schemas/endgames.py`
produced edits that were visible to the agent's `Read` tool but not to disk
(verified via `git status`, `wc -l`, `md5sum`, and direct `cat` from Bash —
all showed the original unchanged file). This appears to be a sandbox
overlay issue specific to this worktree session. Resolved by re-applying all
file modifications via Bash heredocs and `python3 -c '...'` scripts, which
persisted correctly. No semantic change to the planned implementation; just
a longer path to the same end state.

No semantic deviations. The plan was followed exactly:
- 5 Skill fields + 3 per-row diff fields added to schema with `= None` defaults.
- Helper invocation site is between the `rows_by_game` loop and the
  `material_rows` construction loop, exactly as the plan specified.
- Per-bucket call uses `compute_per_bucket_diff_test` (Plan 01) — NOT
  `compute_score_difference_test` (Phase 85.1).
- Phase 85.1 SEC1-08 call site at lines 803-812 untouched.
- Test cases cover the 3 documented scenarios (fully-populated, n_active < 2,
  sparse-opp asymmetric gate).

## Notes

**D-06 site choice: backend, on MaterialRow** (accepted per CONTEXT
recommendation at planning). Rationale:
1. `_compute_score_gap_material` already has per-bucket W/D/L accumulators in
   scope, so the helper call is essentially free (no new accumulation pass).
2. Using `compute_per_bucket_diff_test` (Plan 01) instead of
   `compute_score_difference_test` (Phase 85.1) gives the math-correct
   per-bucket headline-rate variance: Bernoulli on Conv win indicator,
   Bernoulli on Recov save indicator, trinomial chess-score on Parity. The
   Phase 85.1 helper would have applied chess-score variance to all three
   buckets — wrong for Conv and Recov.
3. Single source of truth: 4 frontend cards (Conv / Parity / Recov / Skill)
   all consume the same backend-computed p-values, eliminating any risk of
   frontend math drift across cards or platforms.

**Strict opp-side gate divergence (D-05).**
`compute_per_bucket_diff_test` gates on `opp_row.N >= CONFIDENCE_MIN_N (=10)`
only — NOT the min-of-both gate used by Phase 85.1's
`compute_score_difference_test`. D-05 explicitly specified the opp-side n>=10
baseline as the floor (the user-side rate is already surfaced on the gauge
regardless of N). This creates asymmetric behavior at the per-bucket level:
e.g. a user with 8 conversion games + 80 recovery games will see the
conversion row's `diff_p_value` populated (because opp_row = recov, N=80
passes), while the recovery row's `diff_p_value` is None (because opp_row =
conv, N=8 < 10). Test
`test_score_gap_material_skill_gated_below_opponent_baseline` pins this
asymmetric behavior explicitly.

**Phase 86 plan-checker BLOCKERs.** The plan's `<objective>` section
documented two BLOCKER findings from the plan-checker pass:
1. Per-row diff fields MUST use `compute_per_bucket_diff_test` (Plan 01) —
   not `compute_score_difference_test` (Phase 85.1). The latter treats two
   W/D/L tuples as independent cohorts and would give diff=0 for parity
   self-mirror, hiding the headline signal.
2. Variance MUST be per-bucket headline-rate variance (Bernoulli on Conv win,
   Bernoulli on Recov save, trinomial on Parity), not chess-score variance on
   all three buckets.

Both are pinned by Plan 01 regression tests
(`test_skill_diff_uses_per_bucket_headline_variance_not_chess_score_variance`,
`test_parity_self_mirror_produces_nontrivial_diff`); this plan just wires
the already-correct helpers and adds wire-level coverage.

## Self-Check: PASSED

- FOUND: app/schemas/endgames.py (Task 1 changes, +29 LOC)
- FOUND: app/services/endgame_service.py (Task 2 changes, +66 LOC)
- FOUND: tests/test_endgame_service.py (Task 1 + Task 3 changes, +245 LOC across 5 tests)
- FOUND: frontend/src/types/endgames.ts (Task 4 changes, +14 LOC)
- FOUND commit 2f909a0b (feat 86-02 schema fields + schema-defaults tests)
- FOUND commit 89bf359e (feat 86-02 wire helpers in _compute_score_gap_material)
- FOUND commit ec0d004d (test 86-02 Skill + per-bucket wire-field coverage)
- FOUND commit b8d8edb1 (feat 86-02 frontend TS types mirror)
