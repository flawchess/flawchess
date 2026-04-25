---
phase: 260425-lwz
plan: "01"
subsystem: import
tags: [bug-fix, chess.com, fallback, month-enumeration, tdd]
dependency_graph:
  requires: [body-aware-404-handling]
  provides: [month-enumeration-fallback]
  affects: [chesscom_client]
tech_stack:
  added: []
  patterns: [month-enumeration fallback, _current_year_month helper for testability]
key_files:
  modified:
    - app/services/chesscom_client.py
    - tests/test_chesscom_client.py
decisions:
  - "Extracted _current_year_month() helper instead of patching datetime wholesale — avoids breaking datetime() constructor calls in _archive_before_timestamp during tests"
  - "Extracted _enumerate_archive_urls(api_username, start_ym, end_ym) helper — pure date-math, no network, separately testable"
  - "Player endpoint called twice (exists-probe via _user_exists_on_chesscom, then joined-probe via _fetch_chesscom_player_joined) — kept helpers separate to preserve existing _user_exists_on_chesscom signature per plan constraint"
  - "Updated test_404_with_internal_error_body_and_player_200_raises_archives_unavailable → renamed to _falls_back_to_enumeration to reflect new behavior; old raise removed"
metrics:
  duration: "10 minutes"
  completed: "2026-04-25"
  tasks_completed: 1
  files_modified: 2
---

# Phase 260425-lwz Plan 01: Month-Enumeration Fallback for chess.com Archives-List 404 Summary

Month-enumeration fallback in `fetch_chesscom_games`: when chess.com's `/games/archives` index silently 404s for a real account, enumerate monthly archive URLs from the player's joined date and fetch them individually.

## What Was Built

### Root Cause

chess.com's `/games/archives` endpoint returns 404 with an ambiguous "An internal error has occurred" body for some real accounts (confirmed: user `wasterram`, 2026-04-25). The preceding fix (260425-lii) correctly identified these users as "real but archives temporarily unavailable" and raised a user-actionable ValueError. However, live investigation showed that the individual monthly endpoints `/pub/player/{username}/games/YYYY/MM` return games normally for these accounts — only the index is broken.

### Before (260425-lii)

```
ambiguous 404 + player 200 → raise ValueError("couldn't return games right now, try again later")
```

Users like `wasterram` could never complete an import despite having games.

### After (260425-lwz)

```
ambiguous 404 + player 200 →
  fetch joined date → enumerate months from max(joined_month, since_month) to now →
  feed synthesized URLs into existing per-archive loop →
  log info + Sentry info capture_message →
  yield games (possibly 0 if all months 404, which is a valid empty result)
```

### New Code in `app/services/chesscom_client.py`

**`_CHESSCOM_EARLIEST_ARCHIVE_YEAR_MONTH: tuple[int, int] = (2007, 1)`** — conservative floor for accounts whose `/pub/player` response has no `joined` field (chess.com launched May 2007).

**`_fetch_chesscom_player_joined(client, api_username) -> datetime | None`** — fetches `/pub/player/{username}` and returns the `joined` timestamp as a UTC datetime. Returns None on 404, network error, missing field, or non-integer value. Tolerates `ValueError`/`TypeError` from JSON.

**`_current_year_month() -> tuple[int, int]`** — thin wrapper around `datetime.now(timezone.utc)` returning `(year, month)`. Extracted as a standalone function so tests can patch it without replacing the entire `datetime` class (which would break the `datetime(year, month, 1, ...)` constructor calls inside `_archive_before_timestamp`).

**`_enumerate_archive_urls(api_username, start_ym, end_ym) -> list[str]`** — pure date-math helper, no network. Synthesizes `/pub/player/{username}/games/YYYY/MM` URLs from `start_ym` to `end_ym` inclusive.

**Fallback site in `fetch_chesscom_games`** (ambiguous-404 + `exists is True` branch):
- Removed the `raise ValueError("couldn't return games right now")`.
- Added inline comment block referencing the chess.com bug and live-confirmed account `wasterram` (per CLAUDE.md "comment bug fixes").
- Fetches `joined_at` via `_fetch_chesscom_player_joined`; falls back to `_CHESSCOM_EARLIEST_ARCHIVE_YEAR_MONTH` if None.
- Applies `since_timestamp` truncation: `start_ym = max(start_ym, (since.year, since.month))`.
- Calls `_enumerate_archive_urls` and sets `archive_urls` to the synthesized list.
- Emits `logger.info` and `sentry_sdk.capture_message(level="info", tags={source, platform})`.
- Falls through to the existing per-archive loop, which already handles 404/410 (skip), 5xx (retry), 429 (backoff).

### Decision: `_current_year_month` vs patching `datetime`

The plan offered two patching strategies:

1. Patch `app.services.chesscom_client.datetime` with a MagicMock, pass through `fromtimestamp` and `__call__` to real datetime.
2. Extract `_current_year_month()` helper and patch only that.

