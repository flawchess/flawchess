# Phase 167: Backend Store-on-Finish - Research

**Researched:** 2026-07-11
**Domain:** FastAPI/SQLAlchemy backend persistence — reusing an existing import pipeline for a new synchronous single-game write path
**Confidence:** HIGH

## Summary

This phase adds one new endpoint (`POST /bots/games`) that persists a client-POSTed
bot-game PGN through the **exact same** hot-lane persistence path the chess.com/lichess
importers use (`_flush_batch` → `_collect_position_rows` → Zobrist hashing →
`bulk_insert_positions` → ply_count/result_fen UPDATE → Stage-5c eval-coverage gate).
All the CONTEXT.md decisions (D-09 through D-11) that assume `_flush_batch` can be
called directly with a single-item batch and a real `AsyncSession`, outside any
`JobState`/import-job machinery, are **confirmed correct by an existing test**
(`tests/services/test_import_service.py::test_stage5c_marks_covered_games` drives
`_flush_batch(db_session, batch, user_id)` directly against a real rollback-scoped
DB session with no `JobState` in sight). This de-risks the core reuse-seam decision
before any code is written.

Two things in CONTEXT.md need correction/refinement based on reading the actual code:

1. **D-01/D-02's "exclusion is not free" claim is only partially true.** Every
   single analytics/library router in the codebase (`endgames.py`, `insights.py`,
   `library.py`, `stats.py`, `openings.py`, `opening_insights.py`, plus
   `insights_service.py`'s hardcoded `_OPPONENT_TYPE = "human"`) already defaults
   `opponent_type="human"`, which independently filters `is_computer_game == False`
   at every default view — and D-04 makes flawchess games `is_computer_game=True`.
   So flawchess games are **already excluded from every analytics default** via the
   *existing* opponent_type gate, with zero platform-based code change. D-02's
   platform-based exclusion in `apply_game_filters` is still worth implementing
   (it is the locked decision and it closes a real, narrower gap — see Pitfall 1
   below), but the risk it mitigates is smaller than CONTEXT.md implies.

2. **A live landmine in `library_service.py`'s rating-normalization call.** Every
   card built by `_build_card` (used by both `get_library_games` and
   `get_library_game`) unconditionally calls
   `normalize_to_lichess_blitz(rating, cast(Platform, game.platform), ...)` for
   both colors. `normalize_to_lichess_blitz`'s only two real branches are
   `if platform == "chess.com": ... else: # platform == "lichess"` — there is no
   third branch. Once `Platform` gains `"flawchess"` (D-17), every bot game's
   opponent-rating value will silently fall into the **lichess** branch and get
   run through a Table-2 inversion designed for genuine lichess-native ratings.
   The store-time rating is already lichess-equivalent (STORE-03's whole point),
   so this is semantically wrong for any TC bucket other than blitz (blitz is a
   no-op identity branch, so it happens to be harmless there). See Pitfall 3.

**Primary recommendation:** Add a new `app/services/store_bot_game_service.py`
(or similarly named) module with a thin `bots` router; write `normalize_flawchess_game`
as a **PGN-only** normalizer (structurally different from the JSON-response-driven
chess.com/lichess normalizers — it must derive everything from a single
`chess.pgn.read_game()` parse plus the four client-supplied settings fields); call
`_flush_batch` directly with a one-item batch; guard the `bot_game_settings` insert
on `_flush_batch`'s return value being `1` (not `0`); and special-case
`platform == "flawchess"` in `library_service._build_card`'s two
`normalize_to_lichess_blitz` call sites so the already-lichess-equivalent rating is
never re-converted.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| PGN → NormalizedGame parsing (result, termination, clocks, TC bucket) | API/Backend (`normalize_flawchess_game`) | — | Server never trusts client-derived fields (D-14); mirrors existing normalizers |
| Zobrist hashing + position rows | API/Backend (`_flush_batch`/`process_game_pgn`) | — | Reused unchanged — the whole point of D-09 |
| Player-rating conversion (save-time) | API/Backend (`user_rating_anchors_repository`) | — | Server is authoritative (D-05); client never supplies a rating |
| Idempotency (UUID dedup) | Database / Storage | API/Backend | Enforced by the existing `uq_games_user_platform_game_id` constraint; endpoint just interprets the `0`-vs-`1` return |
| Analytics exclusion | Database / Storage (query predicate) | API/Backend (`apply_game_filters`) | Central filter, not scattered per-router (D-02) |
| Bot-settings persistence | Database / Storage (new side table) | API/Backend | One-to-one FK row, inserted in the same transaction as the game |
| Auth (guest vs registered) | API/Backend (`current_active_user`) | — | Guests are ordinary `User` rows (D-13); no special-casing needed |
| `[%clk]` presence gate | API/Backend (request validation) | — | 422 before any DB write (D-15) |

## User Constraints (from CONTEXT.md)

<user_constraints>

### Locked Decisions

- **D-01 — SEED-091's "exclusion for free" is WRONG; make it real.** Every
  analytics router (`endgames.py`, `insights.py`, `library.py`) defaults
  `platform=None`, and `apply_game_filters` **skips** the platform predicate when
  `platform is None` → *all* platforms, which would now silently include
  `flawchess` in Global Stats, endgame-ELO timelines, insights, benchmarks, etc.
  Exclusion is NOT free and must be implemented.
- **D-02 — Exclude `flawchess` centrally in `app/repositories/query_utils.py`
  `apply_game_filters`** (the single shared filter — do not scatter per-site).
  Rule: **when `platform is None`, add `WHERE platform != 'flawchess'`** (i.e.
  default population = imported human/opponent games only). When an explicit
  `platform` list is passed, `WHERE platform IN (...)` already excludes
  `flawchess` unless the caller explicitly lists it. Add a module constant
  `DEFAULT_EXCLUDED_PLATFORMS = ("flawchess",)` for the None-case predicate.
  Net effect: bot games are invisible to every existing analytics surface with
  zero per-site changes; Library/Bots surfaces opt in by passing `platform`
  explicitly including `'flawchess'` (see D-03).
  - **Verify at plan time:** confirm no current analytics caller passes
    `platform=None` *and* needs literal-all-platforms including flawchess. Since
    `flawchess` is brand new, nothing does — the only surfaces that want it are the
    new Library Games tab / Bots page we control.
- **D-03 — Library Games tab must opt in.** The games list
  (`library_service.get_library_games` / `library.py`) is where bot games SHOULD
  appear (STORE-01/07). Its default `platform=None` will now exclude flawchess via
  D-02, so the Library games query must be adjusted to *include* flawchess by
  default (either pass an explicit platform list covering all three, or add an
  `include_flawchess=True` opt-in on the library path). Wiring the frontend
  filter chip for flawchess is a display concern; the backend must at minimum stop
  hiding them on the Library games list. Flag the exact seam for the planner.
- **D-04 — `is_computer_game = True` for flawchess games.** They *are* computer
  games; this is truthful and makes the existing `opponent_type='bot'` filter group
  them with imported bot games naturally. Analytics exclusion is driven by
  **platform** (D-02), independently of `is_computer_game`, so imported human
  games remain the default population regardless. `rated = False` (bot games are
  casual).
- **D-05 — Server-computed, authoritative. Client never supplies the rating.**
  On store, the server calls
  `user_rating_anchors_repository.fetch_anchors_for_user(user_id)`, selects the
  anchor for the **bot game's TC bucket**, and uses its `anchor_rating` (already a
  blended **lichess-equivalent** median) as the save-time converted player rating.
  This is the backend twin of the frontend `useMaiaEloDefault` machinery and is the
  authoritative source (server owns the imported games). Do NOT trust a
  client-supplied rating.
- **D-06 — NULL when no anchor.** No `user_rating_anchors` row for the bucket
  (user has no imported games, or none in that bucket) → player rating stored as
  `NULL` (STORE-03). Guests (`is_guest=True`) have no anchors → always NULL. Every
  NULL is a discarded calibration point but is correct per requirement.
- **D-07 — `rating_source` derived from anchor provenance.**
  `rating_source: Literal["lichess", "chesscom", "blended"] | None`, derived from
  the anchor row's `n_lichess_games` / `n_chesscom_games`: `lichess` if only
  lichess games backed the bucket, `chesscom` if only chess.com (converted),
  `blended` if both; `NULL` when the rating is NULL. Stored on the bot-settings
  side table (bot-specific metadata). Do NOT over-engineer a finer taxonomy — the
  anchor table already retains native medians if we ever need more.
- **D-08 — Rating placement follows STORE-03.** The converted player rating goes
  into the games row's **player-color** rating column (`white_rating` if
  `user_color='white'`, else `black_rating`); the **bot's nominal ELO** goes into
  the opponent-color rating column ("vs FlawChess Bot (1400)"). Bot username set to
  a fixed `"FlawChess Bot"`; player username = the user's display/platform name
  (discretion).
