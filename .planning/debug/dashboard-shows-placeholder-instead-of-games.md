---
status: diagnosed
trigger: "Dashboard shows placeholder message instead of unfiltered games list on load"
created: 2026-03-14T00:00:00Z
updated: 2026-03-14T00:00:00Z
---

## Current Focus

hypothesis: The dashboard requires a manual "Filter" click to trigger any analysis call; there is no API endpoint or frontend logic to list games without a position hash filter
test: Traced frontend render logic and backend API contract
expecting: Confirm that analysisResult starts as null and no auto-fetch exists
next_action: Return diagnosis

## Symptoms

expected: User sees their unfiltered games list when first loading the dashboard
actual: Dashboard shows "Play moves on the board and click Filter to see your stats" placeholder
errors: None (not an error, a missing feature path)
reproduction: Log in with imported games, navigate to dashboard
started: By design - never showed unfiltered games

## Eliminated

(none needed - root cause identified on first pass)

## Evidence

- timestamp: 2026-03-14
  checked: Dashboard.tsx rightColumn render logic (lines 390-447)
  found: When analysisResult === null (initial state), the placeholder message is shown. analysisResult is only set by handleAnalyze which requires user to click Filter button.
  implication: No auto-fetch of games on mount

- timestamp: 2026-03-14
  checked: handleAnalyze function (lines 87-106)
  found: Always sends target_hash via chess.getHashForAnalysis(filters.matchSide). This is a Zobrist hash of the current board position. The analysis is a mutation (useMutation), not a query - it never runs automatically.
  implication: Games are only fetched through position-hash-based analysis

- timestamp: 2026-03-14
  checked: AnalysisRequest schema (app/schemas/analysis.py line 12)
  found: target_hash is a required int field with no default. The endpoint POST /analysis/positions always requires a position hash.
  implication: Backend API has no way to return "all games" without a position filter

- timestamp: 2026-03-14
  checked: game_repository.py
  found: Only has bulk_insert_games, count_games_for_user, bulk_insert_positions. No paginated list/query function for games.
  implication: No repository method exists to list games without position filtering

- timestamp: 2026-03-14
  checked: Backend routers
  found: No /games list endpoint exists. Only /games/count (returns count) and /analysis/positions (requires hash).
  implication: A new endpoint or modified endpoint is needed

## Resolution

root_cause: |
  Three layers prevent showing unfiltered games on dashboard load:

  1. **Frontend (Dashboard.tsx)**: `analysisResult` state starts as `null` and is only populated
     when user clicks "Filter". The render logic (line 392) shows the placeholder when
     `analysisResult === null`. No `useEffect` or `useQuery` fetches games on mount.

  2. **Frontend (useAnalysis.ts)**: Uses `useMutation` (manual trigger), not `useQuery` (auto-fetch).
     The mutation always requires `target_hash` in the request body.

  3. **Backend (AnalysisRequest schema)**: `target_hash: int` is a required field with no default
     and no `None` option. The repository layer (`_build_base_query`) always includes
     `hash_column == target_hash` in the WHERE clause.

  4. **Backend (no games list endpoint)**: No `GET /games` or similar endpoint exists that returns
     paginated games without a position filter. `game_repository` only has count and bulk-insert.

fix: (not applied - diagnosis only)
verification: (not applicable)
files_changed: []
