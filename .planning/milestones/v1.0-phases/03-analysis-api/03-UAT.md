---
status: testing
phase: 03-analysis-api
source: 03-01-SUMMARY.md, 03-02-SUMMARY.md
started: 2026-03-11T15:30:00Z
updated: 2026-03-11T15:30:00Z
---

## Current Test

number: 1
name: Cold Start Smoke Test
expected: |
  Kill any running server. Start fresh with `uv run uvicorn app.main:app --reload`.
  Server boots without errors. Run: `curl -s http://localhost:8000/docs | head -20`
  The FastAPI docs page loads. The /analysis/positions endpoint appears in the API docs.
awaiting: user response

## Tests

### 1. Cold Start Smoke Test
expected: Kill any running server. Start fresh with `uv run uvicorn app.main:app --reload`. Server boots without errors. The /analysis/positions endpoint appears at http://localhost:8000/docs.
result: [pending]

### 2. Analysis Endpoint Returns Response
expected: With games imported (run import first if needed), POST to the analysis endpoint with a known position hash. Run: `curl -s -X POST http://localhost:8000/analysis/positions -H "Content-Type: application/json" -d '{"target_hash": 0, "match_side": "full"}' | python3 -m json.tool`. Response is valid JSON with `stats` (wins, draws, losses, total, percentages), `games` (list), `matched_count`, `offset`, and `limit` fields.
result: [pending]

### 3. Match Side Filtering
expected: Query with `match_side: "white"` and then `match_side: "black"` using the same `target_hash`. The `matched_count` values may differ because white-piece-only and black-piece-only hashes are independent. Both return valid responses (not errors).
result: [pending]

### 4. Filter Combination
expected: Add filters to the request body: `"time_control": ["blitz", "rapid"], "rated": true, "recency": "year"`. The `matched_count` should be equal to or less than the unfiltered count. No errors.
result: [pending]

### 5. Game Record Fields
expected: Look at one entry in the `games` array from any successful response. It should contain: `game_id` (integer), `opponent_username` (string or null), `user_result` ("win"/"draw"/"loss"), `played_at` (datetime or null), `time_control_bucket` (string or null), `platform` ("chess.com" or "lichess"), `platform_url` (string URL or null).
result: [pending]

### 6. Zero Matches Returns Stats
expected: Query with a hash that matches nothing (e.g., `target_hash: 999999999999`). Response returns 200 (not 404), with `stats.total: 0`, `stats.wins: 0`, `stats.win_pct: 0.0`, empty `games` list, and `matched_count: 0`.
result: [pending]

### 7. All Tests Pass
expected: Run `uv run pytest` — all 158 tests pass with no failures or errors.
result: [pending]

## Summary

total: 7
passed: 0
issues: 0
pending: 7
skipped: 0

## Gaps

[none yet]
