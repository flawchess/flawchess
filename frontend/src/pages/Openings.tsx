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
import { Save, Sparkles, ArrowRightLeft, Swords, BarChart2, Lightbulb, SlidersHorizontal, BookMarked, X, ChevronDown, ChevronUp } from 'lucide-react';
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
import { useMostPlayedOpenings, useBookmarkPhaseEntryMetrics } from '@/hooks/useStats';
import { rangeToQueryParams } from '@/lib/opponentStrength';
import { ChessBoard } from '@/components/board/ChessBoard';
import { MoveExplorer } from '@/components/move-explorer/MoveExplorer';
import { MoveList } from '@/components/board/MoveList';
import { BoardControls } from '@/components/board/BoardControls';
import { FilterPanel, DEFAULT_FILTERS, areFiltersEqual, FILTER_DOT_FIELDS } from '@/components/filters/FilterPanel';
import { useFilterStore } from '@/hooks/useFilterStore';
import { PositionBookmarkList } from '@/components/position-bookmarks/PositionBookmarkList';
import { SuggestionsModal } from '@/components/position-bookmarks/SuggestionsModal';
import { GameCardList } from '@/components/results/GameCardList';
import { SidebarLayout, type SidebarPanelConfig } from '@/components/layout/SidebarLayout';
import { getArrowColor } from '@/lib/arrowColor';
import { WDLChartRow } from '@/components/charts/WDLChartRow';
import { MostPlayedOpeningsTable } from '@/components/stats/MostPlayedOpeningsTable';
import { MinimapPopover } from '@/components/stats/MinimapPopover';
import { MiniBulletChart } from '@/components/charts/MiniBulletChart';
import { BulletConfidencePopover } from '@/components/insights/BulletConfidencePopover';
import {
  EVAL_BULLET_DOMAIN_PAWNS,
  EVAL_NEUTRAL_MAX_PAWNS,
  EVAL_NEUTRAL_MIN_PAWNS,
  EVAL_BASELINE_PAWNS_WHITE,
  EVAL_BASELINE_PAWNS_BLACK,
  buildMgEvalHeaderTooltip,
  evalZoneColor,
} from '@/lib/openingStatsZones';
import { formatSignedEvalPawns } from '@/lib/clockFormat';
import {
  MIN_GAMES_OPENING_ROW,
  UNRELIABLE_OPACITY,
} from '@/lib/theme';
import { pgnToSanArray, sanArrayToPgn } from '@/lib/pgn';
import { WinRateChart } from '@/components/charts/WinRateChart';
import { apiClient } from '@/api/client';
import { OpeningInsightsBlock } from '@/components/insights/OpeningInsightsBlock';
import { getSeverityBorderColor } from '@/lib/openingInsights';
import { getBoardContainerClassName } from '@/lib/openingsBoardLayout';
import { HIGHLIGHT_PULSE_DURATION_MS, HIGHLIGHT_PULSE_ITERATIONS } from '@/lib/highlightPulse';
import type { FilterState } from '@/components/filters/FilterPanel';
import type { Color, MatchSide } from '@/types/api';
import { resolveMatchSide } from '@/types/api';
import type { PositionBookmarkResponse, TimeSeriesRequest } from '@/types/position_bookmarks';
import type { OpeningWDL } from '@/types/stats';
import type { OpeningInsightFinding } from '@/types/insights';

const PAGE_SIZE = 20;
// Number of most-played openings per color to use as default chart data when no bookmarks exist

type SidebarPanel = 'filters' | 'bookmarks';

// MOBILE MostPlayedOpenings renderer (STAB-02 / D-11-D-14)
// Renders each opening as a WDLChartRow, matching the Bookmarked Openings: Results
// visual style. Desktop keeps the existing MostPlayedOpeningsTable (unchanged).
// Preserves the INITIAL_VISIBLE_COUNT = 3 collapse/expand behavior from MostPlayedOpeningsTable.
const MOBILE_MPO_INITIAL_VISIBLE_COUNT = 3;

