---
quick_id: 260515-wye
slug: fix-endgame-skill-gauge-regression
status: complete
date: 2026-05-15
---

# Quick 260515-wye: Fix Endgame Skill gauge regression — Summary

## What changed

Restored the rate-based Endgame Skill composite that Phase 87.2 D-05
accidentally deleted alongside the peer-diff fields. The Endgame Skill
gauge had been aliased onto `section2_score_gap_skill_mean` (the new ΔES
bullet value), so the gauge needle was plotting a ±5pp signal on a 0–100%
scale — pinned to the lower edge.

## Files touched

- `app/schemas/endgames.py` — new field `endgame_skill_rate_mean: float | None`
  on `ScoreGapMaterialResponse` (distinct from `section2_score_gap_skill_mean`).
- `app/services/endgame_service.py` — compute `endgame_skill_rate_mean` in
  `_compute_score_gap_material` as the equal-weighted mean of
  `bucket_score[b]` over active buckets (`bucket_games[b] >= CONFIDENCE_MIN_N`).
  `None` when zero active. 8 lines, inline — no helper warranted.
- `frontend/src/types/endgames.ts` — TS mirror.
- `frontend/src/components/charts/EndgameMetricsSection.tsx:172` —
  `skill={data.endgame_skill_rate_mean}` (was `section2_score_gap_skill_mean`).
- `frontend/src/components/charts/EndgameSkillCard.tsx` — InfoPopover now
  acknowledges both surfaces: gauge = absolute rate composite, bullet =
  performance vs Stockfish baseline.
- `tests/test_endgame_service.py` — new `TestEndgameSkillRateMean` class
  (5 tests: 3-active, 2-active drop-sparse, below-floor → None, empty rows,
  independence-from-ΔES regression guard).
- `frontend/src/components/charts/__tests__/EndgameMetricsSection.test.tsx`
  — fixture default sets `endgame_skill_rate_mean: 0.55`; empty-state test
  updated to set both rate + ΔES skill fields to null (the gauge now drives
  the empty state via the rate field); new regression test asserts the
  bullet renders the ΔES value (-2%) when the rate field is 0.5.

## Quality gates

- `uv run pytest -q` → 1542 passed, 6 skipped (was 1523 — +19 from new tests).
- `uv run ty check app/ tests/` → clean.
- `npm test --run` → 431 passed (was 430 — +1 from new regression test).
- `npx tsc --noEmit` → clean.
- `npm run knip` → clean.
- `npm run build` → success.

Pre-existing ruff errors in `tests/test_endgame_service.py` at lines 5021
(unused `gid`) and 5278 (unused `math` import) and pre-existing format
drift in three test files were verified to predate this change (`git stash`
confirms identical output on `main`) — leaving for a separate cleanup.

## Follow-ups (not in this quick task)

Benchmark calibration of the 4 `section2_score_gap_*` ZoneSpec entries —
the placeholder `(-0.05, +0.05)` bands are still in
`app/services/endgame_zones.py`. The pooled-by-bucket IQR values are in
`reports/benchmarks-latest.md §3.4.4`; a separate session can roll them
into `ZONE_REGISTRY` and regenerate `frontend/src/generated/endgameZones.ts`.

## Verification (deferred to user)

Smoke-check via `bin/run_local.sh` that the gauge needle and the bullet
value differ on an account with real data, and the gauge sits where it sat
pre-Phase 87.2.
