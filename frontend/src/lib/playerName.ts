/**
 * Player display-name resolution for the /bots clock caption
 * (quick-260714-pnk). Mirrors the backend's
 * store_bot_game_service.resolve_player_username precedence chain exactly —
 * this is the ONLY place the chain is written on the frontend.
 */

import type { UserProfile } from '@/types/users';

/** Fallback shown when the user has neither platform username, or the
 * profile hasn't loaded yet (still loading / failed fetch). */
export const DEFAULT_PLAYER_NAME = 'You';

/**
 * Resolve the human player's display name: lichess_username ->
 * chess_com_username -> DEFAULT_PLAYER_NAME ("You"). A blank or
 * whitespace-only username is treated as absent (falls through to the next
 * link in the chain), mirroring the backend resolver.
 *
 * Pure function — no hook, no memoization — call it directly per render.
 *
 * @param profile - The full `useUserProfile().data` shape, or `undefined`
 *   while loading / on a failed fetch.
 */
export function resolvePlayerName(profile: UserProfile | undefined): string {
  if (profile === undefined) return DEFAULT_PLAYER_NAME;

  const lichessUsername = profile.lichess_username?.trim();
  if (lichessUsername) return lichessUsername;

  const chessComUsername = profile.chess_com_username?.trim();
  if (chessComUsername) return chessComUsername;

  return DEFAULT_PLAYER_NAME;
}
