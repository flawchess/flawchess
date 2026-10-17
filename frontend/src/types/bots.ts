/**
 * Wire types for POST /bots/games. Mirrors `app/schemas/bots.py`'s
 * `StoreBotGameRequest`/`StoreBotGameResponse` field-for-field (snake_case on
 * the wire).
 */

/** Request body for `POST /bots/games`. */
export interface StoreBotGameRequest {
  /** Client-minted UUID, stable across a resume. Canonicalized
   * server-side via `uuid.UUID(...)`, but any RFC-4122 textual variant is accepted. */
  game_uuid: string;
  /** The finished game's PGN — must carry a `[%clk h:mm:ss]` comment for every
   * ply, both colors (the server rejects a PGN without them). */
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
   * The server feeds this straight into `parse_time_control()` (in
   * `store_bot_game`, `app/services/store_bot_game_service.py`), which expects
   * base-seconds. Sending a minutes-display string like `"5+3"` would parse as
   * base=5s -> estimated 5 + 3*40 = 125s -> BULLET, silently mis-bucketing the
   * game and picking the wrong rating anchor.
   */
  tc_preset: string;
  /** The persona pinned for this game, or `null` for a Custom-mode game with
   * no persona. Optional on the wire — mirrors the
   * backend `StoreBotGameRequest.persona_id`'s `default=None`. */
  persona_id: string | null;
  /** The persona's display name (e.g. "Ziggy the Wasp"), or `null` for a
   * Custom-mode game with no persona. Client-supplied like
   * `persona_id` — low blast radius, only affects the submitting user's OWN
   * game display. Mirrors the backend `StoreBotGameRequest.persona_name`'s
   * `default=None`. */
  persona_name: string | null;
  /** The persona's CALIBRATED ELO (the honest `~label` value the user sees,
   * e.g. 800) — NOT the internal engine dial `bot_elo` (e.g. 1100). `null`
   * for a Custom-mode game, in which case the server falls back to `bot_elo`.
   * Client-supplied like `persona_id`. Mirrors the backend
   * `StoreBotGameRequest.bot_rating`'s `default=None`. */
  bot_rating: number | null;
}

/** Response body for `POST /bots/games`. */
export interface StoreBotGameResponse {
  game_id: number;
  /** `true` if this call created the row; `false` if the server already had
   * it (idempotent re-POST of the same `game_uuid` — both count as success). */
  created: boolean;
}

/**
 * Response body for `GET /bots/persona-wins`. A per-persona-id
 * map of RAW (uncapped) win counts for the authenticated user — the frontend
 * applies the `Math.min(wins, MAX_DISPLAY_STARS)` display cap at render time
 * (`PersonaCard.tsx`), not here.
 */
export type PersonaWinsResponse = Record<string, number>;
