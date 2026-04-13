# Quick Task 260413-pwv: Conversion / Even / Recovery labels + 4-ply preservation

**Completed:** 2026-04-13
**Branch:** gsd/phase-55-time-pressure-performance-chart

## Scope

Two paired changes to the Endgame Score Gap & Material Breakdown section (Endgames → Stats tab):

1. **Apply the 4-ply preservation rule to material-advantage classification.**
   Previously, a game was bucketed purely on `user_material_imbalance` at endgame entry, so trades at the boundary classified games as "ahead" or "behind" even when the imbalance immediately resolved. Now the bucket also requires `user_material_imbalance_after` (measured 4 plies in) to pass the same threshold — matching the existing persistence rule used by conversion/recovery sequence stats.

2. **Rename buckets `ahead / equal / behind` → `conversion / even / recovery`.**
   The chess-native terms carry the task the user is actually solving ("did I finish won positions?" / "did I save lost ones?") and unify the vocabulary already established in the Endgame Stats tab.

Games whose imbalance does not persist fall into `even` rather than being dropped, preserving game totals.

## Files changed

- `app/schemas/endgames.py` — `MaterialBucket` literal + docstrings.
- `app/services/endgame_service.py` — `_MATERIAL_BUCKET_LABELS`, `_compute_score_gap_material` bucket logic + ordering.
- `frontend/src/types/endgames.ts` — `MaterialBucket` union.
- `frontend/src/components/charts/EndgameScoreGapSection.tsx` — `WARNING_ZONES` keys, InfoPopover text.
- `tests/test_endgame_service.py` — renamed assertions + new persistence-required tests.
- `tests/test_endgames_router.py` — updated expected bucket list.

## Out of scope (will be reworked in later phases)

- `EndgameConvRecovTimelineChart` (conv/recov timeline) — kept as-is; reworked when Endgame Skill is revisited.
- `EndgameGaugesSection` (conversion/recovery gauges) — kept as-is; reworked with Endgame Skill.
- `_aggregate_endgame_stats` per-type conversion/recovery — unchanged (still fed into gauges + Endgame Skill).

Short-term there will be visible overlap between the renamed material-breakdown buckets (Conversion/Recovery) and the existing "Conversion and Recovery" gauges section. This is accepted per user direction.

## Verification

- `uv run ty check app/ tests/` — passes (0 errors).
- `uv run pytest tests/test_endgame_service.py` — 101 passed.
- `uv run pytest tests/test_endgames_router.py` — 15 passed.
- `npm run lint` — clean.
- `npm run build` — succeeds.
