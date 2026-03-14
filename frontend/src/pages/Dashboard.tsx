import { useState, useCallback } from 'react';
import { useQuery } from '@tanstack/react-query';
import { toast } from 'sonner';
import { ChevronUp, ChevronDown, Bookmark, Filter, Download } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Collapsible, CollapsibleTrigger, CollapsibleContent } from '@/components/ui/collapsible';
import { ToggleGroup, ToggleGroupItem } from '@/components/ui/toggle-group';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from '@/components/ui/dialog';
import { useChessGame } from '@/hooks/useChessGame';
import { useAnalysis } from '@/hooks/useAnalysis';
import {
  usePositionBookmarks,
  useCreatePositionBookmark,
  useReorderPositionBookmarks,
} from '@/hooks/usePositionBookmarks';
import { ChessBoard } from '@/components/board/ChessBoard';
import { MoveList } from '@/components/board/MoveList';
import { BoardControls } from '@/components/board/BoardControls';
import { FilterPanel, DEFAULT_FILTERS } from '@/components/filters/FilterPanel';
import { PositionBookmarkList } from '@/components/position-bookmarks/PositionBookmarkList';
import { WDLBar } from '@/components/results/WDLBar';
import { GameTable } from '@/components/results/GameTable';
import { ImportModal } from '@/components/import/ImportModal';
import { ImportProgress } from '@/components/import/ImportProgress';
import { apiClient } from '@/api/client';
import type { FilterState } from '@/components/filters/FilterPanel';
import type { MatchSide, Color, AnalysisResponse } from '@/types/api';
import type { PositionBookmarkResponse } from '@/types/position_bookmarks';

const PAGE_SIZE = 50;

