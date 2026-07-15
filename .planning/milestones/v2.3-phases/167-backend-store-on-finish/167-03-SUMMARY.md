---
phase: 167-backend-store-on-finish
plan: 03
subsystem: api
tags: [fastapi, sqlalchemy, python-chess, pydantic, zobrist, pgn-parsing]

# Dependency graph
requires:
  - phase: 167-backend-store-on-finish
    provides: "Plan 01 (Platform Literal += flawchess, StoreBotGameRequest/Response, BotGameSettings model + migration) and Plan 02 (apply_game_filters default-excludes flawchess, get_library_games opts back in, rating double-conversion guard)"
provides:
  - "normalize_flawchess_game: PGN-only normalizer with [%clk]/result/termination gating and D-08 rating placement"
  - "game_repository.get_game_id_by_platform_game_id: the id-lookup helper _flush_batch's count-only return can't provide"
  - "store_bot_game_service.store_bot_game: rating derivation + _flush_batch reuse + settings insert + idempotency, one commit"
  - "POST /api/bots/games: the store-on-finish endpoint, registered in app/main.py"
affects: [168-calibration-harness, 169-bot-game-loop-pgn-emitter, 170-store-once-orchestration, 171-bots-page-ui]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "PGN-only normalizer (no platform JSON payload) mirroring normalize_chesscom_game/normalize_lichess_game's NormalizedGame return shape"
    - "_flush_batch reuse outside the import-job machinery (no JobState), caller-owned single transaction"
    - "Post-_flush_batch id lookup by (user_id, platform, platform_game_id) — serves both the newly-inserted and idempotent-duplicate paths identically"

key-files:
  created:
    - app/services/store_bot_game_service.py
    - app/routers/bots.py
    - tests/services/test_store_bot_game_service.py
    - tests/routers/test_bots.py
  modified:
    - app/services/normalization.py
    - app/repositories/game_repository.py
    - app/main.py
    - tests/services/test_normalization.py

key-decisions:
  - "normalize_flawchess_game takes user_id as an explicit parameter (not listed in the plan's prose signature) because NormalizedGame.user_id is a required field that bulk_insert_games writes directly to the games row — omitting it would either crash the constructor or (if pydantic ignored the missing required field) fail validation."
  - "tc_str is fed directly into parse_time_control/parse_base_and_increment in the same base-seconds+increment-seconds format used everywhere else in the module (e.g. '180+2'), matching the plan's explicit instruction to derive the bucket from request.tc_preset via parse_time_control. Flagged for Phase 169/171: if the actual wire value ever becomes a minutes-based display label like lichess's '3+2' preset naming, it will misparse (e.g. '3+2' -> bullet, base=3s) — out of this phase's scope to resolve since the PGN/tc_preset wire contract is owned by Phase 169's client emitter."
  - "ply_count/result_fen are NOT NormalizedGame fields (verified against the schema) — _flush_batch's own Stage 5 (_collect_position_rows -> process_game_pgn) re-derives both by re-parsing the PGN for every newly inserted game, so normalize_flawchess_game does not compute or pass them."
  - "Termination header precedence: a PGN [Termination \"...\"] header (closed vocab identical to the Termination Literal) takes precedence over board-state derivation, per Phase 169 coordination (RESEARCH Open Question 1 / plan Assumption A1). Resignation/timeout/abandoned are only derivable via that header; absent it, only checkmate/draw/unknown are inferred from the final board."

patterns-established:
  - "Store-on-finish orchestration order: derive rating (user_rating_anchors) -> normalize (single PGN parse) -> _flush_batch (no commit) -> id lookup -> conditional side-table insert -> one commit. Any future 'persist one client-submitted game outside the import pipeline' feature should follow this exact sequence."

requirements-completed: [STORE-01, STORE-02, STORE-03, STORE-05, STORE-06]

