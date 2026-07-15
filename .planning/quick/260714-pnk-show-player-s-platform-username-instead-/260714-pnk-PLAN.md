---
phase: quick-260714-pnk
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - app/services/normalization.py
  - app/services/store_bot_game_service.py
  - tests/services/test_normalization.py
  - tests/services/test_store_bot_game_service.py
  - tests/test_bot_pgn_clk_roundtrip.py
  - frontend/src/lib/playerName.ts
  - frontend/src/lib/__tests__/playerName.test.ts
  - frontend/src/pages/Bots.tsx
autonomous: true
requirements: []

must_haves:
  truths:
    - "A user with a lichess username sees that username (not 'You') as the player-side clock caption on /bots, on desktop and mobile."
    - "A user with only a chess.com username sees that username; a user (or guest) with neither still sees 'You'."
    - "A finished bot game persisted to `games` stores the same resolved name in the player-color username column (white_username / black_username), not a hardcoded 'You'."
    - "The fallback chain (lichess -> chess.com -> 'You') is written exactly once per stack (one frontend helper, one backend helper)."
  artifacts:
    - frontend/src/lib/playerName.ts
    - frontend/src/lib/__tests__/playerName.test.ts
  key_links:
    - "BotsPage's existing single useUserProfile() call -> playerName prop -> both ClockDisplay call sites (the `userClock` element is shared by the desktop and mobile layouts)."
    - "bots router's authenticated User -> store_bot_game -> user_repository.get_profile -> resolve_player_username -> normalize_flawchess_game -> NormalizedGame.white_username/black_username."
---

<objective>
On /bots the human player is labelled with the hardcoded string "You", and `normalize_flawchess_game` writes that same literal into the `games` player-color username column (`_FLAWCHESS_PLAYER_USERNAME = "You"`, app/services/normalization.py:494). Replace both with the user's real platform username, resolved once per stack: **lichess_username -> chess_com_username -> "You"**.

Purpose: a stored bot game should be indistinguishable from an imported game in the Library (LibraryGameCard/GameCard already render `white_username`/`black_username`), and the board should address the player by the name they use on the platforms they imported from.

**DB fallback decision (explicit):** when the user has neither platform username (guests, or a signed-up user who never linked a platform), the DB stores the literal **"You"** — the same value the UI falls back to.
Justification: (a) `games.user_id` is the real owner key (FK, NOT NULL) — the username column is a *display label*, never an identity; (b) the email local-part would push PII into a display column that is rendered in the Library and shipped in API responses, for no benefit; (c) "Guest" would be wrong for a registered-but-unlinked user; (d) keeping frontend fallback == DB fallback means one literal per stack and zero divergence between what the player saw during the game and what the Library shows afterwards. The existing `FLAWCHESS_BOT_USERNAME = "FlawChess Bot"` opponent label is unchanged.

No migration / backfill: v2.3 (Bot Play) has not shipped to production, so no `platform='flawchess'` rows exist in prod. Dev rows written before this change keep "You" and are not worth a backfill.

Output: one backend resolver + one frontend resolver, wired into the two write/display paths, with unit coverage.
</objective>

<execution_context>
@$HOME/.claude/gsd-core/workflows/execute-plan.md
@$HOME/.claude/gsd-core/templates/summary.md
</execution_context>

<context>
@CLAUDE.md

Backend (read these before editing):
@app/services/normalization.py           # lines ~490-700: FLAWCHESS_BOT_USERNAME / _FLAWCHESS_PLAYER_USERNAME + normalize_flawchess_game
@app/services/store_bot_game_service.py  # store_bot_game(session, user_id, request) — owns the transaction
@app/repositories/user_repository.py     # get_profile(session, user_id) -> User (scalar_one)
@app/routers/bots.py                     # already has the authenticated `User` object

Frontend:
@frontend/src/pages/Bots.tsx             # BotsPage owns the single useUserProfile(); BotsGame builds `botClock` / `userClock` (lines ~316-334)
@frontend/src/components/bots/ClockDisplay.tsx  # `sideLabel: string` prop — no change needed
@frontend/src/types/users.ts             # UserProfile.lichess_username / chess_com_username (both `string | null`)
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: Backend — resolve the player username from the user's platform usernames</name>
  <files>app/services/normalization.py, app/services/store_bot_game_service.py, tests/services/test_normalization.py, tests/services/test_store_bot_game_service.py, tests/test_bot_pgn_clk_roundtrip.py</files>
  <behavior>
    resolve_player_username (new, in store_bot_game_service.py):
    - lichess set, chess.com set -> lichess username
    - lichess None, chess.com set -> chess.com username
    - both None -> FLAWCHESS_PLAYER_FALLBACK_USERNAME ("You")
    - an empty-string or whitespace-only column is treated as absent (falls through to the next link in the chain) — the `users` columns are nullable String(100) with no non-empty CHECK, so an empty string is reachable via the profile-update endpoint.

    store_bot_game (service-level, DB-backed test):
    - user with lichess_username="magnus" playing white -> games.white_username == "magnus", games.black_username == "FlawChess Bot"
    - same user playing black -> games.black_username == "magnus", games.white_username == "FlawChess Bot"
    - user with only chess_com_username="hikaru" -> that username lands in the player-color column
    - user with neither -> "You" lands in the player-color column (asserts the documented fallback, not just "some string")
  </behavior>
  <action>
