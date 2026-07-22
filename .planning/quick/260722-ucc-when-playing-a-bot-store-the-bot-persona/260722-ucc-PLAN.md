---
phase: quick-260722-ucc
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - frontend/src/lib/personas/personaRegistry.ts
  - frontend/src/hooks/useStoreBotGame.ts
  - frontend/src/types/bots.ts
  - frontend/src/hooks/__tests__/useStoreBotGame.test.ts
  - app/schemas/bots.py
  - app/services/store_bot_game_service.py
  - app/services/normalization.py
  - tests/services/test_normalization.py
  - tests/services/test_store_bot_game_service.py
  - tests/schemas/test_bots.py
autonomous: true
requirements: []
must_haves:
  truths:
    - A finished persona bot game stores the persona's name (e.g. "Ziggy the Wasp") as the bot-side PGN player tag and in the bot-side games.*_username column, not the generic "FlawChess Bot".
    - A finished persona bot game stores the persona's CALIBRATED ELO (the ~label value, e.g. 800) in the bot-side PGN Elo tag and games.*_rating column, not the internal engine dial (botElo, e.g. 1100).
    - A Custom-mode game (no persona) still stores "FlawChess Bot" and the raw slider bot_elo — unchanged behavior.
    - BotGameSettings.nominal_elo still stores the raw engine dial (request.bot_elo), unchanged.
  artifacts:
    - frontend/src/lib/personas/personaRegistry.ts (calibrated-ELO parse helper)
    - app/schemas/bots.py (persona_name + bot_rating request fields)
    - app/services/normalization.py (bot_username param + calibrated rating)
  key_links:
    - toStoreRequest derives persona name + calibrated ELO from settings.personaId via personaForId, and sends them on the wire.
    - store_bot_game passes persona_name and effective bot rating (bot_rating ?? bot_elo) into normalize_flawchess_game; bot_game_pgn stamps them automatically from NormalizedGame fields (no change to bot_game_pgn.py).
---

<objective>
When a user finishes a game against a bot PERSONA, store the persona's name and its
calibrated ELO on the persisted `platform='flawchess'` Library game — both in the PGN
header block and in the `games` table rating/username columns — so downstream
stats/filters/exports see the bot like a normal named opponent instead of a generic
"FlawChess Bot" at a misleading rating.

Purpose: Persona games currently persist as `[Black "FlawChess Bot"]` with
`[BlackElo "1100"]`. Two problems, both confirmed by investigation:
  1. The bot player-name tag is the hardcoded `FLAWCHESS_BOT_USERNAME = "FlawChess Bot"`
     (app/services/normalization.py:669/673), never the persona's name — the backend has
     no knowledge of persona names (the 24-slot roster is a frontend-only TS module,
     `frontend/src/lib/personas/personaRegistry.ts`).
  2. VERIFIED: the "1100" in `[BlackElo]` is `request.bot_elo` → `persona.botElo`, which is
     the RETARGETED internal ENGINE DIAL (e.g. `attacker-800` has `botElo: 1100`), NOT the
     persona's honest calibrated strength. The calibrated ELO the user actually sees in the
     UI is `persona.calibratedLabel` (e.g. `~800`), sourced from
     `frontend/src/generated/personaCalibration.ts`. Storing 1100 overstates the opponent's
     strength for WDL-by-rating stats. This plan stores the calibrated ELO (800) instead.

