import { useState, useMemo, useCallback, useRef, useEffect } from 'react';

// localStorage helpers for per-bookmark chart-enable toggle (default: enabled)
function getChartEnabled(bookmarkId: number): boolean {
  const stored = localStorage.getItem(`bookmark-chart-enabled-${bookmarkId}`);
  return stored === null ? true : stored === 'true';
}
function setChartEnabledStorage(bookmarkId: number, enabled: boolean): void {
  localStorage.setItem(`bookmark-chart-enabled-${bookmarkId}`, String(enabled));
}
import { useNavigate, useLocation, Navigate, Link } from 'react-router-dom';
import { useUserProfile } from '@/hooks/useUserProfile';
import { Chess } from 'chess.js';
import { useQuery } from '@tanstack/react-query';
import { Save, Sparkles, ArrowRightLeft, Gamepad2, BarChart2, SlidersHorizontal, BookMarked, X, ChevronDown } from 'lucide-react';
import { Drawer, DrawerContent, DrawerHeader, DrawerTitle, DrawerClose } from '@/components/ui/drawer';
import { Button } from '@/components/ui/button';
import { Tooltip } from '@/components/ui/tooltip';
import { Input } from '@/components/ui/input';
import { ToggleGroup, ToggleGroupItem } from '@/components/ui/toggle-group';
import { InfoPopover } from '@/components/ui/info-popover';
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
import { useOpeningsPositionQuery } from '@/hooks/useOpenings';
import { useDebounce } from '@/hooks/useDebounce';
import {
  usePositionBookmarks,
  useCreatePositionBookmark,
  useReorderPositionBookmarks,
  useUpdateMatchSide,
  useTimeSeries,
} from '@/hooks/usePositionBookmarks';
import { useMostPlayedOpenings } from '@/hooks/useStats';
import { ChessBoard } from '@/components/board/ChessBoard';
import { MoveExplorer } from '@/components/move-explorer/MoveExplorer';
import { MoveList } from '@/components/board/MoveList';
import { BoardControls } from '@/components/board/BoardControls';
import { FilterPanel } from '@/components/filters/FilterPanel';
import { useFilterStore } from '@/hooks/useFilterStore';
import { PositionBookmarkList } from '@/components/position-bookmarks/PositionBookmarkList';
import { SuggestionsModal } from '@/components/position-bookmarks/SuggestionsModal';
import { GameCardList } from '@/components/results/GameCardList';
import { getArrowColor } from '@/lib/arrowColor';
import { WDLChartRow } from '@/components/charts/WDLChartRow';
import { MostPlayedOpeningsTable } from '@/components/stats/MostPlayedOpeningsTable';
import { pgnToSanArray } from '@/lib/pgn';
import { WinRateChart } from '@/components/charts/WinRateChart';
import { apiClient } from '@/api/client';
import type { FilterState } from '@/components/filters/FilterPanel';
import type { Color, MatchSide } from '@/types/api';
import { resolveMatchSide } from '@/types/api';
import type { PositionBookmarkResponse, TimeSeriesRequest } from '@/types/position_bookmarks';

const PAGE_SIZE = 20;
// Number of most-played openings per color to use as default chart data when no bookmarks exist