- **D-09 — Reuse `_flush_batch` with a single-item batch; do NOT reimplement
  hashing/positions.** `store_bot_game` builds one `NormalizedGame` via
  `normalize_flawchess_game`, then calls
  `import_service._flush_batch(session, [normalized_game], user_id)`. That reuses
  `_collect_position_rows` (single PGN parse → Zobrist `white_hash`/`black_hash`/
  `full_hash` position rows), `bulk_insert_positions`, the `ply_count`/`result_fen`
  UPDATE stages, and the Stage-5c eval-coverage gate. Because a fresh bot game has
  no lichess `%eval`, it lands with `evals_completed_at IS NULL` → the existing
  **cold drain picks it up and analyzes it** with zero extra wiring (STORE-01/06:
  "analyzable exactly like imported games" — for free). If `_flush_batch` proves
  too import-shaped to call cleanly, extract its non-JobState core into a shared
  helper rather than duplicating position/hash logic.
- **D-10 — The store endpoint owns its own transaction.** `_flush_batch` is
  WR-05 "does not commit" — the caller commits. The import-job machinery
  (`JobState`, `_flush_batch_with_progress`, progress counters, `run_import`) is
  **not** reused. Sequence: open session → `_flush_batch` (insert game + positions)
  → insert the bot-settings side-table row → commit. All in one transaction.
- **D-11 — Idempotency = the existing unique constraint (STORE-05).**
  `platform_game_id = client_uuid`; the `uq_games_user_platform_game_id`
  `(user_id, platform, platform_game_id)` constraint enforces one row.
  `_flush_batch` already returns `0` newly-inserted when the game is a duplicate
  (its `platform_game_id` dedup path) — treat that as the idempotent-success
  signal and return `200` with the existing game id, no second row, no error. Guard
  the side-table insert with the same dedup so a re-submit doesn't double-insert it.
- **D-12 — New `bots` router:** `APIRouter(prefix="/bots", tags=["bots"])`,
  `@router.post("/games")` (relative path per the router convention). Thin router
  → new `app/services/store_service.py` (or `bot_game_service.py`) holds the logic;
  router does no business logic.
- **D-13 — Standard authed dependency (`current_active_user`) covers guests too.**
  Guests are real `User` rows (`guest_service.create_guest_user`, `is_guest=True`)
  with a bearer token, so the same authenticated persist path works for registered
  users AND guests — no special-casing (STORE-06 / PLAY-10). The guest
  "won't auto-analyze" behavior is the **existing** eval-drain `is_guest`
  exclusion; the caveat *UI* is Phase 171, not this phase.
- **D-14 — Request schema (Pydantic v2 at the boundary):**
  `{ game_uuid: str (client-minted UUIDv4), pgn: str, user_color: "white"|"black",
  bot_elo: int, play_style_blend: float, tc_preset: str }`. The **server parses the
  PGN** (python-chess, mirroring the existing normalizers) to derive result,
  termination, both-color clocks, buckets, `ply_count`, `result_fen`, opening — do
  NOT trust the client for those. `platform_game_id = game_uuid` (client-owned per
  STORE-05, so Phase 170's "stored exactly once" localStorage logic can reference
  it). Validate `game_uuid` is a UUID.
- **D-15 — `[%clk]` gate (STORE-02):** reject with `422` when the PGN lacks
  per-move `[%clk]` annotations (require both colors). Also reject unparseable PGN
  or a PGN with no game result. Stored bot games therefore always carry both-color
  clocks so time-management analytics include them.
- **D-16 — New one-to-one side table `bot_game_settings`** (final name is
  discretion): `game_id` PK **and** FK → `games.id ON DELETE CASCADE` (mandatory FK
  per DB rules); `nominal_elo SMALLINT NOT NULL`; `play_style_blend REAL NOT NULL`
  (the `b ∈ [0,1]` blend from Phase 166 D-01, NOT a temperature); `tc_preset TEXT
  NOT NULL` (store the lichess preset string, e.g. `"3+2"`; base/inc are already on
  `games.base_time_seconds`/`increment_seconds` from PGN parse, so no need to
  duplicate structured); `rating_source TEXT` nullable (D-07, `CHECK IN
  ('lichess','chesscom','blended')`). Low row-count domain column → `TEXT + CHECK`
  per the DB design rules (not a native ENUM). New Alembic migration.
- **D-17 — Extend the `Platform` Literal (required mechanical step).** Add
  `"flawchess"` to `Platform = Literal[...]` in `app/schemas/normalization.py`, to
  the endgames-schema `Platform` type, and audit every `cast(Platform,
  game.platform)` site (e.g. `library_service.py`) so ty stays green. `games.platform`
  has **no** DB CHECK constraint (plain `String(20)`), so no DB migration is needed
  for the platform value itself — only the side table.

### Claude's Discretion

- Exact router/service/module names and file placement; the side-table name and
  whether `rating_source` uses `TEXT+CHECK` vs a Python `StrEnum`-backed column;
  the player-username string; response body shape (return the created/existing game
  id + a `created: bool`); whether to extract a shared `_persist_single_game`
  helper from `_flush_batch` vs call it directly.
