---
status: diagnosed
phase: 15-enhanced-game-import-data
source: [15-01-SUMMARY.md, 15-02-SUMMARY.md]
started: 2026-03-18T20:15:00Z
updated: 2026-03-18T20:20:00Z
---

## Current Test
<!-- OVERWRITE each test - shows where we are -->

[testing complete]

## Tests

### 1. Game Card Time Control Display
expected: Open analysis results for any position with games. Game cards show time control in "Bucket · Exact" format (e.g., "Blitz · 10+5", "Rapid · 15+10"). Both the bucket label and exact time control string appear on the card.
result: issue
reported: "time_control_str has inconsistent values — '180+0' and '180' for same format. The +0 should be removed for consistency. Display should convert base time to minutes and show increment in seconds, e.g. 10+5 for ten minutes and 5 second increment."
severity: minor

### 2. Game Card Termination Reason
expected: Game cards display the termination reason (e.g., "Checkmate", "Resignation", "Timeout"). If a game's termination is "unknown", it should be hidden — no "Unknown" text visible on the card.
result: pass

### 3. Data Isolation on Logout
expected: Log in as one user, run an analysis to populate results. Log out. Log in as a different user (or observe the state after logout). The previous user's analysis results and cached data should NOT appear — the page should be clean with no stale data from the previous session.
result: issue
reported: "I still see the games imported as user A when I log in as user B"
severity: major

### 4. Time Control Classification Fix
expected: After re-importing games (or checking existing imported games), a game with time control "180+0" (3+0) should be classified as "Blitz", not "Bullet". Games under 180s base time (e.g., "120+1") remain "Bullet".
result: pass

### 5. Multi-Username Import
expected: Import games for a username on chess.com (or lichess). Then import a second, different username on the same platform. The second import should fetch that user's full game history independently, not just games since the first user's last import.
result: pass

## Summary

total: 5
passed: 3
issues: 2
pending: 0
skipped: 0

## Gaps

- truth: "Game cards show time control in Bucket · Exact format with consistent formatting"
  status: failed
  reason: "User reported: time_control_str has inconsistent values — '180+0' and '180' for same format. The +0 should be removed for consistency. Display should convert base time to minutes and show increment in seconds, e.g. 10+5 for ten minutes and 5 second increment."
  severity: minor
  test: 1
  root_cause: "Lichess normalizer always constructs '{base}+{increment}' (producing '180+0'), while chess.com passes raw API string (which omits +0). Frontend renders raw stored string with no seconds-to-minutes conversion."
  artifacts:
    - path: "app/services/normalization.py"
      issue: "Lichess path always adds +increment; chess.com passes raw string; no canonical normalization"
    - path: "frontend/src/components/results/GameCard.tsx"
      issue: "Renders time_control_str verbatim — no conversion from seconds to minutes"
  missing:
    - "Normalize time_control_str in both normalizers: drop +0 when increment is 0"
    - "Add formatTimeControl() in GameCard that converts base seconds to minutes and keeps increment in seconds"
  debug_session: ""
- truth: "Logging out clears all cached query data so another user logging in sees only their own data"
  status: failed
  reason: "User reported: I still see the games imported as user A when I log in as user B"
  severity: major
  test: 3
  root_cause: "401 interceptor in client.ts removes token and redirects but never calls queryClient.clear(). All query keys are user-agnostic (no user ID), so cached data from user A collides with user B's queries."
  artifacts:
    - path: "frontend/src/api/client.ts"
      issue: "401 interceptor bypasses logout() — never clears queryClient cache"
    - path: "frontend/src/hooks/useAnalysis.ts"
      issue: "Query keys lack user identifier — cache collides across users"
    - path: "frontend/src/hooks/useStats.ts"
      issue: "Query keys lack user identifier"
    - path: "frontend/src/hooks/usePositionBookmarks.ts"
      issue: "Query key lacks user identifier"
  missing:
    - "401 interceptor must call queryClient.clear() before redirecting"
    - "login() should also call queryClient.clear() to clear residual cache"
    - "Defense-in-depth: include user ID in all query keys so cache never collides across users"
  debug_session: ""
