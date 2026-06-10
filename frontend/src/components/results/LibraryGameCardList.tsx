import { LibraryGameCard } from '@/components/results/LibraryGameCard';
import { Pagination } from '@/components/results/Pagination';
import type { GameFlawCard } from '@/types/library';

// Page size matches the API default (limit=20 per UI-SPEC §Pagination).
const PAGE_SIZE = 20;

interface LibraryGameCardListProps {
  games: GameFlawCard[];
  matchedCount: number;
  total: number;
  offset: number;
  limit: number;
  onPageChange: (offset: number) => void;
}

/**
 * Paginated list of LibraryGameCard for the Library Games subtab.
 *
 * Renders a matched-count row ("{matchedCount} of {total} games"), the card stack,
 * and the shared Pagination control. Page changes convert the 1-based Pagination
 * page number back to an offset and scroll the list container into view.
 *
 * The empty-games case renders nothing in the card stack — GamesTab owns the
 * full empty-state UI (no-games-imported, no-matches, no-analyzed-games copy).
 */
export function LibraryGameCardList({
  games,
  matchedCount,
  total,
  offset,
  limit,
  onPageChange,
}: LibraryGameCardListProps) {
  // Derive pagination state; use PAGE_SIZE as the canonical page size constant.
  const pageSize = limit > 0 ? limit : PAGE_SIZE;
  const totalPages = Math.max(1, Math.ceil(matchedCount / pageSize));
  const currentPage = Math.floor(offset / pageSize) + 1;

  // Convert 1-based page number (from Pagination) back to offset, call parent, scroll.
  const handlePageChange = (page: number) => {
    const newOffset = (page - 1) * pageSize;
    onPageChange(newOffset);
    // Scroll the library list into view — uses the LIBRARY testid, not "game-card-list"
    // (distinct scroll target from GameCardList per UI-SPEC §Pagination).
    document
      .querySelector('[data-testid="library-game-card-list"]')
      ?.scrollIntoView({ behavior: 'smooth', block: 'start' });
  };

  return (
    <section aria-label="Game results" data-testid="library-game-card-list" className="space-y-3">
      {/* Matched-count row — simplified per UI-SPEC §Copywriting */}
      <p className="text-sm text-muted-foreground">
        {matchedCount} of {total} games
      </p>

      {/* Card stack — 2-column grid on md+; analyzed cards span full width, unanalyzed half-width.
          Wrapping div per card carries the span class so LibraryGameCard stays layout-agnostic. */}
      {games.length > 0 && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
          {games.map((game) => (
            <div
              key={game.game_id}
              className={game.analysis_state === 'analyzed' ? 'md:col-span-2' : 'md:col-span-1'}
            >
              <LibraryGameCard game={game} />
            </div>
          ))}
        </div>
      )}

      {/* Pagination row */}
      <Pagination
        currentPage={currentPage}
        totalPages={totalPages}
        onPageChange={handlePageChange}
      />
    </section>
  );
}
