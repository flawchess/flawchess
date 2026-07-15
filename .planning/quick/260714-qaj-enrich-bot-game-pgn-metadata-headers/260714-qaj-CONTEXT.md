# Quick Task 260714-qaj: enrich bot game PGN metadata headers - Context

**Gathered:** 2026-07-14
**Status:** Ready for planning

<domain>
## Task Boundary

Stored `platform='flawchess'` bot games currently carry a near-empty PGN header block. The
client (`frontend/src/lib/botGamePgn.ts::finalizeBotPgn`) sets only `Result`, `Termination`,
and `TimeControl`; chess.js fills the rest of the Seven Tag Roster with `"?"` placeholders, and
`normalize_flawchess_game` stores `pgn=pgn_text` verbatim. Result:

```
[Event "?"]
[Site "?"]
[Date "????.??.??"]
[Round "?"]
[White "?"]
[Black "?"]
[Result "1-0"]
[TimeControl "600+0"]
[Termination "resignation"]
```

Goal: stamp a rich, lichess-comparable header block onto the stored PGN using
server-authoritative data.

</domain>

<decisions>
## Implementation Decisions

### D-01: Headers are stamped SERVER-SIDE, not by the client (LOCKED)

The header block is written on the backend during the store path, NOT in
`botGamePgn.ts`. Rationale:

- Ratings must never be client-trusted (existing threat T-167-01; the whole
  reason `store_bot_game_service` derives `player_rating` from
  `user_rating_anchors` server-side and the request schema has no rating field).
- The username (`resolve_player_username`), the opening (`find_opening` ->
  `opening_eco` / `opening_name`), and `played_at` are ALREADY computed
  server-side. Re-deriving them in the client would duplicate logic and could
  drift from the DB columns.
- Keeps the PGN header block and the `games` columns guaranteed consistent —
  one source of truth.

The frozen client PGN contract (per-move `[%clk]` for both colors + closed-vocab
`[Termination]` + `[Result]`) stays exactly as-is. `botGamePgn.ts` needs no
change. Whatever the client sends for the Seven Tag Roster is OVERWRITTEN, never
trusted.

### D-02: Rating columns are already correct — do NOT change them (LOCKED)

Investigated during discussion: `games.white_rating` / `games.black_rating` for
bot games is already populated from `user_rating_anchors.anchor_rating`, which
is by construction the **Lichess-equivalent blended median** (per-game ChessGoals
conversion of chess.com ratings pooled with native lichess ratings — see
`app/models/user_rating_anchors.py` module docstring).

Empirical proof from the dev DB (user_id 28):

| TC bucket | anchor_rating | chesscom_median_native | lichess_median_native |
|-----------|---------------|------------------------|-----------------------|
| blitz     | 1533          | 1167                   | NULL                  |
| rapid     | 1788          | 1461                   | 1763                  |

The stored `black_rating = 1533` on a blitz bot game is the CONVERTED
Lichess-equivalent, not the raw chess.com 1167. **No change is needed to the
rating columns or to `store_bot_game_service`'s rating derivation.** The real
gap the user observed is that the PGN carries no `Elo` tag at all.

### D-03: Target header block (LOCKED)

For game 693117 (player White, bot Black, 600+0 rapid, resignation):

```
[Event "FlawChess bot game"]
[Site "https://flawchess.com/analysis?game_id=693117"]
[Date "2026.07.14"]
[Round "-"]
[White "aimfeld"]
[Black "FlawChess Bot"]
[Result "1-0"]
[GameId "f81d4fae-7dec-11d0-a765-00a0c91e6bf6"]
[UTCDate "2026.07.14"]
[UTCTime "16:20:42"]
[WhiteElo "1788"]
[BlackElo "1100"]
[BlackTitle "BOT"]
[Variant "Standard"]
[TimeControl "600+0"]
[ECO "A40"]
[Opening "Englund Gambit"]
[Termination "resignation"]
[RatingSource "blended"]
[PlayStyleBlend "0.50"]
```

Field-by-field source of truth:

