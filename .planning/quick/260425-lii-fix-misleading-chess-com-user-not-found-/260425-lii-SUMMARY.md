---
phase: 260425-lii
plan: "01"
subsystem: import
tags: [bug-fix, chess.com, error-handling, tdd]
dependency_graph:
  requires: []
  provides: [body-aware-404-handling]
  affects: [chesscom_client, import_service]
tech_stack:
  added: []
  patterns: [body-text disambiguation, player-endpoint probe]
key_files:
  modified:
    - app/services/chesscom_client.py
    - tests/test_chesscom_client.py
decisions:
  - "Probe /pub/player/{username} only on ambiguous 404 bodies; short-circuit on 'not found' substring to avoid extra round-trip for genuine missing users"
  - "Return bool | None from _user_exists_on_chesscom so caller can distinguish exists/absent/unknown without exceptions"
  - "ValueErrors for user-input/expected failures are not captured by Sentry per CLAUDE.md"
metrics:
  duration: "2 minutes"
  completed: "2026-04-25"
  tasks_completed: 1
  files_modified: 2
---

# Phase 260425-lii Plan 01: Fix Misleading chess.com "User Not Found" Error Summary

Body-aware 404 handling on the chess.com archives endpoint, with a player-endpoint probe to distinguish "user truly absent" from "real user with no public archives or transient error".

## What Was Built

### Root Cause

`app/services/chesscom_client.py` line 122-123 raised `ValueError("chess.com user '{username}' not found")` for every 404 on `/games/archives`. But chess.com returns 404 in two semantically distinct situations:

1. **User truly absent** — body: `{"message": "User \"X\" not found."}`
2. **Real user, archives unavailable** — body: `{"message": "An internal error has occurred."}` (e.g. user `wasterram` who exists at chess.com/member/wasterram but has no public archives)

Users in case 2 were told their username didn't exist, sending them on a fruitless typo hunt.

### Fix

Three additions to `app/services/chesscom_client.py`:

**`_CHESSCOM_NOT_FOUND_MARKER = "not found"`** — named constant for the body-text substring check (no magic strings per CLAUDE.md).

**`_user_exists_on_chesscom(client, api_username) -> bool | None`** — probes `/pub/player/{username}`:
- `True` — player 200, user exists
- `False` — player 404, user absent
- `None` — player 5xx or network error, treat as transient

**Body-aware 404 branch** in `fetch_chesscom_games`:
- Body contains "not found" → raise "user not found" immediately (no probe needed)
- Ambiguous body + player 200 → raise actionable "archives unavailable, try again in a few minutes"
- Ambiguous body + player 404 → raise "user not found" (fallback)
- Ambiguous body + player 5xx/network → raise "request failed" so `last_synced_at` is preserved (consistent with f69842b fix)

### Tests Added

Five 404-branch tests in `TestFetchChesscomGames`:

1. `test_404_raises_value_error` — updated: empty-body 404 flows through ambiguous branch; player mock as 404 asserts fallback "not found"
2. `test_404_with_user_not_found_body_raises_not_found_error` — genuine "not found" body raises immediately; asserts `call_count == 1` (no player probe)
3. `test_404_with_internal_error_body_and_player_200_raises_archives_unavailable` — ambiguous body + player 200 → "archives unavailable" message; asserts `call_count == 2`
4. `test_404_with_internal_error_body_and_player_404_falls_back_to_not_found` — ambiguous body + player 404 → "user not found"
5. `test_404_with_internal_error_body_and_player_500_raises_request_failed` — ambiguous body + player 500 → "request failed"

Total tests in file: 25 (all pass).

## Commits

| Hash | Type | Description |
|------|------|-------------|
| e21dd20 | test (RED) | add failing tests for body-aware 404 handling |
| 0824ef9 | fix (GREEN) | body-aware 404 handling on chess.com archives endpoint |

## Deviations from Plan

None — plan executed exactly as written.

## Known Stubs

None.

## Threat Flags

None — no new network endpoints, auth paths, or schema changes introduced.

## Self-Check: PASSED

- `app/services/chesscom_client.py` exists and contains `_user_exists_on_chesscom` and `_CHESSCOM_NOT_FOUND_MARKER`
- `tests/test_chesscom_client.py` exists and contains all five 404-branch tests
- Commits e21dd20 and 0824ef9 present in git log
- `uv run pytest tests/test_chesscom_client.py`: 25 passed
- `uv run ty check app/ tests/`: zero errors
- `uv run ruff check .`: clean
- `uv run ruff format --check app/services/chesscom_client.py tests/test_chesscom_client.py`: 2 files already formatted
