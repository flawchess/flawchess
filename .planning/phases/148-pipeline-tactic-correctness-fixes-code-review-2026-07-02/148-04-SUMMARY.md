---
phase: 148-pipeline-tactic-correctness-fixes-code-review-2026-07-02
plan: 04
subsystem: api
tags: [import, chesscom, lichess, sentry, error-handling]

requires:
  - phase: 148-01
    provides: n/a (independent fix, no shared code)
provides:
  - Per-game try/except guard around normalize_chesscom_game skipping malformed games
  - Per-game try/except guard around normalize_lichess_game skipping malformed games
  - Two new regression tests proving the import completes despite one bad game
affects: [import-pipeline, chesscom-client, lichess-client]

tech-stack:
  added: []
  patterns:
    - "Per-game try/except + logger.warning + sentry_sdk.set_context/capture_exception + continue, mirroring import_service.py:922-932 verbatim"

key-files:
  created: []
  modified:
    - app/services/chesscom_client.py
    - app/services/lichess_client.py
    - tests/test_chesscom_client.py
    - tests/test_lichess_client.py

key-decisions:
  - "Mirrored the existing PGN-parse Sentry pattern verbatim (one capture_exception per skipped game, not an end-of-batch summary), per RESEARCH.md Assumption A1"
  - "lichess test uses a missing 'id' key (not 'players' as the plan's test description assumed) to reproduce the real KeyError -- normalize_lichess_game reads players via game.get('players', {}), which does not raise; game['id'] is a direct subscript and does raise"

patterns-established:
  - "Import-pipeline per-game normalization failures are now uniformly guarded (PGN parse, chess.com normalize, lichess normalize all follow the same skip-and-continue + aggregated Sentry shape)"

requirements-completed: [ITEM-4]

coverage:
  - id: D1
    description: "A malformed chess.com game (missing 'white' key) is skipped; the import yields the remaining good games and records one Sentry capture"
    requirement: "ITEM-4"
    verification:
      - kind: unit
        ref: "tests/test_chesscom_client.py::TestFetchChesscomGames::test_malformed_game_skipped_and_continues"
        status: pass
    human_judgment: false
  - id: D2
    description: "A structurally-malformed (valid-JSON) lichess game is skipped; the import yields the remaining good games and records one Sentry capture; the pre-existing json.JSONDecodeError line guard is unchanged"
    requirement: "ITEM-4"
    verification:
      - kind: unit
        ref: "tests/test_lichess_client.py::TestFetchLichessGames::test_normalization_failure_skipped_and_continues"
        status: pass
      - kind: unit
        ref: "tests/test_lichess_client.py::TestFetchLichessGames::test_malformed_json_lines_skipped"
        status: pass
    human_judgment: false

duration: 15min
completed: 2026-07-04
status: complete
---

# Phase 148 Plan 04: Import robustness — guard per-game normalization Summary

**Per-game try/except around `normalize_chesscom_game`/`normalize_lichess_game` skips one malformed platform game instead of aborting the whole import, mirroring the existing PGN-parse Sentry pattern.**

## Performance

- **Duration:** 15 min
- **Completed:** 2026-07-04T08:58:10Z
- **Tasks:** 2
- **Files modified:** 4

## Accomplishments
- `chesscom_client.py`: wrapped the unguarded `normalize_chesscom_game(game, username, user_id)` call in a try/except — a malformed game (e.g. missing `"white"`, which the normalizer subscripts directly) is now logged, captured to Sentry (`set_context("import", {"platform": "chess.com", "user_id": user_id})`), and skipped via `continue`; the remaining games in the archive are still yielded.
- `lichess_client.py`: applied the identical guard shape around `normalize_lichess_game(game, username, user_id)`, leaving the pre-existing `json.JSONDecodeError` line guard (lines ~178-182) untouched.
- Two new regression tests confirm the fix: `test_malformed_game_skipped_and_continues` (chess.com) and `test_normalization_failure_skipped_and_continues` (lichess), both asserting the bad game is skipped, the good games are yielded in order, and exactly one `sentry_sdk.capture_exception` call is recorded.

## Task Commits

Each task was committed atomically:

1. **Task 1: chess.com per-game normalization guard + test** - `79a9b8b7` (fix)
2. **Task 2: lichess per-game normalization guard + test** - `7990c8ac` (fix)

## Files Created/Modified
- `app/services/chesscom_client.py` - try/except around `normalize_chesscom_game`, skip + Sentry capture on failure
- `app/services/lichess_client.py` - try/except around `normalize_lichess_game`, skip + Sentry capture on failure; JSON-decode guard untouched
- `tests/test_chesscom_client.py` - new `test_malformed_game_skipped_and_continues`
- `tests/test_lichess_client.py` - new `test_normalization_failure_skipped_and_continues`

## Decisions Made
- Mirrored `import_service.py:922-932`'s existing per-game try/except + `set_context`/`capture_exception` + `continue` shape verbatim for both files, for consistency with the established CLAUDE.md-compliant pattern (one capture per failed game, no variables in message text, variables via `set_context`).
- The plan's task description assumed a missing `"players"` key would trigger the lichess `KeyError`. Verified against `app/services/normalization.py::normalize_lichess_game`: `players = game.get("players", {})` already defaults safely and would NOT raise. The field that actually raises via a direct subscript is `game_id = game["id"]`. The test was built around the field that genuinely reproduces the bug (missing `"id"`), since a test using `"players"` would pass without exercising the new guard at all.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug in plan's own test description] Test fixture field corrected from "players" to "id" for the lichess case**
- **Found during:** Task 2 (lichess per-game normalization guard + test)
- **Issue:** The plan's `<behavior>` and RESEARCH.md both describe deleting `"players"` from a lichess game dict to reproduce the `KeyError`. Reading `normalize_lichess_game` directly shows `players = game.get("players", {})` — a missing `"players"` key does not raise; the function falls through with empty dicts. A test built exactly as described would pass trivially without ever exercising the new try/except (false confidence).
- **Fix:** Built the malformed-game fixture by deleting `"id"` instead — `game_id = game["id"]` is the actual unguarded direct subscript in `normalize_lichess_game`, confirmed by reading the source. The test genuinely exercises the new guard (verified it would fail against the pre-fix code by tracing the call path).
- **Files modified:** `tests/test_lichess_client.py`
- **Verification:** `uv run pytest tests/test_lichess_client.py -k "normaliz or malformed or skip"` — 3 passed.
- **Committed in:** `7990c8ac` (Task 2 commit)

---

**Total deviations:** 1 auto-fixed (Rule 1 — correcting a factually inaccurate test-fixture assumption in the plan itself)
**Impact on plan:** No scope change; the fix shape (try/except + skip + Sentry) is exactly as planned. Only the specific field used to reproduce the KeyError in the lichess test was corrected to one that actually raises.

## Issues Encountered
None beyond the test-fixture correction documented above.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Item 4 (import robustness) of the phase-148 code-review batch is complete; all four plans of phase 148 (148-01 tactic detector fixes, 148-02 entry-drain circuit breaker, 148-03 quintile covariance correction, 148-04 import robustness) are now done.
- No blockers for phase closure.

---
*Phase: 148-pipeline-tactic-correctness-fixes-code-review-2026-07-02*
*Completed: 2026-07-04*

## Self-Check: PASSED

All modified files and both task commits verified present on disk / in git log.
