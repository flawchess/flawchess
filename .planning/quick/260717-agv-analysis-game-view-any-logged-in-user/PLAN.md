---
slug: 260717-agv
title: Analysis game-view accessible to any logged-in user
type: quick
status: complete
---

# Analysis game-view accessible to any logged-in user

## Problem

Opening a game on the analysis page by url (e.g. `/analysis?game_id=640125`)
only works when logged in as the game's owner. `GET /library/games/{game_id}`
(and the tactic-line expansion `GET /library/flaws/{game_id}/{ply}/tactic-lines`)
enforced an owner IDOR guard, returning 404 for any other user. Requirement:
allow any authenticated user to inspect any game by url (opponent scouting,
game sharing).

## Approach

Relax both analysis-view endpoints from owner-scoped to logged-in-only. The
requester's identity does not determine WHAT is returned — the data always
belongs to the game's OWNER (flaws/positions/evals live under `game.user_id`).
So scope downstream queries to the owner, keep `current_active_user` as the
"logged in" gate, and drop the requester-ownership comparison.

Blast radius is contained: `useLibraryGame` / `useTacticLines` are used ONLY by
`Analysis.tsx`. The Library "Games" tab uses the plural list endpoint
(`get_library_games`), which stays owner-scoped and is untouched.

## Changes

- `app/services/library_service.py` — `get_library_game(session, game_id)`:
  drop `user_id` param + ownership check; derive `owner_id = game.user_id` and
  scope all batch queries to the owner. Return None only when the game is missing.
- `app/routers/library.py` — `get_library_game`: stop passing `user_id`; keep
  the `current_active_user` auth gate. `get_tactic_lines`: stop passing `user_id`.
- `app/repositories/library_repository.py` — `fetch_tactic_lines(session, game_id, ply)`:
  drop `user_id` param and the `GameFlaw.user_id` / `GamePosition.user_id`
  filters. `game_id` (games.id PK) is globally unique and determines the owner,
  so `(game_id, ply)` resolves the owner's flaw/PV without a requester filter.
- Tests: drop `user_id=` from all call sites; flip the two cross-user IDOR tests
  (service + both routers) from expect-None/404 to expect-card/200.

## Verification

- `uv run ruff format` / `ruff check` / `ty check` — clean.
- `uv run pytest -n auto` over the 4 affected test files — 121 passed.
- Frontend unchanged: Analysis game mode is param-driven (not ownership-gated)
  and already renders the error branch on fetch failure.

## Security note (intentional)

game_ids are sequential integers, so any logged-in user can now enumerate and
view any game's full analysis (moves, evals, flaws, tactic PVs). This is the
explicitly requested behavior and aligns with the documented "scouting
opponents" / sharing use case. Auth (logged-in) is still required — the
endpoints are not public.
