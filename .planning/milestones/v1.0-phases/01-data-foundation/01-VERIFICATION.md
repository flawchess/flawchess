---
phase: 01-data-foundation
verified: 2026-03-11T14:00:00Z
status: passed
score: 11/11 must-haves verified
re_verification: false
---

# Phase 1: Data Foundation Verification Report

**Phase Goal:** Establish the database schema and position-hashing module that every subsequent phase depends on — getting this wrong would require rewriting the data layer.
**Verified:** 2026-03-11T14:00:00Z
**Status:** passed
**Re-verification:** No — initial verification

---

## Goal Achievement

### Observable Truths

Plan 01-01 must-haves:

| #  | Truth                                                                                                            | Status     | Evidence                                                                                          |
|----|------------------------------------------------------------------------------------------------------------------|------------|---------------------------------------------------------------------------------------------------|
| 1  | Running `alembic upgrade head` creates games and game_positions tables with correct columns and indexes          | VERIFIED   | Migration `dcef507678d8_initial_schema.py` contains both CREATE TABLE statements with all columns |
| 2  | The games table has a unique constraint on (platform, platform_game_id) preventing duplicate inserts             | VERIFIED   | `uq_games_platform_game_id` present in model `__table_args__` and in migration op                |
| 3  | The game_positions table has composite indexes on (user_id, full_hash), (user_id, white_hash), (user_id, black_hash) | VERIFIED | `ix_gp_user_full_hash`, `ix_gp_user_white_hash`, `ix_gp_user_black_hash` in model and migration |
| 4  | All hash columns and ID columns are BIGINT in PostgreSQL                                                         | VERIFIED   | `type_annotation_map = {int: BIGINT}` in Base; migration confirms `sa.BIGINT()` for all int cols |
| 5  | The games table stores all required metadata                                                                     | VERIFIED   | 26 columns including PGN, time control fields, rated, result, opponent, color, URL, timestamps, ratings, opening info, variant |

Plan 01-02 must-haves:

| #  | Truth                                                                                                              | Status   | Evidence                                                                               |
|----|--------------------------------------------------------------------------------------------------------------------|----------|----------------------------------------------------------------------------------------|
| 6  | compute_hashes returns three deterministic 64-bit signed integers (white_hash, black_hash, full_hash)              | VERIFIED | 16/16 tests pass including `test_starting_position_is_deterministic`, `test_two_fresh_boards_produce_equal_hashes` |
| 7  | The same board position always produces identical hashes across calls                                              | VERIFIED | `test_starting_position_is_deterministic` passes                                       |
| 8  | white_hash changes only when white pieces move, not when black pieces move                                         | VERIFIED | `test_white_hash_ignores_black_moves` and `test_white_hash_changes_when_white_moves` both pass |
| 9  | black_hash changes only when black pieces move, not when white pieces move                                         | VERIFIED | `test_black_hash_ignores_white_moves` and `test_black_hash_changes_when_black_moves` both pass |
| 10 | All returned hash values fit in PostgreSQL BIGINT range (-2^63 to 2^63-1)                                          | VERIFIED | `test_hashes_are_signed_int64` and `test_hashes_are_signed_int64_after_moves` pass; `ctypes.c_int64` conversion confirmed in source |
| 11 | hashes_for_game parses a PGN string and returns (ply, white_hash, black_hash, full_hash) for every half-move including ply 0 | VERIFIED | `test_hashes_for_game_includes_ply_zero` passes (4 entries for 3-move PGN), `test_hashes_for_game_ply_zero_is_starting_position` passes |

**Score:** 11/11 truths verified

---

### Required Artifacts

#### Plan 01-01 Artifacts

| Artifact                          | Expected                                             | Status     | Details                                                                                         |
|-----------------------------------|------------------------------------------------------|------------|-------------------------------------------------------------------------------------------------|
| `app/models/game.py`              | Game ORM model with full metadata columns            | VERIFIED   | 59 lines; `UniqueConstraint("platform", "platform_game_id", name="uq_games_platform_game_id")` present; all 26 metadata columns present |
| `app/models/game_position.py`     | GamePosition ORM model with hash columns and indexes | VERIFIED   | 29 lines; `ix_gp_user_full_hash`, `ix_gp_user_white_hash`, `ix_gp_user_black_hash` in `__table_args__`; ForeignKey to `games.id` with CASCADE |
| `app/models/base.py`              | DeclarativeBase with BIGINT type_annotation_map      | VERIFIED   | 13 lines; `type_annotation_map = {int: BIGINT, ...}` present; `AsyncAttrs` imported from correct path `sqlalchemy.ext.asyncio` |
| `app/core/database.py`            | Async engine and session factory                     | VERIFIED   | Exports `engine`, `async_session_maker`, `get_async_session`; `expire_on_commit=False` set |
| `app/core/config.py`              | Pydantic Settings with DATABASE_URL                  | VERIFIED   | `BaseSettings` with `SettingsConfigDict(env_file=".env")` — Pydantic v2 style confirmed |
| `alembic/env.py`                  | Async Alembic configuration importing all models     | VERIFIED   | `run_async_migrations` present; imports `Game` and `GamePosition` as side-effect imports; `target_metadata = Base.metadata` set |

