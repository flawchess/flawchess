# Phase 167: Backend Store-on-Finish - Context

**Gathered:** 2026-07-11
**Status:** Ready for planning

<domain>
## Phase Boundary

Deliver a **backend endpoint that persists one finished bot game** as a
first-class `platform='flawchess'` Library game. A new `normalize_flawchess_game`
builds a `NormalizedGame` from a client-POSTed bot PGN + settings; that flows
through the **existing** persistence path (`_flush_batch` → Zobrist position rows
→ cold-drain eval pickup) so the game is analyzable exactly like an imported
chess.com/lichess game. Adds a bot-settings side table, a **server-computed**
save-time converted player rating, UUID-idempotency, and analytics exclusion.

**In scope:** the store endpoint + request schema, `normalize_flawchess_game`,
the bot-settings side table + migration, extending the `Platform` Literal with
`flawchess`, server-side rating derivation from `user_rating_anchors`, idempotency
on the existing unique constraint, and default-excluding `flawchess` from analytics
in the shared filter.

**NOT in scope (other phases):** the game loop / clocks / PGN `[%clk]` *generation*
(Phase 169 emits the PGN this endpoint consumes); the Bots page, setup screen, and
the client call site / guest caveat UI (Phase 171); localStorage resume + store-once
orchestration (Phase 170); the calibration harness (Phase 168). This phase is fully
independent of all engine work and parallelizable with Phase 166.

</domain>

<decisions>
## Implementation Decisions

> User selected **"You decide"** — all decisions below are Claude's grounded
> calls from codebase scouting, honoring the locked ROADMAP SC / REQUIREMENTS /
> SEED-091. Nothing here re-opens a locked requirement. The planner may refine the
> "Discretion" items.

### Analytics exclusion + `is_computer_game` (Area 1)
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

### Player-rating conversion (Area 2)
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

### Persistence reuse seam (Area 3)
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

### Endpoint contract + UUID + guest auth (Area 4)
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

### Bot-settings side table (Area 5 — mostly discretion, shape locked)
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

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Phase / milestone scope
- `.planning/ROADMAP.md` §"Phase 167" — goal + the 5 success criteria this phase
  is verified against (SC1–SC5).
- `.planning/REQUIREMENTS.md` — STORE-01…STORE-07 (the locked store requirements)
  + the "Non-Goals" table (no server sessions/websockets, no adaptive difficulty).
- `.planning/seeds/SEED-091-flawchess-bot-play-milestone.md` §"Locked design
  decisions" #1 (store-on-finish via existing normalization path, `platform='flawchess'`)
  and #5 (player/bot ELO handling — convert at save time, bot nominal in opponent
  column). **NOTE the correction:** decision #1's "analytics inclusion/exclusion
  for free via the platform filter" is FACTUALLY WRONG (see D-01/D-02) — exclusion
  must be implemented in `apply_game_filters`.

### Persistence / normalization path this phase reuses
- `app/schemas/normalization.py` — `NormalizedGame` Pydantic model + the `Platform`
  Literal to extend (D-17).
- `app/services/normalization.py` — `normalize_chesscom_game` / `normalize_lichess_game`
  are the templates for the new `normalize_flawchess_game`.
- `app/services/import_service.py` — `_flush_batch` (D-09/D-10, WR-05 no-commit),
  `_collect_position_rows` (Zobrist positions), Stage-5c eval-coverage gate; and the
  `JobState`/`_flush_batch_with_progress`/`run_import` machinery this phase does NOT reuse.
- `app/services/zobrist.py` — `process_game_pgn` / `PlyData` (single-parse → hashes).
- `app/models/game.py` — the `games` table: `uq_games_user_platform_game_id`
  (idempotency target, D-11), the player/opponent rating columns (D-08), clock
  columns, `is_computer_game`/`rated` (D-04), `evals_completed_at` cold-drain gate.

### Rating conversion machinery (server-side)
- `app/repositories/user_rating_anchors_repository.py` — `fetch_anchors_for_user`
  (returns per-TC-bucket blended lichess-equivalent `anchor_rating` + `n_lichess_games`/
  `n_chesscom_games` for `rating_source`), `has_any_anchor`.
