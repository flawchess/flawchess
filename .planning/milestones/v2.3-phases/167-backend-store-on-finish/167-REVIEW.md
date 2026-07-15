---
phase: 167-backend-store-on-finish
reviewed: 2026-07-11T00:00:00Z
depth: standard
files_reviewed: 20
files_reviewed_list:
  - app/schemas/normalization.py
  - app/schemas/bots.py
  - app/models/bot_game_settings.py
  - app/models/__init__.py
  - alembic/env.py
  - alembic/versions/20260711_185207_a07ccca76092_phase_167_bot_game_settings_table.py
  - app/repositories/query_utils.py
  - app/repositories/game_repository.py
  - app/services/library_service.py
  - app/services/normalization.py
  - app/services/store_bot_game_service.py
  - app/routers/bots.py
  - app/main.py
  - tests/schemas/test_bots.py
  - tests/repositories/test_bot_game_settings_repository.py
  - tests/repositories/test_query_utils.py
  - tests/services/test_library_service.py
  - tests/services/test_normalization.py
  - tests/services/test_store_bot_game_service.py
  - tests/routers/test_bots.py
findings:
  critical: 2
  warning: 2
  info: 0
  total: 4
status: resolved
resolution: all 4 findings fixed with regression tests (commits d7775a43, 2f2debee, b0e40289, ee2a96d6); full suite green, ty clean
---

# Phase 167: Code Review Report

**Reviewed:** 2026-07-11
**Depth:** standard
**Files Reviewed:** 20
**Status:** issues_found

## Summary

Reviewed the POST `/bots/games` store-on-finish path: schemas, the `bot_game_settings`
side table + migration, `apply_game_filters`' new flawchess-exclusion seam, the
PGN-only `normalize_flawchess_game` normalizer, `store_bot_game_service`'s
transaction/idempotency handling, and the thin router. The overall design is sound
— server-derived rating/platform/user_id, a single commit boundary, idempotent
re-submit via the existing `ON CONFLICT DO NOTHING` + id-lookup pattern, and a
well-centralized default-platform-exclusion seam in `query_utils.py` — and this
is backed by good test coverage for the paths the plan anticipated.

However, two client-reachable string inputs are **not length-bounded** before
they are written to a `String(50)` column (`games.time_control_str` /
`games.termination_raw`), each of which causes an **unhandled 500** (Postgres
`DataError: value too long for type character varying(50)`) instead of the
intended 422 — directly the failure mode this phase's own focus area calls out
("does it robustly 422 on malformed/oversized input... without leaking a 500?").
Both are BLOCKER-tier: reproducible with a single crafted request, no auth
bypass needed (a legitimate authenticated user's own oversized/malformed input
crashes the endpoint), and neither is covered by the otherwise-thorough test
suite. Two lower-severity WARNING-tier robustness gaps are also documented below.

## Critical Issues

### CR-01: Unbounded `tc_preset` overflows `games.time_control_str` (VARCHAR(50)) — 500 instead of 422

**File:** `app/schemas/bots.py:33`
**Issue:** `StoreBotGameRequest.tc_preset: str` has no `Field(max_length=...)` bound,
unlike every other request field (`pgn` is capped at `MAX_BOT_PGN_LENGTH`,
`bot_elo`/`play_style_blend` have `ge`/`le`). The raw value flows unmodified
through `store_bot_game_service.store_bot_game` → `normalize_flawchess_game`
(`app/services/normalization.py:641`, `time_control_str=_normalize_tc_str(tc_str)`)
into `NormalizedGame.time_control_str`, which `_flush_batch` inserts into
`games.time_control_str`, a `String(50)` column
(`app/models/game.py:111`, `Mapped[str | None] = mapped_column(String(50))`).
`_normalize_tc_str` only ever shortens a `"600+0"`-style string (drops a `+0`
suffix) or passes an unrecognized string through **unchanged** — it performs no
length validation. A `tc_preset` longer than 50 characters (e.g. any string of
garbage text, not just a lichess preset) therefore reaches the INSERT unbounded.
Postgres enforces `VARCHAR(50)` strictly (unlike some DBs it does not silently
truncate), so the INSERT raises `asyncpg.exceptions.StringDataRightTruncationError`
/ SQLAlchemy `DataError`. This exception is not the "expected None" validation
path in `normalize_flawchess_game` — it happens deeper, inside
`_flush_batch`/`bulk_insert_games`'s `INSERT ... RETURNING`, so it is caught only
by `store_bot_game`'s generic `except Exception: ... capture_exception(); raise`,
which re-raises past the router (the router only translates a `None` return to
422, not arbitrary exceptions) → FastAPI's default handler returns an unhandled
500, and a genuinely-expected-shape "oversized input" case gets logged to Sentry
as a real bug (alert noise). No test in `tests/schemas/test_bots.py` or
`tests/services/test_store_bot_game_service.py` exercises a `tc_preset` longer
than the DB column bound.
**Fix:**
```python
# app/schemas/bots.py
_MAX_TC_PRESET_LENGTH = 50  # matches games.time_control_str String(50) (app/models/game.py)

class StoreBotGameRequest(BaseModel):
    ...
    tc_preset: str = Field(max_length=_MAX_TC_PRESET_LENGTH)
```
Add a schema test mirroring `test_oversized_pgn_rejected` for `tc_preset`.

### CR-02: `termination_raw` derived from an unbounded, unvalidated PGN `[Termination]` header — same VARCHAR(50) overflow → 500