In app/services/normalization.py: rename the private `_FLAWCHESS_PLAYER_USERNAME` constant to a public `FLAWCHESS_PLAYER_FALLBACK_USERNAME = "You"` (keep it next to `FLAWCHESS_BOT_USERNAME`, and update its comment: it is now the fallback used when the user has no platform username, not an unconditional label). Add a required `player_username: str` parameter to `normalize_flawchess_game` (place it after `player_rating`, before `tc_str`) and use it for the player-color username column in place of the constant. Extend the docstring's Args section for the new parameter — state that the caller resolves it and that the bot-color column stays `FLAWCHESS_BOT_USERNAME`. Do not resolve anything inside normalization.py: it stays a pure PGN normalizer with no session and no User access.

In app/services/store_bot_game_service.py: add `def resolve_player_username(lichess_username: str | None, chess_com_username: str | None) -> str` implementing the precedence chain above (treat a blank/whitespace-only value as absent — strip before testing, and return the stripped value). Keep it a module-level pure function of two nullable strings (not of `User`) so it is directly unit-testable without a DB row. In `store_bot_game`, load the user with `user_repository.get_profile(session, user_id)` (the row is guaranteed to exist — `games.user_id` is an FK, so a missing row is already a hard failure today) and pass `resolve_player_username(user.lichess_username, user.chess_com_username)` into `normalize_flawchess_game`. Keep the `store_bot_game(session, user_id, request)` signature unchanged (the router keeps passing `user.id`) — the extra SELECT is one indexed PK lookup on a path that already does an anchors fetch, an insert batch and a commit.

Tests: add a `TestResolvePlayerUsername` class in tests/services/test_store_bot_game_service.py covering the four pure-function cases plus the blank-string case, and a DB-backed `TestPlayerUsername` class covering the four store_bot_game cases in the behavior block (set `lichess_username` / `chess_com_username` on the user created by `ensure_test_user` before calling `store_bot_game`; use fresh module-unique user IDs in the same style as the existing `_TEST_USER_ID` constant, and reuse `_make_request(...)` with `user_color="black"` for the black case). Update the existing `normalize_flawchess_game` call sites in tests/services/test_normalization.py (5) and tests/test_bot_pgn_clk_roundtrip.py (1) for the new parameter, and assert the passed username reaches the player-color column in at least one of them. Type safety: annotate every new function; no bare `str` where a `Literal` already exists.
  </action>
  <verify>
    <automated>uv run pytest tests/services/test_store_bot_game_service.py tests/services/test_normalization.py tests/test_bot_pgn_clk_roundtrip.py -x -q && uv run ty check app/ tests/ && uv run ruff check app/ tests/</automated>
  </verify>
  <done>The player-color username column of a stored bot game holds the user's lichess username, else their chess.com username, else "You"; the bot-color column is unchanged; the resolver exists once and is unit-tested; `ty` and `ruff` are clean.</done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: Frontend — one playerName resolver, threaded into both clock captions</name>
  <files>frontend/src/lib/playerName.ts, frontend/src/lib/__tests__/playerName.test.ts, frontend/src/pages/Bots.tsx</files>
  <behavior>
    resolvePlayerName(profile: UserProfile | undefined):
    - profile undefined (still loading / failed fetch) -> DEFAULT_PLAYER_NAME ("You")
    - lichess_username set -> that username (wins even when chess_com_username is also set)
    - only chess_com_username set -> that username
    - both null -> "You"
    - blank / whitespace-only username -> treated as absent (falls through), mirroring the backend resolver
  </behavior>
  <action>
Create frontend/src/lib/playerName.ts exporting `export const DEFAULT_PLAYER_NAME = 'You';` and `export function resolvePlayerName(profile: UserProfile | undefined): string` implementing the precedence chain above (trim; a blank value is absent). Take the whole `UserProfile | undefined` (the shape `useUserProfile().data` actually returns) rather than two loose strings, so no call site has to remember which two fields feed the chain. Keep it a pure module function — no hook, no `useMemo`; it is called once per render of a page that already re-renders on every clock tick.

