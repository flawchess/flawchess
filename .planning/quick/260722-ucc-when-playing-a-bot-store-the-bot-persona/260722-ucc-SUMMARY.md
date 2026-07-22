---
phase: quick-260722-ucc
plan: 01
subsystem: bots
tags: [pydantic, react, typescript, persona, pgn, normalization]

requires:
  - phase: 185
    provides: personaRegistry.ts (24-slot Persona registry), persona_id round-trip on StoreBotGameRequest
provides:
  - personaCalibratedElo() helper parsing the honest calibrated ELO from a persona's calibratedLabel
  - StoreBotGameRequest.persona_name/bot_rating (frontend + backend) client-supplied fields
  - normalize_flawchess_game bot_username keyword-only param (default FLAWCHESS_BOT_USERNAME)
affects: [bot-game-storage, library-stats, opening-explorer]

tech-stack:
  added: []
  patterns:
    - "Client-derives-then-sends trust model extended: persona_name/bot_rating mirror persona_id's low-blast-radius client-supplied field pattern"
    - "New optional backend params added as keyword-only with a default to avoid breaking existing positional callers (normalize_flawchess_game's bot_username)"

key-files:
  created: []
  modified:
    - frontend/src/lib/personas/personaRegistry.ts
    - frontend/src/hooks/useStoreBotGame.ts
    - frontend/src/types/bots.ts
    - frontend/src/hooks/__tests__/useStoreBotGame.test.ts
    - app/schemas/bots.py
    - app/services/store_bot_game_service.py
    - app/services/normalization.py
    - tests/schemas/test_bots.py
    - tests/services/test_normalization.py
    - tests/services/test_store_bot_game_service.py

key-decisions:
  - "normalize_flawchess_game's new bot_username param was made keyword-only (after a bare `*`) rather than inserted positionally near bot_elo/player_username as the plan's action text literally suggested — inserting it positionally would have broken every existing 8-positional-arg call site (both production and ~12 test call sites); keyword-only with a default preserves every caller unchanged while still satisfying the plan's must_haves and behavior spec."

requirements-completed: []

coverage:
  - id: D1
    description: "Frontend derives persona_name + calibrated bot_rating from settings.personaId via personaForId/personaCalibratedElo at store time; null/null for Custom-mode games and unrecognized/old personaIds"
    verification:
      - kind: unit
        ref: "frontend/src/hooks/__tests__/useStoreBotGame.test.ts#tc-preset > sends the persona name + calibrated ELO (not botElo) for a persona game"
        status: pass
      - kind: unit
        ref: "frontend/src/hooks/__tests__/useStoreBotGame.test.ts#tc-preset > sends persona_name=null and bot_rating=null for a Custom-mode game (no personaId)"
        status: pass
    human_judgment: false
  - id: D2
    description: "Backend accepts persona_name (min_length=1, max 60) and bot_rating (same bounds as bot_elo) on StoreBotGameRequest, both optional/default None"
    requirement: null
    verification:
      - kind: unit
        ref: "tests/schemas/test_bots.py::TestStoreBotGameRequestValidation::test_persona_name_and_bot_rating_accepted"
        status: pass
      - kind: unit
        ref: "tests/schemas/test_bots.py::TestStoreBotGameRequestValidation::test_persona_name_empty_string_rejected"
        status: pass
      - kind: unit
        ref: "tests/schemas/test_bots.py::TestStoreBotGameRequestValidation::test_bot_rating_out_of_range_rejected"
        status: pass
    human_judgment: false
  - id: D3
    description: "normalize_flawchess_game places a caller-supplied bot_username in the bot-color username column (both user_color orientations), defaulting to FLAWCHESS_BOT_USERNAME"
    verification:
      - kind: unit
        ref: "tests/services/test_normalization.py::TestNormalizeFlawchessGame::test_persona_bot_username_and_calibrated_rating_white_user"
        status: pass
      - kind: unit
        ref: "tests/services/test_normalization.py::TestNormalizeFlawchessGame::test_persona_bot_username_and_calibrated_rating_black_user"
        status: pass
      - kind: unit
        ref: "tests/services/test_normalization.py::TestNormalizeFlawchessGame::test_happy_path_bot_username_defaults_to_flawchess_bot"
        status: pass
    human_judgment: false
  - id: D4
    description: "store_bot_game stamps the persona's name + calibrated rating on the persisted PGN/games row for a persona game; Custom-mode games keep FlawChess Bot + raw bot_elo; BotGameSettings.nominal_elo always stays the raw engine dial"
    verification:
      - kind: integration
        ref: "tests/services/test_store_bot_game_service.py::TestPersonaNameAndCalibratedRating::test_persona_game_stamps_name_and_calibrated_rating"
        status: pass
      - kind: integration
        ref: "tests/services/test_store_bot_game_service.py::TestPersonaNameAndCalibratedRating::test_custom_mode_game_keeps_flawchess_bot_and_raw_bot_elo"
        status: pass
    human_judgment: false

