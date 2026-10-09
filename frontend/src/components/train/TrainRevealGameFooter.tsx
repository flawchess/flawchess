/**
 * TrainRevealGameFooter — Phase 237 plan 08: the reveal's compact game footer,
 * extracted from TrainReveal along its seam.
 *
 * 190.1-03 D-03, format per 190.1 UAT round 3: "Game: <TC> · vs <opponent>
 * (<elo>) · <date>" plus an open-on-the-analysis-board link. The Analyze/Next row
 * that used to close the reveal lives in the reveal action bar.
 */

import type { ReactElement } from 'react';
import { Link } from 'react-router';
import { Search } from 'lucide-react';
import { useLibraryGame } from '@/hooks/useLibrary';
import { LoadError } from '@/components/ui/load-error';
import { buildGameAnalysisUrl } from '@/lib/analysisUrl';
import { formatDateWithYear } from '@/lib/utils';
import { formatTimeControl } from '@/lib/formatTimeControl';
import type { SolveResponse, TrainPuzzle } from '@/types/train';

export interface TrainRevealGameFooterProps {
  puzzle: TrainPuzzle;
  /** The landed solve verdict: TrainReveal only mounts the footer once it exists. */
  verdict: SolveResponse;
  /**
   * Fired by the open-on-the-analysis-board link, immediately before it
   * navigates. Wired to the SAME `handleAnalyzeClick` as the action bar's
   * Analyze: that handler writes the reveal cache, which is what lets a Back
   * from /analysis restore this reveal instead of dropping the user on a fresh
   * puzzle. A link that navigated without it would look identical and silently
   * lose the reveal on Back.
   */
  onAnalyzeClick?: () => void;
}

export function TrainRevealGameFooter({
  puzzle,
  verdict,
  onAnalyzeClick,
}: TrainRevealGameFooterProps): ReactElement | null {
  // SOLV-05/T-190-16: the game card fetch is disabled until the solve response
  // is present, never fetched speculatively. The footer only mounts once
  // `verdict` exists, so passing `puzzle.game_id` here preserves that gate.
  const gameQuery = useLibraryGame(puzzle.game_id);

  // D-07 (Phase 192): a herring reveal omits this footer entirely — "vs
  // <opponent>" has no referent when the solver was never a participant in a
  // stranger's game, and the reveal already labels the puzzle a herring
  // outright, so dropping the line leaks nothing new. A sharp filler (Phase 206)
  // is suppressed the same way — it has no game at all (`game_id` is
  // structurally NULL). Both the error branch and the success branch sit behind
  // the SAME `verdict.source === 'sr_item'` gate (Phase 206, D-19 — replaces the
  // old `puzzle_type !== 'herring'` proxy, which a sharp filler's `puzzle_type:
  // 'sharp'` would have wrongly satisfied) — gating only the success branch
  // would leave a herring/sharp filler free to render "Failed to load the game"
  // for a `useLibraryGame` query that (for a null `game_id`, D-09) never fired
  // in the first place. Reads `verdict`, never `revealQuery.data` (RESEARCH
  // Pitfall 1): `revealQuery` is a separate, asynchronously fetched query that
  // only starts once `verdict` lands, so reading its `source` here would open a
  // real post-solve window where a real SR puzzle briefly misrenders as
  // suppressed.
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

  return (
    <>
      {gameQuery.isError && <LoadError resource="the game" data-testid="train-gamecard-error" />}
      {game !== null && (
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
          {/* Opens the source game on the analysis board at the puzzle's own
              position. `puzzle.ply` is the ply of the move the user had to FIND,
              so the board wants the ply BEFORE it — the same `ply - 1` the
              Analyze button uses. Kept in sync with it deliberately: two controls
              pointing at one position must not drift. `puzzle.game_id` is
              non-null here because the whole footer sits behind `verdict.source
              === 'sr_item'`, and an SR item always has a live source game (an
              orphaned one reveals as not_found). */}
          {puzzle.game_id !== null && (
            <>
              {' '}
              <Link
                to={buildGameAnalysisUrl(puzzle.game_id, puzzle.ply > 0 ? puzzle.ply - 1 : null)}
                data-testid="train-reveal-footer-analyze"
                aria-label="Open this position on the analysis board"
                title="Open this position on the analysis board"
                onClick={onAnalyzeClick}
                className="inline-flex align-middle text-brand-brown-light hover:text-brand-brown-highlight"
              >
                <Search className="h-4 w-4" />
              </Link>
            </>
          )}
        </p>
      )}
    </>
  );
}