- `app/models/user_rating_anchors.py` — the anchor table schema.
- `frontend/src/hooks/useMaiaEloDefault.ts` — the frontend twin (reference for the
  conversion semantics; the *backend* computes authoritatively per D-05).

### Analytics exclusion seam
- `app/repositories/query_utils.py` — `apply_game_filters` (D-02: add the
  `flawchess` default-exclude here) + `is_opponent_expr`.
- `app/services/library_service.py` — `get_library_games` (D-03: the one surface
  that must INCLUDE flawchess).

### Guest / auth
- `app/services/guest_service.py` — guests are real `User` rows with `is_guest=True`
  (D-13); the standard authed dependency covers them.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `import_service._flush_batch(session, batch, user_id)` — the single-parse insert
  path (games + Zobrist positions + ply_count/result_fen + eval-coverage gate).
  Call with a 1-item batch to persist a bot game identically to an imported game
  (D-09). Returns count of *newly* inserted games → `0` = duplicate = idempotent
  success (D-11).
- `normalize_chesscom_game` / `normalize_lichess_game` (`app/services/normalization.py`)
  — copy their structure for `normalize_flawchess_game`; both return `NormalizedGame`.
- `user_rating_anchors_repository.fetch_anchors_for_user` — server-side TC-bucket →
  lichess-equivalent rating, exactly what STORE-03 needs (D-05).
- `guest_service.create_guest_user` — confirms guests are ordinary `User` rows, so
  one authed endpoint serves users + guests (D-13).

### Established Patterns
- Routers use `APIRouter(prefix="/resource", ...)` + relative decorator paths;
  business logic lives in `app/services/`, DB access in `app/repositories/`
  (D-12 — thin `bots` router → new service).
- `apply_game_filters` is the ONE shared filter — the platform-exclusion rule
  belongs there, not scattered (D-02).
- DB rules: mandatory `ForeignKey` + `ondelete`; low-cardinality domain columns use
  `TEXT + CHECK` (not native ENUM) — applies to the side table + `rating_source`
  (D-16). `games.platform` currently has NO CHECK constraint (plain `String(20)`),
  so the new `flawchess` value needs only the `Platform` Literal extended (D-17),
  no DB migration for the platform value.
- Pydantic v2 at the boundary; the server parses the PGN for all derived fields
  rather than trusting the client (D-14).

### Integration Points
- POST `/bots/games` → `store_service.store_bot_game` → `normalize_flawchess_game`
  → `_flush_batch` → commit → side-table insert. The `NormalizedGame` → persistence
  seam is the reuse boundary (identical to import).
- Cold eval drain: bot game lands `evals_completed_at IS NULL`, drain analyzes it
  automatically; drain's `is_guest` filter provides the guest not-auto-analyze
  behavior with no new code.
- Downstream phases: Phase 170 needs the returned game id + idempotent re-submit
  (store-once); Phase 171 calls this endpoint from the Bots page and shows the guest
  caveat.

</code_context>

<specifics>
## Specific Ideas

- Opponent display "vs FlawChess Bot (1400)" — bot username fixed to `"FlawChess Bot"`,
  bot nominal ELO in the opponent-color rating column (SEED-091 #5 / D-08).
- Bot games are `rated=False` and `is_computer_game=True` — casual computer games,
  kept out of the default (imported-human) analytics population by platform (D-02/D-04).
- The `play_style_blend` stored is Phase 166's blend parameter `b ∈ [0,1]` (D-01 of
  Phase 166), NOT the analysis-board temperature slider — store the raw blend value
  for later calibration (STORE-04 / CALX-01).

</specifics>

<deferred>
## Deferred Ideas

- **Post-launch curve fitting** (player rating vs result vs bot config to relabel
  bots with measured ELO) — explicitly a later milestone (CALX-01 / SEED-091 #3);
  this phase only *records* the settings + converted rating that make it possible.
- **Frontend flawchess filter chip / Bots-vs-Library surfacing UX** — display
  wiring belongs to Phase 171; this phase only stops analytics from hiding bot games
  and ensures the Library games query can include them (D-03).

None outside milestone scope — discussion stayed within the phase.

</deferred>

---

*Phase: 167-backend-store-on-finish*
*Context gathered: 2026-07-11*