duration: 25min
completed: 2026-07-22
status: complete
---

# Quick Task 260722-ucc: Store bot persona name and calibrated ELO Summary

**Persona bot games now persist the persona's own name (e.g. "Ziggy the Wasp") and its honest calibrated ELO (~800) in both the PGN header block and the `games` table username/rating columns, instead of the generic "FlawChess Bot" at the internal engine dial (e.g. 1100) — Custom-mode games and `BotGameSettings.nominal_elo` are unchanged.**

## Performance

- **Duration:** ~25 min
- **Tasks:** 2/2 completed
- **Files modified:** 10

## Accomplishments
- `personaCalibratedElo()` extracts the honest ~label integer from a persona's `calibratedLabel` (falls back to `botElo` on a no-match, currently unreachable given all 25 labels are `~<int>`)
- `toStoreRequest` re-derives `persona_name`/`bot_rating` from `settings.personaId` via `personaForId` at store time (no new localStorage schema, robust for old queued entries per Phase 185 Pitfall 3)
- Backend `StoreBotGameRequest` gains `persona_name`/`bot_rating`, both client-supplied and low-blast-radius like the existing `persona_id`
- `normalize_flawchess_game` gains a keyword-only `bot_username` param; `store_bot_game` computes the effective bot username/rating (persona values, or the Custom-mode fallbacks) and passes them through
- `bot_game_pgn.py` required no changes — it already stamps PGN headers straight from `NormalizedGame` fields

## Task Commits

1. **Task 1: Frontend — derive + send persona name and calibrated ELO** - `11884880` (feat)
2. **Task 2: Backend — accept persona_name/bot_rating and stamp them onto the game** - `b02cf181` (feat)

_Both tasks were TDD-flagged in the plan; tests were added alongside each implementation change in the same commit rather than as separate RED/GREEN commits, since each task's behavior additions were small and the existing suites already provided full regression coverage for the unchanged paths._

## Files Created/Modified
- `frontend/src/lib/personas/personaRegistry.ts` - added `personaCalibratedElo()` helper
- `frontend/src/hooks/useStoreBotGame.ts` - `toStoreRequest` resolves persona + sends `persona_name`/`bot_rating`
- `frontend/src/types/bots.ts` - `StoreBotGameRequest` gains the two new optional fields
- `frontend/src/hooks/__tests__/useStoreBotGame.test.ts` - new persona/Custom-mode/unrecognized-id test cases
- `app/schemas/bots.py` - `persona_name`/`bot_rating` fields + `_MAX_PERSONA_NAME_LENGTH` constant
- `app/services/store_bot_game_service.py` - computes effective `bot_username`/`bot_rating`, passes to `normalize_flawchess_game`
- `app/services/normalization.py` - `normalize_flawchess_game` gains keyword-only `bot_username` param, replacing the two literal `FLAWCHESS_BOT_USERNAME` assignments
- `tests/schemas/test_bots.py`, `tests/services/test_normalization.py`, `tests/services/test_store_bot_game_service.py` - new coverage for the above

## Decisions Made
- `normalize_flawchess_game`'s `bot_username` param was added as keyword-only (`*, bot_username: str = FLAWCHESS_BOT_USERNAME`) at the end of the signature rather than positionally near `bot_elo`/`player_username`. The plan's action text suggested placing it "near" those params, but every existing call site (production + ~12 test cases) passes all 8 params positionally; inserting a new param mid-signature would have broken every one of them. Keyword-only with a default achieves the same "any other caller is unaffected" goal the plan specified, without a mechanical signature-position match.

## Deviations from Plan

None - plan executed as specified, with the one signature-placement adjustment noted above (a mechanical implementation detail, not a behavior change).

## Issues Encountered
None.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
Feature is complete and self-contained. Manual smoke test (finish a persona bot game, confirm `[Black "Ziggy the Wasp"] [BlackElo "800"]` in the stored PGN and matching `games.black_username`/`black_rating`) remains optional per the plan's verification section — not required for this quick task's completion.

## Self-Check: PASSED

All 10 modified/created source files verified present on disk; both task commits (`11884880`, `b02cf181`) verified present in git log.