export function DashboardPage() {
  // Board state
  const chess = useChessGame();
  const [boardFlipped, setBoardFlipped] = useState(false);

  // Bookmark state
  const createBookmark = useCreatePositionBookmark();
  const { data: bookmarks = [] } = usePositionBookmarks();
  const reorder = useReorderPositionBookmarks();
  const [bookmarkDialogOpen, setBookmarkDialogOpen] = useState(false);
  const [bookmarkLabel, setBookmarkLabel] = useState('');

  // Filter state
  const [filters, setFilters] = useState<FilterState>(DEFAULT_FILTERS);

  // Section open state
  const [positionFilterOpen, setPositionFilterOpen] = useState(true);
  const [positionBookmarksOpen, setPositionBookmarksOpen] = useState(false);
  const [moreFiltersOpen, setMoreFiltersOpen] = useState(false);

  // Analysis state
  const analysis = useAnalysis();
  const [analysisResult, setAnalysisResult] = useState<AnalysisResponse | null>(null);
  const [analysisOffset, setAnalysisOffset] = useState(0);

  // Import state
  const [importOpen, setImportOpen] = useState(false);
  const [activeJobIds, setActiveJobIds] = useState<string[]>([]);

  // Total game count — fetched on load to drive empty-state messaging
  const { data: gameCountData, refetch: refetchGameCount } = useQuery<{ count: number }>({
    queryKey: ['gameCount'],
    queryFn: async () => {
      const response = await apiClient.get<{ count: number }>('/games/count');
      return response.data;
    },
    staleTime: 30_000,
  });
  const totalGames = gameCountData?.count ?? null;

  // ── Analyze ────────────────────────────────────────────────────────────────

  const handleAnalyze = useCallback(async () => {
    const request = {
      target_hash: chess.getHashForAnalysis(filters.matchSide),
      match_side: filters.matchSide,
      time_control: filters.timeControls,
      platform: filters.platforms,
      rated: filters.rated,
      opponent_type: filters.opponentType,
      recency: filters.recency,
      color: filters.color,
      offset: analysisOffset,
      limit: PAGE_SIZE,
    };
    try {
      const result = await analysis.mutateAsync(request);
      setAnalysisResult(result);
    } catch {
      // Error displayed via toast via axios interceptor
    }
  }, [chess, filters, analysis, analysisOffset]);

  const handlePageChange = useCallback(
    async (newOffset: number) => {
      setAnalysisOffset(newOffset);
      const request = {
        target_hash: chess.getHashForAnalysis(filters.matchSide),
        match_side: filters.matchSide,
        time_control: filters.timeControls,
        platform: filters.platforms,
        rated: filters.rated,
        opponent_type: filters.opponentType,
        recency: filters.recency,
        color: filters.color,
        offset: newOffset,
        limit: PAGE_SIZE,
      };
      try {
        const result = await analysis.mutateAsync(request);
        setAnalysisResult(result);
      } catch {
        // Error handled by axios interceptor
      }
    },
    [chess, filters, analysis],
  );

  const handleFiltersChange = useCallback((newFilters: FilterState) => {
    setFilters(newFilters);
    setAnalysisOffset(0);
    // Don't auto-run analysis — user must click Filter
  }, []);

  // ── Bookmarks ───────────────────────────────────────────────────────────────

  const openBookmarkDialog = useCallback(() => {
    const defaultLabel = chess.openingName?.name ?? `Position (${chess.moveHistory.length} moves)`;
    setBookmarkLabel(defaultLabel);
    setBookmarkDialogOpen(true);
  }, [chess]);

  const handleBookmarkSave = useCallback(async () => {
    const label = bookmarkLabel.trim();
    if (!label) return;

    const matchSide = filters.matchSide;
    const targetHash = chess.getHashForAnalysis(matchSide);
    const data = {
      label,
      target_hash: targetHash,
      fen: chess.position,
      moves: chess.moveHistory,
      color: filters.color,
      match_side: matchSide,
      is_flipped: boardFlipped,
    };
    try {
      await createBookmark.mutateAsync(data);
      setBookmarkDialogOpen(false);
      toast.success('Position bookmarked');
    } catch {
      toast.error('Failed to save bookmark');
    }
  }, [chess, filters, boardFlipped, bookmarkLabel, createBookmark]);

  const handleLoadBookmark = useCallback((bkm: PositionBookmarkResponse) => {
    chess.loadMoves(bkm.moves);
    setBoardFlipped(bkm.is_flipped ?? false);
    setFilters(prev => ({ ...prev, color: bkm.color ?? null, matchSide: bkm.match_side as MatchSide }));
  }, [chess]);

  const handleReorder = useCallback((orderedIds: number[]) => {
    reorder.mutate(orderedIds);
  }, [reorder]);

  // ── Import ─────────────────────────────────────────────────────────────────

  const handleImportStarted = useCallback((jobId: string) => {
    setActiveJobIds((ids) => [...ids, jobId]);
  }, []);

  const handleJobDone = useCallback(
    (jobId: string) => {
      setActiveJobIds((ids) => ids.filter((id) => id !== jobId));
      // Refresh game count after import completes
      refetchGameCount();
    },
    [refetchGameCount],
  );

  // ── Derived ────────────────────────────────────────────────────────────────

  // User has zero imported games (known)
  const hasNoGames = totalGames !== null && totalGames === 0;
  // Analysis returned no results
  const analysisReturnedEmpty = analysisResult !== null && analysisResult.matched_count === 0;
  // Analysis returned no results and user has no games at all
  const noGamesAtAll = analysisReturnedEmpty && (totalGames === 0 || totalGames === null);
  // Analysis returned no results but user has games (filters are too narrow)
  const filtersMatchNothing = analysisReturnedEmpty && totalGames !== null && totalGames > 0;

  // ── Render ─────────────────────────────────────────────────────────────────

  const importButton = (
    <Button variant="outline" size="sm" onClick={() => setImportOpen(true)} data-testid="btn-import-cta">
      Import Games
    </Button>
  );

  const leftColumn = (
    <div className="flex flex-col gap-2">
      {/* Section 1: Position filter */}
      <Collapsible open={positionFilterOpen} onOpenChange={setPositionFilterOpen}>
        <CollapsibleTrigger asChild>
          <Button
            variant="ghost"
            size="sm"
            className="w-full justify-between px-2 text-sm font-medium"
            data-testid="section-position-filter"
          >
            Position filter
            {positionFilterOpen ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
          </Button>
        </CollapsibleTrigger>
        <CollapsibleContent>
          <div className="flex flex-col gap-3 pt-2">
            <ChessBoard
              position={chess.position}
              onPieceDrop={chess.makeMove}
              flipped={boardFlipped}
              lastMove={chess.lastMove}
            />
            {chess.openingName ? (
              <div className="flex items-baseline gap-2 px-1 text-sm">
                <span className="font-mono text-xs text-muted-foreground">{chess.openingName.eco}</span>
                <span className="text-foreground">{chess.openingName.name}</span>
              </div>
            ) : (
              <div className="h-5" />
            )}
            <MoveList
              moveHistory={chess.moveHistory}
              currentPly={chess.currentPly}
              onMoveClick={chess.goToMove}
            />
            <BoardControls
              onBack={chess.goBack}
              onForward={chess.goForward}
              onReset={() => {
                chess.reset();
                setAnalysisResult(null);
                setAnalysisOffset(0);
              }}
              onFlip={() => setBoardFlipped((f) => !f)}
              canGoBack={chess.currentPly > 0}
              canGoForward={chess.currentPly < chess.moveHistory.length}
            />

            {/* Played as + Match side */}
            <div className="flex flex-wrap gap-x-4 gap-y-3">
              <div>
                <p className="mb-1 text-xs text-muted-foreground">Played as</p>
                <ToggleGroup
                  type="single"
                  value={filters.color ?? 'any'}
                  onValueChange={(v) => {
                    if (!v) return;
                    setFilters(prev => ({ ...prev, color: v === 'any' ? null : (v as Color) }));
                  }}
                  variant="outline"
                  size="sm"
                  data-testid="filter-played-as"
                >
                  <ToggleGroupItem value="any" data-testid="filter-played-as-any">Any</ToggleGroupItem>
                  <ToggleGroupItem value="white" data-testid="filter-played-as-white">White</ToggleGroupItem>
                  <ToggleGroupItem value="black" data-testid="filter-played-as-black">Black</ToggleGroupItem>
                </ToggleGroup>
              </div>

              <div>
                <p className="mb-1 text-xs text-muted-foreground">Match side</p>
                <ToggleGroup
                  type="single"
                  value={filters.matchSide}
                  onValueChange={(v) => v && setFilters(prev => ({ ...prev, matchSide: v as MatchSide }))}
                  variant="outline"
                  size="sm"
                  data-testid="filter-match-side"
                >
                  <ToggleGroupItem value="white" data-testid="filter-match-side-white">White</ToggleGroupItem>
                  <ToggleGroupItem value="black" data-testid="filter-match-side-black">Black</ToggleGroupItem>
                  <ToggleGroupItem value="full" data-testid="filter-match-side-full">Both</ToggleGroupItem>
                </ToggleGroup>
              </div>
            </div>

            {/* Bookmark this position */}
            <div>
              <Button
                variant="outline"
                size="lg"
                onClick={openBookmarkDialog}
                data-testid="btn-bookmark"
              >
                <Bookmark className="h-4 w-4" />
                Bookmark this position
              </Button>
            </div>
          </div>
        </CollapsibleContent>
      </Collapsible>

      {/* Section 2: Position bookmarks */}
      <Collapsible open={positionBookmarksOpen} onOpenChange={setPositionBookmarksOpen}>
        <CollapsibleTrigger asChild>
          <Button
            variant="ghost"
            size="sm"
            className="w-full justify-between px-2 text-sm font-medium"
            data-testid="section-position-bookmarks"
          >
            Position bookmarks
            {positionBookmarksOpen ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
          </Button>
        </CollapsibleTrigger>
        <CollapsibleContent>
          <div className="pt-2">
            {bookmarks.length === 0 ? (
              <p className="px-2 text-xs text-muted-foreground">
                No position bookmarks yet. Use the 'Bookmark this position' button above to save positions.
              </p>
            ) : (
              <PositionBookmarkList
                bookmarks={bookmarks}
                onReorder={handleReorder}
                onLoad={handleLoadBookmark}
              />
            )}
          </div>
        </CollapsibleContent>
      </Collapsible>

      {/* Section 3: More filters */}
      <Collapsible open={moreFiltersOpen} onOpenChange={setMoreFiltersOpen}>
        <CollapsibleTrigger asChild>
          <Button
            variant="ghost"
            size="sm"
            className="w-full justify-between px-2 text-sm font-medium"
            data-testid="section-more-filters"
          >
            More filters
            {moreFiltersOpen ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
          </Button>
        </CollapsibleTrigger>
        <CollapsibleContent>
          <div className="pt-2">
            <FilterPanel filters={filters} onChange={handleFiltersChange} />
          </div>
        </CollapsibleContent>
      </Collapsible>

      {/* Always-visible action buttons */}
      <div className="flex gap-2 pt-1">
        <Button
          onClick={handleAnalyze}
          disabled={analysis.isPending}
          className="flex-1"
          size="lg"
          data-testid="btn-filter"
        >
          <Filter className="h-4 w-4" />
          {analysis.isPending ? 'Filtering...' : 'Filter'}
        </Button>
        <Button variant="outline" size="lg" onClick={() => setImportOpen(true)} data-testid="btn-import">
          <Download className="h-4 w-4" />
          Import
        </Button>
      </div>
    </div>
  );

  const rightColumn = (
    <div className="flex flex-col gap-4">
      {analysisResult === null ? (
        /* Initial state: no analysis run yet */
        <div className="flex flex-1 flex-col items-center justify-center py-12 text-center">
          {hasNoGames ? (
            /* New user with no games */
            <>
              <p className="mb-2 text-base font-medium text-foreground">No games imported yet</p>
              <p className="mb-6 text-sm text-muted-foreground">
                Import your games from chess.com or lichess to start analyzing positions.
              </p>
              {importButton}
            </>
          ) : (
            /* Has games (or count unknown) — show normal prompt */
            <>
              <p className="text-base text-muted-foreground">
                Play moves on the board and click Filter to see your stats
              </p>
              {totalGames !== null && totalGames > 0 && (
                <p className="mt-2 text-xs text-muted-foreground">
                  {totalGames.toLocaleString()} games imported
                </p>
              )}
            </>
          )}
        </div>
      ) : noGamesAtAll ? (
        /* Ran analysis, 0 results, 0 total games */
        <div className="flex flex-1 flex-col items-center justify-center py-12 text-center">
          <p className="mb-2 text-base font-medium text-foreground">No games imported yet</p>
          <p className="mb-6 text-sm text-muted-foreground">
            Import your games from chess.com or lichess to start analyzing positions.
          </p>
          {importButton}
        </div>
      ) : filtersMatchNothing ? (
        /* Has games but current filters matched nothing */
        <div className="flex flex-1 flex-col items-center justify-center py-12 text-center text-muted-foreground">
          <p className="text-base">No games matched the current filter settings.</p>
          <p className="mt-1 text-sm">Try adjusting the time control, opponent, rated, or recency filters.</p>
        </div>
      ) : (
        <>
          <WDLBar stats={analysisResult.stats} />
          <GameTable
            games={analysisResult.games}
            matchedCount={analysisResult.matched_count}
            totalGames={totalGames ?? analysisResult.stats.total}
            offset={analysisOffset}
            limit={PAGE_SIZE}
            onPageChange={handlePageChange}
          />
        </>
      )}
    </div>
  );

  return (
    <div data-testid="dashboard-page" className="flex min-h-0 flex-1 flex-col bg-background">
      {/* Body */}
      <main className="mx-auto w-full max-w-7xl flex-1 px-4 py-6 md:px-6">
        {/* Desktop: two-column layout */}
        <div className="hidden md:grid md:grid-cols-[auto_1fr] md:gap-8 xl:grid-cols-[400px_1fr]">
          <div className="min-w-0">{leftColumn}</div>
          <div className="min-w-0">{rightColumn}</div>
        </div>

        {/* Mobile: single column */}
        <div className="md:hidden">{leftColumn}</div>
        <div className="mt-6 md:hidden">{rightColumn}</div>
      </main>

      {/* Import modal */}
      <ImportModal
        open={importOpen}
        onOpenChange={setImportOpen}
        onImportStarted={handleImportStarted}
      />

      {/* Import progress toasts */}
      <ImportProgress jobIds={activeJobIds} onJobDone={handleJobDone} />

      {/* Bookmark label dialog */}
      <Dialog open={bookmarkDialogOpen} onOpenChange={setBookmarkDialogOpen}>
        <DialogContent data-testid="bookmark-dialog">
          <DialogHeader>
            <DialogTitle>Save Bookmark</DialogTitle>
            <DialogDescription>
              Enter a label for this position bookmark.
            </DialogDescription>
          </DialogHeader>
          <Input
            value={bookmarkLabel}
            onChange={(e) => setBookmarkLabel(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === 'Enter') handleBookmarkSave();
            }}
            placeholder="Bookmark label"
            autoFocus
            data-testid="bookmark-label-input"
          />
          <DialogFooter>
            <Button
              onClick={handleBookmarkSave}
              disabled={!bookmarkLabel.trim() || createBookmark.isPending}
              data-testid="btn-bookmark-save"
            >
              {createBookmark.isPending ? 'Saving...' : 'Save'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
