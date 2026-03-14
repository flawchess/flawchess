---
status: diagnosed
phase: 09-rework-the-games-list-with-game-cards-username-import-and-improved-pagination
source: [09-01-SUMMARY.md, 09-02-SUMMARY.md, 09-03-SUMMARY.md]
started: 2026-03-14T16:10:00Z
updated: 2026-03-14T16:45:00Z
---

## Current Test

[testing complete]

## Tests

### 1. Cold Start Smoke Test
expected: Kill any running backend/frontend servers. Run `uv run alembic upgrade head` (migration with move_count backfill should complete). Start backend and frontend. App loads without errors, login works, and dashboard page renders.
result: pass

### 2. Game Cards Layout
expected: After running an analysis query, games display as full-width cards (not a table). Each card has a colored left border accent: green for wins, gray for draws, red for losses. Cards show result badge, opponent name, color indicator (white circle or black circle), ratings, opening name with ECO code, time control, date, move count, and a link to the game on the platform.
result: issue
reported: "The player username should be shown, not only the opponent name. It's still missing in the games table. Make sure it's imported (it may change on chess.com, you can't assume the username of old games is the same as now). Display the players, the color played, and the rating on two lines"
severity: major

### 3. Truncated Pagination
expected: With enough games to produce many pages (at 20 per page), the pagination control shows first page, last page, a window of pages around the current page, and ellipsis (...) for gaps between page ranges. Clicking a page number navigates to that page and scrolls to the top of the results.
result: issue
reported: "It works, but I still see the 'Play moves on the board and click Filter to see your stats' message, instead of the unfiltered games list"
severity: major

### 4. Import Modal - First-Time User
expected: Open the import modal as a user who has never imported. Both chess.com and lichess username fields are shown simultaneously (no platform toggle). Enter a username and import. After import completes, the username should be saved to the backend profile.
result: pass

### 5. Import Modal - Returning User (Sync View)
expected: After at least one import, open the import modal again. Instead of empty text fields, a "sync view" appears showing the stored username(s) with per-platform Sync buttons for quick re-import. An option to edit/add usernames (switch to input view) should also be available.
result: pass

### 6. Profile Endpoint
expected: After importing, GET /users/me/profile (or check via the import modal sync view) returns the chess.com and/or lichess usernames that were used during import. Usernames persist across sessions (no localStorage dependency).
result: skipped
reason: Can't test API endpoint directly without disabling auth

## Summary

total: 6
passed: 3
issues: 2
pending: 0
skipped: 1

## Gaps

- truth: "Game cards show both player usernames, color played, and ratings on two lines"
  status: failed
  reason: "User reported: The player username should be shown, not only the opponent name. It's still missing in the games table. Make sure it's imported (it may change on chess.com, you can't assume the username of old games is the same as now). Display the players, the color played, and the rating on two lines"
  severity: major
  test: 2
  root_cause: "Game model stores user-relative fields (opponent_username, user_color) but discards the per-game username. Normalization extracts white/black usernames from API but only persists opponent_username."
  artifacts:
    - path: "app/models/game.py"
      issue: "Missing white_username, black_username, white_rating, black_rating columns"
    - path: "app/services/normalization.py"
      issue: "Extracts both usernames but only persists opponent_username"
    - path: "app/schemas/analysis.py"
      issue: "GameRecord missing fields for both player names/ratings"
    - path: "frontend/src/types/api.ts"
      issue: "TypeScript type missing both-player fields"
    - path: "frontend/src/components/results/GameCard.tsx"
      issue: "Displays only opponent_username"
  missing:
    - "Add white_username, black_username, white_rating, black_rating to games table"
    - "Persist both player usernames during normalization"
    - "Expose new fields in GameRecord schema"
    - "Redesign GameCard to show both players on two lines"
    - "Migration with backfill (existing games need re-derive from opponent_username + user_color)"
  debug_session: ".planning/debug/game-card-missing-usernames.md"

- truth: "Dashboard shows unfiltered games list by default instead of placeholder message"
  status: failed
  reason: "User reported: It works, but I still see the 'Play moves on the board and click Filter to see your stats' message, instead of the unfiltered games list"
  severity: major
  test: 3
  root_cause: "No path to display games without position hash. AnalysisRequest.target_hash is required, no games-list endpoint exists, and the frontend only populates analysisResult on explicit Filter click."
  artifacts:
    - path: "frontend/src/pages/Dashboard.tsx"
      issue: "analysisResult === null triggers placeholder; no auto-fetch on mount"
    - path: "frontend/src/hooks/useAnalysis.ts"
      issue: "Mutation-only, requires target_hash"
    - path: "app/schemas/analysis.py"
      issue: "target_hash is required int, not optional"
    - path: "app/repositories/analysis_repository.py"
      issue: "All queries require target_hash"
    - path: "app/repositories/game_repository.py"
      issue: "Missing paginated list function"
  missing:
    - "New GET /games paginated endpoint (no position hash required)"
    - "Game repository paginated list function"
    - "Frontend useQuery hook for auto-fetching games on mount"
    - "Dashboard shows games list by default, switches to position-filtered on Filter click"
  debug_session: ".planning/debug/dashboard-shows-placeholder-instead-of-games.md"