**File:** `app/services/normalization.py:589-607`
**Issue:**
```python
termination_header = game.headers.get("Termination")
termination: Termination
if termination_header is not None and termination_header in _FLAWCHESS_TERMINATION_HEADER_MAP:
    termination = _FLAWCHESS_TERMINATION_HEADER_MAP[termination_header]
elif board.is_checkmate():
    termination = "checkmate"
...
else:
    termination = "unknown"
termination_raw = termination_header if termination_header is not None else termination
```
`termination_raw` is set to the **raw PGN header string** whenever a
`[Termination "..."]` tag is present — even when that value is *not* in
`_FLAWCHESS_TERMINATION_HEADER_MAP` (the `elif`/board-derived branches only
gate the `termination` enum, not `termination_raw`). A PGN header value is
bounded only by the overall 100,000-char `pgn` field, so a client can submit
`[Termination "AAAA...(60+ chars)..."]` with an otherwise-valid game (valid
Result, both-color `[%clk]`) and produce a `termination_raw` string that
overflows `games.termination_raw` (`String(50)`, `app/models/game.py:105`),
crashing the same way as CR-01 (unhandled 500 during `_flush_batch`'s
`bulk_insert_games`). Unlike `normalize_chesscom_game`/`normalize_lichess_game`
— where `termination_raw` always comes from a small closed vocabulary defined
by the *platform's own API* (`white_result_str`/`status`, never arbitrary text)
— this is the first normalizer where `termination_raw` is sourced from
client-authored free text, and the length/vocabulary check that exists for
`termination` was not extended to `termination_raw`.
**Fix:**
```python
if termination_header is not None and termination_header in _FLAWCHESS_TERMINATION_HEADER_MAP:
    termination = _FLAWCHESS_TERMINATION_HEADER_MAP[termination_header]
    termination_raw = termination_header
else:
    if board.is_checkmate():
        termination = "checkmate"
    elif (
        board.is_stalemate()
        or board.is_insufficient_material()
        or board.is_fifty_moves()
        or board.is_repetition(3)
    ):
        termination = "draw"
    else:
        termination = "unknown"
    termination_raw = termination  # never trust an unrecognized/unbounded header string
```
This guarantees `termination_raw` is always either a recognized (and therefore
known-short) header value or one of the fixed `Termination` enum strings —
never an arbitrary-length client string.

## Warnings

### WR-01: `game_uuid` is validated as a UUID but stored non-canonicalized — idempotency (D-11) relies on exact string equality

**File:** `app/schemas/bots.py:35-47`
**Issue:** `validate_game_uuid` calls `uuid.UUID(value)` purely to check validity,
then returns the original `value` unchanged — it never normalizes to
`str(uuid.UUID(value))`. `uuid.UUID()` accepts several textual variants of the
same UUID (e.g. with/without hyphens, `urn:uuid:` prefix, braces, mixed case),
and `game_uuid` becomes `platform_game_id` (`String(100)`, case-sensitive
`VARCHAR` comparison) which the `uq_games_user_platform_game_id` unique
constraint keys the D-11 idempotency guarantee on
(`app/repositories/game_repository.py:70-101`,
`app/services/store_bot_game_service.py:107-113`). Two requests carrying
differently-cased/formatted representations of the *same* UUID would be treated
as distinct games (a second row + a second `bot_game_settings` insert), silently
breaking the "re-submitting the same `game_uuid` is a no-op" contract that
`STORE-05`/the idempotency tests assert. Low real-world likelihood today (the
intended client mints the UUID once via `crypto.randomUUID()`, which is always
lowercase-hyphenated), but nothing in this boundary schema enforces it.
**Fix:**
```python
@field_validator("game_uuid")
@classmethod
def validate_game_uuid(cls, value: str) -> str:
    try:
        return str(uuid.UUID(value))
    except ValueError as exc:
        raise ValueError("game_uuid must be a valid UUID") from exc
```

### WR-02: `[%clk]` presence gate assumes the mainline always starts with White to move

**File:** `app/services/normalization.py:577-582`
**Issue:**
```python
white_has_clock = any(node.clock() is not None for i, node in enumerate(nodes) if i % 2 == 0)
black_has_clock = any(node.clock() is not None for i, node in enumerate(nodes) if i % 2 == 1)
```
The even/odd-index-to-color mapping assumes the PGN's mainline starts from the
standard initial position (White to move first). `chess.pgn.read_game` honors a
client-supplied `[FEN "..."]`/`[SetUp "1"]` header pair to start from an
arbitrary position, including one where Black moves first — nothing in
`normalize_flawchess_game` rejects or accounts for a `SetUp`/`FEN` header. A
client submitting such a PGN would have the white/black clock-presence checks
silently swapped, potentially passing the STORE-02/D-15 "both colors must have
at least one `%clk`" gate with only one color's clocks actually present (or
vice versa, rejecting an otherwise-valid submission). Impact is limited (the
resulting `flawchess` game is excluded from all analytics by default per D-02,
and there is no cross-user effect), but it is a verifiable gap in the validation
this function's docstring claims to guarantee.
**Fix:** Reject PGNs carrying a `SetUp`/`FEN` header before applying the parity-based
clock check, e.g.:
```python
if game.headers.get("SetUp") == "1" or "FEN" in game.headers:
    return None  # bot games always start from the standard position
```

---

_Reviewed: 2026-07-11_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
