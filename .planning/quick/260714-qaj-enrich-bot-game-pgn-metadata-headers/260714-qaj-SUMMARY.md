---
phase: quick-260714-qaj
plan: 01
subsystem: api
tags: [python-chess, pgn, bot-play, pydantic]

requires:
  - phase: 167
    provides: store_bot_game_service (server-side bot-game store path, rating derivation)
provides:
  - Server-side PGN header stamping for stored bot games (lichess-comparable Seven Tag Roster + GameId/UTCDate/UTCTime/Elo/Title/Variant/TimeControl/ECO/Opening/Termination/RatingSource/PlayStyleBlend)
  - game_repository.update_game_pgn (single-row targeted PGN UPDATE, no commit)
affects: [bot-play, pgn-export, analysis]

tech-stack:
  added: []
  patterns:
    - "PGN header re-stamp via clear-then-rebuild (chess.pgn.Game.headers cleared then reassigned in exact order, then str(game)) — preserves [%clk] comments while fully controlling header order/content"

key-files:
  created:
    - app/services/bot_game_pgn.py
    - tests/services/test_bot_game_pgn.py
  modified:
    - app/schemas/bots.py
    - app/repositories/game_repository.py
    - app/services/store_bot_game_service.py
    - tests/services/test_store_bot_game_service.py

key-decisions:
  - "RatingSource Literal relocated from store_bot_game_service.py to app/schemas/bots.py to break a circular import (bot_game_pgn.py needs it too)"
  - "Header stamp happens in a second, post-INSERT targeted UPDATE (not folded into normalize_flawchess_game) because the Site deep link needs the auto-increment games.id, which does not exist at normalize time"
  - "Stamp + UPDATE sit inside the existing if created: guard so a duplicate re-submit never rewrites an already-stored PGN"

patterns-established:
  - "Pure header builder taking a NormalizedGame + post-insert game_id, returning a re-serialized PGN string — no session, no DB, no I/O beyond settings.FRONTEND_URL"

requirements-completed: []

coverage:
  - id: D1
    description: "stamp_bot_game_headers produces the full D-03 header block in the exact D-03 order, with RatingSource/PlayStyleBlend last"
    verification:
      - kind: unit
        ref: "tests/services/test_bot_game_pgn.py::TestHappyPath::test_full_d03_header_block"
        status: pass
      - kind: unit
        ref: "tests/services/test_bot_game_pgn.py::TestHappyPath::test_header_order_matches_d03_exactly"
        status: pass
    human_judgment: false
  - id: D2
    description: "D-05 omission: missing rating anchor omits WhiteElo/RatingSource (never '?'/'0'), opening-less games omit ECO/Opening"
    verification:
      - kind: unit
        ref: "tests/services/test_bot_game_pgn.py::TestD05Omission"
        status: pass
    human_judgment: false
  - id: D3
    description: "BOT title placement follows the bot's color (opposite user_color), never both sides"
    verification:
      - kind: unit
        ref: "tests/services/test_bot_game_pgn.py::TestUserColorBlack::test_black_user_gets_white_title_on_bot"
        status: pass
    human_judgment: false
  - id: D4
    description: "[%clk] comments on both colors survive the header re-serialization"
    verification:
      - kind: unit
        ref: "tests/services/test_bot_game_pgn.py::TestClockSurvival::test_clk_survives_on_both_colors"
        status: pass
    human_judgment: false
  - id: D5
    description: "End-to-end: storing a bot game writes the full D-03 header block into games.pgn, with a Site deep link carrying the real post-INSERT game_id, and every header agreeing with its games column"
    verification:
      - kind: integration
        ref: "tests/services/test_store_bot_game_service.py::TestPgnHeaders::test_anchored_white_full_header_block"
        status: pass
      - kind: integration
        ref: "tests/services/test_store_bot_game_service.py::TestPgnHeaders::test_column_header_consistency"
        status: pass
    human_judgment: false
  - id: D6
    description: "A duplicate re-submit of the same game_uuid (with a forged PGN body + different bot_elo) does not rewrite the stored row's PGN"
    verification:
      - kind: integration
        ref: "tests/services/test_store_bot_game_service.py::TestPgnHeaders::test_duplicate_resubmit_does_not_rewrite_pgn"
        status: pass
    human_judgment: false

duration: 40min
completed: 2026-07-14
status: complete
---

# Quick Task 260714-qaj: Enrich Bot Game PGN Metadata Headers Summary

