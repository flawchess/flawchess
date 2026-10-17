/**
 * TrainRevealGameFooter — the reveal's compact game footer, extracted from
 * TrainReveal along its seam.
 *
 * Format: "Game: <TC> · vs <opponent> (<elo>) · <date>". Analyze and Next live
 * in the reveal action bar; don't add an open-on-the-analysis-board icon to
 * this footer (it duplicates the bar's Analyze).
 *
 * A second line under the footer shows the clock context of the
 * flawed move ("Played after 13s, with 3:56 left."). It reads `eval_series` from the
 * same post-solve card query (no extra fetch) and is suppressed with the footer for
 * non-SR sources.
 */

import type { ReactElement } from 'react';
import { useLibraryGame } from '@/hooks/useLibrary';
import { LoadError } from '@/components/ui/load-error';
import { formatDateWithYear } from '@/lib/utils';
import { formatTimeControl } from '@/lib/formatTimeControl';
import { clockContextLine } from '@/lib/trainClockContext';
import type { SolveResponse, TrainPuzzle } from '@/types/train';

export interface TrainRevealGameFooterProps {
  puzzle: TrainPuzzle;
  /** The landed solve verdict: TrainReveal only mounts the footer once it exists. */
  verdict: SolveResponse;
}

export function TrainRevealGameFooter({
  puzzle,
  verdict,
}: TrainRevealGameFooterProps): ReactElement | null {
  // The game card fetch is disabled until the solve response
  // is present, never fetched speculatively. The footer only mounts once
  // `verdict` exists, so passing `puzzle.game_id` here preserves that gate.
  const gameQuery = useLibraryGame(puzzle.game_id);

  // A herring reveal omits this footer entirely — "vs
  // <opponent>" has no referent when the solver was never a participant in a
  // stranger's game, and the reveal already labels the puzzle a herring
  // outright, so dropping the line leaks nothing new. A sharp filler
  // is suppressed the same way — it has no game at all (`game_id` is
  // structurally NULL). Both the error branch and the success branch sit behind
  // the SAME `verdict.source === 'sr_item'` gate (not a `puzzle_type !==
  // 'herring'` check, which a sharp filler's `puzzle_type: 'sharp'` would
  // wrongly satisfy) — gating only the success branch would leave a
  // herring/sharp filler free to render "Failed to load the game" for a
  // `useLibraryGame` query that (for a null `game_id`) never fired in the
  // first place. Reads `verdict`, never `revealQuery.data`: `revealQuery` is a
  // separate, asynchronously fetched query that only starts once `verdict`
  // lands, so reading its `source` here would open a real post-solve window
  // where a real SR puzzle briefly misrenders as suppressed.
  if (verdict.source !== 'sr_item') return null;

  // Opponent-and-rating: the side the user did NOT play.
  const game = gameQuery.data ?? null;
  const opponentName =
    game !== null
      ? game.user_color === 'white'
        ? (game.black_username ?? '?')
        : (game.white_username ?? '?')
      : null;
  const opponentRating =
    game !== null ? (game.user_color === 'white' ? game.black_rating : game.white_rating) : null;

  // The puzzle's `ply` is the flawed move's ply; its eval-series point carries the
  // mover's clock after the move and the time spent on it.
  const point = game?.eval_series?.find((p) => p.ply === puzzle.ply);
  const clockLine = point ? clockContextLine(point.clock_seconds, point.move_seconds) : null;

  return (
    <>
      {gameQuery.isError && <LoadError resource="the game" data-testid="train-gamecard-error" />}
      {game !== null && (
        <div className="flex flex-col gap-1">
          <p className="text-sm text-muted-foreground" data-testid="train-reveal-footer">
            Game:{' '}
            {game.time_control_bucket !== null && (
              <>
                <span className="capitalize">{game.time_control_bucket}</span>
                {game.time_control_str !== null && ` ${formatTimeControl(game.time_control_str)}`}
                {' · '}
              </>
            )}
            vs {opponentName}
            {opponentRating !== null && ` (${opponentRating})`}
            {game.played_at !== null && ` · ${formatDateWithYear(game.played_at)}`}
          </p>
          {clockLine !== null && (
            <p className="text-sm text-muted-foreground" data-testid="train-reveal-clock-line">
              {clockLine}
            </p>
          )}
        </div>
      )}
    </>
  );
}