In frontend/src/pages/Bots.tsx: `BotsPage` already makes the single `useUserProfile()` call and already threads `isGuest` down to `BotsGame` — follow that exact precedent. Compute `const playerName = resolvePlayerName(profile);` in `BotsPage`, add a required `playerName: string` prop to `BotsGameProps` (document it: resolved by `BotsPage` from its own `useUserProfile()` call, never a second hook call here), pass it at BOTH `<BotsGame ... />` call sites (the resume branch and the fresh-game branch), and use it for the `userClock` `ClockDisplay`'s `sideLabel` in place of the hardcoded `"You"`. The `userClock` element is built once and consumed by both the desktop and mobile layouts, so a single edit covers both — verify that by reading the layout branches before finishing; if any layout renders its own second player-side `ClockDisplay`, it gets the same prop. `ClockDisplay` itself needs no change beyond its `sideLabel` doc comment, which should now say the caption is the resolved player name (or "You") rather than always "You". The bot-side `sideLabel="FlawChess Bot"` is unchanged. No new interactive elements, so no new `data-testid` is required; leave `testId="clock-user"` as-is.

Add frontend/src/lib/__tests__/playerName.test.ts covering the five behavior cases (build the `UserProfile` fixtures with a small local factory + spread overrides so the test does not have to restate every unrelated profile field).
  </action>
  <verify>
    <automated>cd frontend && npm test -- --run src/lib/__tests__/playerName.test.ts && npx tsc -b && npm run lint && npm run knip</automated>
  </verify>
  <done>The /bots player-side clock caption shows the lichess username, else the chess.com username, else "You", on both desktop and mobile; the chain lives only in playerName.ts; tsc/lint/knip clean.</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| client -> POST /bots/games | Untrusted request body crosses here (PGN, colors, settings) |
| users table -> games.white_username/black_username -> Library API responses | A user-controlled profile string is echoed back into a rendered display column |

## STRIDE Threat Register

| Threat ID | Category | Component | Severity | Disposition | Mitigation Plan |
|-----------|----------|-----------|----------|-------------|-----------------|
| T-pnk-01 | Spoofing | store_bot_game_service | medium | mitigate | The username is resolved server-side from the authenticated user's own `users` row (`user_repository.get_profile(session, user_id)`, `user_id` from `current_active_user`) — never from the request body. The client cannot POST an arbitrary display name onto a stored game. |
| T-pnk-02 | Tampering / Information disclosure | games.white_username / black_username | low | accept | `lichess_username` / `chess_com_username` are already user-settable (`UserProfileUpdate`) and already surfaced in the Library/profile UI, and are bounded by `String(100)`. Copying one into a same-user game row adds no new disclosure. React escapes the value on render; the column is never interpolated into SQL (SQLAlchemy bind params). |
| T-pnk-03 | Repudiation | games row identity | low | accept | `games.user_id` (FK, NOT NULL) remains the authoritative owner; the username column is a display label only, so a later profile rename cannot re-attribute an existing game. |
| T-pnk-SC | Tampering | npm/pip/cargo installs | n/a | accept | No new dependencies are added by this task — no install step, no package-legitimacy surface. |
</threat_model>

<verification>
Full local gate before the squash-merge (CLAUDE.md pre-merge gate):

```
uv run ruff format app/ tests/
uv run ruff check app/ tests/ --fix
uv run ty check app/ tests/
uv run pytest -n auto -x
( cd frontend && npm run lint && npm test -- --run && npx tsc -b )
```

Mutation check (per MEMORY: never accept symbol-presence as proof) — revert the `player_username` argument in `store_bot_game` back to the "You" literal and confirm the new `TestPlayerUsername` DB test FAILS; revert `sideLabel={playerName}` back to `"You"` and confirm `tsc`/lint still pass but the caption regresses (this one is display-only and has no unit assertion, so eyeball it: log in with a linked lichess account, open /bots, start a game, confirm the player clock caption reads the lichess username on both a narrow and a wide viewport).
</verification>

<success_criteria>
- Player-side clock caption on /bots reads: lichess username -> chess.com username -> "You" (desktop and mobile).
- A finished bot game's player-color username column in `games` holds the same resolved value; the bot-color column still holds "FlawChess Bot".
- Exactly one resolver per stack: `resolve_player_username` (backend) and `resolvePlayerName` (frontend). No third copy of the fallback chain, no `"You"` literal left in `Bots.tsx` or in `normalize_flawchess_game`'s body.
- Full pre-merge gate green.
</success_criteria>

<output>
Create `.planning/quick/260714-pnk-show-player-s-platform-username-instead-/260714-pnk-SUMMARY.md` when done.
</output>
