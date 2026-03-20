---
phase: 02-import-pipeline
plan: "02"
subsystem: import-pipeline
tags: [httpx, chess.com, lichess, ndjson, streaming, rate-limiting, async]

requires:
  - phase: 02-01
    provides: "normalize_chesscom_game, normalize_lichess_game, parse_time_control from normalization.py"
provides:
  - "fetch_chesscom_games async generator with sequential archive fetching, rate-limit delays, 429 backoff, incremental sync"
  - "fetch_lichess_games async generator with NDJSON streaming, since_ms incremental sync, pgnInJson param"
  - "_archive_before_timestamp helper for chess.com month-based incremental sync"
affects: [02-03]

tech-stack:
  added: []
  patterns:
    - "TDD with unittest.mock.AsyncMock to simulate httpx streaming without pytest-httpx"
    - "asyncio.sleep patched in tests to avoid real delays"
    - "async context manager mocking for httpx.stream() with _aiter_lines helper"
    - "chess.com incremental sync via URL year/month parsing; lichess via since= millisecond param"

key-files:
  created:
    - app/services/chesscom_client.py
    - app/services/lichess_client.py
    - tests/test_chesscom_client.py
    - tests/test_lichess_client.py
  modified: []

key-decisions:
  - "chess.com incremental sync: archive is skipped if its end boundary (first day of next month) <= since_timestamp; current month is always included"
  - "429 backoff: single 60-second sleep + one retry (not exponential) for simplicity"
  - "lichess perfType filter sent on every request: ultraBullet,bullet,blitz,rapid,classical — excludes correspondence and unlimited"
  - "moves=false in lichess params: PGN is available via pgnInJson=true, so raw moves field not needed"
  - "unittest.mock AsyncMock used throughout (pytest-httpx not installed); streaming response simulated via _aiter_lines async generator"

patterns-established:
  - "Mock pattern for httpx streaming: MagicMock with __aenter__/AsyncMock and aiter_lines returning async generator"

requirements-completed: [IMP-01, IMP-02]

duration: 3min
completed: "2026-03-11"
---

# Phase 2 Plan 2: Chess.com and Lichess API Clients Summary

**Async generator clients for chess.com (sequential archive fetching with 150ms delays and 429 backoff) and lichess (NDJSON streaming with aiter_lines) — both supporting incremental sync and non-standard variant filtering, with 21 httpx-mocked unit tests.**

## Performance

- **Duration:** ~3 min
- **Started:** 2026-03-11T13:32:24Z
- **Completed:** 2026-03-11T13:35:21Z
- **Tasks:** 2
- **Files modified:** 4 (created)

## Accomplishments

- chess.com client fetches monthly archives sequentially with 150ms delays, 60s backoff on 429, User-Agent header, and month-level incremental sync via `_archive_before_timestamp`
- lichess client streams NDJSON line-by-line via `response.aiter_lines()` with `pgnInJson=true`, `since=` millisecond timestamp for incremental sync, and JSONDecodeError handling for malformed lines
- 21 unit tests with full httpx mocking — no real HTTP calls, no real sleeps

## Task Commits

Each task was committed atomically with TDD RED → GREEN:

1. **Task 1: chess.com API client (RED)** - `501477a` (test)
2. **Task 1: chess.com API client (GREEN)** - `f5c54ec` (feat)
3. **Task 2: lichess API client (RED)** - `95384dd` (test)
4. **Task 2: lichess API client (GREEN)** - `4ff2d59` (feat)

## Files Created/Modified

- `app/services/chesscom_client.py` - fetch_chesscom_games async generator + _archive_before_timestamp helper
- `app/services/lichess_client.py` - fetch_lichess_games async generator with NDJSON streaming
- `tests/test_chesscom_client.py` - 12 tests: archive helper (4), fetch function (8)
- `tests/test_lichess_client.py` - 9 tests: 404, params, streaming, variant filter, malformed JSON, callback

## Decisions Made

- **chess.com incremental sync boundary:** A month's archive is skipped when `archive_end <= since`, where `archive_end` is the first moment of the following month. This means the current month is always included (correct — new games may still arrive).
- **429 backoff:** Simple single 60s sleep + retry (not exponential). Chess.com rate limits are uncommon in normal operation; exponential backoff is overkill for the initial implementation.
- **lichess perfType filter:** `ultraBullet,bullet,blitz,rapid,classical` sent on every request. This pre-filters at the API level, reducing data transfer. Correspondence and unlimited excluded.
- **moves=false:** Since `pgnInJson=true` includes the full PGN, the redundant `moves` array field is excluded from the response to reduce payload size.
- **unittest.mock over pytest-httpx:** pytest-httpx was not installed. The streaming mock pattern (`_aiter_lines` async generator + `__aenter__/AsyncMock`) is straightforward and avoids an additional dependency.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing validation] Removed unused `patch` import from lichess test file**
- **Found during:** Task 2 verification (ruff check)
- **Issue:** `patch` was imported from unittest.mock but never used in test_lichess_client.py — ruff F401
- **Fix:** Removed the unused import
- **Files modified:** `tests/test_lichess_client.py`
- **Verification:** `uv run ruff check .` — only pre-existing F821 model errors remain
- **Committed in:** `4ff2d59` (Task 2 feat commit)

---

**Total deviations:** 1 auto-fixed (1 missing validation/lint)
**Impact on plan:** Trivial cleanup. No scope creep.

## Issues Encountered

None — both clients implemented cleanly on first attempt.

## Next Phase Readiness

- Both API clients are ready for Plan 02-03 (background import service)
- `fetch_chesscom_games` and `fetch_lichess_games` both accept `on_game_fetched` callbacks for progress tracking
- Incremental sync is implemented in both clients; `last_synced_at` from ImportJob (Plan 02-01) feeds directly into `since_timestamp` / `since_ms`

## Self-Check: PASSED

---
*Phase: 02-import-pipeline*
*Completed: 2026-03-11*
