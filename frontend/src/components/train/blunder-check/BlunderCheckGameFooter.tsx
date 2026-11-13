/**
 * BlunderCheckGameFooter: the game line under a solution (Phase 249, D-09).
 *
 * Own windows show the library card's line in the personalized-puzzle format, "Game: <TC> · vs
 * <opponent> (<elo>) · <date>". A foreign window is a stranger's game, so it shows only what the
 * server sent as `game_info` (time control, the mover's rating, date) as "Game: <TC> · player
 * rated <rating> · <date>", never fetches the library card and names nobody. Nothing renders when
 * the game is gone (`game_id` null for an own window, `game_info` null for a foreign one).
 *
 * No Umami event is added for blunder check (D-19).
 */

import type { ReactElement } from 'react';
import { LoadError } from '@/components/ui/load-error';
import { useLibraryGame } from '@/hooks/useLibrary';
import { formatTimeControl } from '@/lib/formatTimeControl';
import { formatDateWithYear } from '@/lib/utils';
import type { GameInfo } from '@/types/blunderCheck';

const FOOTER_SEPARATOR = ' · ';

/** "Blitz 3+2", "Blitz" or "3+2": whichever of the bucket and the time control are known. */
function timeControlLabel(bucket: string | null, timeControl: string | null): string | null {
  const bucketLabel = bucket === null ? null : bucket.charAt(0).toUpperCase() + bucket.slice(1);
  const timeControlText = timeControl === null ? null : formatTimeControl(timeControl);
  const parts = [bucketLabel, timeControlText].filter((part): part is string => part !== null);
  return parts.length === 0 ? null : parts.join(' ');
}

function GameLine({ parts }: { parts: readonly (string | null)[] }): ReactElement | null {
  const present = parts.filter((part): part is string => part !== null);
  if (present.length === 0) return null;
  return (
    <p className="text-sm text-muted-foreground" data-testid="blunder-check-game-footer">
      Game: {present.join(FOOTER_SEPARATOR)}
    </p>
  );
}

/** A stranger's game: only the server's neutral facts, no names and no library fetch. */
function ForeignGameFooter({ gameInfo }: { gameInfo: GameInfo | null }): ReactElement | null {
  if (gameInfo === null) return null;
  return (
    <GameLine
      parts={[
        timeControlLabel(gameInfo.time_control_bucket, gameInfo.time_control_str),
        gameInfo.mover_rating === null ? null : `player rated ${gameInfo.mover_rating}`,
        gameInfo.played_at === null ? null : formatDateWithYear(gameInfo.played_at),
      ]}
    />
  );
}

/** The user's own game: the library card line with the opponent and their rating. */
function OwnGameFooter({ gameId }: { gameId: number }): ReactElement | null {
  const gameQuery = useLibraryGame(gameId);
  if (gameQuery.isError) {
    return <LoadError resource="the game" data-testid="blunder-check-game-error" />;
  }
  const game = gameQuery.data;
  if (game === undefined) return null;
  // The opponent is the side the user did NOT play.
  const userIsWhite = game.user_color === 'white';
  const opponentName = (userIsWhite ? game.black_username : game.white_username) ?? '?';
  const opponentRating = userIsWhite ? game.black_rating : game.white_rating;
  return (
    <GameLine
      parts={[
        timeControlLabel(game.time_control_bucket, game.time_control_str),
        `vs ${opponentName}${opponentRating === null ? '' : ` (${opponentRating})`}`,
        game.played_at === null ? null : formatDateWithYear(game.played_at),
      ]}
    />
  );
}

export function BlunderCheckGameFooter({
  gameId,
  isOwn,
  gameInfo,
}: {
  gameId: number | null;
  isOwn: boolean;
  gameInfo: GameInfo | null;
}): ReactElement | null {
  if (!isOwn) return <ForeignGameFooter gameInfo={gameInfo} />;
  if (gameId === null) return null;
  return <OwnGameFooter gameId={gameId} />;
}
