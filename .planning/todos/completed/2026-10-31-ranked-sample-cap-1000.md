---
status: pending
created: 2026-10-31
source: 243-UAT (out-of-opening popover copy review)
phase_origin: 243
priority: medium
run_as: /gsd-quick, after phase 243 is squash-merged to main
---

# Lower the ranked-sample cap from 3000 to 1000 games per time control

## Why

`RECENT_GAMES_PER_TC_CAP = 3000` (`app/services/canonical_slice_sql.py`) bounds the user side of
every peer-ranked metric (endgame ranked stats, out-of-opening worse/better). The benchmark
ingest already stops at 1000 games per user per TC: on 2026-10-31 no benchmark peer had more
than 1000 games in any TC (bullet/blitz p50 ≈ 1000). So the user basis is up to 3× longer than
the peer basis it is ranked against, and an improving heavy player is dragged back by stale
games. A cap of 1000 makes both sides "most recent 1000 games in the last 36 months".

Prod scale (2026-10-31, non-guest, rated, last 36 months, ≥30 games, no Elo filter so an upper
bound): 186 of 926 user-TC pairs exceed 1000 (bullet 26/76, blitz 89/343, rapid 70/425,
classical 1/82). 1000 games still gives about ±3 pp 95% CI on a 30% rate.

## Scope

- `RECENT_GAMES_PER_TC_CAP = 1000` in `app/services/canonical_slice_sql.py`, and the mirrored
  frontend constant in `frontend/src/components/openings/stats/outOfOpeningCopy.ts`.
- Peer CDFs need no rebuild (no benchmark user exceeds 1000). Verify once by regenerating
  and diffing, or by re-running the max-games-per-TC query against the benchmark DB.
- Recompute persisted per-user values for affected users: Stage B
  (`user_benchmark_percentiles_service.compute_stage_b`) and `user_rating_anchors`
  (one-off backfill script over users with >1000 games in any TC).
- Bump the insights cache version in `app/services/insights_llm.py` (v48 → v49) and fix
  "~3000 games per TC" in `app/prompts/endgame_insights.md`.
- Copy: `frontend/src/components/endgames/EndgameStatsTab.tsx` ("up to 3000 games"),
  `RankedMetricPopover`, the out-of-opening disclosure, plus docstrings that say "3000"
  (`canonical_slice_sql.py`, `endgame_ranked_service.py`, `routers/openings.py`,
  `routers/endgames.py`, `models/user_rating_anchors.py`, `schemas/endgames.py`).
- Tests that pin 3000.

## Out of scope

- The import `game_cap` setting (1000/3000/5000, `user_import_settings`): that is the
  import budget, not the ranking window.
