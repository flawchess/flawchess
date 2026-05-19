---
status: awaiting_human_verify
trigger: "Dashboard shows no games/bookmarks despite data in DB"
created: 2026-03-14T00:00:00Z
updated: 2026-03-14T00:00:00Z
---

## Current Focus

hypothesis: Backend is fully functional; the issue is browser-specific (either stale cache, failed API calls in browser context, or a transient state during testing)
test: Need user to check browser DevTools (Console + Network tab) while loading the dashboard
expecting: Either API calls succeed and games display, or we see specific errors in console/network
next_action: Request human verification with browser DevTools open

## Symptoms

expected: Dashboard shows imported games list, bookmarks are populated, position filter returns matching games
actual: "No games imported yet" message, empty bookmarks, no games after filtering
errors: None reported (no explicit error messages)
reproduction: Log in, navigate to dashboard
started: After phase 09 changes (useGamesQuery, dev auth bypass, optional target_hash)

## Eliminated

- hypothesis: Backend returns wrong data or no data
  evidence: All three endpoints return correct data via curl - /games/count returns {"count":5032}, /analysis/positions returns 5024 games with stats, /position-bookmarks returns 8 bookmarks. Tested both directly (localhost:8000) and through Vite proxy (localhost:5173). Dev auth bypass correctly returns user id=1 who owns all the data.
  timestamp: 2026-03-14

- hypothesis: Dev auth bypass returns wrong user
  evidence: Only one user exists in DB (id=1, email=aimfeld80@gmail.com, is_active=true). Dev bypass queries first active user, which is user 1. User 1 has 5032 games.
  timestamp: 2026-03-14

- hypothesis: Frontend code has logic bug preventing data display
  evidence: Traced all rendering paths in Dashboard.tsx. For "No games imported yet" to show in the default (unfiltered) view, hasNoGames must be true (totalGames !== null && totalGames === 0). But /games/count returns 5032, so totalGames should be 5032 and hasNoGames should be false. The useGamesQuery hook correctly fires a POST to /analysis/positions with {offset:0, limit:20}. The response should populate defaultGames.data with games.
  timestamp: 2026-03-14

- hypothesis: Frontend build has TypeScript errors or compilation issues
  evidence: npm run build completes successfully with zero errors (tsc -b && vite build both pass).
  timestamp: 2026-03-14

- hypothesis: CORS or proxy configuration prevents API calls
  evidence: Vite proxy config correctly forwards /analysis, /games, /position-bookmarks to localhost:8000. CORS middleware allows localhost:5173. Requests through proxy confirmed working via curl.
  timestamp: 2026-03-14

- hypothesis: Pydantic schema rejects the useGamesQuery request body
  evidence: Sending {offset:0, limit:20} to POST /analysis/positions works - target_hash defaults to None, opponent_type defaults to "human", match_side defaults to "full". Returns 5024 human games.
  timestamp: 2026-03-14

## Evidence

- timestamp: 2026-03-14
  checked: Database contents - users table
  found: Single user (id=1, aimfeld80@gmail.com, is_active=true)
  implication: Dev auth bypass unambiguously returns user 1

- timestamp: 2026-03-14
  checked: Database contents - games table
  found: 5032 total games for user_id=1 (5024 human, 8 bot)
  implication: Plenty of data to display

- timestamp: 2026-03-14
  checked: GET /games/count (direct and via proxy)
  found: Returns {"count":5032} both ways
  implication: Game count endpoint works correctly

- timestamp: 2026-03-14
  checked: POST /analysis/positions with {offset:0, limit:5} (direct and via proxy)
  found: Returns full AnalysisResponse with stats (wins:2536, draws:242, losses:2246), 5 games, matched_count:5024
  implication: Analysis endpoint works correctly with no target_hash

- timestamp: 2026-03-14
  checked: GET /position-bookmarks (direct)
  found: Returns 8 bookmarks with labels, target_hash, fen, moves, etc.
  implication: Bookmarks endpoint works correctly

- timestamp: 2026-03-14
  checked: Backend with fake Bearer token
  found: curl with "Authorization: Bearer some-fake-token" still returns data - dev bypass ignores JWT entirely
  implication: Any token in the browser will work; auth is not the issue

- timestamp: 2026-03-14
  checked: Frontend rendering logic in Dashboard.tsx
  found: The "No games imported yet" message appears when hasNoGames is true (totalGames === 0) OR in the position-filtered path when noGamesAtAll is true. For both to trigger, totalGames must be 0 or null AND analysis must return 0 matches.
  implication: Either the API calls are failing silently in the browser, or there's a browser-specific issue (cache, stale JS, network error)

- timestamp: 2026-03-14
  checked: Vite dev server and health endpoint
  found: Both running and responding correctly
  implication: Infrastructure is up

## Resolution

root_cause: Backend fully verified working. Cannot reproduce from CLI. Likely browser-specific issue - need user to check browser DevTools.
fix:
verification:
files_changed: []