coverage:
  - id: D1
    description: "normalize_flawchess_game builds a NormalizedGame from a client PGN with D-08 rating placement (player rating in the player-color column, bot ELO in the opponent column), gating on missing [%clk]/unparseable PGN/invalid Result by returning None"
    requirement: "STORE-02"
    verification:
      - kind: unit
        ref: "tests/services/test_normalization.py::TestNormalizeFlawchessGame"
        status: pass
    human_judgment: false
  - id: D2
    description: "store_bot_game derives the player rating from user_rating_anchors (NULL when no anchor), derives rating_source from anchor provenance (lichess/chesscom/blended), reuses _flush_batch for the games+positions insert, inserts bot_game_settings once, and commits in a single transaction"
    requirement: "STORE-03"
    verification:
      - kind: unit
        ref: "tests/services/test_store_bot_game_service.py::TestRatingDerivation"
        status: pass
    human_judgment: false
  - id: D3
    description: "Re-invoking store_bot_game with the same game_uuid returns the existing game_id with created=False and does not insert a second games row or a second bot_game_settings row"
    requirement: "STORE-05"
    verification:
      - kind: unit
        ref: "tests/services/test_store_bot_game_service.py::TestIdempotency::test_duplicate_game_uuid_returns_existing_id"
        status: pass
      - kind: integration
        ref: "tests/routers/test_bots.py::test_store_bot_game_idempotent_resubmit"
        status: pass
    human_judgment: false
  - id: D4
    description: "POST /api/bots/games persists a valid bot PGN as a platform='flawchess' games row (200, created:true), visible via GET /api/library/games with platform=flawchess opted in; missing-[%clk]/unparseable PGN -> 422; unauthenticated -> 401; a normal-length stored game lands evals_completed_at IS NULL (cold-drain eligible)"
    requirement: "STORE-01"
    verification:
      - kind: integration
        ref: "tests/routers/test_bots.py::test_store_bot_game_creates_flawchess_game"
        status: pass
      - kind: integration
        ref: "tests/routers/test_bots.py::test_store_bot_game_missing_clock_returns_422"
        status: pass
      - kind: integration
        ref: "tests/routers/test_bots.py::test_store_bot_game_unparseable_pgn_returns_422"
        status: pass
      - kind: integration
        ref: "tests/routers/test_bots.py::test_store_bot_game_requires_auth"
        status: pass
    human_judgment: false
  - id: D5
    description: "A stored non-guest bot game lands evals_completed_at IS NULL for a normal-length game (Stage 5c's 'covered' gate only fires for pathologically short games with no midgame/endgame entry plies — the same pre-existing behavior an equivalently short imported game gets)"
    requirement: "STORE-06"
    verification:
      - kind: integration
        ref: "tests/routers/test_bots.py::test_store_bot_game_creates_flawchess_game"
        status: pass
    human_judgment: false

# Metrics
duration: 20min
completed: 2026-07-11
status: complete
---

# Phase 167 Plan 03: Backend Store-on-Finish — Persistence Path Summary

**POST /api/bots/games persists a finished bot game through the existing `_flush_batch` hot-lane path (server-computed rating, [%clk] gate, idempotent on client UUID)**

## Performance

- **Duration:** 20 min
- **Started:** 2026-07-11T19:08:25Z
- **Completed:** 2026-07-11T19:23:12Z
- **Tasks:** 3
- **Files modified:** 8 (4 created, 4 modified)

