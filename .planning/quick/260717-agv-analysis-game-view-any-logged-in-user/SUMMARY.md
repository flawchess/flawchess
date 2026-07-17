---
slug: 260717-agv
title: Analysis game-view accessible to any logged-in user
type: quick
status: complete
date: 2026-07-17
---

# Summary

Relaxed the analysis-page game-view from owner-scoped to any-logged-in-user.
`/analysis?game_id=X` now loads for any authenticated user, not just the game's
owner.

## What changed

- **`get_library_game`** (service + router): dropped the requester-ownership
  IDOR guard and the `user_id` param. The service fetches the game, derives
  `owner_id = game.user_id`, and scopes all batch queries (flaws, positions,
  evals, active-eval-status, best-moves) to the owner. Returns 404 only when the
  game does not exist.
- **`fetch_tactic_lines`** (repo) + **`get_tactic_lines`** (router): dropped the
  `user_id` param and the `GameFlaw.user_id` / `GamePosition.user_id` filters.
  `game_id` (games.id PK) is globally unique and determines the owner, so
  `(game_id, ply)` resolves the owner's flaw/PV without a requester filter. This
  keeps the "expand tactic line" chip working when inspecting another user's game.
- Both endpoints keep `current_active_user` as the "logged in" gate.
- Tests: removed `user_id=` from all call sites; flipped the three cross-user
  IDOR tests (service `get_library_game`, router `GET /library/games/{id}`,
  router tactic-lines) from expect-None/404 to expect-card/200.

## Scope / blast radius

`useLibraryGame` and `useTacticLines` are used **only** by `Analysis.tsx`. The
Library "Games" list (`get_library_games`, plural) stays owner-scoped and was not
touched. No frontend change: game mode is param-driven and already renders an
error branch on fetch failure.

## Verification

- ruff format + ruff check + ty check: clean.
- `uv run pytest -n auto` over the 4 affected files: **121 passed**.

## Note

game_ids are sequential integers, so any logged-in user can now enumerate any
game's full analysis. Intentional and explicitly requested (scouting/sharing);
auth is still required.