**Server-side lichess-comparable PGN header stamping for stored bot games (Event/Site/Date/Elos/Title/ECO/Opening/RatingSource/PlayStyleBlend), via a new pure `bot_game_pgn.py` module and a post-insert targeted UPDATE.**

## Performance

- **Duration:** ~40 min
- **Completed:** 2026-07-14T17:10:14Z
- **Tasks:** 3 (2 code tasks + 1 gate task, gate task produced no diff)
- **Files modified:** 6 (2 created, 4 modified)

## Accomplishments
- New `app/services/bot_game_pgn.py::stamp_bot_game_headers` builds the exact D-03 header block (Event/Site/Date/Round/White/Black/Result/GameId/UTCDate/UTCTime/WhiteElo/BlackElo/Title/Variant/TimeControl/ECO/Opening/Termination/RatingSource/PlayStyleBlend) via python-chess's clear-then-rebuild recipe, preserving `[%clk]` comments
- `RatingSource` Literal relocated to `app/schemas/bots.py` (breaks a circular import; `store_bot_game_service.py` re-exports it unchanged for any external importer)
- `game_repository.update_game_pgn` added — a single targeted, non-committing PGN UPDATE
- `store_bot_game_service.store_bot_game` now stamps + writes the header block once, post-INSERT, inside the existing `if created:` guard (idempotent on duplicate re-submit)
- 8 new unit tests in `tests/services/test_bot_game_pgn.py` (pure, no DB) + 6 new integration tests in a `TestPgnHeaders` class in `tests/services/test_store_bot_game_service.py` (re-read `games.pgn` from the DB and re-parse)

## Task Commits

1. **Task 1: Pure header builder + repository UPDATE + RatingSource relocation** - `af1e4477` (feat)
2. **Task 2: Wire the post-insert stamp into store_bot_game, end-to-end** - `e4509e9b` (feat)
3. **Task 3: Full pre-merge gate** - no commit (ruff format/check/ty/pytest all passed clean on the first run; no reformatting needed)

**Plan metadata:** pending (orchestrator commits this SUMMARY.md/STATE.md/etc. separately)

## Files Created/Modified
- `app/services/bot_game_pgn.py` - New pure module: `stamp_bot_game_headers` + `_build_header_pairs`, D-03 header constants
- `tests/services/test_bot_game_pgn.py` - Unit tests for the header builder (happy path, order, D-05 omissions, black-user title, clock survival, PlayStyleBlend formatting, trailing-slash FRONTEND_URL)
- `app/schemas/bots.py` - Relocated `RatingSource` Literal here (F-5, breaks circular import)
- `app/repositories/game_repository.py` - Added `update_game_pgn(session, game_id, pgn)`
- `app/services/store_bot_game_service.py` - Imports `RatingSource` from schemas; calls `stamp_bot_game_headers` + `update_game_pgn` inside the `if created:` branch
- `tests/services/test_store_bot_game_service.py` - Added `TestPgnHeaders` (6 tests) + a `_PGN_CHECKMATE_ALT` fixture + `bot_elo` override on `_make_request`

## Decisions Made
- Followed the plan's F-1..F-5 design notes verbatim (clear-then-rebuild header recipe, `Variant="Standard"` safety, `tc_preset` not `time_control_str` for `TimeControl`, post-insert stamping for the `Site` deep link, `RatingSource` relocation to break the circular import)
- No deviations beyond what the plan already specified as Claude's discretion

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None. `ty check` passed cleanly on the first run for all new/modified files (the `played_at`/rating `| None` narrowing that the plan anticipated as the likely `ty` friction point was handled correctly by the explicit `raise RuntimeError(...)` guards specified in Task 1, with no `# ty: ignore` needed).

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- Go-forward only (D-08): existing `platform='flawchess'` rows keep their thin headers; no backfill script was written, per the locked decision.
- `frontend/src/lib/botGamePgn.ts` and the rest of `frontend/` are untouched (D-01) — only the pre-existing, unrelated, uncommitted `frontend/src/components/bots/GameResultDialog.tsx` edit remains dirty in the working tree, as instructed.
- `app/services/normalization.py` is unchanged (verified via `git diff --stat`).

---
*Phase: quick-260714-qaj*
*Completed: 2026-07-14*

## Self-Check: PASSED

All created/modified files confirmed present on disk; both task commits (`af1e4477`, `e4509e9b`) confirmed present in `git log`.
