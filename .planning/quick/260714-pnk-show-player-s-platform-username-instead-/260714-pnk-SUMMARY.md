---
phase: quick-260714-pnk
plan: 01
subsystem: bots
tags: [bot-play, normalization, react, typescript, fastapi]

requires: []
provides:
  - "resolve_player_username (backend) — lichess_username -> chess_com_username -> 'You' precedence chain, resolved server-side from the authenticated user's own profile"
  - "resolvePlayerName (frontend) — mirrors the backend chain for the /bots clock caption"
  - "normalize_flawchess_game's player_username parameter — the player-color games.username column is caller-resolved, not a hardcoded literal"
affects: [bots]

tech-stack:
  added: []
  patterns:
    - "Precedence-chain resolver as a pure module-level function of nullable strings (not of the ORM/profile object) — directly unit-testable without DB/hooks"

key-files:
  created:
    - frontend/src/lib/playerName.ts
    - frontend/src/lib/__tests__/playerName.test.ts
  modified:
    - app/services/normalization.py
    - app/services/store_bot_game_service.py
    - tests/services/test_normalization.py
    - tests/services/test_store_bot_game_service.py
    - tests/test_bot_pgn_clk_roundtrip.py
    - frontend/src/pages/Bots.tsx
    - frontend/src/components/bots/ClockDisplay.tsx

key-decisions:
  - "FLAWCHESS_PLAYER_FALLBACK_USERNAME made public (renamed from _FLAWCHESS_PLAYER_USERNAME) so store_bot_game_service can import it as the terminal link in the fallback chain"
  - "normalize_flawchess_game stays a pure PGN normalizer — it never resolves the username itself; the caller (store_bot_game) loads the User row and resolves before calling it"
  - "A blank/whitespace-only lichess_username or chess_com_username is treated as absent (falls through), mirrored identically on both stacks"

patterns-established:
  - "One resolver per stack (resolve_player_username / resolvePlayerName) — no third copy of the fallback chain anywhere in the codebase"

requirements-completed: []

coverage:
  - id: D1
    description: "Backend: stored bot game's player-color username column holds lichess_username, else chess_com_username, else 'You'; bot-color column unchanged (FLAWCHESS_BOT_USERNAME)"
    verification:
      - kind: unit
        ref: "tests/services/test_store_bot_game_service.py::TestPlayerUsername (4 DB-backed cases) — pass"
      - kind: unit
        ref: "tests/services/test_store_bot_game_service.py::TestResolvePlayerUsername (5 pure-function cases) — pass"
    human_judgment: false
  - id: D2
    description: "Frontend: resolvePlayerName precedence chain (lichess -> chess.com -> 'You', blank treated as absent)"
    verification:
      - kind: unit
        ref: "frontend/src/lib/__tests__/playerName.test.ts (5 cases) — pass"
    human_judgment: false
  - id: D3
    description: "/bots player-side clock caption renders the resolved player name on both desktop and mobile layouts (single userClock element consumed by both renderers)"
    verification:
      - kind: unit
        ref: "npx tsc -b (noUnusedLocals catches sideLabel={playerName} being unwired) — pass"
    human_judgment: true
    rationale: "Display-only wiring with no dedicated component test (plan's own verification section calls for an eyeball check on a real browser session, which was not performed in this execution — the resolver logic itself is fully unit-tested)."

duration: ~35min
completed: 2026-07-14
status: complete
---

# Quick Task 260714-pnk: Show player's platform username instead of "You" Summary

**Resolved the /bots player display name from lichess_username -> chess_com_username -> "You", wired into both the clock caption and the stored `games` row, via one resolver per stack.**

## Performance

- **Duration:** ~35 min
- **Tasks:** 2 completed
- **Files modified:** 9 (2 created, 7 modified)

## Accomplishments
- `resolve_player_username` (backend, `store_bot_game_service.py`) — a pure module-level function of two nullable strings implementing the precedence chain, unit-tested independently of the DB.
- `normalize_flawchess_game` now takes a required `player_username: str` parameter instead of writing a hardcoded `"You"` literal; `store_bot_game` loads the user's own profile (`user_repository.get_profile`) and resolves it server-side — never trusting the request body (T-pnk-01 spoofing mitigation).
- `resolvePlayerName` (frontend, `lib/playerName.ts`) mirrors the backend chain and feeds `BotsPage`'s single `useUserProfile()` call into a required `playerName` prop threaded through `BotsGame` to the `userClock` `ClockDisplay`'s `sideLabel` — one element shared by both desktop and mobile layouts.

## Task Commits

Each task was committed atomically:

1. **Task 1: Backend — resolve the player username from the user's platform usernames** - `e7a11535` (feat)
2. **Task 2: Frontend — one playerName resolver, threaded into both clock captions** - `355b52d5` (feat)
3. **Formatting fixup (pre-merge gate)** - `7b652fbb` (style)