Strategy 1 failed in practice: `_archive_before_timestamp` constructs `datetime(year, month, 1, ...)` directly. When `datetime` is replaced wholesale, those constructors return MagicMock objects, causing `TypeError: '<=' not supported between instances of 'MagicMock' and 'datetime'`. Strategy 2 (chosen) avoids that entirely — the patch surface is minimal and the intent is explicit.

### Decision: Two player GET calls

`_user_exists_on_chesscom` and `_fetch_chesscom_player_joined` both hit `/pub/player/{username}`. They could be merged into one call, but:
- The plan explicitly requires keeping `_user_exists_on_chesscom` signature unchanged.
- The two calls serve different purposes: existence check vs. joined timestamp extraction.
- In practice this is one extra HTTP call per affected user (rare code path, not a hot loop).

Tests account for both calls in mock `side_effect` sequences.

### Tests Added / Modified

**Modified (1):**
- `test_404_with_internal_error_body_and_player_200_raises_archives_unavailable` → renamed to `test_404_with_internal_error_body_and_player_200_falls_back_to_enumeration` and updated to verify the new fallback behavior (no raise, 0 games, correct call count).

**New in `TestFetchChesscomGames` (5):**
1. `test_archives_404_ambiguous_with_player_200_enumerates_months_from_joined` — wasterram scenario: joined 2026-03, now 2026-04, 2 games yielded, 5 GET calls.
2. `test_fallback_enumeration_truncates_to_since_timestamp` — joined 2024-01 but since=2026-03: only 2 months enumerated.
3. `test_fallback_enumeration_uses_earliest_when_joined_missing` — no joined field: falls back to 2007-01, 3 months 404'd, 0 games, 6 calls.
4. `test_fallback_per_month_404_skips_and_continues` — 2026/03 → 404, 2026/04 → game: 1 game yielded.
5. `test_fallback_emits_sentry_info_capture_message` — verifies `capture_message` called with `level="info"`, `source=import`, `platform=chess.com`, message contains "archives-list 404".

**New class `TestFetchChesscomPlayerJoined` (5):**
1. `test_returns_datetime_when_joined_present` — 200 with joined ts → correct UTC datetime.
2. `test_returns_none_when_joined_missing` — 200 without joined → None.
3. `test_returns_none_on_404` — 404 → None.
4. `test_returns_none_on_network_error` — TimeoutException → None.
5. `test_returns_none_on_non_int_joined` — joined="not-a-number" → None.

Total tests: 35 (25 existing + 10 new), all pass.

## Commits

| Hash | Type | Description |
|------|------|-------------|
| 94d3f9b | test (RED) | add failing tests for archives-list 404 month-enumeration fallback |
| eebaade | feat (GREEN) | fall back to month enumeration when chess.com archives-list 404s for real users |

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] _current_year_month helper extracted for testability**
- **Found during:** GREEN — attempted datetime wholesale patch, TypeError in _archive_before_timestamp
- **Issue:** Patching `app.services.chesscom_client.datetime` replaced the `datetime` class globally within the module, causing `datetime(y, m, 1, tzinfo=timezone.utc)` calls in `_archive_before_timestamp` to return MagicMock objects and crash with TypeError on `<=` comparison.
- **Fix:** Extracted `_current_year_month()` helper; tests patch only that function. Plan documented this as the recommended alternative approach.
- **Files modified:** `app/services/chesscom_client.py`, `tests/test_chesscom_client.py`
- **Commit:** eebaade

**2. [Rule 1 - Bug] Test mock count updated to account for two player GET calls**
- **Found during:** GREEN test run
- **Issue:** Tests scripted 4 responses but implementation makes 5 (`_user_exists_on_chesscom` + `_fetch_chesscom_player_joined` each hit `/pub/player/`). Mock exhausted → StopAsyncIteration.
- **Fix:** All new tests updated with correct `side_effect` lists (exists-probe + joined-probe as separate mocked responses).
- **Files modified:** `tests/test_chesscom_client.py`
- **Commit:** eebaade

## Known Stubs

None.

## Threat Flags

None — no new network endpoints, auth paths, or schema changes. The fallback makes additional GET calls to existing chess.com public API endpoints already in use.

## Self-Check: PASSED

- `app/services/chesscom_client.py` contains `_fetch_chesscom_player_joined`, `_current_year_month`, `_enumerate_archive_urls`, `_CHESSCOM_EARLIEST_ARCHIVE_YEAR_MONTH`
- `grep -n "couldn't return games" app/services/chesscom_client.py` returns nothing
- `grep -n "archives-list 404" app/services/chesscom_client.py` returns 2 lines (logger.info + capture_message)
- `tests/test_chesscom_client.py` contains all 10 new tests
- Commits 94d3f9b (RED) and eebaade (GREEN) present in git log
- `uv run pytest tests/test_chesscom_client.py`: 35 passed
- `uv run ty check app/ tests/`: All checks passed
- `uv run ruff check .`: All checks passed
- `uv run ruff format --check app/services/chesscom_client.py tests/test_chesscom_client.py`: 2 files already formatted
