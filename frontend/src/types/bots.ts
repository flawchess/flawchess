/**
 * Wire types for POST /bots/games (Phase 167, STORE-01..07; frontend call
 * site added in Phase 170 Plan 02, RESUME-02). Mirrors
 * `app/schemas/bots.py`'s `StoreBotGameRequest`/`StoreBotGameResponse`
 * field-for-field (six request fields, snake_case on the wire).
 */

/** Request body for `POST /bots/games`. */
export interface StoreBotGameRequest {
  /** Client-minted UUID (Phase 170 D-11), stable across a resume. Canonicalized
   * server-side via `uuid.UUID(...)`, but any RFC-4122 textual variant is accepted. */
  game_uuid: string;
  /** The finished game's PGN — must carry a `[%clk h:mm:ss]` comment for every
   * ply, both colors (server's STORE-02 presence gate). */
  pgn: string;
  /** Which color the human played. A closed set — never a bare `string`
   * (CLAUDE.md type-safety rule; mirrors the backend `Color` type). */
  user_color: 'white' | 'black';
  bot_elo: number;
  /** 0 = full-human, 1 = full-stockfish (selectBotMove's regime blend). */
  play_style_blend: number;
  /**
   * Base-SECONDS format (e.g. `"300+3"`), produced by
   * `toBackendTcStr(baseSeconds, incrementSeconds)` — IDENTICAL to the PGN's
   * `[TimeControl]` header. This is NOT the lichess minutes-display preset
   * (`"5+3"`).
   *
   * The server feeds this straight into `parse_time_control()`
   * (`app/services/store_bot_game_service.py:76`), which expects base-seconds.
   * Sending a minutes-display string like `"5+3"` would parse as base=5s ->
   * estimated 5 + 3*40 = 125s -> BULLET, silently mis-bucketing the game and
   * picking the wrong rating anchor. Corrected 2026-07-13 by 170-RESEARCH.md
   * against the shipped, currently-passing test suite — CONTEXT.md's original
   * D-14 text stated the opposite and is superseded; see the ⚠ CORRECTED note
   * on D-14 in `.planning/phases/170-localstorage-resume/170-CONTEXT.md`.
   */
  tc_preset: string;
  /** The persona pinned for this game, or `null` for a Custom-mode game with
   * no persona (Phase 185, PERS-05). Optional on the wire — mirrors the
   * backend `StoreBotGameRequest.persona_id`'s `default=None`. */
  persona_id: string | null;
}

/** Response body for `POST /bots/games`. */
export interface StoreBotGameResponse {
  game_id: number;
  /** `true` if this call created the row; `false` if the server already had
   * it (idempotent re-POST of the same `game_uuid` — both count as success). */
  created: boolean;
}

/**
 * Response body for `GET /bots/persona-wins` (Phase 185). A per-persona-id
 * map of RAW (uncapped) win counts for the authenticated user — the frontend
 * applies the `Math.min(wins, MAX_DISPLAY_STARS)` display cap at render time
 * (`PersonaCard.tsx`), not here.
 */
export type PersonaWinsResponse = Record<string, number>;