Design (minimal, follows the existing persona_id trust model):
  - The persona name + calibrated ELO are deterministically derivable from
    `settings.personaId` on the frontend. `toStoreRequest` re-derives them via
    `personaForId(personaId)` at store time (robust for old queued localStorage entries —
    nothing new is persisted into the queue schema, matching Phase 185's Pitfall-3 note).
  - They ride the wire as two new optional request fields (`persona_name`, `bot_rating`),
    client-supplied and low-blast-radius exactly like the existing `persona_id` (only
    affects the submitting user's OWN game display). NOT resolved server-side — duplicating
    24 names + calibrated ELOs into Python would drift against the frontend registry.
  - Backend threads them through `normalize_flawchess_game`, which already places the bot's
    rating into the opponent-color `*_rating` column; we add a `bot_username` param and pass
    the calibrated rating as the bot rating. `bot_game_pgn.py` stamps both from
    `NormalizedGame.{white,black}_{username,rating}` automatically — no change needed there.
  - `BotGameSettings.nominal_elo` keeps storing the raw engine dial (`request.bot_elo`) —
    that column is the engine nominal, deliberately unchanged.
  - Fallbacks preserve current behavior for Custom-mode games: `persona_name=None` →
    "FlawChess Bot"; `bot_rating=None` → the raw `bot_elo`.

Output: Persona games persist with `[Black "Ziggy the Wasp"]` / `[BlackElo "800"]` and
matching `games.black_username`/`games.black_rating` (color mirrored when the user plays
Black). `[BlackTitle "BOT"]` stays.
</objective>

<execution_context>
@$HOME/.claude/gsd-core/workflows/execute-plan.md
@$HOME/.claude/gsd-core/templates/summary.md
</execution_context>

<context>
@.planning/STATE.md

# Frontend save path + persona registry
@frontend/src/hooks/useStoreBotGame.ts
@frontend/src/types/bots.ts
@frontend/src/lib/personas/personaRegistry.ts

# Backend save path
@app/schemas/bots.py
@app/services/store_bot_game_service.py
@app/services/normalization.py
@app/services/bot_game_pgn.py
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: Frontend — derive + send persona name and calibrated ELO</name>
  <files>frontend/src/lib/personas/personaRegistry.ts, frontend/src/types/bots.ts, frontend/src/hooks/useStoreBotGame.ts, frontend/src/hooks/__tests__/useStoreBotGame.test.ts</files>
  <behavior>
    - personaCalibratedElo(persona) returns the integer parsed from persona.calibratedLabel
      (e.g. "~800" -> 800, "~1850" -> 1850). All 25 labels in personaCalibration.ts are
      tilde + integer, so a `/\d+/` match with Number() is sufficient; guard a no-match to a
      sensible fallback (return persona.botElo) rather than NaN.
    - toStoreRequest for a persona game (settings.personaId resolves via personaForId):
      persona_name === persona.name, bot_rating === personaCalibratedElo(persona).
    - toStoreRequest for a Custom-mode game (personaId unset OR unrecognized id):
      persona_name === null, bot_rating === null (backend falls back).
    - Old queued entry with no personaId still round-trips: persona_name/bot_rating both null,
      no throw.
  </behavior>
  <action>
    In personaRegistry.ts, export a helper `personaCalibratedElo(persona: Persona): number`
    that extracts the leading integer from `persona.calibratedLabel` (strip the tilde), with a
    fallback to `persona.botElo` when the label has no digits. Add a named constant for the
    parse rather than a bare regex literal inline where it reads clearer.

    In types/bots.ts, add two optional fields to StoreBotGameRequest mirroring the backend:
    `persona_name: string | null` and `bot_rating: number | null`, each with a doc comment
    stating they are client-supplied like persona_id, null for Custom-mode games, and that
    bot_rating is the persona's CALIBRATED ELO (not the engine dial `bot_elo`).

    In useStoreBotGame.ts `toStoreRequest`, resolve the persona once via
    `personaForId(entry.settings.personaId)` (import from personaRegistry). Set
    `persona_name: persona?.name ?? null` and `bot_rating: persona ? personaCalibratedElo(persona) : null`.
    Keep `bot_elo: entry.settings.botElo` and `persona_id` exactly as-is. Do NOT tighten the
    localStorage entry validators — derivation is from personaId at store time, so old entries
    keep round-tripping (Phase 185 Pitfall 3).

    Update useStoreBotGame.test.ts: add cases asserting persona_name + bot_rating for a
    persona entry and null for a Custom entry; update any existing toStoreRequest snapshot/shape
    assertion to include the two new fields.
  </action>
  <verify>
    <automated>cd frontend && npx tsc -b && npm test -- --run src/hooks/__tests__/useStoreBotGame.test.ts</automated>
  </verify>
  <done>tsc build passes; toStoreRequest sends persona_name + calibrated bot_rating for persona games and null/null for Custom games; new tests pass.</done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: Backend — accept persona_name/bot_rating and stamp them onto the game</name>
  <files>app/schemas/bots.py, app/services/store_bot_game_service.py, app/services/normalization.py, tests/schemas/test_bots.py, tests/services/test_normalization.py, tests/services/test_store_bot_game_service.py</files>
  <behavior>
    - StoreBotGameRequest accepts optional persona_name (length-bounded, min_length 1 like
      persona_id) and bot_rating (int, same ge/le bounds as bot_elo), both default None; an
      empty-string persona_name is a 422, an out-of-range bot_rating is a 422.
    - normalize_flawchess_game with bot_username="Ziggy the Wasp" and the calibrated rating
      places the persona name in the bot-color *_username column and the calibrated ELO in the
      bot-color *_rating column, mirrored correctly for user_color white vs black.
    - store_bot_game passes persona_name (default FLAWCHESS_BOT_USERNAME when None) and the
      effective bot rating (request.bot_rating if not None else request.bot_elo); the stamped
      PGN's bot-side [White/Black] and [WhiteElo/BlackElo] reflect those values; [xTitle "BOT"]
      still present; BotGameSettings.nominal_elo still == request.bot_elo.
    - Custom-mode game (persona_name=None, bot_rating=None) preserves current output:
      "FlawChess Bot" + raw bot_elo.
  </behavior>
  <action>
    In app/schemas/bots.py StoreBotGameRequest, add `persona_name: str | None` (default None,
    min_length=1, max_length matching a new `_MAX_PERSONA_NAME_LENGTH` constant, e.g. 60 —
    long enough for "Ziggy the Wasp" with headroom) and `bot_rating: int | None` (default None,
    reuse the existing `_MIN_BOT_ELO`/`_MAX_BOT_ELO` Field bounds). Doc-comment both as
    client-supplied persona metadata, null for Custom-mode games, low blast radius (mirrors the
    persona_id trust rationale already in this file).

    In app/services/normalization.py normalize_flawchess_game, add a `bot_username: str` param
    (place it near the existing bot_elo/player_username params; give it a default of
    FLAWCHESS_BOT_USERNAME so any other caller is unaffected). Replace the two literal
    `FLAWCHESS_BOT_USERNAME` assignments in the user_color branch with `bot_username`. Update
    the docstring line that says "The bot-color column always stays FLAWCHESS_BOT_USERNAME" to
    reflect the caller-supplied name with that as the fallback. The `bot_elo` param already
    drives the bot-color rating column — the caller now passes the calibrated rating into it.

    In app/services/store_bot_game_service.py store_bot_game, compute
    `bot_username = request.persona_name or FLAWCHESS_BOT_USERNAME` and
    `bot_rating = request.bot_rating if request.bot_rating is not None else request.bot_elo`.
    Pass `bot_rating` where `request.bot_elo` is currently passed to normalize_flawchess_game,
    and pass the new `bot_username`. Import FLAWCHESS_BOT_USERNAME from app.services.normalization.
    Leave `BotGameSettings(nominal_elo=request.bot_elo, ...)` unchanged — nominal_elo is the
    engine dial. No change to bot_game_pgn.py: it stamps from NormalizedGame fields.

    Tests: in tests/schemas/test_bots.py add valid persona_name/bot_rating acceptance +
    empty-string persona_name 422 + out-of-range bot_rating 422. In
    tests/services/test_normalization.py add a case passing bot_username + a distinct
    calibrated rating and assert the bot-color username/rating columns (both user_color
    orientations) plus a default-fallback case. In tests/services/test_store_bot_game_service.py
    add a persona case asserting the stamped bot-side name/Elo and nominal_elo==bot_elo, and a
    Custom-mode fallback case asserting "FlawChess Bot" + raw bot_elo.
  </action>
  <verify>
    <automated>cd /home/aimfeld/Projects/Python/flawchess && uv run ty check app/ tests/ && uv run pytest -n auto tests/schemas/test_bots.py tests/services/test_normalization.py tests/services/test_store_bot_game_service.py tests/test_bot_pgn_clk_roundtrip.py</automated>
  </verify>
  <done>ty clean; persona games normalize/store with persona name + calibrated ELO on both PGN and games columns (both colors); Custom games unchanged; nominal_elo unchanged; all listed tests pass.</done>
</task>

</tasks>

<verification>
- Full targeted suites green:
  `cd frontend && npx tsc -b && npm run lint && npm test -- --run`
  `uv run ruff check app/ tests/ && uv run ty check app/ tests/ && uv run pytest -n auto -x tests/schemas/test_bots.py tests/services/test_normalization.py tests/services/test_store_bot_game_service.py tests/test_bot_pgn_clk_roundtrip.py`
- Manual smoke (optional): finish a persona game, confirm the stored PGN shows
  `[Black "<persona name>"] [BlackElo "<calibrated ~label value>"] [BlackTitle "BOT"]`
  (or White-side when playing Black) and `games.black_username`/`black_rating` match.
</verification>

<success_criteria>
- Persona bot games persist the persona name + calibrated ELO in both the PGN header and the
  games table rating/username columns.
- Custom-mode games and BotGameSettings.nominal_elo are behaviorally unchanged.
- bot_game_pgn.py is untouched; the stamping flows from NormalizedGame fields.
</success_criteria>

<output>
Create `.planning/quick/260722-ucc-when-playing-a-bot-store-the-bot-persona/260722-ucc-SUMMARY.md` when done
</output>
