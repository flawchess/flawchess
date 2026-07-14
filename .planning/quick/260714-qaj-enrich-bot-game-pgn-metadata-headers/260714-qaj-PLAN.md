---
phase: quick-260714-qaj
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - app/schemas/bots.py
  - app/services/bot_game_pgn.py
  - app/services/store_bot_game_service.py
  - app/repositories/game_repository.py
  - tests/services/test_bot_game_pgn.py
  - tests/services/test_store_bot_game_service.py
autonomous: true
requirements: []

must_haves:
  truths:
    - "A newly stored platform='flawchess' bot game's `games.pgn`, re-parsed with python-chess, yields the full D-03 header block: Event/Site/Date/Round/White/Black/Result/GameId/UTCDate/UTCTime/Elos/Title/Variant/TimeControl/ECO/Opening/Termination/RatingSource/PlayStyleBlend."
    - "`Site` is a working deep link containing the row's real auto-increment `games.id` (e.g. `https://flawchess.com/analysis?game_id=693117`), which only exists post-INSERT."
    - "Every header value that has a `games` column counterpart (White, Black, WhiteElo, BlackElo, ECO, Opening, Result, Termination) equals that column, or is ABSENT when the column is NULL — one source of truth, never a `?` / `0` placeholder."
    - "The per-move `[%clk]` comments on both colors survive the re-serialization (a stamped PGN still normalizes/parses)."
    - "A duplicate re-submit of the same `game_uuid` (D-11) does NOT rewrite the existing row's `pgn`."
    - "The non-standard tags (RatingSource, PlayStyleBlend) are emitted LAST, after every standard/lichess-recognized tag (D-06)."
  artifacts:
    - app/services/bot_game_pgn.py
    - tests/services/test_bot_game_pgn.py
  key_links:
    - "store_bot_game -> _flush_batch (INSERT) -> get_game_id_by_platform_game_id (game_id now exists) -> stamp_bot_game_headers(normalized, game_id, ...) -> game_repository.update_game_pgn -> the SINGLE existing session.commit() (D-10)."
    - "NormalizedGame (already carries white/black username+rating, opening_eco/name, result, termination, played_at) is the header builder's data source — NOT a re-derivation."
---

<objective>
Stamp a rich, lichess-comparable PGN header block onto stored `platform='flawchess'`
bot games, server-side, on the store path.

Purpose: today the stored PGN carries a near-empty Seven Tag Roster of `"?"`
placeholders (the client only sets `Result`/`Termination`/`TimeControl`). The `games`
columns are already correct; the PGN just doesn't reflect them. Making the PGN
self-describing means an exported/inspected bot game reads like a lichess game and
discloses the converted-rating provenance.

Output: a new pure `app/services/bot_game_pgn.py` header builder, a post-insert PGN
UPDATE in `store_bot_game_service`, and end-to-end tests that re-parse a stored row's
PGN with python-chess.
</objective>

<execution_context>
@$HOME/.claude/gsd-core/workflows/execute-plan.md
@$HOME/.claude/gsd-core/templates/summary.md
</execution_context>

<context>
@.planning/quick/260714-qaj-enrich-bot-game-pgn-metadata-headers/260714-qaj-CONTEXT.md
@CLAUDE.md

@app/services/store_bot_game_service.py
@app/services/normalization.py
@app/schemas/bots.py
@app/schemas/normalization.py
@app/repositories/game_repository.py
@tests/services/test_store_bot_game_service.py
</context>

<design_notes>
Findings verified against the installed python-chess (1.11.x) BEFORE planning. These are
load-bearing — do not re-litigate them, and do not deviate without re-verifying.

**F-1 — Header ORDER is fully controllable, but only via clear-then-rebuild.**
`chess.pgn.Headers` emits the Seven Tag Roster first (in STR order), then all other tags
in INSERTION order. The client PGN already carries `TimeControl` and `Termination` as
non-STR tags, so they would otherwise land BEFORE the newly-added ones and break D-06's
"non-standard tags last" rule. Verified working recipe:

```
game = chess.pgn.read_game(io.StringIO(pgn_text))
for key in list(game.headers.keys()):
    del game.headers[key]          # clears STR tags too, leaving {} — verified
for key, value in ordered_pairs:
    game.headers[key] = value
return str(game)
```