## Accomplishments
- `normalize_flawchess_game` — a PGN-only normalizer (no platform JSON payload) that single-parses the client PGN via `chess.pgn.read_game`, gates on missing per-move `[%clk]` on either color / unparseable input / an unrecognized Result header (returns `None`, never raises), derives termination from a `[Termination "..."]` header when present else the final board state, and places the server-computed rating per D-08 (player-color column = converted rating, opponent-color column = bot nominal ELO, bot username fixed to `FLAWCHESS_BOT_USERNAME`).
- `store_bot_game_service.store_bot_game` — derives the player rating from `user_rating_anchors_repository.fetch_anchors_for_user` (NULL when no anchor, D-06), derives `rating_source` from anchor provenance (D-07), calls `import_service._flush_batch` with a one-item batch (D-09, no hashing/position reimplementation), looks up the game id via the new `game_repository.get_game_id_by_platform_game_id` helper (Pitfall 2 — `_flush_batch` returns only a count), inserts `BotGameSettings` only on first insert, and commits once (D-10).
- `POST /bots/games` router — thin, `current_active_user` dependency (covers guests, D-13), maps a `None` service result to `422`, registered in `app/main.py`.
- Idempotency (D-11): a duplicate `game_uuid` returns `200`/`created:false` with the existing `game_id`, no second `games` row, no second `bot_game_settings` row.

## Task Commits

Each task was committed atomically:

1. **Task 1: normalize_flawchess_game (PGN-only normalizer + [%clk] gate)** - `2deae621` (feat)
2. **Task 2: store_bot_game service + game_repository id lookup** - `e8b434c6` (feat)
3. **Task 3: bots router + registration + endpoint integration tests** - `e9a995d9` (feat)

_Note: no TDD gate on this plan (`tdd` not set at plan level); test files were added alongside each implementation file in the same commit._

## Files Created/Modified
- `app/services/normalization.py` - Added `normalize_flawchess_game`, `FLAWCHESS_BOT_USERNAME`, termination-header map
- `app/repositories/game_repository.py` - Added `get_game_id_by_platform_game_id`
- `app/services/store_bot_game_service.py` - NEW: `store_bot_game` orchestration
- `app/routers/bots.py` - NEW: `POST /bots/games` thin router
- `app/main.py` - Registered `bots_router`
- `tests/services/test_normalization.py` - `TestNormalizeFlawchessGame`
- `tests/services/test_store_bot_game_service.py` - NEW: rating derivation, invalid-PGN passthrough, idempotency
- `tests/routers/test_bots.py` - NEW: end-to-end HTTP coverage (STORE-01/02/05/06 + auth)