function MobileMostPlayedRows({
  openings,
  color,
  testIdPrefix,
  onOpenGames,
  evalBaselinePawns,
  showAll = false,
}: {
  openings: OpeningWDL[];
  color: 'white' | 'black';
  testIdPrefix: string;
  onOpenGames: (opening: OpeningWDL, color: 'white' | 'black') => void;
  evalBaselinePawns: number;
  showAll?: boolean;
}) {
  const [expanded, setExpanded] = useState(false);

  if (openings.length === 0) return null;

  const visibleOpenings = showAll || expanded
    ? openings
    : openings.slice(0, MOBILE_MPO_INITIAL_VISIBLE_COUNT);
  const hiddenCount = openings.length - MOBILE_MPO_INITIAL_VISIBLE_COUNT;
  const hasMore = !showAll && hiddenCount > 0;

  return (
    <div data-testid={`${testIdPrefix}-mobile-list`}>
      <div className="space-y-3">
        {visibleOpenings.map((o, i) => {
          const rowKey = o.opening_eco || o.full_hash || `${o.opening_name}-${i}`;
          const isRowMuted = o.total < MIN_GAMES_OPENING_ROW;
          return (
            <div
              key={rowKey}
              data-testid={`${testIdPrefix}-row-${rowKey}`}
              style={isRowMuted ? { opacity: UNRELIABLE_OPACITY } : undefined}
            >
              {/* Name row: opening name wraps full width, games count shrink-0 on right */}
              <div className="flex items-start justify-between gap-2 mb-1">
                <div className="flex-1 min-w-0">
                  <MinimapPopover
                    fen={o.fen}
                    boardOrientation={color}
                    testId={`${testIdPrefix}-minimap-${rowKey}`}
                  >
                    <span className="block text-sm font-medium leading-tight break-words">
                      {/* display_name carries a "vs. " prefix when off-color (PRE-01). */}
                      {o.display_name}
                    </span>
                  </MinimapPopover>
                </div>
                <Tooltip content={`View ${o.total} games for ${o.opening_name}`}>
                  <button
                    className="shrink-0 flex items-center gap-1 text-xs text-brand-brown-light hover:text-brand-brown-highlight transition-colors"
                    aria-label={`View ${o.total} games for ${o.opening_name}`}
                    data-testid={`${testIdPrefix}-games-${rowKey}`}
                    onClick={() => onOpenGames(o, color)}
                  >
                    <span className="tabular-nums">{o.total}</span>
                    <Swords className="h-3.5 w-3.5" />
                  </button>
                </Tooltip>
              </div>
              {/* Full-width WDL bar below the name */}
              <WDLChartRow
                data={{
                  wins: o.wins,
                  draws: o.draws,
                  losses: o.losses,
                  total: o.total,
                  win_pct: o.win_pct,
                  draw_pct: o.draw_pct,
                  loss_pct: o.loss_pct,
                }}
              />

              {/* Phase 80 D-06: Mobile line 2 — MG-entry row (label + eval text + bullet w/ confidence popover). */}
              {(() => {
                const hasMgEval =
                  o.eval_n > 0 &&
                  o.avg_eval_pawns !== null &&
                  o.avg_eval_pawns !== undefined;
                const mgEvalTextContent = hasMgEval ? (
                  <span
                    className="font-semibold"
                    style={{ color: evalZoneColor(o.avg_eval_pawns as number) }}
                  >
                    {formatSignedEvalPawns(o.avg_eval_pawns as number)}
                  </span>
                ) : (
                  <span className="text-muted-foreground">—</span>
                );
                const mgBulletContent = hasMgEval ? (
                  <MiniBulletChart
                    value={o.avg_eval_pawns as number}
                    ciLow={o.eval_ci_low_pawns ?? undefined}
                    ciHigh={o.eval_ci_high_pawns ?? undefined}
                    tickPawns={evalBaselinePawns}
                    neutralMin={EVAL_NEUTRAL_MIN_PAWNS}
                    neutralMax={EVAL_NEUTRAL_MAX_PAWNS}
                    domain={EVAL_BULLET_DOMAIN_PAWNS}
                    ariaLabel={`Avg eval at MG entry: ${(o.avg_eval_pawns as number).toFixed(2)} pawns`}
                  />
                ) : (
                  <span className="text-muted-foreground">—</span>
                );
                return (
                  <div
                    className="mt-2 grid grid-cols-[auto_auto_1fr] gap-2 items-center pb-1"
                    data-testid={`${testIdPrefix}-mobile-mg-line-${rowKey}`}
                  >
                    <span className="inline-flex items-center gap-1 text-xs text-muted-foreground">
                      Eval
                      {hasMgEval && (
                        <BulletConfidencePopover
                          level={o.eval_confidence}
                          pValue={o.eval_p_value}
                          gameCount={o.eval_n}
                          evalMeanPawns={o.avg_eval_pawns}
                          evalCiLowPawns={o.eval_ci_low_pawns}
                          evalCiHighPawns={o.eval_ci_high_pawns}
                          testId={`${testIdPrefix}-bullet-popover-mobile-${rowKey}`}
                          prefaceText={buildMgEvalHeaderTooltip()}
                        />
                      )}
                    </span>
                    <div
                      className="text-sm tabular-nums"
                      data-testid={`${testIdPrefix}-eval-text-mobile-${rowKey}`}
                    >
                      {mgEvalTextContent}
                    </div>
                    <div
                      data-testid={`${testIdPrefix}-bullet-mobile-${rowKey}`}
                    >
                      {mgBulletContent}
                    </div>
                  </div>
                );
              })()}
            </div>
          );
        })}
      </div>

      {hasMore && (
        <button
          className="flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground transition-colors mt-2 px-2"
          onClick={() => setExpanded(!expanded)}
          data-testid={`${testIdPrefix}-btn-more-mobile`}
          aria-label={expanded ? 'Show fewer openings' : `Show ${hiddenCount} more openings`}
        >
          {expanded ? (
            <>
              <ChevronUp className="h-4 w-4" />
              Less
            </>
          ) : (
            <>
              <ChevronDown className="h-4 w-4" />
              {hiddenCount} more
            </>
          )}
        </button>
      )}
    </div>
  );
}

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
      : location.pathname.includes('/insights')
        ? 'insights'
        : 'explorer';

  // ── Board state ─────────────────────────────────────────────────────────────
  const chess = useChessGame();
  const [boardFlipped, setBoardFlipped] = useState(false);

  // ── Filter state (shared across pages) ───────────────────────────────────────
  const [filters, setFilters] = useFilterStore();
  const debouncedFilters = useDebounce(filters, 300);

  // ── Board arrows (hovered move) ─────────────────────────────────────────────
  const [hoveredMove, setHoveredMove] = useState<string | null>(null);

  // ── Deep-link highlight (Insights → MoveExplorer / quick-task 260427-j41) ──
  // Set by handleOpenFinding when the user clicks a "Moves" link on an
  // OpeningFindingCard; cleared by MoveExplorer's onHighlightConsumed (position
  // change or row click), by leaving the explorer subtab, and by filter changes
  // (handled below in a baseline-snapshot effect).
  const [highlightedMove, setHighlightedMove] = useState<{ san: string; color: string } | null>(null);

  // Whether the deep-link pulse animations should currently render. Goes true
  // when highlightedMove is set, then auto-flips false after the pulse window.
  // Decoupling pulse-active from highlight-active prevents any later React
  // re-render (e.g. when hovering another move re-sorts the arrow list) from
  // re-attaching .animate-arrow-pulse and restarting the CSS animation. The
  // arrow/row sit at their static rest opacity/tint once the pulse expires.
  const [pulseActive, setPulseActive] = useState(false);
  useEffect(() => {
    if (highlightedMove == null) {
      setPulseActive(false);
      return;
    }
    setPulseActive(true);
    const timeoutId = window.setTimeout(
      () => setPulseActive(false),
      HIGHLIGHT_PULSE_ITERATIONS * HIGHLIGHT_PULSE_DURATION_MS,
    );
    return () => window.clearTimeout(timeoutId);
  }, [highlightedMove]);

  // ── Sidebar state (desktop only) ────────────────────────────────────────────
  const [sidebarOpen, setSidebarOpen] = useState<SidebarPanel | null>(null);
  const [playedAsHintDismissed, setPlayedAsHintDismissed] = useState(
    () => localStorage.getItem('played-as-hint-dismissed') === 'true'
  );
  const [filtersHintDismissed, setFiltersHintDismissed] = useState(
    () => localStorage.getItem('filters-hint-dismissed') === 'true'
  );

  const dismissPlayedAsHint = useCallback(() => {
    setPlayedAsHintDismissed(true);
    localStorage.setItem('played-as-hint-dismissed', 'true');
  }, []);

  // ── Mobile sidebar state ────────────────────────────────────────────────────
  const [filterSidebarOpen, setFilterSidebarOpen] = useState(false);
  const [bookmarkSidebarOpen, setBookmarkSidebarOpen] = useState(false);
  const [localChartEnabled, setLocalChartEnabled] = useState<Record<number, boolean>>({});
  const [localMatchSides, setLocalMatchSides] = useState<Record<number, MatchSide>>({});
  const [localFilters, setLocalFilters] = useState<FilterState>(filters);

  // ── Games tab pagination ────────────────────────────────────────────────────
  const [gamesOffset, setGamesOffset] = useState(0);

  // Reset pagination on tab switch
  const [prevTab, setPrevTab] = useState(activeTab);
  if (activeTab !== prevTab) {
    setPrevTab(activeTab);
    setGamesOffset(0);
  }

  // Clear the deep-link highlight when leaving the explorer subtab — the
  // highlighted row only makes sense inside MoveExplorer, so don't carry it
  // across tab navigations. Mirrors the prevTab pattern above.
  const [prevTabForHighlight, setPrevTabForHighlight] = useState(activeTab);
  if (activeTab !== prevTabForHighlight) {
    setPrevTabForHighlight(activeTab);
    if (activeTab !== 'explorer' && highlightedMove !== null) {
      setHighlightedMove(null);
    }
  }

  // Clear the deep-link highlight when filters change AFTER the highlight was
  // set. Snapshot the filter identity at the moment the highlight transitions
  // to non-null; later filter changes (with the same highlight active) clear it.
  // Living here (not in MoveExplorer) avoids a false-trigger from the moves-array
  // reference change when the useNextMoves query first resolves on tab mount.
  const filtersAtHighlightRef = useRef<FilterState | null>(null);
  const prevHighlightForFilterClearRef = useRef(highlightedMove);
  useEffect(() => {
    const highlightChanged = prevHighlightForFilterClearRef.current !== highlightedMove;
    prevHighlightForFilterClearRef.current = highlightedMove;
    if (highlightedMove == null) {
      filtersAtHighlightRef.current = null;
      return;
    }
    if (highlightChanged) {
      filtersAtHighlightRef.current = filters;
      return;
    }
    if (filtersAtHighlightRef.current !== null && filtersAtHighlightRef.current !== filters) {
      setHighlightedMove(null);
    }
  }, [filters, highlightedMove]);

  // ── Bookmarks ───────────────────────────────────────────────────────────────
  const { data: bookmarks = [] } = usePositionBookmarks();
  const createBookmark = useCreatePositionBookmark();
  const reorder = useReorderPositionBookmarks();
  const [bookmarkDialogOpen, setBookmarkDialogOpen] = useState(false);
  const [bookmarkLabel, setBookmarkLabel] = useState('');
  const [suggestionsOpen, setSuggestionsOpen] = useState(false);

  // Onboarding hint progression (only one red dot visible at a time):
  // played-as → filters → bookmarks. Each step unlocks the next once used.
  const showPlayedAsHint = hasGames && !playedAsHintDismissed;
  const showFiltersHint = hasGames && playedAsHintDismissed && !filtersHintDismissed;
  const showBookmarksHint =
    hasGames && playedAsHintDismissed && filtersHintDismissed && bookmarks.length === 0;

  // ── Modified-filters indicator ─────────────────────────────────────────────
  // Desktop: filters apply immediately, so the dot tracks `filters` directly.
  // Mobile drawer: defers apply until drawer close, so the dot also tracks `filters`
  // (the committed state), and we add a one-shot pulse on drawer close when
  // localFilters differed from filters at close time.
  const justCommittedFromDrawerRef = useRef(false);
  const isFiltersModified = useMemo(
    () => !areFiltersEqual(filters, DEFAULT_FILTERS, FILTER_DOT_FIELDS),
    [filters],
  );
  const [isFiltersPulsing, setIsFiltersPulsing] = useState(false);
  const filtersPulseTimeoutRef = useRef<number | null>(null);
  const prevFiltersRef = useRef(filters);

  useEffect(() => {
    if (prevFiltersRef.current !== filters) {
      prevFiltersRef.current = filters;
      // On Openings desktop, `filters` changes live as the user toggles — pulsing on every
      // change would be noisy. Only pulse when the mobile drawer JUST closed AND committed
      // a change. We guard via `justCommittedFromDrawerRef` set inside handleFilterSidebarOpenChange.
      if (justCommittedFromDrawerRef.current) {
        justCommittedFromDrawerRef.current = false;
        setIsFiltersPulsing(true);
        if (filtersPulseTimeoutRef.current !== null) {
          window.clearTimeout(filtersPulseTimeoutRef.current);
        }
        filtersPulseTimeoutRef.current = window.setTimeout(() => {
          setIsFiltersPulsing(false);
          filtersPulseTimeoutRef.current = null;
        }, 1000);
      }
    }
    return () => {
      if (filtersPulseTimeoutRef.current !== null) {
        window.clearTimeout(filtersPulseTimeoutRef.current);
        filtersPulseTimeoutRef.current = null;
      }
    };
  }, [filters]);

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

  // Board arrows derived from next move frequencies.
  // Highlight pulse decision (quick-task 260427-j41): the matching arrow gets
  // isHighlightPulse=true so its <path> animates briefly. The arrow's COLOR
  // stays whatever getArrowColor returned — we deliberately do NOT recolor it
  // to highlightedMove.color. The MoveExplorer row border uses the severity
  // color (which encodes weakness/strength + minor/major); the on-board pulse
  // only modulates opacity so the arrow stays consistent with the rest of the
  // arrow set. This keeps the visual language clean: row = severity-coded
  // emphasis, arrow = pulse-only attention grab.
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
        const isHighlightPulse = pulseActive && highlightedMove !== null && entry.move_san === highlightedMove.san;
        return {
          startSquare: squares.from,
          endSquare: squares.to,
          color: getArrowColor(entry.score, entry.game_count, entry.confidence, isHovered),
          width: entry.game_count / maxCount,
          isHovered,
          isHighlightPulse,
        };
      })
      .filter((a): a is NonNullable<typeof a> => a !== null);
  }, [nextMoves.data, chess.position, hoveredMove, highlightedMove, pulseActive]);

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
  const {
    data: mostPlayedData,
    isLoading: mostPlayedLoading,
    isError: mostPlayedError,
  } = useMostPlayedOpenings({
    recency: debouncedFilters.recency,
    timeControls: debouncedFilters.timeControls,
    platforms: debouncedFilters.platforms,
    rated: debouncedFilters.rated,
    opponentType: debouncedFilters.opponentType,
    opponentStrength: debouncedFilters.opponentStrength,
  });

  // Chart entries: real bookmarks filtered by chart-enable toggle.
  // Memoized so the array identity is stable across renders that don't change
  // the underlying bookmarks or toggle map — keeps `timeSeriesRequest` (which
  // depends on this) from being rebuilt on every parent tick.
  const chartBookmarks = useMemo(
    () => bookmarks.filter(b => chartEnabledMap[b.id] !== false),
    [bookmarks, chartEnabledMap],
  );

  // Phase 80 fix: per-bookmark MG/EG entry eval + clock-diff metrics.
  // Without this, bookmark rows in the Stats subtab tables permanently render with
  // eval_n=0 / "low" / "0 games" because buildBookmarkRows hardcoded those fields.
  const bookmarkMetricsRequest = useMemo(
    () =>
      chartBookmarks.map((b) => ({
        target_hash: b.target_hash,
        match_side: resolveMatchSide(b.match_side, (b.color ?? 'white') as Color),
        color: b.color,
      })),
    [chartBookmarks],
  );
  const { data: bookmarkPhaseEntryData } = useBookmarkPhaseEntryMetrics(
    bookmarkMetricsRequest,
    {
      recency: debouncedFilters.recency,
      timeControls: debouncedFilters.timeControls,
      platforms: debouncedFilters.platforms,
      rated: debouncedFilters.rated,
      opponentType: debouncedFilters.opponentType,
      opponentStrength: debouncedFilters.opponentStrength,
    },
  );
  const bookmarkPhaseEntryByHash = useMemo(() => {
    const map = new Map<string, NonNullable<typeof bookmarkPhaseEntryData>['items'][number]>();
    for (const item of bookmarkPhaseEntryData?.items ?? []) {
      map.set(item.target_hash, item);
    }
    return map;
  }, [bookmarkPhaseEntryData]);

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
      ...rangeToQueryParams(debouncedFilters.opponentStrength),
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
      setSidebarOpen('bookmarks');
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

  /**
   * Phase 71 (D-13): Deep-link from OpeningInsightsBlock to Move Explorer.
   * Mirror of handleOpenGames retargeted at /openings/explorer. The finding
   * carries entry_san_sequence as a pre-parsed string[], so no pgnToSanArray
   * conversion is needed.
   */
  const handleOpenFinding = useCallback(
    (finding: OpeningInsightFinding) => {
      chess.loadMoves(finding.entry_san_sequence);
      // Set the deep-link highlight BEFORE navigation so MoveExplorer renders
      // with the highlight on its first paint after the route change. The
      // severity color matches the OpeningFindingCard's left-border color.
      setHighlightedMove({
        san: finding.candidate_move_san,
        color: getSeverityBorderColor(finding.classification, finding.severity),
      });
      setBoardFlipped(finding.color === 'black');
      setFilters((prev) => ({
        ...prev,
        color: finding.color,
        matchSide: 'both' as MatchSide,
      }));
      navigate('/openings/explorer');
      window.scrollTo({ top: 0 });
    },
    [chess, navigate, setFilters],
  );

  /**
   * Same as handleOpenFinding but routes to the Games subtab. Loads the position
   * AFTER the candidate move (entry_san_sequence + candidate_move_san) so the
   * Games filter matches the resulting position, not the entry position.
   */
  const handleOpenFindingGames = useCallback(
    (finding: OpeningInsightFinding) => {
      chess.loadMoves([...finding.entry_san_sequence, finding.candidate_move_san]);
      setBoardFlipped(finding.color === 'black');
      setFilters((prev) => ({
        ...prev,
        color: finding.color,
        matchSide: 'both' as MatchSide,
      }));
      navigate('/openings/games');
      window.scrollTo({ top: 0 });
    },
    [chess, navigate, setFilters],
  );

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
      // Pulse the filter indicator if the drawer commit actually changes `filters`.
      // Check BEFORE handleFiltersChange runs (which updates `filters`).
      if (!areFiltersEqual(localFilters, filters)) {
        justCommittedFromDrawerRef.current = true;
      }
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
  }, [filterSidebarOpen, localFilters, handleFiltersChange, filters, activeTab, navigate]);

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

  const handleLoadBookmarkFromDesktopSidebar = useCallback((bkm: PositionBookmarkResponse) => {
    handleLoadBookmark(bkm);
    setSidebarOpen(null);
  }, [handleLoadBookmark]);

  // ── Desktop sidebar panel content ───────────────────────────────────────────

  const desktopFilterPanelContent = (
    <div className="p-3 space-y-3">
      {/* Piece filter */}
      <div className="space-y-3">
        <div>
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
              handleFiltersChange({ ...filters, matchSide: v as MatchSide });
              if (activeTab !== 'explorer' && activeTab !== 'games') navigate('/openings/explorer');
            }}
            variant="outline"
            size="sm"
            className="w-full"
            data-testid="filter-piece-filter"
          >
            <ToggleGroupItem value="mine" className="flex-1" data-testid="filter-piece-filter-mine">Mine</ToggleGroupItem>
            <ToggleGroupItem value="opponent" className="flex-1" data-testid="filter-piece-filter-opponent">Opponent</ToggleGroupItem>
            <ToggleGroupItem value="both" className="flex-1" data-testid="filter-piece-filter-both">Both</ToggleGroupItem>
          </ToggleGroup>
        </div>
      </div>
      <div className="border-t border-border/20" />
      {/* FilterPanel — all filter controls. Uses filters/handleFiltersChange directly (NOT localFilters — desktop applies live) */}
      <FilterPanel filters={filters} onChange={handleFiltersChange} />
    </div>
  );

  const desktopBookmarkPanelContent = (
    <div className="p-3">
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
        onLoad={handleLoadBookmarkFromDesktopSidebar}
        chartEnabledMap={chartEnabledMap}
        onChartEnabledChange={handleChartEnabledChange}
      />
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
      <span>Results played as</span>
      {colorIconSquare}
      <span>{colorName}</span>
      {pieceFilterLabel && <span className="basis-full md:basis-auto text-muted-foreground">{pieceFilterLabel}</span>}
    </span>
  );

  const moveExplorerContent = (
    <div className="flex flex-col gap-4">
      {gamesData && gamesData.stats.total > 0 && (
        <div className="charcoal-texture rounded-md p-4 order-2 lg:order-1">
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
      <div className="charcoal-texture rounded-md p-4 order-1 lg:order-2">
        <MoveExplorer
          moves={nextMoves.data?.moves ?? []}
          isLoading={nextMoves.isLoading}
          isError={nextMoves.isError}
          position={chess.position}
          onMoveClick={(from, to) => chess.makeMove(from, to)}
          onMoveHover={setHoveredMove}
          highlightedMove={
            highlightedMove !== null
              ? { ...highlightedMove, pulse: pulseActive }
              : null
          }
          onHighlightConsumed={() => setHighlightedMove(null)}
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
            hideMatchLabelOnMobile
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

  const insightsContent = (
    <div className="flex flex-col gap-4">
      {/* Phase 71: dedicated Insights subtab. */}
      {/* Hidden block + friendly empty state when user has no imported games (proxy: mostPlayedData empty). */}
      {mostPlayedData &&
      (mostPlayedData.white.length > 0 || mostPlayedData.black.length > 0) ? (
        <OpeningInsightsBlock
          debouncedFilters={debouncedFilters}
          onFindingClick={handleOpenFinding}
          onOpenGames={handleOpenFindingGames}
        />
      ) : (
        <p className="text-sm text-muted-foreground" data-testid="opening-insights-no-games">
          Import some games to see opening insights.
        </p>
      )}
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
          <p
            className="text-sm italic text-muted-foreground mb-3"
            data-testid="bookmarks-tip"
          >
            <span className="font-semibold text-foreground/80">Tip:</span> Save some openings as bookmarks to see your results and win rate over time here. Each bookmark has a Piece filter setting (Mine/Opponent/Both) that controls how positions are matched. Use the Suggest button to pick from your most-played positions.
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
      ) : chartBookmarks.length > 0 && (() => {
        if (!tsData) {
          return (
            <div className="charcoal-texture rounded-md p-4 text-center text-muted-foreground">
              Loading chart data...
            </div>
          );
        }

        // Build OpeningWDL rows for bookmarks of a given color
        const buildBookmarkRows = (targetColor: 'white' | 'black'): OpeningWDL[] =>
          chartBookmarks
            .filter((b) => b.color === targetColor)
            .flatMap((b) => {
              const s = wdlStatsMap[b.id];
              if (!s || s.total <= 0) return [];
              const winPct = s.total > 0 ? (s.wins / s.total) * 100 : 0;
              const drawPct = s.total > 0 ? (s.draws / s.total) * 100 : 0;
              const lossPct = s.total > 0 ? (s.losses / s.total) * 100 : 0;
              const pe = bookmarkPhaseEntryByHash.get(b.target_hash);
              const row: OpeningWDL = {
                opening_eco: '',
                opening_name: b.label,
                // Bookmarks have no parity context: display_name === canonical name.
                display_name: b.label,
                label: b.label,
                pgn: sanArrayToPgn(b.moves),
                fen: b.fen,
                full_hash: b.target_hash,
                wins: s.wins,
                draws: s.draws,
                losses: s.losses,
                total: s.total,
                win_pct: winPct,
                draw_pct: drawPct,
                loss_pct: lossPct,
                avg_eval_pawns: pe?.avg_eval_pawns ?? null,
                eval_ci_low_pawns: pe?.eval_ci_low_pawns ?? null,
                eval_ci_high_pawns: pe?.eval_ci_high_pawns ?? null,
                eval_n: pe?.eval_n ?? 0,
                eval_p_value: pe?.eval_p_value ?? null,
                eval_confidence: pe?.eval_confidence ?? 'low',
              };
              return [row];
            })
            .sort((a, b) => b.total - a.total);

        const whiteBookmarkRows = buildBookmarkRows('white');
        const blackBookmarkRows = buildBookmarkRows('black');

        if (whiteBookmarkRows.length === 0 && blackBookmarkRows.length === 0) {
          return (
            <div className="charcoal-texture rounded-md p-4 text-center text-muted-foreground">
              No stats available for saved positions yet.
            </div>
          );
        }

        // Lookup map so the table's onOpenGames callback can resolve the bookmark by full_hash
        const bookmarkByHash = new Map<string, PositionBookmarkResponse>(
          chartBookmarks.map((b) => [b.target_hash, b])
        );
        const handleOpenBookmarkRow = (opening: OpeningWDL) => {
          const bookmark = bookmarkByHash.get(opening.full_hash);
          if (bookmark) handleOpenChartBookmarkGames(bookmark);
        };

        return (
          <>
            {whiteBookmarkRows.length > 0 && (
              <div className="charcoal-texture rounded-md p-4" data-testid="bookmarks-white-section">
                <h2 className="text-lg font-medium mb-3 flex items-center gap-1.5">
                  <BookMarked className="h-5 w-5" />
                  <span className="inline-block h-3.5 w-3.5 rounded-xs border border-muted-foreground bg-white" />
                  White Opening Bookmarks
                </h2>
                <div className="hidden lg:block">
                  <MostPlayedOpeningsTable
                    openings={whiteBookmarkRows}
                    color="white"
                    testIdPrefix="bookmarks-white"
                    onOpenGames={(opening) => handleOpenBookmarkRow(opening)}
                    evalBaselinePawns={mostPlayedData?.eval_baseline_pawns_white ?? EVAL_BASELINE_PAWNS_WHITE}
                    showAll
                  />
                </div>
                <div className="lg:hidden">
                  <MobileMostPlayedRows
                    openings={whiteBookmarkRows}
                    color="white"
                    testIdPrefix="bookmarks-white"
                    onOpenGames={(opening) => handleOpenBookmarkRow(opening)}
                    evalBaselinePawns={mostPlayedData?.eval_baseline_pawns_white ?? EVAL_BASELINE_PAWNS_WHITE}
                    showAll
                  />
                </div>
              </div>
            )}
            {blackBookmarkRows.length > 0 && (
              <div className="charcoal-texture rounded-md p-4" data-testid="bookmarks-black-section">
                <h2 className="text-lg font-medium mb-3 flex items-center gap-1.5">
                  <BookMarked className="h-5 w-5" />
                  <span className="inline-block h-3.5 w-3.5 rounded-xs border border-muted-foreground bg-zinc-900" />
                  Black Opening Bookmarks
                </h2>
                <div className="hidden lg:block">
                  <MostPlayedOpeningsTable
                    openings={blackBookmarkRows}
                    color="black"
                    testIdPrefix="bookmarks-black"
                    onOpenGames={(opening) => handleOpenBookmarkRow(opening)}
                    evalBaselinePawns={mostPlayedData?.eval_baseline_pawns_black ?? EVAL_BASELINE_PAWNS_BLACK}
                    showAll
                  />
                </div>
                <div className="lg:hidden">
                  <MobileMostPlayedRows
                    openings={blackBookmarkRows}
                    color="black"
                    testIdPrefix="bookmarks-black"
                    onOpenGames={(opening) => handleOpenBookmarkRow(opening)}
                    evalBaselinePawns={mostPlayedData?.eval_baseline_pawns_black ?? EVAL_BASELINE_PAWNS_BLACK}
                    showAll
                  />
                </div>
              </div>
            )}
          </>
        );
      })()}
      {/* Win Rate Over Time — shown when bookmarks have time series data */}
      {tsData && (
        <div className="charcoal-texture rounded-md p-4">
          <WinRateChart bookmarks={chartBookmarks} series={tsData.series} />
        </div>
      )}
      {/* Most Played Openings — error / loading branches per CLAUDE.md.
          Without these, a failed or hanging /stats/most-played-openings request
          silently hides both color sections. */}
      {mostPlayedError && (
        <div
          className="charcoal-texture rounded-md p-4 text-center text-muted-foreground"
          data-testid="mpo-error"
        >
          Failed to load most-played openings. Something went wrong. Please try again in a moment.
        </div>
      )}
      {!mostPlayedError && mostPlayedLoading && !mostPlayedData && (
        <div
          className="charcoal-texture rounded-md p-4 text-center text-muted-foreground"
          data-testid="mpo-loading"
        >
          Loading most-played openings...
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
                Your most frequently played openings as White, based on the lichess opening table. Games passing through each opening's position are counted, including games that continued into deeper variations. Openings under 3 half-moves are excluded, so trivial trunks like 1.d4 don't dominate. Rows prefixed with "vs." are openings defined by Black's move (e.g. "vs. Sicilian Defense") that you faced as White.
              </InfoPopover>
            </span>
          </h2>
          {/* Desktop: 3-col table (unchanged) */}
          <div className="hidden lg:block">
            <MostPlayedOpeningsTable
              openings={mostPlayedData.white}
              color="white"
              testIdPrefix="mpo-white"
              onOpenGames={(opening, color) => handleOpenGames(opening.pgn, color)}
              evalBaselinePawns={mostPlayedData.eval_baseline_pawns_white}
            />
          </div>
          {/* Mobile: stacked WDLChartRows (STAB-02) */}
          <div className="lg:hidden">
            <MobileMostPlayedRows
              openings={mostPlayedData.white}
              color="white"
              testIdPrefix="mpo-white"
              onOpenGames={(opening, color) => handleOpenGames(opening.pgn, color)}
              evalBaselinePawns={mostPlayedData.eval_baseline_pawns_white}
            />
          </div>
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
                Your most frequently played openings as Black, based on the lichess opening table. Games passing through each opening's position are counted, including games that continued into deeper variations. Openings under 3 half-moves are excluded, so trivial trunks like 1.e4 don't dominate. Rows prefixed with "vs." are openings defined by White's move (e.g. "vs. Blackmar-Diemer Gambit") that you faced as Black.
              </InfoPopover>
            </span>
          </h2>
          {/* Desktop: 3-col table (unchanged) */}
          <div className="hidden lg:block">
            <MostPlayedOpeningsTable
              openings={mostPlayedData.black}
              color="black"
              testIdPrefix="mpo-black"
              onOpenGames={(opening, color) => handleOpenGames(opening.pgn, color)}
              evalBaselinePawns={mostPlayedData.eval_baseline_pawns_black}
            />
          </div>
          {/* Mobile: stacked WDLChartRows (STAB-02) */}
          <div className="lg:hidden">
            <MobileMostPlayedRows
              openings={mostPlayedData.black}
              color="black"
              testIdPrefix="mpo-black"
              onOpenGames={(opening, color) => handleOpenGames(opening.pgn, color)}
              evalBaselinePawns={mostPlayedData.eval_baseline_pawns_black}
            />
          </div>
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
        {/* Desktop: sidebar strip + (subnav over board column + main content). Tabs lives INSIDE
            SidebarLayout so the subnav does NOT span above the sidebar strip — matches Endgames. */}
        <SidebarLayout
          breakpoint="lg"
          panels={[
            {
              id: 'filters',
              label: 'Filters',
              icon: <SlidersHorizontal className="h-5 w-5" />,
              content: desktopFilterPanelContent,
              notificationDot: showFiltersHint ? (
                <span className="absolute top-0.5 right-0.5 flex h-2.5 w-2.5" data-testid="filters-notification-dot">
                  <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-red-500 opacity-75" />
                  <span className="relative inline-flex h-2.5 w-2.5 rounded-full bg-red-500" />
                </span>
              ) : isFiltersModified ? (
                <span
                  className="absolute top-0.5 right-0.5 flex h-2.5 w-2.5"
                  data-testid="filters-modified-dot"
                  aria-hidden="true"
                >
                  {isFiltersPulsing && (
                    <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-brand-brown opacity-75" />
                  )}
                  <span className="relative inline-flex h-2.5 w-2.5 rounded-full bg-brand-brown" />
                </span>
              ) : undefined,
            },
            {
              id: 'bookmarks',
              label: 'Bookmarks',
              icon: <BookMarked className="h-5 w-5" />,
              content: desktopBookmarkPanelContent,
              headerExtra: (
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
              ),
              notificationDot: showBookmarksHint ? (
                <span className="absolute top-0.5 right-0.5 flex h-2.5 w-2.5" data-testid="bookmarks-notification-dot">
                  <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-red-500 opacity-75" />
                  <span className="relative inline-flex h-2.5 w-2.5 rounded-full bg-red-500" />
                </span>
              ) : undefined,
            },
          ] satisfies SidebarPanelConfig[]}
          activePanel={sidebarOpen}
          onActivePanelChange={(panel) => setSidebarOpen(panel as SidebarPanel | null)}
          stripExtra={
            <Tooltip content={`Played as: ${filters.color === 'white' ? 'White' : 'Black'}`} side="right">
              <Button
                variant="ghost"
                size="icon"
                className="relative"
                onClick={() => {
                  const next = filters.color === 'white' ? 'black' : 'white';
                  setFilters(prev => ({ ...prev, color: next as Color }));
                  setBoardFlipped(next === 'black');
                  dismissPlayedAsHint();
                }}
                aria-label={`Switch to ${filters.color === 'white' ? 'black' : 'white'}`}
                data-testid="sidebar-strip-btn-color"
              >
                <span className={`inline-block h-3.5 w-3.5 rounded-xs border border-muted-foreground ${filters.color === 'white' ? 'bg-white' : 'bg-zinc-900'}`} />
                {showPlayedAsHint && (
                  <span className="absolute top-0.5 right-0.5 flex h-2.5 w-2.5" data-testid="played-as-notification-dot">
                    <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-red-500 opacity-75" />
                    <span className="relative inline-flex h-2.5 w-2.5 rounded-full bg-red-500" />
                  </span>
                )}
              </Button>
            </Tooltip>
          }
        >
          <Tabs
            value={activeTab}
            onValueChange={(val) => { navigate(`/openings/${val}`); window.scrollTo({ top: 0 }); }}
          >
            <TabsList variant="brand" className="w-full" data-testid="openings-tabs">
              <TabsTrigger value="explorer" data-testid="tab-move-explorer" className="flex-1">
                <ArrowRightLeft className="mr-1.5 h-4 w-4" />
                Moves
              </TabsTrigger>
              <TabsTrigger value="games" data-testid="tab-games" className="flex-1">
                <Swords className="mr-1.5 h-4 w-4" />
                Games
              </TabsTrigger>
              <TabsTrigger value="stats" data-testid="tab-stats" className="flex-1">
                <BarChart2 className="mr-1.5 h-4 w-4" />
                Stats
              </TabsTrigger>
              <TabsTrigger value="insights" data-testid="tab-insights" className="flex-1">
                <Lightbulb className="mr-1.5 h-4 w-4" />
                Insights
              </TabsTrigger>
            </TabsList>
            <div className="mt-4 flex flex-row items-start gap-6">
              <div className={getBoardContainerClassName(activeTab)} data-testid="openings-board-container">
                <ChessBoard
                  position={chess.position}
                  onPieceDrop={chess.makeMove}
                  flipped={boardFlipped}
                  lastMove={chess.lastMove}
                  arrows={boardArrows}
                />
                <BoardControls
                  onBack={chess.goBack}
                  onForward={chess.goForward}
                  onReset={() => { chess.reset(); setGamesOffset(0); }}
                  onFlip={() => setBoardFlipped((f) => !f)}
                  canGoBack={chess.currentPly > 0}
                  canGoForward={chess.currentPly < chess.moveHistory.length}
                  infoSlot={
                    <InfoPopover ariaLabel="Chessboard info" testId="chessboard-info" side="top">
                      <div className="space-y-2">
                        <p>Play moves on the board by clicking on squares or dragging pieces, or by clicking on the moves in the Moves tab.</p>
                        <p>The arrows on the board show the next moves from your games that match the current filter settings. Thicker arrows mean the move occurred more frequently. Arrow colors indicate your win rate: dark green (60%+), light green (55-60%), grey (45-55%), light red (loss rate 55-60%), dark red (loss rate 60%+). Moves with fewer than 10 games are always grey.</p>
                      </div>
                    </InfoPopover>
                  }
                />
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
              </div>
              <div className="flex-1 min-w-0">
                <TabsContent value="explorer">
                  {moveExplorerContent}
                </TabsContent>
                <TabsContent value="games">
                  {gamesContent}
                </TabsContent>
                <TabsContent value="stats">
                  {statisticsContent}
                </TabsContent>
                <TabsContent value="insights">
                  {insightsContent}
                </TabsContent>
              </div>
            </div>
          </Tabs>
        </SidebarLayout>

        {/* Mobile: sticky subnav + non-sticky board (matches Endgames pattern, 71.1-02) */}
        <Tabs value={activeTab} onValueChange={(val) => { navigate(`/openings/${val}`); window.scrollTo({ top: 0 }); }} className="lg:hidden flex flex-col gap-2 min-w-0">
          {/* Sticky sub-navigation + filter button (D-05, D-11) */}
          {/* z-20 keeps subnav above ToggleGroupItem's focus:z-10 and below SidebarLayout panel z-40 */}
          <div
            className="sticky top-0 z-20 flex items-center gap-2 h-[52px] bg-white/20 backdrop-blur-md rounded-md px-1 py-1"
            data-testid="openings-mobile-subnav"
          >
            <TabsList variant="brand" className="flex-1 !h-full !p-0" data-testid="openings-tabs-mobile">
              <TabsTrigger value="explorer" className="flex-1" data-testid="tab-move-explorer-mobile">
                Moves
              </TabsTrigger>
              <TabsTrigger value="games" className="flex-1" data-testid="tab-games-mobile">
                Games
              </TabsTrigger>
              <TabsTrigger value="stats" className="flex-1" data-testid="tab-stats-mobile">
                Stats
              </TabsTrigger>
              <TabsTrigger value="insights" className="flex-1" data-testid="tab-insights-mobile">
                Insights
              </TabsTrigger>
            </TabsList>
            <Tooltip content="Open filters" side="left">
              <Button
                variant="ghost"
                size="icon"
                className="h-11 w-11 shrink-0 bg-toggle-active text-toggle-active-foreground hover:bg-toggle-active/80 relative"
                onClick={openFilterSidebar}
                data-testid="subnav-filter-button"
                aria-label="Open filters"
              >
                <SlidersHorizontal className="h-4 w-4" />
                {showFiltersHint ? (
                  <span
                    className="absolute top-0.5 right-0.5 flex h-2.5 w-2.5"
                    data-testid="filters-notification-dot-mobile"
                  >
                    <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-red-500 opacity-75" />
                    <span className="relative inline-flex h-2.5 w-2.5 rounded-full bg-red-500" />
                  </span>
                ) : isFiltersModified ? (
                  <span
                    className="absolute top-0.5 right-0.5 flex h-2.5 w-2.5"
                    data-testid="filters-modified-dot-mobile"
                    aria-hidden="true"
                  >
                    {isFiltersPulsing && (
                      <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-brand-brown opacity-75" />
                    )}
                    <span className="relative inline-flex h-2.5 w-2.5 rounded-full bg-brand-brown" />
                  </span>
                ) : null}
              </Button>
            </Tooltip>
          </div>

          {/* Non-sticky board block — only visible on Moves + Games subtabs (D-07, D-08, D-09) */}
          {(activeTab === 'explorer' || activeTab === 'games') && (
            <>
              <div className="flex items-stretch gap-1 px-1">
                <div className="flex-1 min-w-0 flex flex-col gap-1">
                  <ChessBoard
                    position={chess.position}
                    onPieceDrop={chess.makeMove}
                    flipped={boardFlipped}
                    lastMove={chess.lastMove}
                    arrows={boardArrows}
                  />
                  {/* Board controls aligned to chessboard width (excludes settings column) */}
                  <BoardControls
                    onBack={chess.goBack}
                    onForward={chess.goForward}
                    onReset={() => { chess.reset(); setGamesOffset(0); }}
                    onFlip={() => setBoardFlipped((f) => !f)}
                    canGoBack={chess.currentPly > 0}
                    canGoForward={chess.currentPly < chess.moveHistory.length}
                  />
                </div>
                {/* Settings column: 3 stacked 44px buttons — bookmarks, played-as, info (filter button moved to subnav) */}
                <div className="flex flex-col gap-1 w-11" data-testid="openings-mobile-settings-column">
                  <Tooltip content="Open bookmarks" side="left">
                    <Button
                      variant="ghost"
                      size="icon"
                      className="h-11 w-11 shrink-0 bg-toggle-active text-toggle-active-foreground hover:bg-toggle-active/80 relative"
                      onClick={openBookmarkSidebar}
                      data-testid="btn-open-bookmark-sidebar"
                      aria-label="Open bookmarks"
                    >
                      <BookMarked className="h-4 w-4" />
                      {showBookmarksHint && (
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
                  <Tooltip content={`Playing as ${filters.color}`} side="left">
                    <Button
                      variant="ghost"
                      size="icon"
                      className="relative h-11 w-11 shrink-0 !bg-toggle-active text-toggle-active-foreground hover:!bg-toggle-active"
                      onClick={() => {
                        const newColor: Color = filters.color === 'white' ? 'black' : 'white';
                        // Change color without dismissing the filters hint — only the
                        // Played-as hint advances when the color toggle is used.
                        setFilters({ ...filters, color: newColor });
                        setGamesOffset(0);
                        setBoardFlipped(newColor === 'black');
                        dismissPlayedAsHint();
                        if (activeTab !== 'explorer' && activeTab !== 'games') navigate('/openings/explorer');
                      }}
                      data-testid="btn-toggle-played-as"
                      aria-label={`Playing as ${filters.color}, tap to switch`}
                    >
                      <span className={`inline-block h-4 w-4 rounded-xs border border-muted-foreground ${filters.color === 'white' ? 'bg-white' : 'bg-zinc-900'}`} />
                      {showPlayedAsHint && (
                        <span
                          className="absolute top-0.5 right-0.5 flex h-2.5 w-2.5"
                          data-testid="played-as-notification-dot-mobile"
                        >
                          <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-red-500 opacity-75" />
                          <span className="relative inline-flex h-2.5 w-2.5 rounded-full bg-red-500" />
                        </span>
                      )}
                    </Button>
                  </Tooltip>
                  <div className="flex h-11 w-11 items-center justify-center">
                    <InfoPopover ariaLabel="Chessboard info" testId="chessboard-info-mobile" side="left">
                      Play moves on the board by tapping squares or dragging pieces.
                      <br /><br />
                      The arrows on the board show the next moves from your games that match the current filter settings. Thicker arrows mean the move occurred more frequently. Arrow colors indicate your win rate: dark green (60%+), light green (55-60%), grey (45-55%), light red (loss rate 55-60%), dark red (loss rate 60%+). Moves with fewer than 10 games are always grey.
                    </InfoPopover>
                  </div>
                </div>
              </div>
              {/* Opening name line (always visible on Moves/Games subtabs) */}
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
                {/* Piece filter — spans full drawer width. Played-as is intentionally NOT here:
                    it's always accessible via btn-toggle-played-as in the sticky mobile header. */}
                <div>
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
                    className="w-full"
                  >
                    <ToggleGroupItem value="mine" data-testid="filter-piece-filter-mine-sidebar" className="flex-1 min-h-11">Mine</ToggleGroupItem>
                    <ToggleGroupItem value="opponent" data-testid="filter-piece-filter-opponent-sidebar" className="flex-1 min-h-11">Opponent</ToggleGroupItem>
                    <ToggleGroupItem value="both" data-testid="filter-piece-filter-both-sidebar" className="flex-1 min-h-11">Both</ToggleGroupItem>
                  </ToggleGroup>
                </div>

                {/* Remaining filters (5 fields: timeControl, platform, rated, opponent, recency) */}
                <FilterPanel
                  filters={localFilters}
                  onChange={setLocalFilters}
                  showDeferredApplyHint
                />
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

          <TabsContent value="explorer" className="mt-2">
            {moveExplorerContent}
          </TabsContent>
          <TabsContent value="games" className="mt-2">
            {gamesContent}
          </TabsContent>
          <TabsContent value="stats" className="mt-2">
            {statisticsContent}
          </TabsContent>
          <TabsContent value="insights" className="mt-2">
            {insightsContent}
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
          setSidebarOpen('bookmarks');
        }}
      />
    </div>
  );
}
