---
quick_id: 260515-wye
slug: fix-endgame-skill-gauge-regression
date: 2026-05-15
files_modified:
  - app/schemas/endgames.py
  - app/services/endgame_service.py
  - frontend/src/types/endgames.ts
  - frontend/src/components/charts/EndgameMetricsSection.tsx
  - frontend/src/components/charts/EndgameSkillCard.tsx
  - tests/test_endgame_service.py
  - frontend/src/components/charts/__tests__/EndgameSkillCard.test.tsx
---

# Quick 260515-wye: Fix Endgame Skill gauge regression (Phase 87.2 follow-up)

## Bug

`frontend/src/components/charts/EndgameMetricsSection.tsx:172` feeds
`data.section2_score_gap_skill_mean` (ΔES bullet value) to the `skill={}` prop
on `EndgameSkillCard`. The card renders the gauge via
`gaugeValue = (skill ?? 0) * 100`, so the gauge needle plots the ΔES Score
Gap (range ≈ ±0.05) instead of the rate-based Endgame Skill composite
(range 0–1). The gauge currently shows a near-zero value glued to the lower
edge of `ENDGAME_SKILL_ZONES`.

## Root cause

Phase 87.2 D-05 schema deletion removed the rate-based composite `skill`
field from `ScoreGapMaterialResponse` together with the peer-diff family
(`opp_skill`, `skill_diff_p_value/ci_low/ci_high`). The diff family was the
intended deletion target — the composite rate was load-bearing for the
gauge. Plan 03 aliased the gauge onto the new ΔES field to make it render
something.

## Fix

Restore the rate-based composite as a fresh schema field
(`endgame_skill_rate_mean`) and wire it to the gauge. Keep the new ΔES
field powering the bullet — those are correct.

### Backend

1. `app/schemas/endgames.py`: add `endgame_skill_rate_mean: float | None = None`
   to `ScoreGapMaterialResponse`, near the existing
   `section2_score_gap_skill_*` block. Doc comment explains it's the
   rate-based composite that drives the Endgame Skill gauge (distinct from
   `section2_score_gap_skill_mean` which is the ΔES bullet value).
2. `app/services/endgame_service.py`: in `_compute_score_gap_material`,
   compute `endgame_skill_rate_mean` from `bucket_score` and `bucket_games`
   as the equal-weighted mean over active buckets where
   `bucket_games[b] >= CONFIDENCE_MIN_N`. Return `None` when zero buckets
   are active. Pass it into the `ScoreGapMaterialResponse` constructor.
   Place the helper inline (5–10 lines) — too small for a separate function.

### Frontend

3. `frontend/src/types/endgames.ts`: add `endgame_skill_rate_mean: number | null`
   to the `ScoreGapMaterialResponse` TS type, beside the existing
   `section2_score_gap_skill_*` mirrors.
4. `frontend/src/components/charts/EndgameMetricsSection.tsx:172`: change
   `skill={data.section2_score_gap_skill_mean}` →
   `skill={data.endgame_skill_rate_mean}`. Leave the `scoreGapMean` prop
   pointing at the ΔES field (correct as-is).
5. `frontend/src/components/charts/EndgameSkillCard.tsx`: update the
   `InfoPopover` body (lines ~101-119) to acknowledge the bullet beneath
   the gauge in one extra short paragraph. Gauge = absolute rate composite
   (Conversion + Parity + Recovery rates, equal-weighted); bullet = Skill
   Score Gap (performance vs Stockfish baseline). Keep the existing
   "calibrated bands don't shift with filters" line. No methodology jargon
   per `feedback_popover_copy_minimalism.md`.

### Tests

6. `tests/test_endgame_service.py`: extend the Section 2 / skill aggregation
   test fixture group with a case asserting `endgame_skill_rate_mean` equals
   `mean(bucket_score[b] for b in active)` and that it's `None` when all
   buckets are below the floor. Active-bucket fallback (2 active → divide by
   2, 1 active → divide by 1) covered by a parameterized case.
7. `frontend/src/components/charts/__tests__/EndgameSkillCard.test.tsx`: the
   existing tests mostly pass `skill={...}` directly. Update the
   `EndgameMetricsSection.test.tsx` integration test (or add a focused case
   if absent) that confirms a fixture with `endgame_skill_rate_mean = 0.5`
   and `section2_score_gap_skill_mean = -0.02` renders the gauge at 50% and
   the bullet near -2% — they must be visibly independent.

## Out of scope

- Benchmark calibration of the 4 `section2_score_gap_*` ZoneSpec entries
  (`app/services/endgame_zones.py`). The IQR values are in
  `reports/benchmarks-latest.md §3.4.4`; rolling them into
  `ZONE_REGISTRY` + regenerating TS is a separate task.

## Verification

- `uv run pytest -q` clean.
- `uv run ty check app/ tests/` clean.
- `uv run ruff check . && uv run ruff format --check .` clean.
- `npm test`, `npx tsc --noEmit`, `npm run knip`, `npm run build` clean.
- Smoke-check with `bin/run_local.sh`: gauge needle and bullet value differ
  on an account with real data; gauge sits where it sat pre-87.2.
