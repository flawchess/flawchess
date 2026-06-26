/**
 * URL construction helpers for the /analysis route.
 *
 * Extracted to a standalone module so the FEN→URL encoding behavior is
 * directly unit-testable without rendering any page components (mirroring
 * the openingsBoardLayout.ts extraction precedent).
 */

const ANALYSIS_PATH = '/analysis';
const FEN_PARAM = 'fen';

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
