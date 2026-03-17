import { useState, useMemo, useCallback } from 'react';
import { useNavigate, useLocation, Navigate, Link } from 'react-router-dom';
import { Chess } from 'chess.js';
import { useQuery } from '@tanstack/react-query';
import { ChevronUp, ChevronDown, Bookmark } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Collapsible, CollapsibleTrigger, CollapsibleContent } from '@/components/ui/collapsible';
import { ToggleGroup, ToggleGroupItem } from '@/components/ui/toggle-group';
import { Tabs, TabsList, TabsTrigger, TabsContent } from '@/components/ui/tabs';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from '@/components/ui/dialog';
import { toast } from 'sonner';
import { useChessGame } from '@/hooks/useChessGame';
import { useNextMoves } from '@/hooks/useNextMoves';
import { usePositionAnalysisQuery } from '@/hooks/useAnalysis';
import { useDebounce } from '@/hooks/useDebounce';
import {
  usePositionBookmarks,
  useCreatePositionBookmark,
  useReorderPositionBookmarks,
  useTimeSeries,
} from '@/hooks/usePositionBookmarks';
import { ChessBoard } from '@/components/board/ChessBoard';
import { MoveExplorer } from '@/components/move-explorer/MoveExplorer';
import { MoveList } from '@/components/board/MoveList';
import { BoardControls } from '@/components/board/BoardControls';
import { FilterPanel, DEFAULT_FILTERS } from '@/components/filters/FilterPanel';
import { PositionBookmarkList } from '@/components/position-bookmarks/PositionBookmarkList';
import { WDLBar } from '@/components/results/WDLBar';
import { GameCardList } from '@/components/results/GameCardList';
import { WDLBarChart } from '@/components/charts/WDLBarChart';
import { WinRateChart } from '@/components/charts/WinRateChart';
import { apiClient } from '@/api/client';
import type { FilterState } from '@/components/filters/FilterPanel';
import type { Color, MatchSide } from '@/types/api';
import { resolveMatchSide } from '@/types/api';
import type { PositionBookmarkResponse, TimeSeriesRequest } from '@/types/position_bookmarks';

const PAGE_SIZE = 20;