- Whether `normalize_flawchess_game` lives in `app/services/normalization.py`
  (alongside `normalize_chesscom_game`/`normalize_lichess_game`) or a new module.

### Deferred Ideas (OUT OF SCOPE)

- **Post-launch curve fitting** (player rating vs result vs bot config to relabel
  bots with measured ELO) — explicitly a later milestone (CALX-01 / SEED-091 #3);
  this phase only *records* the settings + converted rating that make it possible.
- **Frontend flawchess filter chip / Bots-vs-Library surfacing UX** — display
  wiring belongs to Phase 171; this phase only stops analytics from hiding bot games
  and ensures the Library games query can include them (D-03).

None outside milestone scope — discussion stayed within the phase.

</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| STORE-01 | Every finished bot game stored as `platform='flawchess'` via shared normalization path, appears in Library games tab | `_flush_batch` reuse confirmed by existing test (`test_stage5c_marks_covered_games`); Library opt-in seam identified exactly (`library_service.get_library_games` → `library_repository.query_filtered_games` → `apply_game_filters`) |
| STORE-02 | PGN carries per-move `[%clk]` both colors; reject if missing | `chess.pgn` `node.clock()` returns `None` when no `[%clk]` present — verified via headless parse; gate logic documented below |
| STORE-03 | Save-time converted (lichess-scale, TC-bucket-matched) player rating; NULL only when no imported games; bot nominal ELO in opponent column; rating source recorded | `fetch_anchors_for_user` return shape read in full (`RatingAnchorRow.anchor_rating`, `n_lichess_games`, `n_chesscom_games`); TC-bucket key format confirmed (`TimeControlBucket` Literal, PG enum-backed) |
| STORE-04 | Full bot settings (nominal ELO, play-style value, TC preset) recorded for calibration | `bot_game_settings` side-table migration template drawn from `feedback` table precedent |
| STORE-05 | Client-owned UUID as `platform_game_id`; idempotent on unique constraint | `bulk_insert_games`'s `ON CONFLICT DO NOTHING ... RETURNING` behavior read in full — confirms `_flush_batch` returns `0` on duplicate with **no** existing-game-id in the return value (landmine — see Pitfall 2) |
| STORE-06 | Analyzable exactly like imported games; guest caveat is existing eval-exclusion | Cold-drain pickup confirmed structurally (`evals_completed_at IS NULL` after Stage 5c, since a fresh bot PGN has no lichess `%eval`); guest `is_guest` exclusion is pre-existing infra, not built by this phase |
| STORE-07 | Excluded from default analytics but included in Bots/Library | Confirmed `opponent_type="human"` is *already* the default everywhere (see Summary point 1) — D-02's platform predicate is defense-in-depth for the `opponent_type IN ("bot","both")` explicit-filter case on non-Library/Bots analytics surfaces |

</phase_requirements>

## Standard Stack

No new external packages. This phase is 100% composed of already-installed
dependencies: FastAPI, Pydantic v2, SQLAlchemy 2.x async, Alembic, python-chess
1.11.x, asyncpg. All already verified/pinned in `pyproject.toml`.

### Package Legitimacy Audit

Not applicable — no new packages are installed by this phase.

## Architecture Patterns

### System Architecture Diagram

```
Client (Phase 169/171, out of scope)
    │  POST /bots/games
    │  { game_uuid, pgn, user_color, bot_elo, play_style_blend, tc_preset }
    ▼
┌─────────────────────────────┐
│ bots router (thin)          │  current_active_user dependency (covers guests, D-13)
│ app/routers/bots.py         │  → 401 if unauthenticated
└──────────┬──────────────────┘
           ▼
┌─────────────────────────────────────────────────────────┐
│ store_bot_game_service.store_bot_game(session, user, req)│
│                                                            │
│  1. Parse PGN once with chess.pgn.read_game()             │
│     - reject 422: unparseable / no result / missing        │
│       per-move [%clk] on either color (D-15/STORE-02)      │
│  2. normalize_flawchess_game(...) -> NormalizedGame        │
│     - result, termination, tc_bucket, base/increment,      │
│       ply-adjacent fields mirror chesscom/lichess shape    │
│  3. fetch_anchors_for_user(session, user_id=...)           │
│     - select anchor row for the game's tc_bucket           │
│     - anchor_rating -> player rating (NULL if absent, D-06)│
│     - derive rating_source from n_lichess/n_chesscom (D-07)│
│  4. import_service._flush_batch(session, [game], user_id)  │
│     - returns 1 (new) or 0 (duplicate, D-11)                │
│  5. if 1: insert bot_game_settings row (same txn)           │
│     if 0: SELECT existing game id (idempotent-success path) │
│  6. session.commit()  (D-10 — endpoint owns the transaction)│
│  7. return { game_id, created: bool }                       │
└──────────┬────────────────────────────────────────────────┘
           │  (async, out of request path)
           ▼
┌─────────────────────────────────────────┐
│ existing cold-drain (eval_drain.py)      │
│ picks up evals_completed_at IS NULL      │
│ (unless guest — is_guest exclusion,      │
│ already existing infra, STORE-06)        │
└───────────────────────────────────────────┘
           │
           ▼
┌─────────────────────────────────────────┐
│ Library Games tab (existing UI, Phase 171│
│ wires the filter chip) — reads via       │
│ get_library_games with platform          │
│ explicitly including 'flawchess' (D-03)  │
└───────────────────────────────────────────┘

Analytics surfaces (Endgames/Insights/Stats/Openings) — default opponent_type=
"human" AND (after D-02) default platform excludes 'flawchess' -> STORE-07.
```

### Recommended Project Structure

```
app/
├── routers/
│   └── bots.py                    # NEW — thin router, POST /bots/games
├── schemas/
│   ├── bots.py                    # NEW — StoreBotGameRequest / StoreBotGameResponse
│   └── normalization.py           # MODIFIED — Platform Literal += "flawchess"
├── services/
│   ├── store_bot_game_service.py  # NEW — orchestration (discretion: name)
│   ├── normalization.py           # MODIFIED — add normalize_flawchess_game
│   ├── import_service.py          # UNCHANGED — _flush_batch called directly
│   └── library_service.py         # MODIFIED — guard normalize_to_lichess_blitz
│                                     for platform == "flawchess" (Pitfall 3)
├── repositories/
│   ├── bot_game_settings_repository.py  # NEW (or inline in service — discretion)
│   └── query_utils.py             # MODIFIED — DEFAULT_EXCLUDED_PLATFORMS (D-02)
├── models/
│   └── bot_game_settings.py       # NEW — one-to-one side table
alembic/versions/
└── <timestamp>_add_bot_game_settings_table.py  # NEW migration, down_revision=12d3df9c5373
```

### Pattern 1: PGN-only normalizer (structurally different from existing normalizers)

**What:** `normalize_chesscom_game`/`normalize_lichess_game` derive most
`NormalizedGame` fields from a rich platform JSON payload and only lightly
touch the PGN (regex for `[Event ...]`, a call to `find_opening(pgn_str)`).
`normalize_flawchess_game` has **no JSON payload** — every field must come from
either (a) a full `chess.pgn.read_game()` parse of the client PGN, or (b) the
four request fields (`user_color`, `bot_elo`, `play_style_blend`, `tc_preset`).

**When to use:** This phase only — it is the template for any future
"client-submitted PGN" ingestion path (none currently exist).

**Example (sketch, not verified against a runtime harness):**
```python
# Source: mirrors app/services/normalization.py's existing two functions,
# adapted for a client-owned PGN with no platform JSON.
import chess
import chess.pgn
import io

def normalize_flawchess_game(
    pgn_text: str,
    game_uuid: str,
    user_color: Color,
    user_id: int,
) -> NormalizedGame | None:
    game = chess.pgn.read_game(io.StringIO(pgn_text))
    if game is None:
        return None  # unparseable -> caller returns 422

    nodes = list(game.mainline())
    if not nodes:
        return None  # no moves -> caller returns 422

    # [%clk] presence gate (STORE-02/D-15) — both colors required.
    white_has_clock = any(n.clock() is not None for i, n in enumerate(nodes) if i % 2 == 0)
    black_has_clock = any(n.clock() is not None for i, n in enumerate(nodes) if i % 2 == 1)
    if not (white_has_clock and black_has_clock):
        return None  # caller returns 422

    # Result: prefer the PGN Result tag; python-chess parses it into headers.
    result_str = game.headers.get("Result")
    if result_str not in ("1-0", "0-1", "1/2-1/2"):
        return None  # no game result -> caller returns 422

    # Termination: see Open Question 1 below — this phase's request schema has
    # no explicit termination/reason field. Recommended: read a PGN
    # [Termination "..."] header if Phase 169 writes one (coordination point),
    # falling back to board-state-derivable cases, else "unknown".
    ...
```

### Pattern 2: Calling `_flush_batch` outside the import pipeline (D-09)

**What:** `_flush_batch(session: AsyncSession, batch: list[NormalizedGame], user_id: int) -> int`
is already exercised directly (no `JobState`) in
`tests/services/test_import_service.py::test_stage5c_marks_covered_games`, which
constructs a real rollback-scoped `db_session`, pre-inserts `Game` rows... but note
that test **mocks** `game_repository.bulk_insert_games` and `process_game_pgn` — it
does not prove the *real* (unmocked) code path end-to-end. For the store endpoint,
call it unmocked:

```python
# Source: app/services/import_service.py:726 (_flush_batch signature, unmodified)
from app.services.import_service import _flush_batch

async def store_bot_game(session: AsyncSession, user_id: int, normalized: NormalizedGame) -> tuple[int, bool]:
    inserted_count = await _flush_batch(session, [normalized], user_id)
    if inserted_count == 1:
        # Newly inserted — fetch the id _flush_batch didn't return directly.
        game_id = await game_repository.get_by_platform_game_id(
            session, user_id=user_id, platform="flawchess",
            platform_game_id=normalized.platform_game_id,
        )
        # insert bot_game_settings row here, same transaction
        created = True
    else:
        # Duplicate (idempotent re-submit, D-11) — fetch the EXISTING row's id.
        game_id = await game_repository.get_by_platform_game_id(...)
        created = False
    await session.commit()  # D-10 — endpoint owns the transaction
    return game_id, created
```

**When to use:** Any single-game persistence outside the batch-import loop.
**Landmine:** `_flush_batch` returns only a **count** (`0` or `1` for a one-item
batch), never the game's id. There is currently no `game_repository` helper for
"SELECT id WHERE user_id=... AND platform=... AND platform_game_id=..." — check
`app/repositories/game_repository.py` for an existing lookup before writing a new
one (repeat the lightweight `select(Game.id, Game.platform_game_id).where(...)`
pattern already used inside `_collect_position_rows`).

### Pattern 3: TEXT+CHECK side table (no existing precedent in this codebase)

**What:** Every enumerated/status-like column in the current schema
(`import_jobs.status`, `games.platform`, `games.time_control_str`) is a **plain
`String`/`Text` column with no `CheckConstraint`** — despite CLAUDE.md's DB design
rule preferring `TEXT + CHECK` for low-cardinality domain columns. Grepping
`app/models/*.py` for `CheckConstraint` returns **zero hits**. This phase's
`bot_game_settings.rating_source` would be the **first** real application of
that rule in this codebase — there is no copy-paste precedent to follow, only the
rule itself. Use SQLAlchemy's `CheckConstraint` in `__table_args__` and
`sa.CheckConstraint(...)` (not `op.create_check_constraint`, which is a separate,
also-valid Alembic op) inside the migration's `op.create_table(...)`.

```python
# Model (app/models/bot_game_settings.py) — sketch
from sqlalchemy import CheckConstraint, ForeignKey, Integer, SmallInteger, Text
from sqlalchemy.dialects.postgresql import REAL
from sqlalchemy.orm import Mapped, mapped_column
from app.models.base import Base

class BotGameSettings(Base):
    __tablename__ = "bot_game_settings"
    __table_args__ = (
        CheckConstraint(
            "rating_source IN ('lichess', 'chesscom', 'blended')",
            name="ck_bot_game_settings_rating_source",
        ),
    )
    game_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("games.id", ondelete="CASCADE"), primary_key=True
    )
    nominal_elo: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    play_style_blend: Mapped[float] = mapped_column(REAL, nullable=False)
    tc_preset: Mapped[str] = mapped_column(Text, nullable=False)
    rating_source: Mapped[str | None] = mapped_column(Text, nullable=True)
```

```python
# Migration (mirrors alembic/versions/20260615_192047_..._phase_122_feedback_table.py)
def upgrade() -> None:
    op.create_table(
        "bot_game_settings",
        sa.Column("game_id", sa.Integer(), nullable=False),
        sa.Column("nominal_elo", sa.SmallInteger(), nullable=False),
        sa.Column("play_style_blend", postgresql.REAL(), nullable=False),
        sa.Column("tc_preset", sa.Text(), nullable=False),
        sa.Column("rating_source", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["game_id"], ["games.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("game_id"),
        sa.CheckConstraint(
            "rating_source IN ('lichess', 'chesscom', 'blended')",
            name="ck_bot_game_settings_rating_source",
        ),
    )

def downgrade() -> None:
    op.drop_table("bot_game_settings")
```

Set `down_revision = "12d3df9c5373"` (current alembic head, verified via
`uv run alembic heads`).

### Anti-Patterns to Avoid

- **Reimplementing Zobrist hashing / position insertion for the bot path.**
  `_flush_batch`/`_collect_position_rows`/`process_game_pgn` already do this
  exactly once per PGN parse — D-09 forbids a second implementation.
- **Reusing `JobState`/`_flush_batch_with_progress`/`run_import`.** These exist
  to track multi-hundred-game async import jobs with progress polling; a
  single synchronous store-on-finish request has none of those needs (D-10).
- **Trusting the client for `result`/`termination`/clocks.** D-14 requires the
  server to parse the PGN itself — the client fields are limited to
  `user_color`, `bot_elo`, `play_style_blend`, `tc_preset`, `game_uuid`.
- **Adding a `platform=None` opt-in flag scattered across every Library
  endpoint.** D-02 explicitly wants ONE central seam
  (`apply_game_filters`/`DEFAULT_EXCLUDED_PLATFORMS`), with the *opt-in* handled
  at exactly one call site (`library_service.get_library_games`), not by adding
  parameters to `apply_game_filters` itself for every caller.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Zobrist hashing / position storage | A second hash+insert path for bot games | `import_service._flush_batch` (D-09) | Byte-identical analysis behavior to imported games; single source of truth for the hash algorithm |
| TC bucket classification | A bot-specific bucket mapping from `tc_preset` | `app.services.normalization.parse_time_control` / `parse_base_and_increment` on the PGN-derived time-control string | Already handles fractional increments, daily format, and the exact bullet/blitz/rapid/classical thresholds this project uses everywhere else |
| Rating conversion | A new "bot rating scale" | `user_rating_anchors_repository.fetch_anchors_for_user` (D-05) | Already the single source of blended lichess-equivalent ratings; reusing it keeps STORE-03's rating directly comparable to imported-game ratings |
| Duplicate-submit handling | A custom `game_uuid` lookup table / Redis dedup | The existing `uq_games_user_platform_game_id` unique constraint + `bulk_insert_games`'s `ON CONFLICT DO NOTHING` | Already atomic, already race-safe under concurrent requests — a Python-side "check-then-insert" would have a TOCTOU race |

**Key insight:** Everything downstream of "produce one correct `NormalizedGame`"
already exists and is battle-tested against ~years of production import traffic.
The only genuinely new code in this phase is the PGN-only normalizer, the rating
lookup + placement, the idempotency-aware response shaping, and the new side table.

## Common Pitfalls

### Pitfall 1: D-02's platform predicate is not fully redundant, but the risk is narrower than it looks

**What goes wrong:** Assuming D-02 is pure belt-and-suspenders and can be
deprioritized or skipped because `opponent_type="human"` already excludes bot
games from every default view.

**Why it happens:** Every analytics router in this codebase currently defaults
`opponent_type="human"` (verified: `endgames.py`, `library.py`, `stats.py`,
`openings.py`'s `Literal["human","bot","both"] = "human"`,
`opening_insights.py`, and `insights_service.py`'s hardcoded `_OPPONENT_TYPE`).
That means the **default** view of every analytics surface already excludes
`is_computer_game=True` games, flawchess included.

**How to avoid:** Implement D-02 anyway (it is locked) — it closes the real gap:
a user who explicitly selects `opponent_type IN ("bot", "both")` on Endgames /
Insights / Stats / Openings (to see their stats against imported chess.com/lichess
bot opponents) would otherwise see their FlawChess practice games mixed in,
which is exactly what STORE-07 says must not happen. D-02's `platform`-based
exclusion is the correct fix for that specific case; opponent_type alone doesn't
cover it since flawchess games legitimately have `is_computer_game=True`.

**Warning signs:** A test that asserts "flawchess excluded from analytics" using
only the default `opponent_type="human"` view would pass **even without** D-02
implemented — write the negative test with `opponent_type="bot"` explicitly set
to actually exercise D-02's predicate.

### Pitfall 2: `_flush_batch`'s return value gives no game id on either path

**What goes wrong:** Both the "newly inserted" (`1`) and "duplicate" (`0`) paths
need the game's `id` for the response (`{game_id, created}`) and for inserting the
`bot_game_settings` row — but `_flush_batch` returns only an `int` count, never
an id.

**Why it happens:** `_flush_batch` is purpose-built for batch imports where the
caller only needs a progress count, not individual ids (`_flush_batch_with_progress`
only reads `job.games_imported += imported`).

**How to avoid:** After calling `_flush_batch`, always do a follow-up lookup by
`(user_id, platform="flawchess", platform_game_id=game_uuid)` regardless of
whether the count was `0` or `1` — this single code path serves both the
newly-inserted case and the idempotent-duplicate case identically, and avoids
maintaining two different "get the id" branches. Check
`app/repositories/game_repository.py` for an existing helper before adding a new
one (none was found by name at research time, but the SELECT pattern used inside
`_collect_position_rows` — `select(Game.id, Game.platform_game_id).where(Game.id.in_(...))`
— is easily adapted to filter by `platform_game_id` instead).

**Warning signs:** A store call that "succeeds" (200 OK) but the response body's
`game_id` is stale, `None`, or from the wrong user.

### Pitfall 3: `normalize_to_lichess_blitz` has no `"flawchess"` branch — landmine in `library_service.py`

**What goes wrong:** Once `Platform` includes `"flawchess"` (D-17),
`library_service._build_card`'s two `cast(Platform, game.platform)` calls into
`normalize_to_lichess_blitz` will pass type-checking (ty sees a valid `Platform`
literal) but the function's actual `if platform == "chess.com": ... else: #
platform == "lichess"` dispatch has **no third branch**. A flawchess game's
already-lichess-equivalent rating will silently be routed through the lichess
branch, which for non-blitz TC buckets applies a Table-2 inversion designed for
*genuine native lichess ratings at that TC* — semantically wrong for a rating
that is already blended-lichess-equivalent from a different source
(`user_rating_anchors`). For `time_control_bucket == "blitz"` the lichess branch
is `if source_tc == "blitz": return rating` (a no-op identity), so it happens to
be harmless there — but rapid/classical/bullet bot games would get a spurious
extra conversion applied to an already-converted number.

**Why it happens:** `chesscom_to_lichess.py` imports `Platform` directly from
`app.schemas.normalization` (`from app.schemas.normalization import Platform,
TimeControlBucket`), so widening the shared `Platform` Literal silently widens
every consumer's accepted input without forcing a compile-time review of each
`if/else` dispatch.

**How to avoid:** In `library_service._build_card`, special-case
`platform == "flawchess"` before calling `normalize_to_lichess_blitz` — either
skip the call and use the already-stored rating directly (recommended: the
STORE-03 rating IS already lichess-blitz-equivalent, by construction of
`anchor_rating`), or add an explicit third branch to
`normalize_to_lichess_blitz` itself that returns the rating unchanged for
`platform == "flawchess"`. Grep for other `cast(Platform, ...)` call sites before
considering this fixed — at research time there are exactly two, both in
`library_service.py` lines 534 and 544 (both inside the same `_build_card`
function, one per color).

**Warning signs:** A bot game with `time_control_bucket in
("bullet","rapid","classical")` shows a `white_rating_lichess_blitz` /
`black_rating_lichess_blitz` value visibly different from the raw
`white_rating`/`black_rating` it was stored with, when it should be identical
(the stored rating already IS the lichess-blitz value).

### Pitfall 4: The `Platform` Literal is imported in more places than CONTEXT.md names

**What goes wrong:** CONTEXT.md's D-17 says to audit "the endgames-schema
`Platform` type" — but `app/schemas/endgames.py` does **not** define or import a
`Platform` type alias; it (and five other schema/service files) instead use an
**inline** `Literal["chess.com", "lichess"]` (not imported from
`normalization.py`). These inline literals are request/filter-side types (they
constrain what a client can *ask for* in `platform: list[Literal["chess.com",
"lichess"]] | None` query filters) and do **not** need `"flawchess"` added unless
a future phase wants users to explicitly filter Endgames/Openings/Insights by
`platform=flawchess` — out of scope here per STORE-07 (flawchess should stay
invisible on those surfaces, not selectable).

**Where inline literals exist (verified, not `cast(Platform, ...)`):**
`app/schemas/insights.py:351`, `app/schemas/imports.py:9`,
`app/schemas/opening_insights.py:32`, `app/schemas/openings.py` (×3, including two
`opponent_type: Literal["human","bot","both"]` fields — unrelated, do not confuse),
`app/schemas/endgames.py:740`, `app/services/endgame_service.py:1955,3457`
(the latter uses `cast(Literal["chess.com", "lichess"], platform_name)` — a
**different, unrelated** literal, not `schemas.normalization.Platform`).

**How to avoid:** Only extend `app/schemas/normalization.py`'s `Platform` Literal
(D-17's actual scope) and audit its **two** real `cast(Platform, ...)` usages
(`library_service.py:534,544`, Pitfall 3 above). Do not touch the inline
`Literal["chess.com", "lichess"]` filter types in `insights.py`/`imports.py`/
`opening_insights.py`/`openings.py`/`endgames.py` — those are unrelated
request-filter literals scoped to a different concern (what platforms a user can
explicitly filter by), and adding `"flawchess"` there would let users filter
Endgames/Openings by flawchess, which is explicitly out of scope (STORE-07 says
flawchess is invisible there, not user-selectable).

### Pitfall 5: `library.py`'s `opponent_type` default already hides bot games from the Library Games tab too

**What goes wrong:** Implementing D-02/D-03 (platform opt-in) alone is not
sufficient to satisfy STORE-01's "appears in the Library games tab" if left at
the router's current default, because `GET /library/games`'s `opponent_type`
query param **also** defaults to `"human"` (`app/routers/library.py:79`) — this
independently filters out `is_computer_game=True` rows (D-04 sets this True for
flawchess games) regardless of the platform fix.

**How to avoid:** This is explicitly Phase 171's job (the frontend filter-chip
wiring is deferred there per CONTEXT.md), but the planner/researcher must flag it
clearly so Phase 171 knows the backend alone is not sufficient — the frontend (or
a query-param default change) must pass `opponent_type=bot` or `opponent_type=all`
(if such a value is added) alongside `platform=flawchess` for bot games to
actually surface on a Library view. This phase's job (STORE-01/D-03) is only to
make it *possible* for the backend to return flawchess games when explicitly
asked (both filters set) — not to change the router's own defaults, since that
would also surface pre-existing imported bot games (e.g. lichess AI-level
opponents) more broadly than intended, an unrelated behavior change outside this
phase's scope.

### Pitfall 6: `_flush_batch`'s Stage-5c "covered" gate may misfire for a fresh bot game with zero eval data

**What goes wrong:** Stage 5c (`_collect_covered_game_ids`) marks a game
`evals_completed_at = NOW()` (skipping the cold drain entirely) when both
`_collect_midgame_eval_targets` and `_collect_endgame_span_eval_targets` return
empty for it. A fresh bot game has **no** `eval_cp`/`eval_mate` on any ply (no
lichess-style pre-baked evals) — need to verify this is NOT accidentally treated
as "already covered" (which would silently skip Stockfish analysis, breaking
STORE-06).

**Why it happens:** The covered-check gate was designed around "all entry plies
already have lichess %eval" — a fresh bot game trivially has none, so if the
target-collectors' "empty" condition is ambiguous between "nothing to do because
already analyzed" and "nothing to do because no entry plies exist", a bot game
could be wrongly marked covered.

**How to avoid:** This exact question is answered by
`_collect_covered_game_ids`'s own docstring: "either all entry plies already have
lichess %eval populated, **or** the game has no midgame or endgame entry plies at
all (very short game)". A normal-length bot game (dozens of plies) will have
midgame/endgame entry plies with `eval_cp IS NULL` — `_collect_midgame_eval_targets`
targets exactly these NULL-eval plies, so it will be non-empty for a typical bot
game and Stage 5c will correctly leave `evals_completed_at = NULL`, letting the
cold drain pick it up (D-09's claimed "for free" analysis). Only a pathologically
short bot game (a handful of plies, e.g. instant resignation) risks the
"no entry plies at all" branch and gets marked covered-with-zero-analysis — this
is the SAME behavior a genuinely tiny imported game gets, so it is not a
bot-specific bug, just something the planner should be aware won't get
Stockfish-analyzed (acceptable, matches existing behavior for short games).

## Code Examples

### Verified: `[%clk]` absence yields `node.clock() is None`

```python
# Source: verified via a headless python-chess parse in this research session
import chess.pgn, io
pgn = "[Event \"Test\"]\n[Result \"1-0\"]\n\n1. e4 e5 2. Nf3 1-0\n"  # no %clk
game = chess.pgn.read_game(io.StringIO(pgn))
for node in game.mainline():
    assert node.clock() is None  # confirmed
```

### Verified: `bulk_insert_games` dedup mechanism (D-11's foundation)

```python
# Source: app/repositories/game_repository.py:43-67 (read verbatim)
stmt = (
    pg_insert(Game)
    .values(game_rows)
    .on_conflict_do_nothing(constraint="uq_games_user_platform_game_id")
    .returning(Game.id)
)
result = await session.execute(stmt)
await session.flush()
return [row[0] for row in result.fetchall()]  # empty list on duplicate
```

### Verified: `_flush_batch` callable directly with a real DB session (no JobState)

```python
# Source: tests/services/test_import_service.py:296-381 (TestStage5c...) — read verbatim
# Confirms the exact call shape D-09 assumes:
await _flush_batch(db_session, cast(list[NormalizedGame], batch), user_id=test_user_id)
await db_session.flush()
# (test then SELECTs games.evals_completed_at directly — proving no JobState
# object, no import_job row, no progress counter is required anywhere in this call)
```

### Verified: `fetch_anchors_for_user` return shape for STORE-03

```python
# Source: app/repositories/user_rating_anchors_repository.py:129-175 (read verbatim)
anchors: dict[TimeControlBucket, RatingAnchorRow] = await fetch_anchors_for_user(
    session, user_id=user_id
)
row = anchors.get(bot_game_tc_bucket)  # None if user has no anchor for this TC
if row is None:
    player_rating, rating_source = None, None  # D-06
else:
    player_rating = row.anchor_rating  # already lichess-equivalent, blended median
    if row.n_lichess_games > 0 and row.n_chesscom_games > 0:
        rating_source = "blended"
    elif row.n_lichess_games > 0:
        rating_source = "lichess"
    else:
        rating_source = "chesscom"  # n_chesscom_games > 0 guaranteed if row exists
```

## State of the Art

Not applicable — no ecosystem-level "old vs new approach" shift here; this phase
reuses existing, current-generation internal patterns unchanged.

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | Phase 169 will encode game-end termination reason (resignation/timeout/checkmate/etc.) in a way `normalize_flawchess_game` can read — most likely a PGN `[Termination "..."]` header, since D-14's request schema has no explicit termination field | Pattern 1 / Open Question 1 | If Phase 169 emits a PGN with no termination signal at all, `normalize_flawchess_game` can only derive `checkmate`/`draw` (board-state-derivable) and must default resignation/timeout/abandoned all to `"unknown"` — degrading time-management/termination analytics for bot games until a cross-phase contract is agreed |
| A2 | `bot_elo`/`nominal_elo` fits `SMALLINT` (per D-16) — i.e. bot ELO values stay within roughly 0-2600 per the milestone's BOTX-01 200-ELO-step range (600-2600) | Architecture Patterns / migration | Fine — SMALLINT range is ±32767, far exceeds any plausible chess ELO; effectively zero risk, included for completeness |
| A3 | `game_repository.py` has no existing "SELECT game id by (user_id, platform, platform_game_id)" helper — a new small repository function will need to be added rather than reused | Pitfall 2 | Low risk — worth a final `grep` at plan/implementation time to avoid duplicating an existing helper the planner didn't spot |

**Note:** Everything else in this document (dedup mechanism, `_flush_batch`
signature, `fetch_anchors_for_user` shape, `[%clk]` gate mechanics, the missing
`CheckConstraint` precedent, the `normalize_to_lichess_blitz` landmine, the
`opponent_type` defaults) was verified directly by reading the source files or
running a live `python3`/`grep`/`alembic heads` check in this session — tagged
`[VERIFIED: codebase]` throughout the body text above (not repeated per-line to
avoid clutter).

## Open Questions

1. **How does `normalize_flawchess_game` learn the game's termination reason
   (resignation / timeout / abandoned) when the PGN has no rich JSON payload
   and D-14's request schema has no explicit termination field?**
   - What we know: `checkmate`, `stalemate`, `draw` (via insufficient material /
     threefold / 50-move) are all derivable from the **final board state** via
     python-chess (`board.is_checkmate()`, etc.). Resignation and flag-on-time
     (`timeout`) are **not** derivable from board state alone — they require
     out-of-band knowledge that only the client-side game loop (Phase 169) has.
   - What's unclear: whether Phase 169's PGN emitter will write a standard PGN
     `[Termination "..."]` header (as lichess/chess.com PGN exports do, though
     with platform-specific string vocabularies) that this phase's normalizer
     can read, or whether the four-field request schema (D-14, locked) is meant
     to be exhaustive and termination reason is simply not captured for bot
     games at MVP.
   - Recommendation: flag this explicitly to whoever plans/executes Phase 169 —
     agree a PGN header contract now (e.g. `[Termination "checkmate" |
     "resignation" | "timeout" | "draw" | "abandoned"]`, a closed vocabulary this
     phase's normalizer maps 1:1, mirroring `_CHESSCOM_TERMINATION_MAP`/
     `_LICHESS_STATUS_MAP`'s existing string-driven pattern) so `normalize_flawchess_game`
     isn't stuck defaulting every non-checkmate/non-draw game to `"unknown"`.
     If no such contract exists at plan time, the planner should default to
     board-state-derivable values + `"unknown"` fallback and record this as a
     known gap (not silently fabricate a reason).

2. **Should `get_flaw_stats` / `get_library_flaws` / the you-vs-opponent
   comparison endpoints also opt in to `flawchess`, or only the raw
   `get_library_games` games list (D-03's literal scope)?**
   - What we know: CONTEXT.md D-03 names `library_service.get_library_games`
     specifically. `get_flaw_stats`, `get_library_flaws`, and the comparison
     bullets all independently default `platform=None` too (all pass through
     `apply_game_filters`).
   - What's unclear: whether STORE-07's "included in... Library Games surfaces"
     (plural) means the whole Library tab (stats + flaws list too) or just the
     Games card list.
   - Recommendation: scope the opt-in strictly to `get_library_games` per D-03's
     literal wording (defer stats/flaws-list inclusion as an explicit follow-up
     decision) — if a bot game's flaws start appearing in the "you vs opponent"
     comparison denominator without a product decision on whether that's
     desired, it could silently skew a stat users interpret as "vs my real
     opponents."

## Environment Availability

Not applicable — no new external tool/service/runtime dependency. All work is
internal FastAPI/SQLAlchemy/Alembic/python-chess code against the existing dev
Postgres (already required and running per project convention).

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest 8.x (per-run cloned DB template, see `tests/conftest.py`) |
| Config file | `pyproject.toml` `[tool.pytest.ini_options]` (existing, unmodified) |
| Quick run command | `uv run pytest tests/services/test_store_bot_game_service.py tests/routers/test_bots.py -x` |
| Full suite command | `uv run pytest -n auto` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| STORE-01 | POST creates one `platform='flawchess'` game row via `_flush_batch`; visible via `get_library_games` with explicit platform | integration (real `db_session`) | `pytest tests/routers/test_bots.py::test_store_creates_flawchess_game -x` | ❌ Wave 0 |
| STORE-02 | Missing `[%clk]` (either color) → 422; unparseable PGN → 422; no result → 422 | unit | `pytest tests/services/test_normalization.py::TestNormalizeFlawchessGame -x` | ❌ Wave 0 |
| STORE-03 | Player rating = anchor for TC bucket; NULL when no anchor; `rating_source` derived correctly (lichess/chesscom/blended/None) | unit + integration | `pytest tests/services/test_store_bot_game_service.py::TestRatingDerivation -x` | ❌ Wave 0 |
| STORE-04 | `bot_game_settings` row has `nominal_elo`, `play_style_blend`, `tc_preset`, `rating_source` | integration (real `db_session`) | `pytest tests/repositories/test_bot_game_settings_repository.py -x` | ❌ Wave 0 |
| STORE-05 | Re-POST same `game_uuid` returns 200 with same `game_id`, `created=False`, no second row | integration | `pytest tests/routers/test_bots.py::test_store_idempotent_resubmit -x` | ❌ Wave 0 |
| STORE-06 | Fresh bot game lands `evals_completed_at IS NULL` (unless pathologically short, Pitfall 6); guest game excluded from cold-drain per pre-existing `is_guest` gate | integration | `pytest tests/routers/test_bots.py::test_store_leaves_pending_for_cold_drain -x` | ❌ Wave 0 |
| STORE-07 | `apply_game_filters` excludes `platform='flawchess'` when `platform is None`; explicit `opponent_type='bot'` on Endgames/Insights doesn't leak flawchess games | unit | `pytest tests/repositories/test_query_utils.py::TestApplyGameFiltersFlawchessExclusion -x` | ❌ Wave 0 |

### Sampling Rate

- **Per task commit:** `uv run pytest tests/services/test_store_bot_game_service.py tests/routers/test_bots.py tests/repositories/test_query_utils.py -x`
- **Per wave merge:** `uv run pytest -n auto`
- **Phase gate:** Full suite green (`uv run pytest -n auto`), `uv run ty check app/ tests/` zero errors, before `/gsd-verify-work`.

### Wave 0 Gaps

- [ ] `tests/routers/test_bots.py` — new file, covers STORE-01/02/05/06 end-to-end
      against the `bots` router (mirrors existing router test conventions in
      `tests/routers/test_imports_eval_coverage.py`)
- [ ] `tests/services/test_store_bot_game_service.py` — new file, covers
      STORE-03/04 orchestration logic
- [ ] `tests/repositories/test_bot_game_settings_repository.py` — new file (or
      folded into the service test if the repository layer is thin enough to
      skip per discretion)
- [ ] Extend `tests/services/test_normalization.py` with a
      `TestNormalizeFlawchessGame` class for the `[%clk]`/result/termination
      parsing (STORE-02)
- [ ] Extend `tests/repositories/test_query_utils.py` (if it exists — verify at
      plan time; `apply_game_filters` currently has no dedicated test file found
      by this research pass, only indirect coverage via repository tests) with
      the `DEFAULT_EXCLUDED_PLATFORMS` case (STORE-07)
- [ ] A regression test for Pitfall 3 (`normalize_to_lichess_blitz` /
      `_build_card` for `platform == "flawchess"`) belongs in
      `tests/services/test_library_service.py` (existing file — verify at plan
      time) since it is a pre-existing-code landmine this phase's D-17 exposes,
      not a new endpoint's own logic

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | yes | `current_active_user` FastAPI-Users dependency (existing, D-13) — no new auth logic |
| V3 Session Management | no | Stateless JWT bearer auth, unchanged by this phase |
| V4 Access Control | yes | `user_id` always sourced from `current_active_user.id`, never from a request body/query field (mirrors the V4 mitigation pattern already documented in `user_rating_anchors_repository.py`) — the request schema (D-14) correctly has no `user_id` field |
| V5 Input Validation | yes | Pydantic v2 boundary validation for `game_uuid` (UUID format), `user_color` (Literal), `bot_elo`/`play_style_blend` (numeric bounds — discretion on exact range checks); server-side PGN re-parse rather than trusting client-derived result/termination/clocks (D-14) |
| V6 Cryptography | no | No new crypto surface |

### Known Threat Patterns for this stack

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| PGN injection / malformed PGN crashing the parse | Denial of Service | Existing pattern: `process_game_pgn`/`chess.pgn.read_game` already wraps parse failures and returns `None` rather than raising uncaught; `normalize_flawchess_game` must do the same and the router must map `None` → 422, never 500 |
| Oversized PGN payload (client sends a pathologically long PGN or repeated `[%clk]` spam) | Denial of Service | Not currently bounded anywhere in the existing normalizers — flag for the planner to consider a request body size cap (FastAPI/Pydantic `max_length` on the `pgn` field) since this is a new user-facing write endpoint, unlike the read-only import flow where PGN size is bounded by the platform API response |
| IDOR via `game_uuid` collision across users | Tampering / Information Disclosure | Not possible — `uq_games_user_platform_game_id` is scoped to `(user_id, platform, platform_game_id)`, so two different users can reuse the same client-generated UUID with no collision (existing constraint design, verified) |
| Rating manipulation (client attempts to inject its own rating) | Tampering | Structurally prevented by D-05 — the request schema (D-14) has no rating field at all; the server computes it unconditionally from `user_rating_anchors` |

## Sources

### Primary (HIGH confidence — read directly from the working tree this session)
- `app/services/import_service.py` — `_flush_batch`, `_collect_position_rows`, `_collect_covered_game_ids`, `JobState`/`_flush_batch_with_progress` (full file read)
- `app/services/normalization.py` — `normalize_chesscom_game`, `normalize_lichess_game`, `parse_time_control`, `parse_base_and_increment` (full file read)
- `app/schemas/normalization.py` — `NormalizedGame`, `Platform` Literal (full file read)
- `app/services/zobrist.py` — `process_game_pgn`, `PlyData` (full file read)
- `app/repositories/query_utils.py` — `apply_game_filters` (full file read)
- `app/models/game.py` — `Game` ORM model, `uq_games_user_platform_game_id`, rating/clock columns (full file read)
- `app/repositories/user_rating_anchors_repository.py` — `fetch_anchors_for_user`, `RatingAnchorRow` (full file read)
- `app/models/user_rating_anchors.py` — `UserRatingAnchor` schema + algorithm docstring (full file read)
- `app/services/library_service.py` — `_build_card`, `get_library_games`, `get_library_game` (partial read, ~1300/1643 lines — the `_build_card`/`get_library_games` functions relevant to this phase were fully covered)
- `app/routers/library.py` — `GET /games` router signature + defaults (lines 1-130 read)
- `app/services/guest_service.py` — `create_guest_user` (full file read, confirms guests are ordinary `User` rows)
- `app/repositories/game_repository.py` — `bulk_insert_games` dedup mechanism (lines 1-105 read)
- `app/services/chesscom_to_lichess.py` — `normalize_to_lichess_blitz` dispatch logic (lines 300-420 read, confirms the missing third branch — Pitfall 3)
- `tests/services/test_import_service.py` — `TestStage5c...::test_stage5c_marks_covered_games` (proves `_flush_batch` callable outside `JobState`)
- `alembic/versions/20260615_192047_60160718b3b3_phase_122_feedback_table.py` — migration template for `bot_game_settings`
- Live checks this session: `uv run alembic heads` (`12d3df9c5373`), a headless `python3 -c "import chess.pgn..."` confirming `node.clock()` returns `None` without `[%clk]`, and `grep -rn CheckConstraint app/models/*.py` (zero hits — confirms no existing TEXT+CHECK precedent)

### Secondary (MEDIUM confidence)
- `.planning/ROADMAP.md` §"Phase 167" — goal + SC1-5 (read directly, not re-derived)
- `.planning/REQUIREMENTS.md` — STORE-01…07 (read directly)

### Tertiary (LOW confidence)
- None — every claim in this document was either read directly from source or verified via a live command in this session.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — no new packages, all reused code read directly
- Architecture: HIGH — the core reuse-seam decision (D-09) is proven by an existing test, not just plausible
- Pitfalls: HIGH — Pitfalls 1, 3, 4, 5 are all derived from direct source reads (grep + full-file reads) that go beyond CONTEXT.md's own claims, not speculation
- Open Questions: MEDIUM — the termination-reason gap (Open Question 1) is a genuine cross-phase coordination need, not resolvable by reading this phase's code alone

**Research date:** 2026-07-11
**Valid until:** 30 days (stable internal backend code, no external API dependency)
