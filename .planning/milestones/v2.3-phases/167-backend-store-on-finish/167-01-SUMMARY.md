---
phase: 167-backend-store-on-finish
plan: 01
subsystem: database
tags: [sqlalchemy, alembic, pydantic, fastapi]

# Dependency graph
requires: []
provides:
  - "Platform Literal extended with 'flawchess' in app/schemas/normalization.py"
  - "StoreBotGameRequest/StoreBotGameResponse boundary schemas (app/schemas/bots.py)"
  - "BotGameSettings model + bot_game_settings table (FK CASCADE, CHECK rating_source)"
affects: [167-02, 167-03]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "First TEXT+CHECK CheckConstraint in app/models/*.py (no prior codebase precedent) — used as the template for future low-cardinality domain columns"
    - "_kwargs_with(**overrides) helper pattern for negative-case Pydantic tests, avoiding ty's dict-spread literal-union false positives"

key-files:
  created:
    - app/schemas/bots.py
    - app/models/bot_game_settings.py
    - alembic/versions/20260711_185207_a07ccca76092_phase_167_bot_game_settings_table.py
    - tests/schemas/test_bots.py
    - tests/repositories/test_bot_game_settings_repository.py
  modified:
    - app/schemas/normalization.py
    - alembic/env.py
    - app/models/__init__.py

key-decisions:
  - "Platform Literal extended only in app/schemas/normalization.py (D-17); left the unrelated inline Literal['chess.com','lichess'] filter types in insights.py/imports.py/opening_insights.py/openings.py/endgames.py untouched, per RESEARCH Pitfall 4 — those are user-facing filter literals, not this schema's Platform."
  - "bot_elo bounded 600-2600 (BOTX-01's 200-ELO-step bot-card range) via Pydantic Field(ge=..., le=...) rather than an unbounded int."
  - "Autogenerate correctly emitted both the ForeignKeyConstraint(ondelete='CASCADE') and the CheckConstraint on rating_source — RESEARCH/PATTERNS flagged this as a likely miss, but the generated migration needed no hand-editing; verified via grep for ENUM (zero hits) and manual read."

patterns-established:
  - "TEXT + CHECK for a low-cardinality domain column (rating_source) — first real use of this CLAUDE.md DB rule in the codebase; app/models/bot_game_settings.py is now the reference implementation."

requirements-completed: [STORE-03, STORE-04, STORE-05]

coverage:
  - id: D1
    description: "Platform Literal accepts 'flawchess'; uv run ty check app/schemas/ stays green"
    requirement: STORE-04
    verification:
      - kind: unit
        ref: "tests/schemas/test_bots.py::TestStoreBotGameRequestValidation (ty check app/schemas/)"
        status: pass
    human_judgment: false
  - id: D2
    description: "StoreBotGameRequest validates game_uuid as UUID, rejects malformed input, bounds bot_elo/play_style_blend/pgn length, and carries no server-owned field"
    requirement: STORE-05
    verification:
      - kind: unit
        ref: "tests/schemas/test_bots.py::TestStoreBotGameRequestValidation"
        status: pass
    human_judgment: false
  - id: D3
    description: "bot_game_settings table exists after alembic upgrade head with FK game_id ON DELETE CASCADE and CHECK constraint on rating_source"
    requirement: STORE-03
    verification:
      - kind: integration
        ref: "tests/repositories/test_bot_game_settings_repository.py::TestBotGameSettingsCheckConstraint::test_bogus_rating_source_raises_integrity_error"
        status: pass
      - kind: integration
        ref: "tests/repositories/test_bot_game_settings_repository.py::TestBotGameSettingsCascadeDelete::test_deleting_game_cascades_settings_row"
        status: pass
    human_judgment: false

# Metrics
duration: 25min
completed: 2026-07-11
status: complete
---

# Phase 167 Plan 01: Backend Store-on-Finish Schema + DDL Foundation Summary

**Extended the Platform Literal with "flawchess", added the StoreBotGameRequest/Response boundary schemas, and created the bot_game_settings side table via a hand-verified Alembic migration.**

## Performance

- **Duration:** 25 min
- **Started:** 2026-07-11T18:48:49Z
- **Completed:** 2026-07-11T19:14:00Z
- **Tasks:** 2
- **Files modified:** 8 (3 modified, 5 created)

## Accomplishments
- `Platform` Literal in `app/schemas/normalization.py` now includes `"flawchess"` (D-17), scoped to exactly that one file per RESEARCH Pitfall 4 — no unrelated inline filter literals touched.
- New `app/schemas/bots.py`: `StoreBotGameRequest` (UUID-validated `game_uuid`, length-bounded `pgn`, ELO-bounded `bot_elo`, range-bounded `play_style_blend`, no rating/platform/user_id/username/is_computer_game field per T-167-01) and `StoreBotGameResponse`.
- New `app/models/bot_game_settings.py`: one-to-one `bot_game_settings` table (`game_id` PK/FK → `games.id ON DELETE CASCADE`, `nominal_elo` SMALLINT, `play_style_blend` REAL, `tc_preset` TEXT, `rating_source` TEXT with a `CheckConstraint` — the first TEXT+CHECK domain column in the codebase).
- New Alembic migration `a07ccca76092` (down_revision `12d3df9c5373`), applied via `alembic upgrade head` against the dev DB; verified no native ENUM used.
- Registered `BotGameSettings` in `alembic/env.py` and `app/models/__init__.py`.

