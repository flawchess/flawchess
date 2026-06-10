import { type ReactNode } from 'react';
import { GameCard } from '@/components/results/GameCard';
import { Pagination } from '@/components/results/Pagination';
import type { GameRecord } from '@/types/api';

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
          {/* Card stack */}
          <div className="flex flex-col gap-2">
            {games.map((game) => (
              <GameCard key={game.game_id} game={game} />
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
