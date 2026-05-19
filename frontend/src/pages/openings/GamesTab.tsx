import { Link } from 'react-router-dom';
import type { UseQueryResult } from '@tanstack/react-query';
import { Button } from '@/components/ui/button';
import { PositionResultsPanel } from '@/components/charts/PositionResultsPanel';
import { GameCardList } from '@/components/results/GameCardList';
import type { OpeningsResponse } from '@/types/api';
import type { ReactNode } from 'react';

type GamesTabProps = {
  gamesQuery: UseQueryResult<OpeningsResponse>;
  hasNoGames: boolean;
  filtersMatchNothing: boolean;
  gameCount: number | null;
  positionResultsLabel: ReactNode;
  colorIconSquare: ReactNode;
  filterColor: 'white' | 'black';
  gamesOffset: number;
  pageSize: number;
  onPageChange: (offset: number) => void;
};

export function GamesTab({
  gamesQuery,
  hasNoGames,
  filtersMatchNothing,
  gameCount,
  positionResultsLabel,
  colorIconSquare,
  filterColor,
  gamesOffset,
  pageSize,
  onPageChange,
}: GamesTabProps) {
  const gamesData = gamesQuery.data;

  return (
    <div className="flex flex-col gap-4">
      {gamesQuery.isLoading ? (
        <div className="flex items-center justify-center py-12">
          <p className="text-muted-foreground">Loading games...</p>
        </div>
      ) : hasNoGames ? (
        <div className="flex flex-1 flex-col items-center justify-center py-12 text-center">
          <p className="mb-2 text-base font-medium text-foreground">No games imported yet</p>
          <p className="mb-6 text-sm text-muted-foreground">
            Import your games from chess.com or lichess to start analyzing positions.
          </p>
          <Button variant="outline" size="sm" asChild>
            <Link to="/import">Import Games</Link>
          </Button>
        </div>
      ) : filtersMatchNothing ? (
        <div className="flex flex-1 flex-col items-center justify-center py-12 text-center text-muted-foreground">
          <p className="text-base font-medium text-foreground">No games matched</p>
          <p className="mt-1 text-sm">Try adjusting the time control, opponent, rated, or recency filters.</p>
        </div>
      ) : gamesQuery.isError ? (
        <div className="flex flex-1 flex-col items-center justify-center py-12 text-center">
          <p className="mb-2 text-base font-medium text-foreground">Failed to load games</p>
          <p className="text-sm text-muted-foreground">
            Something went wrong. Please try again in a moment.
          </p>
        </div>
      ) : gamesData ? (
        <>
          <PositionResultsPanel
            stats={gamesData.stats}
            evalBaselinePawns={gamesData.eval_baseline_pawns}
            filterColor={filterColor}
            label={positionResultsLabel}
            className="charcoal-texture rounded-md p-4"
          />
          <GameCardList
            games={gamesData.games}
            matchedCount={gamesData.matched_count}
            totalGames={gameCount ?? gamesData.stats.total}
            offset={gamesOffset}
            limit={pageSize}
            onPageChange={onPageChange}
            hideMatchLabelOnMobile
            matchLabel={(() => {
              const total = gameCount ?? gamesData.stats.total;
              const pct = total > 0 ? (gamesData.matched_count / total * 100).toFixed(1) : '0.0';
              return (
                <>
                  {gamesData.matched_count} of {total} ({pct}%) games played as{' '}
                  <span className="inline-flex items-center gap-1 align-middle">
                    {colorIconSquare}
                    {filterColor}
                  </span>
                  {' '}matched
                </>
              );
            })()}
          />
        </>
      ) : null}
    </div>
  );
}