## Decisions Made
- Added `user_id: int` as an explicit parameter to `normalize_flawchess_game` even though the plan's prose signature list omitted it — `NormalizedGame.user_id` is a required Pydantic field that `bulk_insert_games` writes directly into the `games` row, so the normalizer cannot build a valid `NormalizedGame` without it (Rule 3 — blocking issue, the model's own required-field contract).
- `tc_str` is passed straight into `parse_time_control`/`parse_base_and_increment` in the same base-seconds+increment-seconds format every other normalizer in the module expects (e.g. `"180+2"`), per the plan's explicit "derive the bucket from request.tc_preset via parse_time_control" instruction. Flagging for Phase 169/171: if the actual `tc_preset` wire value ends up being a lichess-style minutes-based preset label (e.g. `"3+2"` meaning 3 minutes), it will silently misparse under the current seconds-based convention — this is a downstream wire-contract question (owned by Phase 169's PGN emitter), not something resolvable from this phase's code alone.
- `ply_count`/`result_fen` are not `NormalizedGame` fields (confirmed against `app/schemas/normalization.py`) — `_flush_batch`'s own Stage 5 re-parses the PGN and bulk-UPDATEs both columns for every newly inserted game, bot games included, so `normalize_flawchess_game` does not compute or pass them (avoids a redundant/incorrect duplicate computation).
- Termination-header precedence: a `[Termination "..."]` PGN header (closed vocab, 1:1 mapped to the `Termination` Literal) takes precedence over board-state derivation, matching RESEARCH's Open Question 1 / plan Assumption A1 — this is the only channel for resignation/timeout/abandoned since the request schema has no explicit termination field.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Added `user_id` parameter to `normalize_flawchess_game`**
- **Found during:** Task 1
- **Issue:** The plan's prose signature list for `normalize_flawchess_game` did not include `user_id`, but `NormalizedGame.user_id` is a required field that flows directly into the `games` table row via `bulk_insert_games`. Without it the function could not construct a valid `NormalizedGame`.
- **Fix:** Added `user_id: int` as the third positional parameter (matching `normalize_chesscom_game`/`normalize_lichess_game`'s existing convention), and threaded it through from `store_bot_game`.
- **Files modified:** `app/services/normalization.py`, `app/services/store_bot_game_service.py`
- **Verification:** `TestNormalizeFlawchessGame` and `TestRatingDerivation` both assert on the resulting `games` row's `user_id`-scoped lookups.
- **Committed in:** `2deae621` (Task 1 commit), threaded through in `e8b434c6` (Task 2 commit)

**2. [Rule 1 - Bug] Corrected the test PGN's `[%clk]` time format to `H:MM:SS`**
- **Found during:** Task 3 (writing the STORE-06 integration test)
- **Issue:** An initial long-game test fixture used raw-seconds `[%clk 178.9]` annotations; `chess.pgn`'s `CLOCK_REGEX` only matches the `H:MM:SS[.f]` format, so `node.clock()` silently returned `None` for every ply, and the resulting short "covered" Stage 5c classification masked the STORE-06 assertion this test exists to prove.
- **Fix:** Regenerated the fixture with `H:MM:SS.f`-formatted clocks (e.g. `[%clk 0:02:58.9]`), verified against a headless `chess.pgn.read_game` parse showing all 40 plies now report a non-`None` clock.
- **Files modified:** `tests/routers/test_bots.py`
- **Verification:** `test_store_bot_game_creates_flawchess_game` passes, including the `evals_completed_at IS NULL` assertion.
- **Committed in:** `e9a995d9` (Task 3 commit)

---

**Total deviations:** 2 auto-fixed (1 blocking, 1 bug)
**Impact on plan:** Both were necessary for functional correctness of the tests/implementation; neither expands scope beyond the plan's stated deliverables.

## Issues Encountered
- Confirmed empirically (not assumed) that `session.commit()` called inside `store_bot_game` against the rollback-scoped `db_session` fixture does not commit the underlying DBAPI transaction — `AsyncSession(bind=conn)` joins the connection's already-open (manually-`begin()`'d) transaction, so `session.commit()` only ends the ORM session's unit of work; the fixture's final `conn.rollback()` still fully undoes all writes. Verified via a standalone script (INSERT + `session.commit()` + `conn.rollback()`, then a fresh connection shows zero rows) before relying on this in `tests/services/test_store_bot_game_service.py`.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Phase 168 (calibration harness) can read `bot_game_settings` rows (nominal_elo, play_style_blend, rating_source) alongside the stored player rating for curve-fitting.
- Phase 169 (bot game loop / PGN emitter) needs to agree the exact wire format for `tc_preset` (seconds-based `"180+2"` vs a minutes-based display label like `"3+2"`) and should emit a `[Termination "..."]` PGN header using the closed vocabulary (`checkmate`/`resignation`/`timeout`/`draw`/`abandoned`/`unknown`) so resignation/timeout aren't permanently stuck at `"unknown"`.
- Phase 170 (store-once orchestration) can rely on the idempotent `{game_id, created}` response shape.
- Phase 171 (Bots page UI) still needs its own `opponent_type`/`platform` query wiring on the Library Games tab — this phase only made the backend capable of returning flawchess games when both filters are explicitly set (RESEARCH Pitfall 5, confirmed unchanged from Plan 02).
- No blockers.

---
*Phase: 167-backend-store-on-finish*
*Completed: 2026-07-11*

## Self-Check: PASSED

All created/modified files verified present on disk; all task commits (`2deae621`, `e8b434c6`, `e9a995d9`) and the metadata commit (`1a9e1244`) verified present in git log.
