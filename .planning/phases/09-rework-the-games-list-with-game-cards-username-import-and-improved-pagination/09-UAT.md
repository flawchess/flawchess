---
status: complete
phase: 09-rework-the-games-list-with-game-cards-username-import-and-improved-pagination
source: [09-01-SUMMARY.md, 09-02-SUMMARY.md, 09-03-SUMMARY.md, 09-04-SUMMARY.md, 09-05-SUMMARY.md]
started: 2026-03-14T19:00:00Z
updated: 2026-03-14T19:20:00Z
---

## Current Test

[testing complete]

## Tests

### 1. Cold Start Smoke Test
expected: Kill any running backend/frontend servers. Run `uv run alembic upgrade head` (migrations complete). Start backend and frontend. App loads without errors, login works, dashboard renders.
result: pass

### 2. Default Games List on Dashboard
expected: After logging in, the dashboard right column immediately shows your imported games as cards — no "Play moves on the board and click Filter" placeholder. Games appear without clicking Filter or selecting a position.
result: pass

### 3. Game Cards with Both Player Usernames
expected: Each game card shows both player usernames with color circle indicators (○ for white, ● for black) and ratings. Your own username is bolded. Cards have colored left border: green=win, gray=draw, red=loss. Second line shows opening name with ECO code, time control, date, move count, and platform link.
result: issue
reported: "I want the opponent name bolded, not mine. Also, the color circle indicators are not working, I think they are reversed (show white when I played black and vice versa). Always show the white player on the left. In the DB I see redundant fields in the games table, opponent_username, opponent_rating, user_rating, and opponent_rating should be removed, and inferred from user_color and the newer <color>_username and <color>_rating fields"
severity: major

### 4. Truncated Pagination
expected: With enough games to produce many pages (20 per page), the pagination shows first page, last page, a window around the current page, and ellipsis (...) for gaps. Clicking a page number navigates to that page and scrolls to the top of the results.
result: pass

### 5. Position Filter Mode
expected: Play moves on the board and click Filter. The right column switches from the default games list to position-filtered results with WDL bar and filtered game cards. Reset the board — the right column returns to the default (unfiltered) games list.
result: pass

### 6. Import Modal - First-Time User
expected: Open the import modal as a user who has never imported. Both chess.com and lichess username fields are shown simultaneously (no platform toggle). Enter a username and import. After import completes, the username is saved to the backend profile.
result: issue
reported: "It works, but when I import only from one platform, I cannot import from the other platform afterwards. After importing from chess.com, I have a sync button for chess.com, but no import button for lichess. I only see lichess Not set"
severity: major

### 7. Import Modal - Returning User (Sync View)
expected: After at least one import, open the import modal again. A "sync view" appears showing stored username(s) with per-platform Sync buttons for quick re-import. An option to edit/add usernames (switch to input view) is available.
result: pass

## Summary

total: 7
passed: 5
issues: 2
pending: 0
skipped: 0

## Gaps

- truth: "Game cards show white player on left with correct color circles, opponent name bolded; DB has no redundant username/rating fields"
  status: failed
  reason: "User reported: I want the opponent name bolded, not mine. Also, the color circle indicators are not working, I think they are reversed (show white when I played black and vice versa). Always show the white player on the left. In the DB I see redundant fields in the games table, opponent_username, opponent_rating, user_rating, and opponent_rating should be removed, and inferred from user_color and the newer <color>_username and <color>_rating fields"
  severity: major
  test: 3
  artifacts: []
  missing: []

- truth: "After importing from one platform, user can import from the other platform without going through Edit usernames"
  status: failed
  reason: "User reported: It works, but when I import only from one platform, I cannot import from the other platform afterwards. After importing from chess.com, I have a sync button for chess.com, but no import button for lichess. I only see lichess Not set"
  severity: major
  test: 6
  root_cause: "In ImportModal.tsx sync view, lines 180 and 202 conditionally render Sync button only when username is set. Null usernames get 'Not set' text with no interactive element. isFirstTime is false once any single platform is configured, so input view never shown automatically."
  artifacts:
    - path: "frontend/src/components/import/ImportModal.tsx"
      issue: "Sync view lines 180 and 202: no else branch for null usernames — renders 'Not set' with no action button"
  missing:
    - "Add 'Add' button in sync view for unconfigured platforms that switches to input view or inline input"
  debug_session: ".planning/debug/import-modal-second-platform.md"
