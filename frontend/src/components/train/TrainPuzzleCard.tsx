import type { ReactElement } from 'react';
import { Link } from 'react-router';
import { format, parseISO } from 'date-fns';
import { Search } from 'lucide-react';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { LazyMiniBoard } from '@/components/board/LazyMiniBoard';
import { useMiniBoardSize } from '@/hooks/useMiniBoardSize';
import { uciToSquares } from '@/lib/sanToSquares';
import { buildTrainPuzzleAnalysisUrl } from '@/lib/analysisUrl';
import { trackFeature } from '@/lib/analytics';
import { formatTimeControl } from '@/lib/formatTimeControl';
import type { ArchiveList, TrainArchiveItem } from '@/types/train';

/**
 * One archived (mastered or parked) Train puzzle. A standalone sibling of
 * `FlawCard` (shares no import with it).
 *
 * Spoiler-free by design (D-08): the card shows the pre-mistake position and
 * the arriving move only. The originally played move, the motif and the
 * severity are deliberately absent, as text and as board arrows, because they
 * would hint at the answer on a later Retry. The wire shape carries none of
 * them either.
 *
 * One horizontal tree at every width (D-05): `useMiniBoardSize` already
 * resolves the right board size above and below the `sm` breakpoint.
 */

const DESKTOP_BOARD_SIZE = 200;
// D-07's date format. Both the game date and the mastered/parked date use it.
const ARCHIVE_DATE_FORMAT = 'MMM d, yyyy';

const LIST_LABEL: Record<ArchiveList, string> = {
  mastered: 'Mastered',
  parked: 'Parked',
};

function capitalize(word: string): string {
  return word.charAt(0).toUpperCase() + word.slice(1);
}

/**
 * `Mastered Oct 3, 2026` or `Parked Oct 3, 2026 · 4 misses`. A null date drops the
 * date part; only Parked carries a miss count (`1 miss` singular).
 */
function statusLine(list: ArchiveList, lastSolvedAt: string | null, failCount: number): string {
  const parts: string[] = [LIST_LABEL[list]];
  if (lastSolvedAt !== null) parts.push(format(parseISO(lastSolvedAt), ARCHIVE_DATE_FORMAT));
  const base = parts.join(' ');
  if (list !== 'parked') return base;
  return `${base} · ${failCount} ${failCount === 1 ? 'miss' : 'misses'}`;
}

/** Opponent name and rating: the side the user is NOT playing. Null name is `?`. */
function opponentLabel(item: TrainArchiveItem): { name: string; rating: number | null } {
  const userIsWhite = item.user_color === 'white';
  return {
    name: (userIsWhite ? item.black_username : item.white_username) ?? '?',
    rating: userIsWhite ? item.black_rating : item.white_rating,
  };
}

export function TrainPuzzleCard({
  item,
  list,
}: {
  item: TrainArchiveItem;
  list: ArchiveList;
}): ReactElement {
  // Capped because the hook returns an uncapped 50vw below sm: the board reached 320px
  // at a 639px viewport, then snapped back to 200px at 640px.
  const boardSize = Math.min(useMiniBoardSize(DESKTOP_BOARD_SIZE), DESKTOP_BOARD_SIZE);
  const opponent = opponentLabel(item);

  return (
    <Card
      as="article"
      overflowVisible
      data-testid={`train-puzzle-card-${item.game_id}-${item.ply}`}
    >
      <div className="flex items-start gap-3 p-3">
        {item.fen === null ? (
          // Unreplayable PGN: keep the row (list equals count) with an empty board slot.
          <div
            className="bg-muted rounded shrink-0"
            style={{ width: boardSize, height: boardSize }}
            aria-hidden="true"
            data-testid="train-puzzle-board-unavailable"
          />
        ) : (
          <LazyMiniBoard
            fen={item.fen}
            flipped={item.user_color === 'black'}
            size={boardSize}
            lastMove={uciToSquares(item.last_move_uci) ?? undefined}          />
        )}
        {/* Tighter gaps below sm: index.css bumps text-sm to 16/24 there, which made this
            column taller than the board on phones under ~392px and pushed Analyze below it. */}
        <div className="flex min-w-0 flex-1 flex-col gap-1 self-stretch sm:gap-2">
          {/* Game details and status (D-07). Usernames are React text children only. */}
          <div className="flex flex-col text-sm text-muted-foreground sm:gap-1">
            {/* break-words: a long unbroken username would otherwise spill out of the
                narrow text column, since the card sets overflowVisible. */}
            <span className="break-words" data-testid="train-puzzle-opponent">
              <span className="text-foreground">{opponent.name}</span>
              {opponent.rating !== null ? ` (${opponent.rating})` : ''}
            </span>
            {item.played_at !== null && (
              <span data-testid="train-puzzle-date">
                {format(parseISO(item.played_at), ARCHIVE_DATE_FORMAT)}
              </span>
            )}
            {item.time_control_bucket !== null && (
              <span data-testid="train-puzzle-time-control">
                {capitalize(item.time_control_bucket)}
                {item.time_control_str ? ` ${formatTimeControl(item.time_control_str)}` : ''}
              </span>
            )}
            <span data-testid="train-puzzle-status">
              {statusLine(list, item.last_solved_at, item.fail_count)}
            </span>
          </div>
          {/* Action row: Analyze is flex-1 so a later Retry button drops in beside it.
              mt-auto bottom-aligns it with the board. */}
          <div className="mt-auto flex gap-2">
            <Button asChild variant="brand-outline" className="flex-1">
              {/* Real <a> via Link for middle-click / cmd-click new-tab support. */}
              <Link
                to={buildTrainPuzzleAnalysisUrl(item.game_id, item.ply)}
                data-testid="btn-train-puzzle-analyze"
                aria-label="Analyze game"
                // Internal Link: track in onClick, never data-umami-event (frontend/CLAUDE.md).
                onClick={() => trackFeature('action', { target: 'analyze' })}
              >
                <Search className="h-4 w-4 mr-1" />
                Analyze
              </Link>
            </Button>
          </div>
        </div>
      </div>
    </Card>
  );
}
