import { useState, useCallback } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { toast } from 'sonner';
import { ChevronUp, ChevronDown, Bookmark, Filter, Download, Trash2 } from 'lucide-react';
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
import { useAnalysis, useGamesQuery } from '@/hooks/useAnalysis';
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
import { GameCardList } from '@/components/results/GameCardList';
import { ImportModal } from '@/components/import/ImportModal';
import { ImportProgress } from '@/components/import/ImportProgress';
import { useUserProfile } from '@/hooks/useUserProfile';
import { apiClient } from '@/api/client';
import type { FilterState } from '@/components/filters/FilterPanel';
import type { MatchSide, Color, AnalysisResponse } from '@/types/api';
import { resolveMatchSide } from '@/types/api';
import type { PositionBookmarkResponse } from '@/types/position_bookmarks';

const PAGE_SIZE = 20;

export function DashboardPage() {
  // Prefetch user profile so it's ready when import modal opens
  useUserProfile();
  const queryClient = useQueryClient();

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

  // Default unfiltered games list (shown before user runs a position filter)
  const [positionFilterActive, setPositionFilterActive] = useState(false);
  const [defaultOffset, setDefaultOffset] = useState(0);
  const defaultGames = useGamesQuery({
    offset: defaultOffset,
    limit: PAGE_SIZE,
    enabled: !positionFilterActive,
  });

  // Import state
  const [importOpen, setImportOpen] = useState(false);
  const [activeJobIds, setActiveJobIds] = useState<string[]>([]);

  // Delete all games state
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [isDeleting, setIsDeleting] = useState(false);

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
    setPositionFilterActive(true);
    const request = {
      target_hash: chess.getHashForAnalysis(filters.matchSide, filters.color),
      match_side: resolveMatchSide(filters.matchSide, filters.color),
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
        target_hash: chess.getHashForAnalysis(filters.matchSide, filters.color),
        match_side: resolveMatchSide(filters.matchSide, filters.color),
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

  const handleDefaultPageChange = useCallback((newOffset: number) => {
    setDefaultOffset(newOffset);
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
    const targetHash = chess.getHashForAnalysis(matchSide, filters.color);
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
    setFilters(prev => ({ ...prev, color: bkm.color ?? 'white', matchSide: bkm.match_side }));
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
      // Invalidate user profile so stored usernames reflect latest import
      queryClient.invalidateQueries({ queryKey: ['userProfile'] });
      // Refresh default games list so newly imported games appear immediately
      queryClient.invalidateQueries({ queryKey: ['games'] });
    },
    [refetchGameCount, queryClient],
  );

  // ── Delete All Games ────────────────────────────────────────────────────────

  const handleDeleteAllGames = useCallback(async () => {
    setIsDeleting(true);
    try {
      await apiClient.delete('/imports/games');
      setDeleteDialogOpen(false);
      // Reset analysis state
      setAnalysisResult(null);
      setPositionFilterActive(false);
      setAnalysisOffset(0);
      setDefaultOffset(0);
      // Refetch total games count and default games list
      refetchGameCount();
      defaultGames.refetch();
    } catch {
      // Error handled by axios interceptor
    } finally {
      setIsDeleting(false);
    }
  }, [refetchGameCount, defaultGames]);

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
    <div className="flex flex-col gap-2 min-w-0">
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
                setPositionFilterActive(false);
              }}
              onFlip={() => setBoardFlipped((f) => !f)}
              canGoBack={chess.currentPly > 0}
              canGoForward={chess.currentPly < chess.moveHistory.length}
            />

            {/* Played as + Piece filter */}
            <div className="flex flex-wrap gap-x-4 gap-y-3">
              <div>
                <p className="mb-1 text-xs text-muted-foreground">Played as</p>
                <ToggleGroup
                  type="single"
                  value={filters.color}
                  onValueChange={(v) => {
                    if (!v) return;
                    const color = v as Color;
                    setFilters(prev => ({ ...prev, color }));
                    setBoardFlipped(color === 'black');
                  }}
                  variant="outline"
                  size="sm"
                  data-testid="filter-played-as"
                >
                  <ToggleGroupItem value="white" data-testid="filter-played-as-white">
                    <span className="inline-block h-3 w-3 rounded-full border border-muted-foreground bg-white mr-1" />
                    White
                  </ToggleGroupItem>
                  <ToggleGroupItem value="black" data-testid="filter-played-as-black">
                    <span className="inline-block h-3 w-3 rounded-full border border-muted-foreground bg-zinc-900 mr-1" />
                    Black
                  </ToggleGroupItem>
                </ToggleGroup>
              </div>

              <div>
                <p className="mb-1 text-xs text-muted-foreground">Piece filter</p>
                <ToggleGroup
                  type="single"
                  value={filters.matchSide}
                  onValueChange={(v) => v && setFilters(prev => ({ ...prev, matchSide: v as MatchSide }))}
                  variant="outline"
                  size="sm"
                  data-testid="filter-piece-filter"
                >
                  <ToggleGroupItem value="mine" data-testid="filter-piece-filter-mine">Mine</ToggleGroupItem>
                  <ToggleGroupItem value="opponent" data-testid="filter-piece-filter-opponent">Opponent</ToggleGroupItem>
                  <ToggleGroupItem value="both" data-testid="filter-piece-filter-both">Both</ToggleGroupItem>
                </ToggleGroup>
              </div>
            </div>

            {/* Bookmark */}
            <div>
              <Button
                variant="outline"
                size="lg"
                onClick={openBookmarkDialog}
                data-testid="btn-bookmark"
              >
                <Bookmark className="h-4 w-4" />
                Bookmark
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
            <PositionBookmarkList
              bookmarks={bookmarks}
              onReorder={handleReorder}
              onLoad={handleLoadBookmark}
            />
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
      </div>
    </div>
  );

  const headerActions = (
    <div className="flex items-center gap-2">
      <Button
        variant="outline"
        size="sm"
        onClick={() => setDeleteDialogOpen(true)}
        data-testid="btn-delete-games"
      >
        <Trash2 className="h-4 w-4" />
        Delete
      </Button>
      <Button variant="outline" size="sm" onClick={() => setImportOpen(true)} data-testid="btn-import">
        <Download className="h-4 w-4" />
        Import
      </Button>
    </div>
  );

  const rightColumn = (
    <div className="flex flex-col gap-4">
      {positionFilterActive ? (
        /* Position-filtered view */
        analysisResult === null ? (
          <div className="flex flex-1 flex-col items-center justify-center py-12 text-center">
            <p className="text-base text-muted-foreground">Filtering...</p>
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
            <GameCardList
              games={analysisResult.games}
              matchedCount={analysisResult.matched_count}
              totalGames={totalGames ?? analysisResult.stats.total}
              offset={analysisOffset}
              limit={PAGE_SIZE}
              onPageChange={handlePageChange}
              headerAction={headerActions}
            />
          </>
        )
      ) : (
        /* Default unfiltered games list — shown on mount */
        hasNoGames ? (
          /* New user with zero games */
          <div className="flex flex-1 flex-col items-center justify-center py-12 text-center">
            <p className="mb-2 text-base font-medium text-foreground">No games imported yet</p>
            <p className="mb-6 text-sm text-muted-foreground">
              Import your games from chess.com or lichess to start analyzing positions.
            </p>
            {importButton}
          </div>
        ) : defaultGames.isLoading ? (
          <div className="flex items-center justify-center py-12">
            <p className="text-muted-foreground">Loading games...</p>
          </div>
        ) : defaultGames.data ? (
          <>
            <GameCardList
              games={defaultGames.data.games}
              matchedCount={defaultGames.data.matched_count}
              totalGames={defaultGames.data.matched_count}
              offset={defaultOffset}
              limit={PAGE_SIZE}
              onPageChange={handleDefaultPageChange}
              headerAction={headerActions}
            />
          </>
        ) : null
      )}
    </div>
  );

  return (
    <div data-testid="dashboard-page" className="flex min-h-0 flex-1 flex-col bg-background">
      {/* Body */}
      <main className="mx-auto w-full max-w-7xl flex-1 px-4 py-6 md:px-6">
        {/* Desktop: two-column layout */}
        <div className="hidden md:grid md:grid-cols-[350px_1fr] md:gap-8 xl:grid-cols-[400px_1fr]">
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

      {/* Delete all games confirmation dialog */}
      <Dialog open={deleteDialogOpen} onOpenChange={setDeleteDialogOpen}>
        <DialogContent data-testid="delete-games-modal">
          <DialogHeader>
            <DialogTitle>Delete All Games</DialogTitle>
            <DialogDescription>
              This will delete all your imported games. You can import them again anytime.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button
              variant="outline"
              onClick={() => setDeleteDialogOpen(false)}
              data-testid="btn-delete-cancel"
            >
              Cancel
            </Button>
            <Button
              variant="destructive"
              onClick={handleDeleteAllGames}
              disabled={isDeleting}
              data-testid="btn-delete-confirm"
            >
              {isDeleting ? 'Deleting...' : 'Delete All Games'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

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