| Header | Value | Source |
|--------|-------|--------|
| `Event` | literal `"FlawChess bot game"` | constant (user choice; no TC bucket interpolation) |
| `Site` | `{FRONTEND_URL}/analysis?game_id={game_id}` | `settings.FRONTEND_URL` (already exists in `app/core/config.py`; prod = `https://flawchess.com`) + the post-insert `game_id` |
| `Date` / `UTCDate` | `played_at` date, `YYYY.MM.DD` | `NormalizedGame.played_at` (UTC) |
| `Round` | literal `"-"` | lichess convention |
| `White` / `Black` | resolved player username / `FLAWCHESS_BOT_USERNAME` | already computed by `resolve_player_username` + `normalization.FLAWCHESS_BOT_USERNAME` |
| `Result` | unchanged | already set by the client, validated by the normalizer |
| `GameId` | the canonicalized `game_uuid` | `StoreBotGameRequest.game_uuid` (= `platform_game_id`) |
| `UTCTime` | `played_at` time, `HH:MM:SS` | `NormalizedGame.played_at` |
| `WhiteElo` / `BlackElo` | player: `anchor_rating`; bot: `bot_elo` | same values already going into `white_rating`/`black_rating` |
| `WhiteTitle` / `BlackTitle` | `"BOT"` on the BOT's color only | derived from `user_color` |
| `Variant` | literal `"Standard"` | constant |
| `TimeControl` | `tc_preset` e.g. `"600+0"` | unchanged (client already sets it; keep the `base+inc` seconds form) |
| `ECO` / `Opening` | `opening_eco` / `opening_name` | `find_opening(pgn_text)` — already called by the normalizer |
| `Termination` | unchanged | FlawChess closed vocab (see D-04) |
| `RatingSource` | `"lichess"` / `"chesscom"` / `"blended"` | `_derive_rating_source(...)` in `store_bot_game_service` |
| `PlayStyleBlend` | `"0.50"` (2dp) | `StoreBotGameRequest.play_style_blend` |

### D-04: Deliberate deviations from the lichess header set (LOCKED)

- **No `WhiteRatingDiff` / `BlackRatingDiff`.** Bot games are unrated
  (`rated=False`); nothing moves. Emitting `"+0"` would be a lie.
- **`Termination` keeps the FlawChess closed vocabulary**
  (`checkmate` / `resignation` / `timeout` / `draw` / `abandoned` / `unknown`), NOT
  lichess's flat `"Normal"`. `_FLAWCHESS_TERMINATION_HEADER_MAP` already parses it
  and it is strictly more informative.
- **No `SetUp` / `FEN`.** Bot games start from the standard position.

### D-05: Missing-anchor case — OMIT the Elo tag (LOCKED)

When the user has no `user_rating_anchors` row for the game's TC bucket (guest,
or no imported games in that bucket), `player_rating` is `None` today and
`white_rating`/`black_rating` is NULL. In that case, **omit the player-color
`Elo` tag entirely** — do NOT write `"?"` or `"0"`. Same for `RatingSource`:
omit it when `rating_source is None`. The bot-color `Elo` is always present
(`bot_elo` is a required request field).

### D-06: Non-standard tags to include (LOCKED — user choice)

Both `RatingSource` and `PlayStyleBlend` are included. Rationale:

- `RatingSource` discloses that the player `Elo` is a CONVERTED
  Lichess-equivalent ESTIMATE derived from their chess.com / lichess history —
  not a real rating earned on FlawChess. Given that the anchor conversion is the
  whole point, this disclosure belongs in the PGN.
- `PlayStyleBlend` (the Maia/Stockfish blend `b` in `[0, 1]`) makes a stored bot
  game reproducible. It lives only in `bot_game_settings` today and is invisible
  in an exported PGN.

Both are non-standard tags. They must be appended AFTER the standard/lichess-
recognized tags so a strict PGN reader that stops at unknown keys still gets the
full standard block. python-chess and chess.js both tolerate unknown tags.

### D-07: `Site` deep link requires a post-insert PGN UPDATE (LOCKED — user choice)