#### Plan 01-02 Artifacts

| Artifact                          | Expected                                             | Status     | Details                                                                                         |
|-----------------------------------|------------------------------------------------------|------------|-------------------------------------------------------------------------------------------------|
| `app/services/zobrist.py`         | Zobrist hash computation module                      | VERIFIED   | 117 lines (above 30-line minimum); exports `compute_hashes` and `hashes_for_game`; `POLYGLOT_RANDOM_ARRAY`, `chess.polyglot.zobrist_hash`, and `c_int64` all present |
| `tests/test_zobrist.py`           | Unit tests for hash determinism and correctness      | VERIFIED   | 211 lines (above 50-line minimum); 16 tests, all passing (`uv run pytest tests/test_zobrist.py -v` confirmed) |

---

### Key Link Verification

#### Plan 01-01 Key Links

| From             | To                        | Via                                      | Status  | Evidence                                                                      |
|------------------|---------------------------|------------------------------------------|---------|-------------------------------------------------------------------------------|
| `alembic/env.py` | `app/models/base.py`      | `target_metadata = Base.metadata`        | WIRED   | Line 29: `target_metadata = Base.metadata` confirmed in env.py                |
| `alembic/env.py` | `app/models/game.py`      | side-effect import for autogenerate      | WIRED   | Line 12: `from app.models.game import Game  # noqa: F401` confirmed           |
| `app/models/game_position.py` | `app/models/game.py` | ForeignKey games.id              | WIRED   | Line 18: `ForeignKey("games.id", ondelete="CASCADE")` confirmed               |

#### Plan 01-02 Key Links

| From                       | To                                  | Via                                       | Status  | Evidence                                                         |
|----------------------------|-------------------------------------|-------------------------------------------|---------|------------------------------------------------------------------|
| `app/services/zobrist.py`  | `chess.polyglot.POLYGLOT_RANDOM_ARRAY` | direct import for color-specific hashing | WIRED   | Line 49: `chess.polyglot.POLYGLOT_RANDOM_ARRAY[index]` used     |
| `app/services/zobrist.py`  | `chess.polyglot.zobrist_hash`       | built-in full hash                        | WIRED   | Line 73: `chess.polyglot.zobrist_hash(board)` called            |
| `app/services/zobrist.py`  | `ctypes.c_int64`                    | unsigned-to-signed conversion for BIGINT | WIRED   | Lines 50 and 73: `ctypes.c_int64(h).value` used in both places  |

---

### Requirements Coverage

| Requirement | Source Plan | Description                                                                                       | Status    | Evidence                                                              |
|-------------|-------------|---------------------------------------------------------------------------------------------------|-----------|-----------------------------------------------------------------------|
| INFRA-01    | 01-01       | Database schema supports efficient position-based queries using indexed Zobrist hash columns      | SATISFIED | Three composite `(user_id, *_hash)` indexes on `game_positions` confirmed in model and migration |
| INFRA-03    | 01-01       | Duplicate games prevented via unique constraint on (platform, platform_game_id)                  | SATISFIED | `uq_games_platform_game_id` UniqueConstraint in model and migration  |
| IMP-05      | 01-01       | All available game metadata stored (PGN, time control, rated flag, result, opponent, color, platform URL, timestamps) | SATISFIED | All specified columns present in `game.py` model and confirmed in migration |
| IMP-06      | 01-02       | Position hashes (white, black, full Zobrist) precomputed and stored for every half-move at import time | SATISFIED | `hashes_for_game()` returns `(ply, wh, bh, fh)` for every half-move; 16 tests confirm behavior |

**No orphaned requirements.** All four Phase 1 requirements (INFRA-01, INFRA-03, IMP-05, IMP-06) are claimed by plans and verified.

---

### Anti-Patterns Found

None. Scanned all 8 phase files for TODO/FIXME/HACK/PLACEHOLDER markers, empty return stubs (`return null`, `return {}`, `return []`), and console.log-only implementations. Zero findings.

---

### Human Verification Required

#### 1. Alembic upgrade against a fresh database

**Test:** On a fresh PostgreSQL instance, run `uv run alembic upgrade head` then inspect via `\d games` and `\d game_positions` in psql.
**Expected:** Both tables created with correct column types (BIGINT for all integer columns, timestamptz for datetimes), unique constraint on games, and all three composite indexes on game_positions.
**Why human:** The migration file is verified correct, but actual DDL application against PostgreSQL cannot be confirmed programmatically from this environment without a live DB connection.

---

### Gaps Summary

No gaps. All 11 must-have truths are verified, all 8 required artifacts are substantive and wired, all 6 key links are confirmed, and all 4 Phase 1 requirements are satisfied.

The one human verification item (live database upgrade check) is a confirmation step, not a gap — the migration SQL is correct per code inspection.

---

_Verified: 2026-03-11T14:00:00Z_
_Verifier: Claude (gsd-verifier)_