_Note: both tasks combined pure-function implementation and its tests into a single commit each — the plan's `<behavior>` blocks were used directly to derive test cases before wiring the call sites, rather than a separate `test(...)` -> `feat(...)` two-commit split._

## Files Created/Modified
- `frontend/src/lib/playerName.ts` - `resolvePlayerName`/`DEFAULT_PLAYER_NAME` — the frontend precedence chain
- `frontend/src/lib/__tests__/playerName.test.ts` - 5 unit tests covering the precedence chain
- `frontend/src/pages/Bots.tsx` - `BotsPage` computes `playerName` once; threaded through `BotsGameProps` to both `<BotsGame />` call sites and the `userClock`'s `sideLabel`
- `frontend/src/components/bots/ClockDisplay.tsx` - `sideLabel` doc comment updated to describe the resolved name
- `app/services/normalization.py` - `_FLAWCHESS_PLAYER_USERNAME` renamed to public `FLAWCHESS_PLAYER_FALLBACK_USERNAME`; `normalize_flawchess_game` takes a required `player_username` param
- `app/services/store_bot_game_service.py` - `resolve_player_username` (new); `store_bot_game` loads the user profile and resolves before calling `normalize_flawchess_game`
- `tests/services/test_normalization.py` - all 12 `normalize_flawchess_game` call sites updated for the new param; two happy-path tests assert the resolved username reaches the player-color column
- `tests/services/test_store_bot_game_service.py` - `TestResolvePlayerUsername` (5 pure cases) + `TestPlayerUsername` (4 DB-backed cases); `_make_request` gained a `user_color` param
- `tests/test_bot_pgn_clk_roundtrip.py` - call site updated for the new param

## Decisions Made
- `FLAWCHESS_PLAYER_FALLBACK_USERNAME` made public (was `_FLAWCHESS_PLAYER_USERNAME`) so `store_bot_game_service.py` can import it as the fallback terminal.
- `normalize_flawchess_game` never resolves the username itself — stays a pure PGN normalizer with no session/User access, per the plan's explicit instruction.
- Blank/whitespace-only usernames on either stack are treated as absent and fall through to the next link in the chain, matching the users table's nullable-`String(100)`-with-no-CHECK reality.

## Deviations from Plan

None - plan executed exactly as written, including the CLAUDE.md-mandated `ruff format` pass after the fact (one line reformatted in `test_store_bot_game_service.py`, committed separately as `style(quick-260714-pnk)`).

## Issues Encountered

None.

## Mutation Check (per project convention)

**Backend:** Reverted `store_bot_game`'s `player_username = resolve_player_username(...)` line to the literal `player_username = "You"` and re-ran `TestPlayerUsername`. Observed failure output (verbatim):

```
FAILED tests/services/test_store_bot_game_service.py::TestPlayerUsername::test_lichess_username_white
FAILED tests/services/test_store_bot_game_service.py::TestPlayerUsername::test_lichess_username_black
FAILED tests/services/test_store_bot_game_service.py::TestPlayerUsername::test_chesscom_only_username
3 failed, 1 passed in 2.62s
```

(`test_no_platform_username_falls_back_to_you` still passed — coincidentally correct since "You" is the intended fallback for that one case, exactly as expected.) Sample assertion diff:

```
>       assert game.white_username == "magnus"
E       AssertionError: assert 'You' == 'magnus'
```

Restored the original line afterward; `TestPlayerUsername` (4/4) and the full `test_store_bot_game_service.py` file (14/14) pass again.

**Frontend (display-only, per plan's own admission there is no unit assertion for the wiring):** Reverted `sideLabel={playerName}` back to `sideLabel="You"` in `Bots.tsx` and ran `npx tsc -b`. Observed failure output (verbatim):

```
src/pages/Bots.tsx(218,3): error TS6133: 'playerName' is declared but its value is never read.
```

This proves the `playerName` prop is load-bearing (the destructured prop becomes an unused local under `noUnusedLocals` the moment it's disconnected from the caption), not dead wiring. Restored; `npx tsc -b` clean again. A live-browser eyeball check (log in with a linked lichess account, confirm the caption on narrow/wide viewports) was **not** performed in this execution — flagged as `human_judgment: true` (D3) in the coverage block above.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Both resolvers exist exactly once per stack; no third copy of the fallback chain anywhere in the codebase.
- Full local pre-merge gate green: `ruff format`, `ruff check --fix`, `ty check`, `pytest -n auto -x` (3261 passed, 18 skipped), and `frontend: lint + test + tsc -b` (165 test files, 2159 tests passed).
- Recommend a quick live-browser UAT pass (log in with a linked lichess/chess.com account, start a bot game, confirm the caption on both a narrow and wide viewport) before this is considered fully closed — see D3 above.

---
*Phase: quick-260714-pnk*
*Completed: 2026-07-14*

## Self-Check: PASSED

All created files and referenced commit hashes verified present on disk / in git history.
