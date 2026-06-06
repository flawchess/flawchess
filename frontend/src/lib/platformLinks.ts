/**
 * Deep links to the flawed move's resulting position on the originating platform,
 * oriented to the user's side where the platform supports it.
 *
 * `ply` is the flaw's 0-indexed half-move (FlawRecord.ply: the flawed move is the
 * (ply+1)-th half-move). Both platforms count half-moves from the start, where
 * "N" means the position AFTER N half-moves (N=0 is the starting position). To
 * land on the blunder itself — the position right after the flawed move, with that
 * move highlighted — we navigate to `ply + 1`.
 *
 * - **lichess** — append a `/{color}` orientation suffix (lichess defaults to
 *   white's POV; `/black` flips the board) plus a `#{n}` ply fragment, e.g.
 *   https://lichess.org/abcd1234/black#42.
 * - **chess.com** — rewrite the game URL to the analysis board with a `move` query
 *   param (e.g. https://www.chess.com/analysis/game/live/123?tab=details-tab&move=42).
 *   chess.com has no documented board-orientation URL param, so it is not flipped.
 *
 * Falls back to the plain game URL when the chess.com URL has an unexpected shape,
 * and returns null when no platform URL is available.
 */

// chess.com game URLs are https://www.chess.com/game/{live|daily}/{id}.
const CHESS_COM_GAME_RE = /^(https?:\/\/(?:www\.)?chess\.com)\/game\/(live|daily)\/(\d+)/i;

export function flawPlyUrl(
  platform: string,
  platformUrl: string | null,
  ply: number,
  userColor: string,
): string | null {
  if (!platformUrl) return null;
  const p = platform.toLowerCase();

  // Navigate to the position AFTER the flawed move so the board shows the blunder.
  const targetPly = ply + 1;

  if (p === 'lichess') {
    // Default orientation is white's POV; append /black to flip to black's side.
    const orientation = userColor.toLowerCase() === 'black' ? '/black' : '';
    return `${platformUrl}${orientation}#${targetPly}`;
  }

  if (p === 'chess.com') {
    const match = platformUrl.match(CHESS_COM_GAME_RE);
    const origin = match?.[1];
    const gameType = match?.[2];
    const gameId = match?.[3];
    if (origin && gameType && gameId) {
      return `${origin}/analysis/game/${gameType}/${gameId}?tab=details-tab&move=${targetPly}`;
    }
    // Unexpected chess.com URL shape — open the game at its final position.
    return platformUrl;
  }

  // Unknown platform: no per-move deep link — open the game.
  return platformUrl;
}

/** True when the platform supports a per-ply deep link (lichess + chess.com). */
export function supportsPlyDeepLink(platform: string): boolean {
  const p = platform.toLowerCase();
  return p === 'lichess' || p === 'chess.com';
}

/**
 * Game-level link to the originating platform, oriented to the user's side where
 * the platform supports it. lichess defaults to white's POV; appending `/black`
 * flips the board to black's side (e.g. https://lichess.org/abcd1234/black).
 * chess.com and unknown platforms have no documented orientation URL param, so
 * they are returned unchanged. Returns null when no platform URL is available.
 */
export function gamePlatformUrl(
  platform: string,
  platformUrl: string | null,
  userColor: string,
): string | null {
  if (!platformUrl) return null;
  if (platform.toLowerCase() === 'lichess' && userColor.toLowerCase() === 'black') {
    return `${platformUrl}/black`;
  }
  return platformUrl;
}
