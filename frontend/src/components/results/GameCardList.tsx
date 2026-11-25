import { type ReactNode } from 'react';
import { GameCard } from '@/components/results/GameCard';
import { Pagination } from '@/components/results/Pagination';
import type { GameRecord } from '@/types/api';

/** As many columns as fit with cards at least 320px wide (about a phone's card): 3 on desktop,
 *  2 on a foldable's inner screen and up to about 1100px, 1 on phones. Sized by the list, so it
 *  needs no breakpoints. */
const MULTI_COLUMN_CLASS =
  'grid grid-cols-[repeat(auto-fill,minmax(min(20rem,100%),1fr))] gap-2';
const SINGLE_COLUMN_CLASS = 'flex flex-col gap-2';

interface GameCardListProps {
  games: GameRecord[];
  matchedCount: number;
  totalGames: number;
  offset: number;
  limit: number;
  onPageChange: (offset: number) => void;
  headerAction?: ReactNode;
  matchLabel?: ReactNode;
  hideMatchLabelOnMobile?: boolean;
  /** When set, each card renders a full-width Analyze button opening the game at this ply. */
  analyzePly?: number;
  /** Cards in up to three columns (compact cards) instead of one full-width column. */
  multiColumn?: boolean;
}

export function GameCardList({
  games,
  matchedCount,
  totalGames,
  offset,
  limit,
  onPageChange,
  headerAction,
  matchLabel,
  hideMatchLabelOnMobile = false,
  analyzePly,
  multiColumn = false,
}: GameCardListProps) {
  const totalPages = Math.max(1, Math.ceil(matchedCount / limit));
  const currentPage = Math.floor(offset / limit) + 1;

  const handlePageChange = (newOffset: number) => {
    onPageChange(newOffset);
    document
      .querySelector('[data-testid="game-card-list"]')
      ?.scrollIntoView({ behavior: 'smooth', block: 'start' });
  };

  // Convert 1-based page number from Pagination to the offset this component uses.
  const handlePaginationPageChange = (page: number) => {
    handlePageChange((page - 1) * limit);
  };

  return (
    <div data-testid="game-card-list" className="space-y-3">
      {/* Matched count row */}
      <div className={`${hideMatchLabelOnMobile ? 'hidden lg:flex' : 'flex'} items-center justify-between`}>
        <p className="text-sm text-muted-foreground">
          {matchLabel ?? (
            <>
              {matchedCount} of {totalGames}{' '}
              ({totalGames > 0 ? (matchedCount / totalGames * 100).toFixed(1) : '0.0'}%){' '}
              games matched
            </>
          )}
        </p>
        {headerAction}
      </div>

      {games.length === 0 ? (
        <p className="py-4 text-center text-sm text-muted-foreground">No games to display</p>
      ) : (
        <>
          <div
            className={multiColumn ? MULTI_COLUMN_CLASS : SINGLE_COLUMN_CLASS}
            data-testid="game-card-grid"
          >
            {games.map((game) => (
              <GameCard
                key={game.game_id}
                game={game}
                analyzePly={analyzePly}
                compact={multiColumn}
              />
            ))}
          </div>

          {/* Truncated pagination — delegates to shared Pagination component */}
          <Pagination
            currentPage={currentPage}
            totalPages={totalPages}
            onPageChange={handlePaginationPageChange}
          />
        </>
      )}
    </div>
  );
}
