/**
 * URL construction / parsing helpers for the /analysis route.
 *
 * Extracted to a standalone module so the move-list↔URL encoding behavior is
 * directly unit-testable without rendering any page components (mirroring
 * the openingsBoardLayout.ts extraction precedent).
 *
 * The free-play entry point carries an opening line as a `?line=` param: a
 * comma-separated list of UCI moves (e.g. `e2e4,e7e5,g1f3`) replayed from the
 * standard start position. UCI tokens are URL-safe as-is (lowercase letters +
 * digits, plus an optional promotion letter), so no encoding is required — this
 * replaced the earlier `?fen=` snapshot param, which needed encodeURIComponent
 * and could not seed a navigable main line back to move 1.
 */

import { Chess } from 'chess.js';

const ANALYSIS_PATH = '/analysis';
const LINE_PARAM = 'line';
const GAME_ID_PARAM = 'game_id';
const PLY_PARAM = 'ply';

/**
 * Converts a SAN move list (as held by the Openings explorer's `chess.moveHistory`)
 * to a navigable /analysis URL carrying the moves as a `?line=` UCI param.
 *
 * Replays each SAN on a fresh board from the standard start, emitting one UCI
 * token (`from + to + promotion?`) per move. Stops at the first illegal SAN
 * (defensive — should not happen for a valid explorer history). An empty move
 * list returns the bare `/analysis` path (free play from the start position).
 */
export function buildAnalysisLineUrl(sans: string[]): string {
  const chess = new Chess();
  const uci: string[] = [];
  for (const san of sans) {
    try {
      const move = chess.move(san);
      uci.push(`${move.from}${move.to}${move.promotion ?? ''}`);
    } catch {
      break; // stop on illegal SAN (chess.js throws) rather than emitting a broken token
    }
  }
  if (uci.length === 0) return ANALYSIS_PATH;
  return `${ANALYSIS_PATH}?${LINE_PARAM}=${uci.join(',')}`;
}

/**
 * Parses a `?line=` param value (comma-separated UCI moves) into a SAN array
 * suitable for `useAnalysisBoard.loadMainLine(sans, STARTING_FEN)`.
 *
 * Replays each UCI token from the standard start, collecting the resolved SAN.
 * Stops at the first illegal or unparseable token (mirrors loadMainLine's
 * "stop on illegal SAN" tolerance), so a hand-typed bad URL degrades to the
 * legal prefix instead of throwing. `null`/empty → `[]` (bare start position).
 */
export function parseAnalysisLineParam(lineParam: string | null): string[] {
  if (!lineParam) return [];
  const chess = new Chess();
  const sans: string[] = [];
  for (const token of lineParam.split(',')) {
    const from = token.slice(0, 2);
    const to = token.slice(2, 4);
    const promotion = token.slice(4, 5) || undefined;
    if (from.length < 2 || to.length < 2) break;
    try {
      const move = chess.move({ from, to, promotion });
      if (!move) break;
      sans.push(move.san);
    } catch {
      break; // illegal move: keep the legal prefix, stop here
    }
  }
  return sans;
}

/**
 * Constructs a navigable /analysis URL for game-mode entry: carries a numeric
 * game_id and an optional starting ply. Both params are numeric so no encoding
 * is required. Used by the unified Analyze button in LibraryGameCard and FlawCard
 * (D-06, plan 140-03).
 *
 * When `ply` is null/undefined the ply param is omitted, so the analysis board
 * loads the game and opens at ply 0 (Quick 260628-qta UAT: the Analyze button
 * omits ply when the slider rests on the game's end position).
 */
export function buildGameAnalysisUrl(gameId: number, ply?: number | null): string {
  if (ply == null) return `${ANALYSIS_PATH}?${GAME_ID_PARAM}=${gameId}`;
  return `${ANALYSIS_PATH}?${GAME_ID_PARAM}=${gameId}&${PLY_PARAM}=${ply}`;
}
