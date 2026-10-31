---
quick_id: 261031-et9
slug: retune-gem-great-maia-thresholds-to-0-30
date: 2026-10-31
status: complete
commits: [7cd14f219, 34489868b, 702494c0b]
---

# Quick 261031-et9 Summary: gem/great Maia ceilings 0.20/0.50 -> 0.30/0.70

Executed inline (mechanical change; no planner/executor subagents).

- **Backend** (`7cd14f219`): `GEM_MAIA_MAX_PROB` 0.30, `GREAT_MAIA_MAX_PROB` 0.70 in
  `app/services/best_move_candidates.py`, read by both the Python classifier and its SQL
  twin. Tests moved to band values that tell the old and new cutoffs apart (great fixtures
  at 0.50/0.60, neither at 0.80; the game-640125 case at maia 0.257 is now gem before the guard).
- **Frontend** (`34489868b`): mirrored constants in `gemMove.ts` (live-engine fallback only),
  copy in FlawFilterControl and MoveStats ("~3 in 10", "3 in 10 to 7 in 10"), comments in
  theme.ts and GreatMoveIcon.tsx, gemMove tests.
- **Docs** (`702494c0b`): CHANGELOG [Unreleased] bullet; SEED-159 definitions recap.

Verification:
- Mutation check: reverting the backend constants to 0.20/0.50 fails 4 tests (Python
  classifier + SQL-twin repository/router filters); restored afterwards.
- Backend: test_best_move_candidates, test_library_service, test_library_repository,
  test_library_router, test_guest_cleanup_service pass; ruff + ty clean on touched files.
- Frontend: lint, build (tsc -b), full vitest suite (5665 tests) pass.
- Full pre-merge gate NOT run (direct small main commits; run it before the next release).

Expected effect on prod (from 2026-10-31 data): gems 0.051 -> ~0.10 per player-game,
greats 0.21 -> ~0.44. No backfill needed; the tier is computed at query time.