`games.id` is an auto-increment PK, so it does not exist at
`normalize_flawchess_game` time. The user chose the deep-link `Site` over a
static `https://flawchess.com` + `[GameId]`-only variant. Therefore the store
path becomes:

1. `normalize_flawchess_game(...)` stamps every header EXCEPT `Site` (or stamps
   a placeholder), returns the `NormalizedGame`.
2. `_flush_batch` inserts the game + positions (Stage 5 re-parses the PGN for
   `game_positions` — header-only changes do not affect the mainline, so this
   stays valid).
3. `store_bot_game_service` already looks up `game_id` right after `_flush_batch`
   (existing code, Pitfall 2). With the id in hand, re-stamp `Site` and issue a
   targeted `UPDATE games SET pgn = :pgn WHERE id = :game_id` **inside the same
   transaction** (the service already owns the single commit, D-10).

Cost: one extra `str(game)` serialization (~4 KB) + one single-row UPDATE per
stored bot game. Negligible. It MUST be guarded by the existing `created` flag
semantics so a duplicate re-submit (D-11 idempotency) does not rewrite the PGN
of an existing row.

### D-08: No backfill (LOCKED — user choice)

Existing `platform='flawchess'` rows (5 in dev; bot play is still beta in prod)
keep their thin headers. Their DB columns are already correct, so nothing is
functionally broken. Go-forward only — do NOT write a `scripts/backfill_*.py`.

### Claude's Discretion

- Exactly where the header-stamping logic lives (a new private helper in
  `app/services/normalization.py` alongside `normalize_flawchess_game`, vs. a
  small dedicated module). Prefer whatever keeps `normalize_flawchess_game`
  under the CLAUDE.md function-size limits — it is already long, so a helper is
  likely warranted.
- Whether to re-serialize via python-chess (`chess.pgn.Game` -> `str(game)`,
  which preserves the `[%clk]` comments) or to splice the header block textually.
  python-chess round-trip is strongly preferred (the module already parses the
  game; hand-templating PGN is explicitly warned against in the client module's
  docstring for the same reason).
- The precise repository function signature for the PGN UPDATE
  (`game_repository`).

</decisions>

<specifics>
## Specific Ideas

Reference lichess bot-game header block the user supplied as the target shape:

```
[Event "rated rapid game"]
[Site "https://lichess.org/LRPhWXAs"]
[Date "2025.11.18"]
[Round "-"]
[White "maia5"]
[Black "aimfeld"]
[Result "0-1"]
[GameId "LRPhWXAs"]
[UTCDate "2025.11.18"]
[UTCTime "18:54:16"]
[WhiteElo "1618"]
[BlackElo "1703"]
[WhiteRatingDiff "-5"]
[BlackRatingDiff "+2"]
[WhiteTitle "BOT"]
[Variant "Standard"]
[TimeControl "600+5"]
[ECO "B01"]
[Opening "Scandinavian Defense: Main Line"]
[Termination "Normal"]
```

Uncommitted working-tree change at plan time: `frontend/src/components/bots/GameResultDialog.tsx`
(unrelated DialogFooter ordering fix). Do not touch it, do not commit it.

</specifics>

<canonical_refs>
## Canonical References

- `app/services/store_bot_game_service.py` — the store path; owns the transaction, derives
  `player_rating` from anchors, resolves the player username, knows `game_id` post-insert.
- `app/services/normalization.py` — `normalize_flawchess_game` (line ~539),
  `FLAWCHESS_BOT_USERNAME`, `FLAWCHESS_PLAYER_FALLBACK_USERNAME`,
  `_FLAWCHESS_TERMINATION_HEADER_MAP`, `find_opening`, `parse_time_control`.
- `app/models/user_rating_anchors.py` — proves `anchor_rating` is already Lichess-equivalent.
- `app/core/config.py` — `settings.FRONTEND_URL` (the `Site` base).
- `frontend/src/lib/botGamePgn.ts` — the frozen client PGN contract. UNCHANGED by this task.
- `app/schemas/bots.py` — `StoreBotGameRequest` (`game_uuid`, `play_style_blend`, `tc_preset`).

</canonical_refs>
