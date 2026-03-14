import { Button } from '@/components/ui/button';
import { GameCard } from '@/components/results/GameCard';
import type { GameRecord } from '@/types/api';

interface GameCardListProps {
  games: GameRecord[];
  matchedCount: number;
  totalGames: number;
  offset: number;
  limit: number;
  onPageChange: (offset: number) => void;
}

type PaginationItem = number | 'ellipsis-start' | 'ellipsis-end';

/**
 * Returns an array of page numbers and ellipsis markers for truncated pagination.
 *
 * Rules:
 * - If totalPages <= 7, show all pages.
 * - Otherwise: always show page 1 and last page; show a window of 2 pages on
 *   either side of the current page; fill gaps with ellipsis markers.
 */
function getPaginationItems(currentPage: number, totalPages: number): PaginationItem[] {
  if (totalPages <= 7) {
    return Array.from({ length: totalPages }, (_, i) => i + 1);
  }

  const items: PaginationItem[] = [];
  // Always include first page
  items.push(1);

  // Window: currentPage - 2 to currentPage + 2, clamped inside [2, totalPages - 1]
  const windowStart = Math.max(2, currentPage - 2);
  const windowEnd = Math.min(totalPages - 1, currentPage + 2);

  // Ellipsis before window?
  if (windowStart > 2) {
    items.push('ellipsis-start');
  }

  for (let p = windowStart; p <= windowEnd; p++) {
    items.push(p);
  }

  // Ellipsis after window?
  if (windowEnd < totalPages - 1) {
    items.push('ellipsis-end');
  }

  // Always include last page
  items.push(totalPages);

  return items;
}

export function GameCardList({
  games,
  matchedCount,
  totalGames,
  offset,
  limit,
  onPageChange,
}: GameCardListProps) {
  const totalPages = Math.max(1, Math.ceil(matchedCount / limit));
  const currentPage = Math.floor(offset / limit) + 1;

  const handlePageChange = (newOffset: number) => {
    onPageChange(newOffset);
    document
      .querySelector('[data-testid="game-card-list"]')
      ?.scrollIntoView({ behavior: 'smooth', block: 'start' });
  };

  const paginationItems = getPaginationItems(currentPage, totalPages);

  return (
    <div data-testid="game-card-list" className="space-y-3">
      {/* Matched count */}
      <p className="text-sm text-muted-foreground">
        <span className="font-medium text-foreground">{matchedCount}</span> of{' '}
        <span className="font-medium text-foreground">{totalGames}</span> games matched
      </p>

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

          {/* Truncated pagination */}
          {totalPages > 1 && (
            <div className="flex flex-wrap items-center justify-center gap-1">
              <Button
                variant="ghost"
                size="sm"
                disabled={currentPage === 1}
                onClick={() => handlePageChange(offset - limit)}
                data-testid="pagination-prev"
                aria-label="Previous page"
              >
                &lt;
              </Button>

              {paginationItems.map((item, idx) => {
                if (item === 'ellipsis-start' || item === 'ellipsis-end') {
                  return (
                    <span
                      key={item}
                      className="inline-flex h-8 min-w-8 items-center justify-center text-sm text-muted-foreground"
                      aria-hidden="true"
                    >
                      ...
                    </span>
                  );
                }
                return (
                  <Button
                    key={`page-${item}-${idx}`}
                    variant={item === currentPage ? 'default' : 'ghost'}
                    size="sm"
                    onClick={() => handlePageChange((item - 1) * limit)}
                    className="min-w-8"
                    data-testid={`pagination-page-${item}`}
                    aria-label={`Go to page ${item}`}
                    aria-current={item === currentPage ? 'page' : undefined}
                  >
                    {item}
                  </Button>
                );
              })}

              <Button
                variant="ghost"
                size="sm"
                disabled={currentPage === totalPages}
                onClick={() => handlePageChange(offset + limit)}
                data-testid="pagination-next"
                aria-label="Next page"
              >
                &gt;
              </Button>
            </div>
          )}
        </>
      )}
    </div>
  );
}
