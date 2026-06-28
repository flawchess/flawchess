/**
 * URL construction helpers for the /analysis route.
 *
 * Extracted to a standalone module so the FEN→URL encoding behavior is
 * directly unit-testable without rendering any page components (mirroring
 * the openingsBoardLayout.ts extraction precedent).
 */

const ANALYSIS_PATH = '/analysis';
const FEN_PARAM = 'fen';
const GAME_ID_PARAM = 'game_id';
const PLY_PARAM = 'ply';

/**
 * Constructs a navigable /analysis URL carrying the given FEN as a
 * url-encoded query parameter.
 *
 * FENs contain spaces and '/' which are query-breaking characters, so
 * encodeURIComponent is mandatory (spaces → %20, slashes → %2F).
 */
export function buildAnalysisUrl(fen: string): string {
  return `${ANALYSIS_PATH}?${FEN_PARAM}=${encodeURIComponent(fen)}`;
}

/**
 * Constructs a navigable /analysis URL for game-mode entry: carries a numeric
 * game_id and an optional starting ply. Both params are numeric so no encoding
 * is required (distinct from the FEN path which requires encodeURIComponent).
 * Used by the unified Analyze button in LibraryGameCard and FlawCard (D-06, plan 140-03).
 *
 * When `ply` is null/undefined the ply param is omitted, so the analysis board
 * loads the game and opens at ply 0 (Quick 260628-qta UAT: the Analyze button
 * omits ply when the slider rests on the game's end position).
 */
export function buildGameAnalysisUrl(gameId: number, ply?: number | null): string {
  if (ply == null) return `${ANALYSIS_PATH}?${GAME_ID_PARAM}=${gameId}`;
  return `${ANALYSIS_PATH}?${GAME_ID_PARAM}=${gameId}&${PLY_PARAM}=${ply}`;
}
