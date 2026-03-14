---
status: resolved
trigger: "Game cards don't show the player's own username — only the opponent name is displayed. The user wants both player usernames shown with color played and ratings on two lines. Also, the player username should be imported per-game."
created: 2026-03-14T00:00:00Z
updated: 2026-03-14T00:00:00Z
---

## Current Focus

hypothesis: white_username and black_username are not stored per-game; the DB only stores opponent_username relative to the user
test: checked Game model, normalization, schema, and frontend
expecting: confirm missing columns
next_action: return diagnosis

## Symptoms

expected: Game cards show both player usernames (white and black) with their ratings on two lines
actual: Only opponent_username is shown; user's own username is not stored per-game and not displayed
errors: none (functional gap, not a crash)
reproduction: View any game card in the dashboard
started: always been this way — the data model was designed user-relative, not game-absolute

## Eliminated

(none needed — root cause identified on first pass)

## Evidence

- timestamp: 2026-03-14
  checked: app/models/game.py — Game model columns
  found: Stores opponent_username, opponent_rating, user_rating, user_color. No white_username, black_username, white_rating, black_rating columns.
  implication: The DB schema is user-relative — it knows "opponent" and "user" but not "white player" and "black player" by name.

- timestamp: 2026-03-14
  checked: app/services/normalization.py — normalize_chesscom_game and normalize_lichess_game
  found: Both functions extract white_username and black_username from API data but only persist opponent_username. The user's own per-game username is discarded.
  implication: The username used at game time (which can change on chess.com) is lost. It cannot be reconstructed later.

- timestamp: 2026-03-14
  checked: app/schemas/analysis.py — GameRecord schema
  found: GameRecord has opponent_username, user_rating, opponent_rating, user_color. No white_username/black_username fields.
  implication: API response cannot provide both player names.

- timestamp: 2026-03-14
  checked: frontend/src/types/api.ts — GameRecord TypeScript type
  found: Mirrors the backend schema exactly — no username fields for both players.
  implication: Frontend has no data to display both usernames.

- timestamp: 2026-03-14
  checked: frontend/src/components/results/GameCard.tsx
  found: Line 1 shows: result badge, color circle, opponent_username, platform link. Line 2 shows: "userRating vs oppRating", opening, time control, date, moves. User's own name is never displayed.
  implication: Even if the data were available, the card layout would need redesign.

## Resolution

root_cause: The data model stores games in a user-relative format (opponent_username, user_rating, user_color) instead of a game-absolute format (white_username, black_username, white_rating, black_rating). The user's per-game username is extracted during import but discarded — only opponent_username is persisted.
fix: (not applied — diagnosis only)
verification: (not applicable)
files_changed: []