## Task Commits

Each task was committed atomically (Task 1 followed TDD: test → feat, plus one ty-compliance fix):

1. **Task 1: Extend Platform Literal + add bot request/response schemas**
   - `0dd0853c` (test) — failing test for bot game store schemas (RED)
   - `fd0eb5d2` (feat) — Platform Literal + StoreBotGameRequest/Response (GREEN)
   - `42167b2f` (fix) — ty dict-spread literal-union false positive in test negative cases
2. **Task 2: BotGameSettings model + Alembic migration** - `13ddda80` (feat)

**Plan metadata:** commit pending (this SUMMARY + STATE/ROADMAP update)

_Note: Task 1 followed the plan's `tdd="true"` flag — RED (failing import) confirmed before GREEN._

## Files Created/Modified
- `app/schemas/normalization.py` - `Platform` Literal extended with `"flawchess"`
- `app/schemas/bots.py` - `StoreBotGameRequest`/`StoreBotGameResponse`
- `app/models/bot_game_settings.py` - `BotGameSettings` model, one-to-one side table
- `alembic/env.py` - imports `BotGameSettings` for autogenerate/metadata visibility
- `app/models/__init__.py` - exports `BotGameSettings`
- `alembic/versions/20260711_185207_a07ccca76092_phase_167_bot_game_settings_table.py` - new migration
- `tests/schemas/test_bots.py` - schema validation tests (UUID, range, size, forbidden-field checks)
- `tests/repositories/test_bot_game_settings_repository.py` - insert/read-back, CHECK-violation, FK-CASCADE tests

## Decisions Made
- `bot_elo` bounded 600–2600 in the Pydantic schema (matches BOTX-01's bot-card ELO range), not left as an unbounded `int`.
- `MAX_BOT_PGN_LENGTH = 100_000` module constant added to bound the PGN DoS surface (T-167-03), per RESEARCH Security guidance — not explicitly spelled out in CONTEXT.md but required by the plan's `<action>` text.
- Kept the unrelated inline `Literal["chess.com", "lichess"]` filter types (insights.py, imports.py, opening_insights.py, openings.py, endgames.py) untouched — extending them would make bot games user-selectable on analytics filters, violating STORE-07 (deferred correctly to out-of-scope).

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] ty check false positive on dict-spread negative-case tests**
- **Found during:** Task 1 verification (`uv run ty check app/ tests/`)
- **Issue:** `{**_VALID_KWARGS, "field": value}` inline dict-spread syntax made `ty` infer a narrowed `Any | Literal[...]` union type per call site, tripping `invalid-argument-type` across every negative-case test in `tests/schemas/test_bots.py`, even though the tests themselves are correct (Pydantic validates fine at runtime — this is a static-analysis artifact of dict-merge literal inference, not a real bug).
- **Fix:** Replaced the inline dict-spread pattern with a `_kwargs_with(**overrides: Any) -> dict[str, Any]` helper function, whose `dict[str, Any]` return type is compatible with `**kwargs` unpacking under ty's checker.
- **Files modified:** `tests/schemas/test_bots.py`
- **Verification:** `uv run ty check app/ tests/` reports zero errors; `uv run pytest tests/schemas/test_bots.py -x` still green (8/8).
- **Committed in:** `42167b2f`

---

**Total deviations:** 1 auto-fixed (1 blocking — ty false positive)
**Impact on plan:** No scope creep; pure test-authoring fix required to satisfy the plan's own zero-ty-error acceptance criterion.

## Issues Encountered
- RESEARCH/PATTERNS flagged that Alembic autogenerate "commonly DROPS the CHECK constraint and may not emit ondelete='CASCADE'" for this genuinely-new-ground TEXT+CHECK pattern. In practice, the generated migration correctly included both the `CheckConstraint` and `ForeignKeyConstraint(ondelete="CASCADE")` on the first attempt — no hand-editing was needed, only `ruff format`/`ruff check --fix` for style. Verified with a `grep -i enum` (zero hits) and a manual read before applying.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- `Platform`, `StoreBotGameRequest`/`Response`, and `bot_game_settings` (with its migration applied to the dev DB) are all in place for Plan 02 (`DEFAULT_EXCLUDED_PLATFORMS` / library rating guard) and Plan 03 (`normalize_flawchess_game`, `store_bot_game`, the `bots` router).
- Note for Plan 03: RESEARCH Pitfall 2 still applies — `_flush_batch` returns only a count, never a game id; Plan 03 will need to add a `game_repository` lookup helper by `(user_id, platform, platform_game_id)` (none exists yet; not built in this plan since it wasn't in this plan's `files_modified`).
- Note for Plan 02/03: RESEARCH Pitfall 3 (`normalize_to_lichess_blitz` has no `"flawchess"` branch in `library_service.py`) is still open — this plan only widened the `Platform` Literal type-wise; the runtime landmine in `_build_card`'s two `cast(Platform, ...)` call sites is unaddressed and out of this plan's file scope.

---
*Phase: 167-backend-store-on-finish*
*Completed: 2026-07-11*

## Self-Check: PASSED

All created files verified present on disk; all task commit hashes
(`0dd0853c`, `fd0eb5d2`, `42167b2f`, `13ddda80`, `3c9a1647`) verified present
in `git log --oneline --all`.