export function OpeningsPage() {
  const location = useLocation();
  const navigate = useNavigate();
  const { data: profile } = useUserProfile();
  const hasGames = (profile?.chess_com_game_count ?? 0) + (profile?.lichess_game_count ?? 0) > 0;

  const needsRedirect = location.pathname === '/openings' || location.pathname === '/openings/';
  // Redirect old /openings/compare and /openings/statistics URLs to /openings/stats after tab rename
  const needsLegacyRedirect = location.pathname.endsWith('/statistics') || location.pathname.endsWith('/compare');

  const activeTab = location.pathname.includes('/games')
    ? 'games'
    : location.pathname.includes('/stats')
      ? 'stats'
      : 'explorer';

  // ── Board state ─────────────────────────────────────────────────────────────
  const chess = useChessGame();
  const [boardFlipped, setBoardFlipped] = useState(false);

  // ── Filter state (shared across pages) ───────────────────────────────────────
  const [filters, setFilters] = useFilterStore();
  const debouncedFilters = useDebounce(filters, 300);

  // ── Board arrows (hovered move) ─────────────────────────────────────────────
  const [hoveredMove, setHoveredMove] = useState<string | null>(null);

  // ── Sidebar tab state (desktop only) ────────────────────────────────────────
  const [sidebarTab, setSidebarTab] = useState<string>('filters');
  const [filtersHintDismissed, setFiltersHintDismissed] = useState(
    () => localStorage.getItem('filters-hint-dismissed') === 'true'
  );

  // ── Mobile sidebar state ────────────────────────────────────────────────────
  const [filterSidebarOpen, setFilterSidebarOpen] = useState(false);
  const [bookmarkSidebarOpen, setBookmarkSidebarOpen] = useState(false);
  const [localChartEnabled, setLocalChartEnabled] = useState<Record<number, boolean>>({});
  const [localMatchSides, setLocalMatchSides] = useState<Record<number, MatchSide>>({});
  const [localFilters, setLocalFilters] = useState<FilterState>(filters);

  // ── Mobile board collapse (swipe/tap handle) ─────────────────────────────
  const [boardCollapsed, setBoardCollapsed] = useState(false);
  const touchStartY = useRef(0);

  // Auto-collapse board when switching away from Moves tab, expand when returning
  const prevCollapseTab = useRef(activeTab);
  useEffect(() => {
    if (activeTab !== prevCollapseTab.current) {
      prevCollapseTab.current = activeTab;
      setBoardCollapsed(activeTab !== 'explorer');
    }
  }, [activeTab]);

  const handleHandleTouchStart = useCallback((e: React.TouchEvent) => {
    touchStartY.current = e.touches[0]!.clientY;
  }, []);

  const handleHandleTouchEnd = useCallback((e: React.TouchEvent) => {
    const MIN_SWIPE_DISTANCE = 30;
    const deltaY = e.changedTouches[0]!.clientY - touchStartY.current;
    if (deltaY < -MIN_SWIPE_DISTANCE) setBoardCollapsed(true);
    if (deltaY > MIN_SWIPE_DISTANCE) setBoardCollapsed(false);
  }, []);

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
  const [suggestionsOpen, setSuggestionsOpen] = useState(false);

  // ── Chart-enable toggle (persisted per bookmark in localStorage) ─────────────
  // Version counter to force chartEnabledMap recompute when a toggle changes
  const [chartToggleVersion, setChartToggleVersion] = useState(0);

  const chartEnabledMap = useMemo(() => {
    const map: Record<number, boolean> = {};
    for (const b of bookmarks) {
      map[b.id] = getChartEnabled(b.id);
    }
    return map;
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [bookmarks, chartToggleVersion]);

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

    return moves
      .map(entry => {
        const squares = moveMap.get(entry.move_san);
        if (!squares) return null;
        const isHovered = entry.move_san === hoveredMove;
        return {
          startSquare: squares.from,
          endSquare: squares.to,
          color: getArrowColor(entry.win_pct, entry.loss_pct, entry.game_count, isHovered),
          width: entry.game_count / maxCount,
          isHovered,
        };
      })
      .filter((a): a is NonNullable<typeof a> => a !== null);
  }, [nextMoves.data, chess.position, hoveredMove]);

  // ── Games tab data ──────────────────────────────────────────────────────────
  const targetHash = chess.getHashForOpenings(filters.matchSide, filters.color);
  const gamesQuery = useOpeningsPositionQuery({
    targetHash,
    filters: debouncedFilters,
    offset: gamesOffset,
    limit: PAGE_SIZE,
  });

  // Total game count — fetched on load to drive empty-state messaging
  const { data: gameCountData } = useQuery<{ count: number }>({
    queryKey: ['gameCount'],
    queryFn: async () => {
      const response = await apiClient.get<{ count: number }>('/users/games/count');
      return response.data;
    },
    staleTime: 30_000,
  });
  const gameCount = gameCountData?.count ?? null;

  // ── Stats tab data ─────────────────────────────────────────────────────────────

  // Most played openings — filter params applied to show top openings per color
  const { data: mostPlayedData } = useMostPlayedOpenings({
    recency: debouncedFilters.recency,
    timeControls: debouncedFilters.timeControls,
    platforms: debouncedFilters.platforms,
    rated: debouncedFilters.rated,
    opponentType: debouncedFilters.opponentType,
  });

  // Chart entries: real bookmarks filtered by chart-enable toggle
  const chartBookmarks = bookmarks.filter(b => chartEnabledMap[b.id] !== false);

  const timeSeriesRequest: TimeSeriesRequest | null = useMemo(() => {
    if (chartBookmarks.length === 0) return null;
    return {
      bookmarks: chartBookmarks.map((b) => ({
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
  }, [chartBookmarks, debouncedFilters]);

  const { data: tsData } = useTimeSeries(timeSeriesRequest);

  // Derive WDL stats per bookmark using aggregate fields (not rolling sub-counts)
  const wdlStatsMap = useMemo(() => {
    const map: Record<number, { wins: number; draws: number; losses: number; total: number }> = {};
    for (const s of tsData?.series ?? []) {
      map[s.bookmark_id] = {
        wins: s.total_wins,
        draws: s.total_draws,
        losses: s.total_losses,
        total: s.total_games,
      };
    }
    return map;
  }, [tsData]);

  // ── Handlers ────────────────────────────────────────────────────────────────

  const handleChartEnabledChange = useCallback((id: number, enabled: boolean) => {
    setChartEnabledStorage(id, enabled);
    setChartToggleVersion(v => v + 1);
    if (activeTab !== 'stats') navigate('/openings/stats');
  }, [activeTab, navigate]);

  const handleFiltersChange = useCallback((newFilters: FilterState) => {
    setFilters(newFilters);
    setGamesOffset(0);
    setFiltersHintDismissed(true);
    localStorage.setItem('filters-hint-dismissed', 'true');
  }, [setFilters]);

  const openBookmarkDialog = useCallback(() => {
    // Use currentPly, not full moveHistory length — user may have navigated back
    const defaultLabel = chess.openingName?.name ?? `Position (${chess.currentPly} moves)`;
    setBookmarkLabel(defaultLabel);
    setBookmarkDialogOpen(true);
  }, [chess]);

  const handleBookmarkSave = useCallback(async () => {
    const label = bookmarkLabel.trim();
    if (!label) return;

    const matchSide = filters.matchSide;
    const targetHash = chess.getHashForOpenings(matchSide, filters.color);
    const data = {
      label,
      target_hash: targetHash,
      fen: chess.position,
      // Truncate to currentPly — bookmark saves the displayed position, not moves played after it
      moves: chess.moveHistory.slice(0, chess.currentPly),
      color: filters.color,
      match_side: matchSide,
      is_flipped: boardFlipped,
    };
    try {
      await createBookmark.mutateAsync(data);
      setBookmarkDialogOpen(false);
      if (activeTab !== 'stats') navigate('/openings/stats');
      setSidebarTab('bookmarks');
    } catch {
      toast.error('Failed to save bookmark');
    }
  }, [chess, filters, boardFlipped, bookmarkLabel, createBookmark, activeTab, navigate]);

  /** Open games for a chart bookmark — loads position on board and navigates to games tab */
  const handleOpenChartBookmarkGames = useCallback((bookmark: PositionBookmarkResponse) => {
    if (bookmark.moves.length > 0) {
      // Real bookmark — load its moves
      chess.loadMoves(bookmark.moves);
    } else if (mostPlayedData) {
      // Default chart entry — find PGN from most-played data
      const allOpenings = [...(mostPlayedData.white ?? []), ...(mostPlayedData.black ?? [])];
      const opening = allOpenings.find(o => o.full_hash === bookmark.target_hash);
      if (opening) {
        chess.loadMoves(pgnToSanArray(opening.pgn));
      }
    }
    const color = bookmark.color ?? 'white';
    setBoardFlipped(color === 'black');
    setFilters(prev => ({ ...prev, color, matchSide: bookmark.match_side }));
    navigate('/openings/games');
    window.scrollTo({ top: 0 });
  }, [chess, navigate, mostPlayedData, setFilters]);

  /** Load opening PGN onto the board, set color/flip/filters, and navigate to games subtab */
  const handleOpenGames = useCallback((pgn: string, color: "white" | "black") => {
    chess.loadMoves(pgnToSanArray(pgn));
    setBoardFlipped(color === 'black');
    setFilters(prev => ({ ...prev, color, matchSide: 'both' as MatchSide }));
    navigate('/openings/games');
    window.scrollTo({ top: 0 });
  }, [chess, navigate, setFilters]);

  const handleLoadBookmark = useCallback((bkm: PositionBookmarkResponse) => {
    chess.loadMoves(bkm.moves);
    setBoardFlipped(bkm.is_flipped ?? false);
    setFilters(prev => ({ ...prev, color: bkm.color ?? 'white', matchSide: bkm.match_side }));
    if (activeTab !== 'explorer' && activeTab !== 'games') navigate('/openings/explorer');
    window.scrollTo({ top: 0 });
  }, [chess, setFilters, activeTab, navigate]);

  const handleReorder = useCallback((orderedIds: number[]) => {
    reorder.mutate(orderedIds);
  }, [reorder]);

  // ── Mobile sidebar handlers ──────────────────────────────────────────────────

  const openFilterSidebar = useCallback(() => {
    setLocalFilters({ ...filters });
    setFilterSidebarOpen(true);
  }, [filters]);

  const handleFilterSidebarOpenChange = useCallback((open: boolean) => {
    if (!open && filterSidebarOpen) {
      // Commit deferred filters on close (D-10, D-12)
      handleFiltersChange(localFilters);
      setBoardFlipped(localFilters.color === 'black');
      // Navigate to explorer if color or piece filter changed
      if ((localFilters.color !== filters.color || localFilters.matchSide !== filters.matchSide)
          && activeTab !== 'explorer' && activeTab !== 'games') {
        navigate('/openings/explorer');
      }
    }
    setFilterSidebarOpen(open);
  }, [filterSidebarOpen, localFilters, handleFiltersChange, filters.color, filters.matchSide, activeTab, navigate]);

  const updateMatchSide = useUpdateMatchSide();

  const openBookmarkSidebar = useCallback(() => {
    setLocalChartEnabled({ ...chartEnabledMap });
    setLocalMatchSides({});
    setBookmarkSidebarOpen(true);
  }, [chartEnabledMap]);

  const handleBookmarkSidebarOpenChange = useCallback((open: boolean) => {
    if (!open && bookmarkSidebarOpen) {
      // Commit deferred chart toggle changes on close
      for (const [idStr, enabled] of Object.entries(localChartEnabled)) {
        const id = Number(idStr);
        if (chartEnabledMap[id] !== enabled) {
          setChartEnabledStorage(id, enabled);
        }
      }
      // Commit deferred match side changes on close
      for (const [idStr, matchSide] of Object.entries(localMatchSides)) {
        const id = Number(idStr);
        updateMatchSide.mutate({ id, data: { match_side: matchSide } });
      }
      // Bump chart toggle version to refresh chartEnabledMap
      const chartChanged = Object.keys(localChartEnabled).some(idStr => chartEnabledMap[Number(idStr)] !== localChartEnabled[Number(idStr)]);
      if (chartChanged) {
        setChartToggleVersion(v => v + 1);
        if (activeTab !== 'stats') navigate('/openings/stats');
      }
    }
    setBookmarkSidebarOpen(open);
  }, [bookmarkSidebarOpen, localChartEnabled, localMatchSides, chartEnabledMap, updateMatchSide, activeTab, navigate]);

  const handleLocalChartEnabledChange = useCallback((id: number, enabled: boolean) => {
    setLocalChartEnabled(prev => ({ ...prev, [id]: enabled }));
  }, []);

  const handleLocalMatchSideChange = useCallback((id: number, matchSide: MatchSide) => {
    setLocalMatchSides(prev => ({ ...prev, [id]: matchSide }));
  }, []);

  // Bookmarks with local match_side overrides applied for visual feedback in mobile drawer
  const localBookmarks = useMemo(() => {
    if (Object.keys(localMatchSides).length === 0) return bookmarks;
    return bookmarks.map(b => {
      const localSide = localMatchSides[b.id];
      return localSide ? { ...b, match_side: localSide } : b;
    });
  }, [bookmarks, localMatchSides]);

  const handleLoadBookmarkFromSidebar = useCallback((bkm: PositionBookmarkResponse) => {
    handleLoadBookmark(bkm);
    setBookmarkSidebarOpen(false);
  }, [handleLoadBookmark]);

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

      {/* Board controls — directly below board, with info icon on the right */}
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
        infoSlot={
          <InfoPopover ariaLabel="Chessboard info" testId="chessboard-info" side="top">
            <div className="space-y-2">
              <p>
                Play moves on the board by clicking on squares or dragging pieces, or by clicking on the moves in the Moves tab.
              </p>
              <p>
                The arrows on the board show the next moves from your games that match the current filter settings. Thicker arrows mean the move occurred more frequently. Arrow colors indicate your win rate: dark green (60%+), light green (55-60%), grey (45-55%), light red (loss rate 55-60%), dark red (loss rate 60%+). Moves with fewer than 10 games are always grey.
              </p>
            </div>
          </InfoPopover>
        }
      />

      {/* Opening name */}
      <div className="flex items-center gap-2 px-1 text-sm min-h-[1.25rem]">
        {chess.openingName ? (
          <div className="flex items-baseline gap-2">
            <span className="font-mono text-xs text-muted-foreground">{chess.openingName.eco}</span>
            <span className="text-foreground">{chess.openingName.name}</span>
          </div>
        ) : (
          <span className="text-muted-foreground italic">Play some moves</span>
        )}
      </div>

      {/* Move list */}
      <MoveList
        moveHistory={chess.moveHistory}
        currentPly={chess.currentPly}
        onMoveClick={chess.goToMove}
      />

      <div className="border-t border-border/40" />

      {/* Sidebar tabs: Filters & Bookmarks */}
      <div className="border border-border rounded-md">
      <Tabs value={sidebarTab} onValueChange={setSidebarTab} className="gap-0">
        <TabsList variant="brand" className="w-full rounded-b-none" data-testid="sidebar-tabs">
          <TabsTrigger value="filters" data-testid="sidebar-tab-filters" className="flex-1 relative">
            <SlidersHorizontal className="mr-1.5 h-4 w-4" />
            Filters
            {bookmarks.length > 0 && !filtersHintDismissed && (
              <span
                className="absolute top-0.5 right-0.5 flex h-2.5 w-2.5"
                data-testid="filters-notification-dot"
              >
                <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-red-500 opacity-75" />
                <span className="relative inline-flex h-2.5 w-2.5 rounded-full bg-red-500" />
              </span>
            )}
          </TabsTrigger>
          <TabsTrigger value="bookmarks" data-testid="sidebar-tab-bookmarks" className="flex-1 relative">
            <BookMarked className="mr-1.5 h-4 w-4" />
            Bookmarks
            {bookmarks.length === 0 && hasGames && (
              <span
                className="absolute top-0.5 right-0.5 flex h-2.5 w-2.5"
                data-testid="bookmarks-notification-dot"
              >
                <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-red-500 opacity-75" />
                <span className="relative inline-flex h-2.5 w-2.5 rounded-full bg-red-500" />
              </span>
            )}
          </TabsTrigger>
        </TabsList>
        <TabsContent value="filters">
          <div className="p-2 space-y-3">
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
                    if (activeTab !== 'explorer' && activeTab !== 'games') navigate('/openings/explorer');
                  }}
                  variant="outline"
                  size="sm"
                  data-testid="filter-played-as"
                >
                  <ToggleGroupItem value="white" data-testid="filter-played-as-white">
                    <span className="inline-block h-3 w-3 rounded-xs border border-muted-foreground bg-white mr-1" />
                    White
                  </ToggleGroupItem>
                  <ToggleGroupItem value="black" data-testid="filter-played-as-black">
                    <span className="inline-block h-3 w-3 rounded-xs border border-muted-foreground bg-zinc-900 mr-1" />
                    Black
                  </ToggleGroupItem>
                </ToggleGroup>
              </div>

              <div className="ml-auto">
                <div className="mb-1 flex items-center gap-1">
                  <p className="text-xs text-muted-foreground">Piece filter</p>
                  <InfoPopover ariaLabel="Piece filter info" testId="piece-filter-info" side="top">
                    Use the option "Mine" to find games with a specific formation (e.g. the London System) regardless of the opponent's moves. "Mine" matches only your pieces, "Opponent" only theirs, and "Both" requires an exact match of all pieces. The Moves tab always uses "Both".
                  </InfoPopover>
                </div>
                <ToggleGroup
                  type="single"
                  value={filters.matchSide}
                  onValueChange={(v) => {
                    if (!v) return;
                    setFilters(prev => ({ ...prev, matchSide: v as MatchSide }));
                    if (activeTab !== 'explorer' && activeTab !== 'games') navigate('/openings/explorer');
                  }}
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
            <div className="border-t border-border/20" />
            {/* FilterPanel — all filter controls */}
            <FilterPanel filters={filters} onChange={handleFiltersChange} />
          </div>
        </TabsContent>
        <TabsContent value="bookmarks">
          <div className="p-2">
            {/* Save/Suggest buttons */}
            <div className="flex items-center gap-2 mb-2">
              <Button
                size="lg"
                variant="brand-outline"
                className="flex-1"
                onClick={openBookmarkDialog}
                data-testid="btn-bookmark"
              >
                <Save className="h-4 w-4" />
                Save
              </Button>
              <div className="px-1">
                <InfoPopover ariaLabel="Opening bookmarks info" testId="position-bookmarks-info" side="top">
                <div className="space-y-2">
                  <p>
                    Save the current position on the chess board as an opening bookmark.
                    Bookmarked openings appear in the Stats tab, showing your win/draw/loss breakdown and win rate over time for each bookmark.
                  </p>
                  <p>
                    Each bookmark has a Piece filter setting (Mine/Opponent/Both) that controls how positions are matched. You can change the Piece filter directly on each bookmark card.
                  </p>
                  <p>
                    Use the chart toggle on each bookmark to include or exclude it from the Bookmarked Openings charts.
                  </p>
                </div>
              </InfoPopover>
              </div>
              <Button
                size="lg"
                variant="brand-outline"
                className="flex-1"
                onClick={() => setSuggestionsOpen(true)}
                data-testid="btn-suggest-bookmarks"
              >
                <Sparkles className="h-4 w-4" />
                Suggest
              </Button>
            </div>
            <PositionBookmarkList
              bookmarks={bookmarks}
              onReorder={handleReorder}
              onLoad={handleLoadBookmark}
              chartEnabledMap={chartEnabledMap}
              onChartEnabledChange={handleChartEnabledChange}
            />
          </div>
        </TabsContent>
      </Tabs>
      </div>
    </div>
  );

  // ── Tab content ─────────────────────────────────────────────────────────────

  const hasNoGames = gameCount !== null && gameCount === 0;
  const gamesData = gamesQuery.data;
  const filtersMatchNothing = gamesData !== undefined && gamesData.matched_count === 0 && !hasNoGames;

  // Color icon + name reused in Position Results labels and the matched-games summary
  const colorIconSquare = (
    <span className={`inline-block h-3 w-3 rounded-xs border border-muted-foreground ${filters.color === 'white' ? 'bg-white' : 'bg-zinc-900'}`} />
  );
  const colorName = filters.color === 'white' ? 'White' : 'Black';
  const pieceFilterLabel = filters.matchSide === 'both' ? null : `(Piece filter: ${filters.matchSide === 'mine' ? 'Mine' : 'Opponent'})`;
  const positionResultsLabel = (
    <span className="inline-flex flex-wrap items-center gap-1.5">
      <span>Position Results played as</span>
      {colorIconSquare}
      <span>{colorName}</span>
      {pieceFilterLabel && <span className="basis-full md:basis-auto text-muted-foreground">{pieceFilterLabel}</span>}
    </span>
  );

  const moveExplorerContent = (
    <div className="flex flex-col gap-4">
      {gamesData && gamesData.stats.total > 0 && (
        <div className="charcoal-texture rounded-md p-4">
          <WDLChartRow
            data={gamesData.stats}
            label={positionResultsLabel}
            barHeight="h-6"
            gamesLink="/openings/games"
            onGamesLinkClick={() => window.scrollTo({ top: 0 })}
            gamesLinkTestId="btn-moves-to-games"
            gamesLinkAriaLabel="View games for this position"
            testId="wdl-moves-position"
          />
        </div>
      )}
      <div className="charcoal-texture rounded-md p-4">
        <MoveExplorer
          moves={nextMoves.data?.moves ?? []}
          isLoading={nextMoves.isLoading}
          isError={nextMoves.isError}
          position={chess.position}
          onMoveClick={(from, to) => chess.makeMove(from, to)}
          onMoveHover={setHoveredMove}
        />
      </div>
    </div>
  );

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
      ) : gamesQuery.isError ? (
        <div className="flex flex-1 flex-col items-center justify-center py-12 text-center">
          <p className="mb-2 text-base font-medium text-foreground">Failed to load games</p>
          <p className="text-sm text-muted-foreground">
            Something went wrong. Please try again in a moment.
          </p>
        </div>
      ) : gamesData ? (
        <>
          <div className="charcoal-texture rounded-md p-4">
            <WDLChartRow
              data={gamesData.stats}
              label={positionResultsLabel}
              barHeight="h-6"
              testId="wdl-games-position"
            />
          </div>
          <GameCardList
            games={gamesData.games}
            matchedCount={gamesData.matched_count}
            totalGames={gameCount ?? gamesData.stats.total}
            offset={gamesOffset}
            limit={PAGE_SIZE}
            onPageChange={setGamesOffset}
            matchLabel={(() => {
              const total = gameCount ?? gamesData.stats.total;
              const pct = total > 0 ? (gamesData.matched_count / total * 100).toFixed(1) : '0.0';
              return (
                <>
                  {gamesData.matched_count} of {total} ({pct}%) games played as{' '}
                  <span className="inline-flex items-center gap-1 align-middle">
                    {colorIconSquare}
                    {filters.color}
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

  const statisticsContent = (
    <div className="flex flex-col gap-4">
      {/* Bookmarked Openings: Results — empty state when no bookmarks, chart when data available */}
      {bookmarks.length === 0 ? (
        <div className="charcoal-texture rounded-md p-4">
          <h2 className="text-lg font-medium mb-3">
            <span className="inline-flex items-center gap-1">
              <BookMarked className="h-5 w-5" />
              Bookmarked Openings
            </span>
          </h2>
          <p className="text-sm text-muted-foreground mb-3">
            Save some openings as bookmarks to see your results and win rate over time here. Each bookmark has a Piece filter setting (Mine/Opponent/Both) that controls how positions are matched. Use the Suggest button to pick from your most-played positions.
          </p>
          <Button
            size="lg"
            variant="brand-outline"
            className="w-full"
            onClick={() => setSuggestionsOpen(true)}
            data-testid="btn-suggest-bookmarks-empty"
          >
            <Sparkles className="h-4 w-4" />
            Suggest
          </Button>
        </div>
      ) : chartBookmarks.length > 0 && (
        <div className="charcoal-texture rounded-md p-4">
          <div>
            <h2 className="text-lg font-medium mb-3">
              <span className="inline-flex items-center gap-1">
                <BookMarked className="h-5 w-5" />
                Bookmarked Openings: Results
                <InfoPopover ariaLabel="Results by opening info" testId="wdl-bar-chart-info" side="top">
                  Shows your win, draw, and loss percentages for each saved or most played position, based on the games that match the current filter settings. The length of the transparent bar indicates game count relative to other openings.
                </InfoPopover>
              </span>
            </h2>
            {!tsData ? (
              <div className="text-center text-muted-foreground py-8">Loading chart data...</div>
            ) : (() => {
              const rows = chartBookmarks
                .flatMap((b) => {
                  const s = wdlStatsMap[b.id];
                  // skip bookmarks with no stats or zero games
                  if (!s || s.total <= 0) return [];
                  const colorIcon = b.color === 'white' ? (
                    <span className="inline-block h-3 w-3 rounded-xs border border-muted-foreground bg-white" />
                  ) : b.color === 'black' ? (
                    <span className="inline-block h-3 w-3 rounded-xs border border-muted-foreground bg-zinc-900" />
                  ) : null;
                  const label = colorIcon ? (
                    <span className="inline-flex items-center gap-1.5">{colorIcon}{b.label}</span>
                  ) : b.label;
                  return [{ bookmark: b, label, stats: s }];
                })
                .sort((a, b) => b.stats.total - a.stats.total);

              if (rows.length === 0) {
                return (
                  <div className="text-center text-muted-foreground py-8">
                    No stats available for saved positions yet.
                  </div>
                );
              }

              const maxTotal = Math.max(...rows.map((r) => r.stats.total));

              return (
                <div className="space-y-2">
                  {rows.map((row) => (
                    <WDLChartRow
                      key={row.bookmark.id}
                      data={{
                        wins: row.stats.wins,
                        draws: row.stats.draws,
                        losses: row.stats.losses,
                        total: row.stats.total,
                        win_pct: row.stats.total > 0 ? (row.stats.wins / row.stats.total) * 100 : 0,
                        draw_pct: row.stats.total > 0 ? (row.stats.draws / row.stats.total) * 100 : 0,
                        loss_pct: row.stats.total > 0 ? (row.stats.losses / row.stats.total) * 100 : 0,
                      }}
                      label={row.label}
                      maxTotal={maxTotal}
                      onOpenGames={() => handleOpenChartBookmarkGames(row.bookmark)}
                      openGamesTestId={`wdl-opening-games-${row.bookmark.id}`}
                      testId={`wdl-opening-${row.bookmark.id}`}
                    />
                  ))}
                </div>
              );
            })()}
          </div>
        </div>
      )}
      {/* Win Rate Over Time — shown when bookmarks have time series data */}
      {tsData && (
        <div className="charcoal-texture rounded-md p-4">
          <WinRateChart bookmarks={chartBookmarks} series={tsData.series} />
        </div>
      )}
      {/* Most Played Openings as White */}
      {mostPlayedData && mostPlayedData.white.length > 0 && (
        <div className="charcoal-texture rounded-md p-4" data-testid="mpo-white-section">
          <h2 className="text-lg font-medium mb-3 flex items-center gap-1.5">
            <span className="inline-block h-3.5 w-3.5 rounded-xs border border-muted-foreground bg-white" />
            <span className="inline-flex items-center gap-1">
              Most Played Openings as White
              <InfoPopover ariaLabel="White openings info" testId="mpo-white-info" side="top">
                Your most frequently played openings as White, based on the lichess opening table. Only openings where White made the last move are shown here.
              </InfoPopover>
            </span>
          </h2>
          <MostPlayedOpeningsTable
            openings={mostPlayedData.white}
            color="white"
            testIdPrefix="mpo-white"
            onOpenGames={handleOpenGames}
          />
        </div>
      )}
      {/* Most Played Openings as Black */}
      {mostPlayedData && mostPlayedData.black.length > 0 && (
        <div className="charcoal-texture rounded-md p-4" data-testid="mpo-black-section">
          <h2 className="text-lg font-medium mb-3 flex items-center gap-1.5">
            <span className="inline-block h-3.5 w-3.5 rounded-xs border border-muted-foreground bg-zinc-900" />
            <span className="inline-flex items-center gap-1">
              Most Played Openings as Black
              <InfoPopover ariaLabel="Black openings info" testId="mpo-black-info" side="top">
                Your most frequently played openings as Black, based on the lichess opening table. Only openings where Black made the last move are shown here.
              </InfoPopover>
            </span>
          </h2>
          <MostPlayedOpeningsTable
            openings={mostPlayedData.black}
            color="black"
            testIdPrefix="mpo-black"
            onOpenGames={handleOpenGames}
          />
        </div>
      )}
    </div>
  );

  // ── Render ──────────────────────────────────────────────────────────────────

  if (needsRedirect) {
    return <Navigate to="/openings/explorer" replace />;
  }

  if (needsLegacyRedirect) {
    return <Navigate to="/openings/stats" replace />;
  }

  return (
    <div data-testid="openings-page" className="flex min-h-0 flex-1 flex-col bg-background">
      <main className="mx-auto w-full max-w-7xl flex-1 px-4 py-2 md:py-6 md:px-6">
        {/* Desktop: two-column layout */}
        <div className="hidden md:grid md:grid-cols-[350px_1fr] md:gap-8 xl:grid-cols-[400px_1fr]">
          <div className="min-w-0">{sidebar}</div>
          <div className="min-w-0">
            <Tabs value={activeTab} onValueChange={(val) => navigate(`/openings/${val}`)}>
              <TabsList variant="brand" className="w-full" data-testid="openings-tabs">
                <TabsTrigger value="explorer" data-testid="tab-move-explorer" className="flex-1">
                  <ArrowRightLeft className="mr-1.5 h-4 w-4" />
                  Moves
                </TabsTrigger>
                <TabsTrigger value="games" data-testid="tab-games" className="flex-1">
                  <Gamepad2 className="mr-1.5 h-4 w-4" />
                  Games
                </TabsTrigger>
                <TabsTrigger value="stats" data-testid="tab-stats" className="flex-1">
                  <BarChart2 className="mr-1.5 h-4 w-4" />
                  Stats
                </TabsTrigger>
              </TabsList>
              <TabsContent value="explorer" className="mt-4">
                {moveExplorerContent}
              </TabsContent>
              <TabsContent value="games" className="mt-4">
                {gamesContent}
              </TabsContent>
              <TabsContent value="stats" className="mt-4">
                {statisticsContent}
              </TabsContent>
            </Tabs>
          </div>
        </div>

        {/* Mobile: single column with sticky board */}
        <Tabs value={activeTab} onValueChange={(val) => navigate(`/openings/${val}`)} className="md:hidden flex flex-col gap-2 min-w-0">
          {/* Sticky board + controls — sticks to top of viewport while scrolling content below */}
          {/* z-20 to stay above ToggleGroupItem's focus:z-10 */}
          <div className="sticky top-0 z-20 bg-background shadow-[0_6px_20px_rgba(0,0,0,0.8)]">
            {/* Collapsible board section — animates via grid-rows trick */}
            <div className={`grid transition-[grid-template-rows] duration-200 ease-in-out ${boardCollapsed ? 'grid-rows-[0fr]' : 'grid-rows-[1fr]'}`}>
              <div className="overflow-hidden">
                <div className="flex items-stretch gap-1 pb-1">
                  <div className="flex-1 min-w-0">
                    <ChessBoard
                      position={chess.position}
                      onPieceDrop={chess.makeMove}
                      flipped={boardFlipped}
                      lastMove={chess.lastMove}
                      arrows={boardArrows}
                    />
                  </div>
                  {/* Vertical controls column: board nav + sidebar triggers */}
                  <div className="flex flex-col gap-0.5">
                    <BoardControls
                      vertical
                      className="flex-1"
                      onBack={chess.goBack}
                      onForward={chess.goForward}
                      onReset={() => { chess.reset(); setGamesOffset(0); }}
                      onFlip={() => setBoardFlipped((f) => !f)}
                      canGoBack={chess.currentPly > 0}
                      canGoForward={chess.currentPly < chess.moveHistory.length}
                      infoSlot={
                        <InfoPopover ariaLabel="Chessboard info" testId="chessboard-info-mobile" side="left">
                          Play moves on the board by tapping squares or dragging pieces.
                          <br /><br />
                          The arrows on the board show the next moves from your games that match the current filter settings. Thicker arrows mean the move occurred more frequently. Arrow colors indicate your win rate: dark green (60%+), light green (55-60%), grey (45-55%), light red (loss rate 55-60%), dark red (loss rate 60%+). Moves with fewer than 10 games are always grey.
                        </InfoPopover>
                      }
                    />
                    {/* Sidebar trigger buttons — icon-only, separated from nav buttons */}
                    <div className="mt-1 flex flex-col gap-1">
                      <Tooltip content={`Playing as ${filters.color}`} side="left">
                        <Button
                          variant="ghost"
                          size="icon"
                          className="h-9 w-9 !bg-toggle-active text-toggle-active-foreground hover:!bg-toggle-active"
                          onClick={() => {
                            const newColor: Color = filters.color === 'white' ? 'black' : 'white';
                            handleFiltersChange({ ...filters, color: newColor });
                            setBoardFlipped(newColor === 'black');
                            if (activeTab !== 'explorer' && activeTab !== 'games') navigate('/openings/explorer');
                          }}
                          data-testid="btn-toggle-played-as"
                          aria-label={`Playing as ${filters.color}, tap to switch`}
                        >
                          <span className={`inline-block h-4 w-4 rounded-xs border border-muted-foreground ${filters.color === 'white' ? 'bg-white' : 'bg-zinc-900'}`} />
                        </Button>
                      </Tooltip>
                      <Tooltip content="Open filters" side="left">
                        <Button
                          variant="ghost"
                          size="icon"
                          className="h-9 w-9 bg-toggle-active text-toggle-active-foreground hover:bg-toggle-active/80 relative"
                          onClick={openFilterSidebar}
                          data-testid="btn-open-filter-sidebar"
                          aria-label="Open filters"
                        >
                          <SlidersHorizontal className="h-4 w-4" />
                          {bookmarks.length > 0 && !filtersHintDismissed && (
                            <span
                              className="absolute top-0.5 right-0.5 flex h-2.5 w-2.5"
                              data-testid="filters-notification-dot-mobile"
                            >
                              <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-red-500 opacity-75" />
                              <span className="relative inline-flex h-2.5 w-2.5 rounded-full bg-red-500" />
                            </span>
                          )}
                        </Button>
                      </Tooltip>
                      <Tooltip content="Open bookmarks" side="left">
                        <Button
                          variant="ghost"
                          size="icon"
                          className="h-9 w-9 bg-toggle-active text-toggle-active-foreground hover:bg-toggle-active/80 relative"
                          onClick={openBookmarkSidebar}
                          data-testid="btn-open-bookmark-sidebar"
                          aria-label="Open bookmarks"
                        >
                          <BookMarked className="h-4 w-4" />
                          {bookmarks.length === 0 && hasGames && (
                            <span
                              className="absolute top-0.5 right-0.5 flex h-2.5 w-2.5"
                              data-testid="bookmarks-notification-dot-mobile"
                            >
                              <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-red-500 opacity-75" />
                              <span className="relative inline-flex h-2.5 w-2.5 rounded-full bg-red-500" />
                            </span>
                          )}
                        </Button>
                      </Tooltip>
                    </div>
                  </div>
                </div>
              </div>
            </div>
            <TabsList variant="brand" className="w-full h-8! mt-0.5" data-testid="openings-tabs-mobile">
              <TabsTrigger value="explorer" className="flex-1 text-xs!" data-testid="tab-move-explorer-mobile">
                Moves
              </TabsTrigger>
              <TabsTrigger value="games" className="flex-1 text-xs!" data-testid="tab-games-mobile">
                Games
              </TabsTrigger>
              <TabsTrigger value="stats" className="flex-1 text-xs!" data-testid="tab-stats-mobile">
                Stats
              </TabsTrigger>
            </TabsList>
            {/* Swipe/tap handle — toggle board collapse */}
            <button
              className="mt-1 flex w-full items-center justify-center py-0.5 touch-none bg-white/15 border-t border-white/15 rounded-b-md"
              onTouchStart={handleHandleTouchStart}
              onTouchEnd={handleHandleTouchEnd}
              onClick={() => setBoardCollapsed((c) => !c)}
              aria-label={boardCollapsed ? 'Expand board' : 'Collapse board'}
              data-testid="btn-board-collapse-handle"
            >
              <ChevronDown className={`h-4 w-4 text-muted-foreground transition-transform duration-200 ${boardCollapsed ? 'rotate-0' : 'rotate-180'}`} />
            </button>
          </div>

          {/* Filter sidebar (D-04, D-05, D-06, D-10, D-12) */}
          <Drawer open={filterSidebarOpen} onOpenChange={handleFilterSidebarOpenChange} direction="right">
            <DrawerContent className="!w-full sm:!w-3/4 !bottom-auto !rounded-bl-xl max-h-[85vh]" data-testid="drawer-filter-sidebar">
              <DrawerHeader className="flex flex-row items-center justify-between">
                <DrawerTitle>Filters</DrawerTitle>
                <Tooltip content="Close filters">
                  <DrawerClose asChild>
                    <Button variant="ghost" size="icon" aria-label="Close filters" data-testid="btn-close-filter-sidebar">
                      <X className="h-4 w-4" />
                    </Button>
                  </DrawerClose>
                </Tooltip>
              </DrawerHeader>
              <div className="overflow-y-auto flex-1 p-4 space-y-4">
                {/* Played as + Piece filter — same row like desktop */}
                <div className="flex flex-wrap gap-x-4 gap-y-3">
                  <div>
                    <p className="mb-1 text-xs text-muted-foreground">Played as</p>
                    <ToggleGroup
                      type="single"
                      value={localFilters.color}
                      onValueChange={(v) => {
                        if (!v) return;
                        setLocalFilters(prev => ({ ...prev, color: v as Color }));
                      }}
                      variant="outline"
                      size="sm"
                      data-testid="filter-played-as-sidebar"
                    >
                      <ToggleGroupItem value="white" data-testid="filter-played-as-white-sidebar" className="min-h-11">
                        <span className="inline-block h-3 w-3 rounded-xs border border-muted-foreground bg-white mr-1" />
                        White
                      </ToggleGroupItem>
                      <ToggleGroupItem value="black" data-testid="filter-played-as-black-sidebar" className="min-h-11">
                        <span className="inline-block h-3 w-3 rounded-xs border border-muted-foreground bg-zinc-900 mr-1" />
                        Black
                      </ToggleGroupItem>
                    </ToggleGroup>
                  </div>
                  <div className="ml-auto">
                    <div className="mb-1 flex items-center gap-1">
                      <p className="text-xs text-muted-foreground">Piece filter</p>
                      <InfoPopover ariaLabel="Piece filter info" testId="piece-filter-info-sidebar" side="top">
                        Use the option "Mine" to find games with a specific formation (e.g. the London System) regardless of the opponent's moves. "Mine" matches only your pieces, "Opponent" only theirs, and "Both" requires an exact match of all pieces. The Moves tab always uses "Both".
                      </InfoPopover>
                    </div>
                    <ToggleGroup
                      type="single"
                      value={localFilters.matchSide}
                      onValueChange={(v) => {
                        if (!v) return;
                        setLocalFilters(prev => ({ ...prev, matchSide: v as MatchSide }));
                      }}
                      variant="outline"
                      size="sm"
                      data-testid="filter-piece-filter-sidebar"
                    >
                      <ToggleGroupItem value="mine" data-testid="filter-piece-filter-mine-sidebar" className="min-h-11">Mine</ToggleGroupItem>
                      <ToggleGroupItem value="opponent" data-testid="filter-piece-filter-opponent-sidebar" className="min-h-11">Opponent</ToggleGroupItem>
                      <ToggleGroupItem value="both" data-testid="filter-piece-filter-both-sidebar" className="min-h-11">Both</ToggleGroupItem>
                    </ToggleGroup>
                  </div>
                </div>

                {/* Remaining filters (5 fields: timeControl, platform, rated, opponent, recency) */}
                <FilterPanel filters={localFilters} onChange={setLocalFilters} />
              </div>
            </DrawerContent>
          </Drawer>

          {/* Bookmark sidebar (D-04, D-05, D-06, D-13, D-14) */}
          <Drawer open={bookmarkSidebarOpen} onOpenChange={handleBookmarkSidebarOpenChange} direction="right">
            <DrawerContent className="!w-full sm:!w-3/4 !bottom-auto !rounded-bl-xl max-h-[85vh]" data-testid="drawer-bookmark-sidebar">
              <DrawerHeader className="flex flex-row items-center justify-between">
                <DrawerTitle className="flex items-center gap-1">
                  Opening Bookmarks
                  <InfoPopover ariaLabel="Opening bookmarks info" testId="position-bookmarks-info-sidebar" side="top">
                    <div className="space-y-2">
                    <p>
                      Save the current position on the chess board as an opening bookmark.
                      Bookmarked openings appear in the Stats tab, showing your win/draw/loss breakdown and win rate over time for each bookmark.
                    </p>
                      <p>
                        Each bookmark has a Piece filter setting (Mine/Opponent/Both) that controls how positions are matched. You can change the Piece filter directly on each bookmark card.
                      </p>
                      <p>
                        Use the chart toggle on each bookmark to include or exclude it from the Bookmarked Openings charts.
                      </p>
                    </div>
                  </InfoPopover>
                </DrawerTitle>
                <Tooltip content="Close bookmarks">
                  <DrawerClose asChild>
                    <Button variant="ghost" size="icon" aria-label="Close bookmarks" data-testid="btn-close-bookmark-sidebar">
                      <X className="h-4 w-4" />
                    </Button>
                  </DrawerClose>
                </Tooltip>
              </DrawerHeader>
              <div className="overflow-y-auto flex-1 p-4">
                <div className="space-y-3">
                  <div className="flex items-center gap-2">
                    <Button
                      size="lg"
                      variant="brand-outline"
                      className="flex-1"
                      onClick={openBookmarkDialog}
                      data-testid="btn-bookmark-sidebar"
                    >
                      <Save className="h-4 w-4" />
                      Save
                    </Button>
                    <Button
                      size="lg"
                      variant="brand-outline"
                      className="flex-1"
                      onClick={() => setSuggestionsOpen(true)}
                      data-testid="btn-suggest-bookmarks-sidebar"
                    >
                      <Sparkles className="h-4 w-4" />
                      Suggest
                    </Button>
                  </div>
                  <PositionBookmarkList
                    bookmarks={localBookmarks}
                    onReorder={handleReorder}
                    onLoad={handleLoadBookmarkFromSidebar}
                    chartEnabledMap={localChartEnabled}
                    onChartEnabledChange={handleLocalChartEnabledChange}
                    onMatchSideChange={handleLocalMatchSideChange}
                  />
                </div>
              </div>
            </DrawerContent>
          </Drawer>

          {/* Opening name + move list — hidden when board is collapsed */}
          {!boardCollapsed && (
            <>
              <div className="flex items-center gap-2 px-1 text-sm min-h-[1.25rem]">
                {chess.openingName ? (
                  <div className="flex items-baseline gap-2">
                    <span className="font-mono text-xs text-muted-foreground">{chess.openingName.eco}</span>
                    <span className="text-foreground">{chess.openingName.name}</span>
                  </div>
                ) : (
                  <span className="text-muted-foreground italic">Play some moves</span>
                )}
              </div>
              <MoveList
                moveHistory={chess.moveHistory}
                currentPly={chess.currentPly}
                onMoveClick={chess.goToMove}
              />
            </>
          )}

          <TabsContent value="explorer" className="mt-2">
            {moveExplorerContent}
          </TabsContent>
          <TabsContent value="games" className="mt-2">
            {gamesContent}
          </TabsContent>
          <TabsContent value="stats" className="mt-2">
            {statisticsContent}
          </TabsContent>
        </Tabs>
      </main>

      {/* Bookmark label dialog */}
      <Dialog open={bookmarkDialogOpen} onOpenChange={setBookmarkDialogOpen}>
        <DialogContent data-testid="bookmark-dialog">
          <DialogHeader>
            <DialogTitle>Save Bookmark</DialogTitle>
            <DialogDescription>
              Enter a label for this opening bookmark.
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

      <SuggestionsModal
        open={suggestionsOpen}
        onOpenChange={setSuggestionsOpen}
        mostPlayedData={mostPlayedData}
        bookmarks={bookmarks}
        onSaved={() => {
          if (activeTab !== 'stats') navigate('/openings/stats');
          setSidebarTab('bookmarks');
        }}
      />
    </div>
  );
}