export function OpeningsPage() {
  const location = useLocation();
  const navigate = useNavigate();

  const needsRedirect = location.pathname === '/openings' || location.pathname === '/openings/';

  const activeTab = location.pathname.includes('/games')
    ? 'games'
    : location.pathname.includes('/statistics')
      ? 'statistics'
      : 'explorer';

  // ── Board state ─────────────────────────────────────────────────────────────
  const chess = useChessGame();
  const [boardFlipped, setBoardFlipped] = useState(false);

  // ── Filter state ────────────────────────────────────────────────────────────
  const [filters, setFilters] = useState<FilterState>(DEFAULT_FILTERS);
  const debouncedFilters = useDebounce(filters, 300);

  // ── Board arrows (hovered move) ─────────────────────────────────────────────
  const [hoveredMove, setHoveredMove] = useState<string | null>(null);

  // ── Collapsible section state ───────────────────────────────────────────────
  const [positionBookmarksOpen, setPositionBookmarksOpen] = useState(false);
  const [moreFiltersOpen, setMoreFiltersOpen] = useState(false);

  // ── Games tab pagination ────────────────────────────────────────────────────
  const [gamesOffset, setGamesOffset] = useState(0);

  // Reset pagination on tab switch
  const [prevTab, setPrevTab] = useState(activeTab);
  if (activeTab !== prevTab) {
    setPrevTab(activeTab);
    setGamesOffset(0);
  }

  // ── Bookmarks ───────────────────────────────────────────────────────────────
  const { data: bookmarks = [] } = usePositionBookmarks();
  const createBookmark = useCreatePositionBookmark();
  const reorder = useReorderPositionBookmarks();
  const [bookmarkDialogOpen, setBookmarkDialogOpen] = useState(false);
  const [bookmarkLabel, setBookmarkLabel] = useState('');

  // ── Moves data ──────────────────────────────────────────────────────
  const nextMoves = useNextMoves(chess.hashes.fullHash, debouncedFilters);

  // Board arrows derived from next move frequencies
  const boardArrows = useMemo(() => {
    if (!nextMoves.data?.moves.length) return [];

    const chessInstance = new Chess(chess.position);
    const legalMoves = chessInstance.moves({ verbose: true });
    const moveMap = new Map(legalMoves.map(m => [m.san, { from: m.from, to: m.to }]));

    const moves = nextMoves.data.moves;
    const maxCount = Math.max(...moves.map(m => m.game_count), 1);
    const MIN_OPACITY = 0.15;

    return moves
      .map(entry => {
        const squares = moveMap.get(entry.move_san);
        if (!squares) return null;
        const isHovered = entry.move_san === hoveredMove;
        if (isHovered) {
          return {
            startSquare: squares.from,
            endSquare: squares.to,
            color: '#0a3d6b',
          };
        }
        const opacity = MIN_OPACITY + (1 - MIN_OPACITY) * (entry.game_count / maxCount);
        const alpha = Math.round(opacity * 255).toString(16).padStart(2, '0');
        return {
          startSquare: squares.from,
          endSquare: squares.to,
          color: `#1d6ab1${alpha}`,
        };
      })
      .filter((a): a is NonNullable<typeof a> => a !== null);
  }, [nextMoves.data, chess.position, hoveredMove]);

  // ── Games tab data ──────────────────────────────────────────────────────────
  const targetHash = chess.getHashForAnalysis(filters.matchSide, filters.color);
  const gamesQuery = usePositionAnalysisQuery({
    targetHash,
    filters: debouncedFilters,
    offset: gamesOffset,
    limit: PAGE_SIZE,
  });

  // Total game count — fetched on load to drive empty-state messaging
  const { data: gameCountData } = useQuery<{ count: number }>({
    queryKey: ['gameCount'],
    queryFn: async () => {
      const response = await apiClient.get<{ count: number }>('/games/count');
      return response.data;
    },
    staleTime: 30_000,
  });
  const gameCount = gameCountData?.count ?? null;

  // ── Statistics tab data ─────────────────────────────────────────────────────
  const timeSeriesRequest: TimeSeriesRequest | null = useMemo(() => {
    if (bookmarks.length === 0) return null;
    return {
      bookmarks: bookmarks.map((b) => ({
        bookmark_id: b.id,
        target_hash: b.target_hash,
        match_side: resolveMatchSide(b.match_side, (b.color ?? 'white') as Color),
        color: b.color,
      })),
      time_control: debouncedFilters.timeControls,
      platform: debouncedFilters.platforms,
      rated: debouncedFilters.rated,
      opponent_type: debouncedFilters.opponentType,
      recency: debouncedFilters.recency === 'all' ? null : debouncedFilters.recency,
    };
  }, [bookmarks, debouncedFilters]);

  const { data: tsData } = useTimeSeries(timeSeriesRequest);

  // Derive WDL stats per bookmark
  const wdlStatsMap = useMemo(() => {
    const map: Record<number, { wins: number; draws: number; losses: number; total: number }> = {};
    for (const s of tsData?.series ?? []) {
      let wins = 0, draws = 0, losses = 0;
      for (const p of s.data) {
        wins += p.wins;
        draws += p.draws;
        losses += p.losses;
      }
      const total = wins + draws + losses;
      map[s.bookmark_id] = { wins, draws, losses, total };
    }
    return map;
  }, [tsData]);

  // ── Handlers ────────────────────────────────────────────────────────────────

  const handleFiltersChange = useCallback((newFilters: FilterState) => {
    setFilters(newFilters);
    setGamesOffset(0);
  }, []);

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

  // ── Sidebar ─────────────────────────────────────────────────────────────────

  const sidebar = (
    <div className="flex flex-col gap-2 min-w-0">
      {/* Chess board — always visible, NOT in collapsible */}
      <ChessBoard
        position={chess.position}
        onPieceDrop={chess.makeMove}
        flipped={boardFlipped}
        lastMove={chess.lastMove}
        arrows={boardArrows}
      />

      {/* Opening name */}
      {chess.openingName ? (
        <div className="flex items-baseline gap-2 px-1 text-sm">
          <span className="font-mono text-xs text-muted-foreground">{chess.openingName.eco}</span>
          <span className="text-foreground">{chess.openingName.name}</span>
        </div>
      ) : (
        <div className="h-5" />
      )}

      {/* Move list */}
      <MoveList
        moveHistory={chess.moveHistory}
        currentPly={chess.currentPly}
        onMoveClick={chess.goToMove}
      />

      {/* Board controls */}
      <BoardControls
        onBack={chess.goBack}
        onForward={chess.goForward}
        onReset={() => {
          chess.reset();
          setGamesOffset(0);
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

      {/* Bookmark button */}
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

      {/* Position bookmarks collapsible */}
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

      {/* More filters collapsible */}
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
    </div>
  );

  // ── Tab content ─────────────────────────────────────────────────────────────

  const moveExplorerContent = (
    <div className="flex flex-col gap-4">
      {gamesQuery.data && gamesQuery.data.matched_count > 0 && (
        <WDLBar stats={gamesQuery.data.stats} />
      )}
      <MoveExplorer
        moves={nextMoves.data?.moves ?? []}
        isLoading={nextMoves.isLoading}
        isError={nextMoves.isError}
        position={chess.position}
        onMoveClick={(from, to) => chess.makeMove(from, to)}
        onMoveHover={setHoveredMove}
      />
    </div>
  );

  const hasNoGames = gameCount !== null && gameCount === 0;
  const gamesData = gamesQuery.data;
  const filtersMatchNothing = gamesData !== undefined && gamesData.matched_count === 0 && !hasNoGames;

  const gamesContent = (
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
      ) : gamesData ? (
        <>
          <WDLBar stats={gamesData.stats} />
          <GameCardList
            games={gamesData.games}
            matchedCount={gamesData.matched_count}
            totalGames={gameCount ?? gamesData.stats.total}
            offset={gamesOffset}
            limit={PAGE_SIZE}
            onPageChange={setGamesOffset}
          />
        </>
      ) : null}
    </div>
  );

  const statisticsContent = (
    <div className="flex flex-col gap-4">
      {bookmarks.length === 0 ? (
        <div className="flex flex-1 flex-col items-center justify-center py-12 text-center text-muted-foreground">
          <p className="text-base font-medium text-foreground">No bookmarks yet</p>
          <p className="mt-1 text-sm">Save positions on the Games tab to see opening stats here.</p>
        </div>
      ) : tsData ? (
        <>
          <WDLBarChart bookmarks={bookmarks} wdlStatsMap={wdlStatsMap} />
          <WinRateChart bookmarks={bookmarks} series={tsData.series} />
        </>
      ) : null}
    </div>
  );

  // ── Render ──────────────────────────────────────────────────────────────────

  if (needsRedirect) {
    return <Navigate to="/openings/explorer" replace />;
  }

  return (
    <div data-testid="openings-page" className="flex min-h-0 flex-1 flex-col bg-background">
      <main className="mx-auto w-full max-w-7xl flex-1 px-4 py-6 md:px-6">
        {/* Desktop: two-column layout */}
        <div className="hidden md:grid md:grid-cols-[350px_1fr] md:gap-8 xl:grid-cols-[400px_1fr]">
          <div className="min-w-0">{sidebar}</div>
          <div className="min-w-0">
            <Tabs value={activeTab} onValueChange={(val) => navigate(`/openings/${val}`)}>
              <TabsList className="w-full" data-testid="openings-tabs">
                <TabsTrigger value="explorer" data-testid="tab-move-explorer" className="flex-1">
                  Moves
                </TabsTrigger>
                <TabsTrigger value="games" data-testid="tab-games" className="flex-1">
                  Games
                </TabsTrigger>
                <TabsTrigger value="statistics" data-testid="tab-statistics" className="flex-1">
                  Statistics
                </TabsTrigger>
              </TabsList>
              <TabsContent value="explorer" className="mt-4">
                {moveExplorerContent}
              </TabsContent>
              <TabsContent value="games" className="mt-4">
                {gamesContent}
              </TabsContent>
              <TabsContent value="statistics" className="mt-4">
                {statisticsContent}
              </TabsContent>
            </Tabs>
          </div>
        </div>

        {/* Mobile: single column */}
        <div className="md:hidden">{sidebar}</div>
        <div className="mt-6 md:hidden">
          <Tabs value={activeTab} onValueChange={(val) => navigate(`/openings/${val}`)}>
            <TabsList className="w-full">
              <TabsTrigger value="explorer" className="flex-1">Moves</TabsTrigger>
              <TabsTrigger value="games" className="flex-1">Games</TabsTrigger>
              <TabsTrigger value="statistics" className="flex-1">Statistics</TabsTrigger>
            </TabsList>
            <TabsContent value="explorer" className="mt-4">
              {moveExplorerContent}
            </TabsContent>
            <TabsContent value="games" className="mt-4">
              {gamesContent}
            </TabsContent>
            <TabsContent value="statistics" className="mt-4">
              {statisticsContent}
            </TabsContent>
          </Tabs>
        </div>
      </main>

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