This reproduces D-03's exact block byte-for-byte, and the per-move `[%clk]` comments
survive `str(game)` unchanged (the mainline re-serializes as
`1. e4 { [%clk 0:09:58] } 1... e5 { [%clk 0:09:57] } 1-0` — the `1...` prefix before a
commented black move is normal python-chess output, not a regression).

**F-2 — `[Variant "Standard"]` is safe.** `str(game)` calls `game.board()`, which calls
`chess.variant.find_variant(headers["Variant"])` and RAISES on an unknown name.
`"Standard"` is a valid python-chess alias. Any other value would blow up serialization.

**F-3 — TimeControl must come from `request.tc_preset`, NOT `normalized.time_control_str`.**
`normalization._normalize_tc_str("600+0")` returns `"600"` (it strips a zero increment).
D-03 requires the `base+inc` seconds form `"600+0"`. Using the NormalizedGame column here
would silently drop the `+0`.

**F-4 — Stamp ONCE, post-insert. Do NOT touch `normalize_flawchess_game`.**
Everything the header block needs is already on the returned `NormalizedGame`
(`white_username`/`black_username`, `white_rating`/`black_rating`, `opening_eco`/
`opening_name`, `result`, `termination`, `played_at`, `platform_game_id`, `user_color`).
So the full stamp (including `Site`, which needs the post-INSERT `games.id`) happens once
in `store_bot_game_service` after `get_game_id_by_platform_game_id`. This means ONE extra
PGN parse + ONE single-row UPDATE (exactly D-07's cost estimate), no new params threaded
into the already-8-arg `normalize_flawchess_game`, and no second parse.
`_flush_batch` Stage 5 re-parses the RAW client PGN for `game_positions` — header-only
changes never touch the mainline, so this stays valid (D-07).

**F-5 — `RatingSource` must move to break a circular import.** It is currently declared in
`store_bot_game_service.py` and is used NOWHERE else (verified by grep). The new
`bot_game_pgn` module needs it, and `store_bot_game_service` imports `bot_game_pgn` →
move the alias to `app/schemas/bots.py` and import it in both. `store_bot_game_service`
re-binds the name in its own namespace via the import, so any future
`from app.services.store_bot_game_service import RatingSource` still resolves.
</design_notes>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: Pure header builder + repository UPDATE + RatingSource relocation</name>
  <files>app/schemas/bots.py, app/services/bot_game_pgn.py, app/repositories/game_repository.py, tests/services/test_bot_game_pgn.py</files>

  <behavior>
Unit tests for `stamp_bot_game_headers` (pure, no DB, no session):
- Happy path (user=white, anchor present, blended): re-parsing the returned PGN yields
  EXACTLY the D-03 header block — `Event`="FlawChess bot game", `Site`=
  "http://localhost:5173/analysis?game_id=693117" (test settings' FRONTEND_URL),
  `Date`/`UTCDate` from `played_at` as `YYYY.MM.DD`, `Round`="-", `White`/`Black` from the
  NormalizedGame usernames, `Result`, `GameId`=the canonical uuid, `UTCTime` as `HH:MM:SS`,
  `WhiteElo`=player rating, `BlackElo`=bot elo, `BlackTitle`="BOT", `Variant`="Standard",
  `TimeControl`="600+0" (the tc_preset), `ECO`/`Opening`, `Termination`, `RatingSource`,
  `PlayStyleBlend`="0.50".
- Header ORDER: `list(reparsed.headers.keys())` equals the D-03 order exactly; assert the
  last two keys are `RatingSource`, `PlayStyleBlend` (D-06).
- D-05 omission: `white_rating=None` + `rating_source=None` → `"WhiteElo" not in headers`
  AND `"RatingSource" not in headers` (never `"?"`/`"0"`), while `BlackElo` is still present.
- user_color="black": `WhiteTitle`="BOT", `"BlackTitle" not in headers`, `WhiteElo`=bot elo,
  `BlackElo`=player rating (the BOT-title tag follows the BOT's color, not a fixed side).
- `opening_eco`/`opening_name` None → `ECO`/`Opening` omitted (never a literal "None").
- `[%clk]` survival: every mainline node of the re-parsed stamped PGN has a non-None
  `.clock()` for BOTH colors.
- `PlayStyleBlend` formatting: `0.5` → `"0.50"`, `1.0` → `"1.00"`, `0.0` → `"0.00"` (2dp).
- FRONTEND_URL with a trailing slash does not produce a `//analysis` double slash.
  </behavior>

  <action>
Do these three edits, then write `tests/services/test_bot_game_pgn.py`.

**(a) `app/schemas/bots.py`** — move the `RatingSource` Literal alias here (per F-5):
`RatingSource = Literal["lichess", "chesscom", "blended"]`, with a short docstring/comment
naming it as the `bot_game_settings.rating_source` closed vocabulary (the model already
CHECKs those three values). Import `Literal` from `typing`.

**(b) `app/services/bot_game_pgn.py`** (NEW) — a pure module, no session, no DB, no I/O
beyond reading `settings.FRONTEND_URL`. Module docstring: names quick-260714-qaj, states
that this is the SINGLE writer of the stored bot-game header block, cites D-01
(server-side only; whatever the client sent for the Seven Tag Roster is OVERWRITTEN,
never trusted) and D-03/D-05/D-06.

Named constants (CLAUDE.md: no magic strings) for the literal VALUES the block asserts:
`PGN_EVENT = "FlawChess bot game"`, `PGN_ROUND = "-"`, `PGN_VARIANT = "Standard"`
(with a comment citing F-2: python-chess validates this on serialization),
`PGN_BOT_TITLE = "BOT"`, plus private `_PGN_DATE_FORMAT = "%Y.%m.%d"`,
`_PGN_TIME_FORMAT = "%H:%M:%S"`, `_PLAY_STYLE_BLEND_DECIMALS = 2`, and a
`_SITE_PATH_TEMPLATE` for the `/analysis?game_id={game_id}` deep link.
Header KEY names appear exactly once each, inside the single ordered builder list below —
that list IS the spec, so hoisting 20 one-use key constants would only add noise. Do not
create them. (The color-conditional Elo/Title keys are the one place a key name recurs;
write both branches out explicitly rather than f-string-assembling
`f"{color}Elo"` — keep it grep-able and ty-legible.)

Public function:

```
def stamp_bot_game_headers(
    *,
    normalized: NormalizedGame,
    game_id: int,
    tc_preset: str,
    rating_source: RatingSource | None,
    play_style_blend: float,
) -> str:
```

Body:
1. Re-parse `normalized.pgn` via `chess.pgn.read_game(io.StringIO(...))`. A `None` here is
   structurally unreachable (`normalize_flawchess_game` already parsed this exact string
   successfully) — `raise RuntimeError("bot-game PGN failed to re-parse for header stamping")`
   with NO variables in the message (Sentry grouping rule). The caller's existing
   `try/except` in `store_bot_game` is what captures it.
2. Same guard for `normalized.played_at is None` (typed `| None` on NormalizedGame, always
   set by `normalize_flawchess_game`) — raise, do not silently substitute `now()`. This is
   also what satisfies `ty` on the `.strftime` calls.
3. Build an `ordered: list[tuple[str, str]]` in EXACTLY the D-03 order, appending
   conditionally so omitted tags never appear:
   - Event = `PGN_EVENT`
   - Site = `settings.FRONTEND_URL.rstrip("/")` + the deep-link path with `game_id`
   - Date = played_at.strftime(_PGN_DATE_FORMAT)
   - Round = `PGN_ROUND`
   - White = `normalized.white_username`; Black = `normalized.black_username`
   - Result = `normalized.result`
   - GameId = `normalized.platform_game_id` (already canonicalized by the schema's
     `validate_game_uuid`)
   - UTCDate = same as Date; UTCTime = played_at.strftime(_PGN_TIME_FORMAT)
   - WhiteElo — append ONLY if `normalized.white_rating is not None` (D-05)
   - BlackElo — append ONLY if `normalized.black_rating is not None` (D-05)
   - WhiteTitle / BlackTitle — append `PGN_BOT_TITLE` on the BOT's color ONLY, i.e. the
     color OPPOSITE `normalized.user_color`. Never both.
   - Variant = `PGN_VARIANT`
   - TimeControl = `tc_preset` (F-3: NOT `normalized.time_control_str`, which strips `+0`)
   - ECO / Opening — append ONLY if the respective NormalizedGame field is not None
   - Termination = `normalized.termination` (FlawChess closed vocab, D-04 — do NOT map to
     lichess's flat "Normal")
   - RatingSource — append ONLY if `rating_source is not None` (D-05)
   - PlayStyleBlend = `f"{play_style_blend:.{_PLAY_STYLE_BLEND_DECIMALS}f}"`
   Per D-04 emit NO `WhiteRatingDiff`/`BlackRatingDiff` (bot games are unrated) and no
   `SetUp`/`FEN`.
4. Clear every existing header (`for key in list(game.headers.keys()): del game.headers[key]`),
   then assign the ordered pairs in sequence (F-1), and `return str(game)`.
Keep the function under the CLAUDE.md nesting/LOC limits — it is a flat build-list-then-emit,
so it should sit around 40 logic LOC with depth 1-2. If the pair-building grows, split the
ordered-pair construction into a private `_build_header_pairs(...) -> list[tuple[str, str]]`
and keep `stamp_bot_game_headers` as the parse/clear/emit shell.

**(c) `app/repositories/game_repository.py`** — add:

```
async def update_game_pgn(session: AsyncSession, game_id: int, pgn: str) -> None:
```
A single `update(Game).where(Game.id == game_id).values(pgn=pgn)` execute. Docstring: cites
quick-260714-qaj / D-07 (the `Site` deep link needs the auto-increment PK, which does not
exist at normalize time), and states it does NOT commit — the caller owns the transaction
(D-10). Import `update` from sqlalchemy alongside the existing imports.

Write `tests/services/test_bot_game_pgn.py` covering every case in `<behavior>`. Construct
`NormalizedGame` fixtures directly (it is a plain Pydantic model — no DB needed); reuse the
Scholar's-Mate-with-`[%clk]` PGN string shape already in
`tests/services/test_store_bot_game_service.py` (`_PGN_CHECKMATE`) so the clk-survival
assertion has real clock comments to preserve. Re-parse the returned string with
`chess.pgn.read_game(io.StringIO(...))` and assert against `.headers` — assert on the
PARSED headers, never by string-matching the raw PGN text.
  </action>

  <verify>
    <automated>uv run pytest tests/services/test_bot_game_pgn.py -x -q</automated>
  </verify>

  <done>
`stamp_bot_game_headers` returns a PGN whose re-parsed headers are exactly the D-03 block in
the D-03 order, with the D-05 omissions honored and `[%clk]` intact on both colors.
`RatingSource` lives in `app/schemas/bots.py`. `game_repository.update_game_pgn` exists and
does not commit. `normalize_flawchess_game` is UNCHANGED. `frontend/` is UNTOUCHED (D-01).
  </done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: Wire the post-insert stamp into store_bot_game, end-to-end</name>
  <files>app/services/store_bot_game_service.py, tests/services/test_store_bot_game_service.py</files>

  <behavior>
New `TestPgnHeaders` class in `tests/services/test_store_bot_game_service.py` — every
assertion re-reads `games.pgn` FROM THE DB and re-parses it with `chess.pgn.read_game`
(never asserts on the in-memory return value):
- Anchored user, plays white: the stored row's re-parsed headers carry the full D-03 block;
  `Site` == `f"{settings.FRONTEND_URL.rstrip('/')}/analysis?game_id={response.game_id}"`
  with the REAL returned `game_id` (proves the post-INSERT id reached the PGN, D-07);
  `TimeControl` == `"180+2"` (the tc_preset); `Termination` == `"checkmate"`;
  `PlayStyleBlend` == `"0.50"`; `Event`/`Round`/`Variant` == the named constants.
- Column/header consistency (the D-01 "one source of truth" invariant): for the stored
  `Game` row, `headers["White"] == game.white_username`, `headers["Black"] ==
  game.black_username`, `int(headers["WhiteElo"]) == game.white_rating`, `int(headers
  ["BlackElo"]) == game.black_rating`, `headers["ECO"] == game.opening_eco`,
  `headers["Opening"] == game.opening_name`, `headers["Result"] == game.result`,
  `headers["Termination"] == game.termination` — and the header is ABSENT wherever the
  column is NULL.
- D-05 no-anchor case: user with NO `user_rating_anchors` row for the TC bucket → the
  stored PGN has NO `WhiteElo` and NO `RatingSource` tag (assert `not in headers`), but
  DOES have `BlackElo` == bot_elo. `games.white_rating` is NULL, confirming header and
  column agree on absence.
- user plays black: `WhiteTitle` == "BOT", no `BlackTitle`.
- `[%clk]` end-to-end: the stored PGN's re-parsed mainline still has a non-None `.clock()`
  on both colors (a stamped PGN would otherwise be rejected by
  `normalize_flawchess_game`'s own clock gate on a re-import).
- **D-11 duplicate re-submit does NOT rewrite the PGN**: store once (capture
  `game_id` + the stored `pgn` string), then call `store_bot_game` again with the SAME
  `game_uuid` but a materially DIFFERENT `pgn` body (e.g. a different mainline) and a
  different `bot_elo`; assert the response is `created=False` with the same `game_id`, and
  that the DB row's `pgn` is BYTE-IDENTICAL to the first stored value (the second
  submission's content must not leak in). Refresh/expire the ORM identity map before the
  re-read so the assertion reads the DB, not a cached instance.
  </behavior>

  <action>
In `app/services/store_bot_game_service.py`:

1. Replace the local `RatingSource = Literal[...]` declaration with
   `from app.schemas.bots import RatingSource, StoreBotGameRequest, StoreBotGameResponse`
   (F-5). Drop the now-unused `from typing import Literal` if nothing else needs it.
2. Import `stamp_bot_game_headers` from `app.services.bot_game_pgn`.
3. Inside the EXISTING `try:` block, inside the EXISTING `if created:` branch (right
   alongside the `session.add(BotGameSettings(...))`), add the header stamp + UPDATE:

   ```
   stamped_pgn = stamp_bot_game_headers(
       normalized=normalized,
       game_id=game_id,
       tc_preset=request.tc_preset,
       rating_source=rating_source,
       play_style_blend=request.play_style_blend,
   )
   await game_repository.update_game_pgn(session, game_id, stamped_pgn)
   ```

   The `created` guard is LOAD-BEARING (D-07/D-11): a duplicate re-submit must never
   rewrite the existing row's PGN. Do NOT hoist this out of the `if created:` branch.
   Do NOT add a second `session.commit()` — the existing single commit at the end of the
   function (D-10) covers the INSERT + the UPDATE + the settings row in one transaction.

4. Update the module docstring's flow sentence to mention the post-insert header stamp +
   targeted PGN UPDATE, and add a short comment at the stamp site explaining WHY it is
   post-insert (the `Site` deep link needs the auto-increment `games.id`, D-07) and why the
   `_flush_batch` Stage 5 position parse is unaffected (header-only change, mainline
   untouched).

Then add `TestPgnHeaders` to `tests/services/test_store_bot_game_service.py` covering every
case in `<behavior>`. Reuse the module's existing `_make_request` / `ensure_test_user` /
`upsert_anchor` helpers and the rollback-scoped `db_session` fixture; extend `_make_request`
with a `bot_elo` override param only if the D-11 test needs it. Import `settings` from
`app.core.config` for the `Site` assertion (do NOT hardcode the localhost URL — the test
must assert against the same config value the code reads).

Finally, re-run the two adjacent bot-PGN test modules (`tests/test_bot_pgn_clk_roundtrip.py`,
`tests/routers/test_bots.py`) — they exercise the same store path and may assert on the
stored PGN. If either breaks, fix the ASSERTION to the new (richer) expected headers; do not
weaken the stamping to preserve an old assertion.
  </action>

  <verify>
    <automated>uv run pytest tests/services/test_store_bot_game_service.py tests/services/test_normalization.py tests/test_bot_pgn_clk_roundtrip.py tests/routers/test_bots.py -x -q</automated>
  </verify>

  <done>
Storing a bot game writes the full D-03 header block into `games.pgn`, with a `Site` deep
link carrying the real post-INSERT `game_id`. Every header agrees with its `games` column
(or is absent when the column is NULL). A duplicate re-submit returns `created=False` and
leaves the stored PGN byte-identical. `[%clk]` survives end-to-end.
  </done>
</task>

<task type="auto">
  <name>Task 3: Full pre-merge gate</name>
  <files>app/, tests/</files>

  <action>
Run the mandatory backend gate and resolve every finding:

```
uv run ruff format app/ tests/
uv run ruff check app/ tests/ --fix
uv run ty check app/ tests/
uv run pytest -n auto -x
```

`ty` must report ZERO errors. Expect the `played_at` / rating `| None` narrowing to be where
`ty` pushes back — fix it with the explicit `raise` guards specified in Task 1, NOT with a
`# ty: ignore`.

If `ruff format` rewrites anything, commit it separately with a `style(quick-260714-qaj):`
prefix (CLAUDE.md).

The frontend is NOT part of this task's gate — `frontend/` must have ZERO changes from this
plan (D-01). Confirm with `git status frontend/` that the only frontend entry is the
pre-existing, unrelated, UNCOMMITTED `frontend/src/components/bots/GameResultDialog.tsx`
edit. Do NOT stage it, do NOT commit it, do NOT revert it.
  </action>

  <verify>
    <automated>uv run ruff format --check app/ tests/ && uv run ruff check app/ tests/ && uv run ty check app/ tests/ && uv run pytest -n auto -x -q</automated>
  </verify>

  <done>
ruff format/check clean, `ty check` reports zero errors, the full backend suite passes under
`-n auto`, and `git status` shows no staged/committed change under `frontend/`.
  </done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| client → `POST /bots/games` | The client-POSTed PGN (its Seven Tag Roster, `Elo`, `White`/`Black`, `Site`) is untrusted input. |
| service → `games.pgn` (DB) | The stamped PGN is persisted and later re-parsed by the import/analysis pipeline. |

## STRIDE Threat Register

| Threat ID | Category | Component | Severity | Disposition | Mitigation Plan |
|-----------|----------|-----------|----------|-------------|-----------------|
| T-qaj-01 | Spoofing | client-supplied PGN headers (`WhiteElo`, `White`, `Site`) | high | mitigate | D-01: the builder CLEARS every incoming header before rebuilding (F-1). Nothing the client sent for Event/Site/White/Black/Elo/Title survives. Every value is sourced from `NormalizedGame` (server-derived) or a module constant — never from `game.headers` as read. |
| T-qaj-02 | Tampering | `game_repository.update_game_pgn` | medium | mitigate | The UPDATE is keyed on the `game_id` returned by `get_game_id_by_platform_game_id`, which is already scoped by `user_id` — no cross-user write is reachable. It runs inside the service's single transaction (D-10); a failure rolls back the INSERT too. |
| T-qaj-03 | Tampering | duplicate re-submit rewriting a stored PGN | medium | mitigate | The stamp + UPDATE sit inside the existing `if created:` guard (D-11). A second POST with the same `game_uuid` but a forged PGN body cannot overwrite the original row. Asserted end-to-end in Task 2. |
| T-qaj-04 | Denial of Service | PGN re-serialization cost | low | accept | One extra parse + `str(game)` (~4 KB) + one single-row UPDATE per stored bot game (D-07's own cost estimate). PGN length is already bounded by `MAX_BOT_PGN_LENGTH` (100 KB) at the schema boundary. |
| T-qaj-05 | Tampering | `[Variant]` header injection into `str(game)` | low | mitigate | F-2: python-chess RAISES on an unknown `Variant` during serialization. `Variant` is set from the `PGN_VARIANT` constant AFTER the clear, so a hostile client `[Variant "…"]` is discarded before it can reach `find_variant`. |
| T-qaj-SC | Tampering | npm/pip/cargo installs | high | mitigate | N/A — this plan adds ZERO new dependencies. `python-chess` and `sqlalchemy` are already in the lockfile. No package-manager install task exists, so no legitimacy checkpoint is required. |
</threat_model>

<verification>
1. `uv run pytest tests/services/test_bot_game_pgn.py tests/services/test_store_bot_game_service.py -q` — green.
2. Full gate (Task 3): `ruff format --check` + `ruff check` + `ty check` (zero errors) + `pytest -n auto`.
3. `git status frontend/` shows only the pre-existing uncommitted `GameResultDialog.tsx` (D-01 — backend-only).
4. `git diff --stat app/services/normalization.py` is EMPTY (the normalizer is unchanged, F-4).
5. No backfill script was created (D-08): `git status scripts/` is clean.
</verification>

<success_criteria>
- A newly stored bot game's `games.pgn`, re-parsed with python-chess, yields the exact D-03
  header block in the D-03 order, with `RatingSource`/`PlayStyleBlend` last (D-06).
- `Site` contains the row's real auto-increment `games.id`.
- Missing anchor → `WhiteElo`/`BlackElo` (player color) and `RatingSource` are ABSENT, not
  `"?"`/`"0"` (D-05).
- A duplicate re-submit leaves the stored PGN byte-identical (D-11).
- `[%clk]` on both colors survives the re-serialization.
- `frontend/src/lib/botGamePgn.ts` and the rest of `frontend/` are untouched (D-01);
  the rating derivation is untouched (D-02); no backfill script exists (D-08).
- Backend gate green: ruff format, ruff check, `ty check` (zero errors), `pytest -n auto`.
</success_criteria>

<output>
Create `.planning/quick/260714-qaj-enrich-bot-game-pgn-metadata-headers/260714-qaj-SUMMARY.md` when done.
</output>
