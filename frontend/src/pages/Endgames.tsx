import { useState, useCallback, useEffect, useMemo, useRef } from 'react';
import { useNavigate, useLocation, Navigate, Link } from 'react-router-dom';
import { SlidersHorizontal, X, BarChart2Icon, Gamepad2Icon, HelpCircle } from 'lucide-react';
import { SidebarLayout } from '@/components/layout/SidebarLayout';
import { Accordion, AccordionItem, AccordionTrigger, AccordionContent } from '@/components/ui/accordion';
import { Button } from '@/components/ui/button';
import { Drawer, DrawerContent, DrawerHeader, DrawerTitle, DrawerClose } from '@/components/ui/drawer';
import { Tooltip } from '@/components/ui/tooltip';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Tabs, TabsList, TabsTrigger, TabsContent } from '@/components/ui/tabs';
import { FilterPanel, DEFAULT_FILTERS, areFiltersEqual, FILTER_DOT_FIELDS } from '@/components/filters/FilterPanel';
import { useFilterStore } from '@/hooks/useFilterStore';
import { EndgameWDLChart } from '@/components/charts/EndgameWDLChart';
import { EndgamePerformanceSection, MATERIAL_ADVANTAGE_POINTS, PERSISTENCE_MOVES, ScoreDiffTimelineChart } from '@/components/charts/EndgamePerformanceSection';
import { EndgameConvRecovChart } from '@/components/charts/EndgameConvRecovChart';
import { EndgameTimelineChart } from '@/components/charts/EndgameTimelineChart';
import { EndgameScoreGapSection } from '@/components/charts/EndgameScoreGapSection';
import { EndgameClockPressureSection, ClockDiffTimelineChart } from '@/components/charts/EndgameClockPressureSection';
import { EndgameTimePressureSection } from '@/components/charts/EndgameTimePressureSection';
import { EndgameEloTimelineSection } from '@/components/charts/EndgameEloTimelineSection';
import { GameCardList } from '@/components/results/GameCardList';
import { WDLChartRow } from '@/components/charts/WDLChartRow';
import { useEndgameOverview, useEndgameGames } from '@/hooks/useEndgames';
import type { FilterState } from '@/components/filters/FilterPanel';
import type { EndgameClass } from '@/types/endgames';

const PAGE_SIZE = 20;

const ENDGAME_CLASS_LABELS: Record<EndgameClass, string> = {
  mixed: 'Mixed',
  rook: 'Rook',
  minor_piece: 'Minor Piece',
  pawn: 'Pawn',
  queen: 'Queen',
  pawnless: 'Pawnless',
};

// Pawnless endgames are rare (~0.5% of positions, ~0.7% of qualifying game spans
// in prod) and sample sizes per user are almost always too small to be meaningful.
// Hide from the Endgames tab UI; classification remains in the DB so it can be
// re-enabled without a reimport.
const HIDDEN_ENDGAME_CLASSES: ReadonlySet<EndgameClass> = new Set(['pawnless']);

const VISIBLE_ENDGAME_CLASS_ENTRIES = (
  Object.entries(ENDGAME_CLASS_LABELS) as [EndgameClass, string][]
).filter(([value]) => !HIDDEN_ENDGAME_CLASSES.has(value));

const DEFAULT_ENDGAME_CLASS: EndgameClass = 'mixed';

export function EndgamesPage() {
  const location = useLocation();
  const navigate = useNavigate();

  const needsRedirect =
    location.pathname === '/endgames' || location.pathname === '/endgames/';
  // Redirect old /endgames/statistics URL to /endgames/stats after tab rename
  const needsLegacyRedirect = location.pathname.endsWith('/statistics');
  const activeTab = location.pathname.includes('/games') ? 'games' : 'stats';

  // ── Filter state (shared across pages) — color and matchSide are not used for endgames ──
  // appliedFilters keys the backend query; pendingFilters tracks in-progress sidebar edits.
  // Queries only fire when the sidebar/drawer closes and commits pending -> applied.
  const [appliedFilters, setAppliedFilters] = useFilterStore();
  const [pendingFilters, setPendingFilters] = useState<FilterState>(appliedFilters);

  // Sync pending -> applied when the filter store changes from another page/tab
  useEffect(() => {
    setPendingFilters(appliedFilters);
  }, [appliedFilters]);

  // ── Category selection state ─────────────────────────────────────────────────
  const [selectedCategory, setSelectedCategory] = useState<EndgameClass>(DEFAULT_ENDGAME_CLASS);
  const [gamesOffset, setGamesOffset] = useState(0);

  // ── Mobile collapsible state ───────────────────────────────────────────────
  const [mobileFiltersOpen, setMobileFiltersOpen] = useState(false);

  // ── Desktop sidebar state ───────────────────────────────────────────────────
  const [sidebarOpen, setSidebarOpen] = useState<string | null>(null);

  // ── Modified-filters indicator state ────────────────────────────────────────
  // The dot reflects APPLIED filters (what the backend is filtering by), not pending.
  // When appliedFilters changes away from defaults via a commit, pulse once.
  const isModified = useMemo(
    () => !areFiltersEqual(appliedFilters, DEFAULT_FILTERS, FILTER_DOT_FIELDS),
    [appliedFilters],
  );
  const [isPulsing, setIsPulsing] = useState(false);
  const pulseTimeoutRef = useRef<number | null>(null);
  const prevAppliedRef = useRef(appliedFilters);

  useEffect(() => {
    // Pulse once whenever appliedFilters transitions to a new value (i.e. a commit fired).
    // On initial mount prevAppliedRef.current === appliedFilters so no pulse fires on load.
    // Subsequent changes to appliedFilters (via setAppliedFilters in handleSidebarOpenChange
    // or handleMobileFiltersOpenChange) will trigger the pulse.
    if (prevAppliedRef.current !== appliedFilters) {
      prevAppliedRef.current = appliedFilters;
      setIsPulsing(true);
      if (pulseTimeoutRef.current !== null) {
        window.clearTimeout(pulseTimeoutRef.current);
      }
      pulseTimeoutRef.current = window.setTimeout(() => {
        setIsPulsing(false);
        pulseTimeoutRef.current = null;
      }, 1000); // ~1s pulse duration
    }
    return () => {
      if (pulseTimeoutRef.current !== null) {
        window.clearTimeout(pulseTimeoutRef.current);
        pulseTimeoutRef.current = null;
      }
    };
  }, [appliedFilters]);

  const modifiedDotNode = isModified ? (
    <span
      className="absolute top-0.5 right-0.5 flex h-2.5 w-2.5"
      data-testid="filters-modified-dot"
      aria-hidden="true"
    >
      {isPulsing && (
        <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-brand-brown opacity-75" />
      )}
      <span className="relative inline-flex h-2.5 w-2.5 rounded-full bg-brand-brown" />
    </span>
  ) : undefined;

  // ── Data ─────────────────────────────────────────────────────────────────────
  const {
    data: overviewData,
    isLoading: overviewLoading,
    isError: overviewError,
  } = useEndgameOverview(appliedFilters);

  const rawStatsData = overviewData?.stats;
  const statsData = useMemo(() => {
    if (!rawStatsData) return rawStatsData;
    return {
      ...rawStatsData,
      categories: rawStatsData.categories.filter(
        (c) => !HIDDEN_ENDGAME_CLASSES.has(c.endgame_class),
      ),
    };
  }, [rawStatsData]);
  const perfData = overviewData?.performance;
  const rawTimelineData = overviewData?.timeline;
  const timelineData = useMemo(() => {
    if (!rawTimelineData) return rawTimelineData;
    const per_type = Object.fromEntries(
      Object.entries(rawTimelineData.per_type).filter(
        ([key]) => !HIDDEN_ENDGAME_CLASSES.has(key as EndgameClass),
      ),
    );
    return { ...rawTimelineData, per_type };
  }, [rawTimelineData]);
  const scoreGapData = overviewData?.score_gap_material;
  const clockPressureData = overviewData?.clock_pressure;
  const timePressureChartData = overviewData?.time_pressure_chart;
  const eloTimelineData = overviewData?.endgame_elo_timeline;

  const { data: gamesData, isLoading: gamesLoading, isError: gamesError } = useEndgameGames(
    selectedCategory,
    appliedFilters,
    gamesOffset,
    PAGE_SIZE,
  );

  // ── Desktop sidebar handler — defers filter apply until the panel closes ────
  // When the filter panel closes (filters -> null or filters -> other), commit
  // pending -> applied. When it opens, snapshot applied as pending.
  const handleSidebarOpenChange = useCallback((panelId: string | null) => {
    if (sidebarOpen === 'filters' && panelId !== 'filters') {
      setAppliedFilters(pendingFilters);
      setGamesOffset(0);
    }
    if (sidebarOpen !== 'filters' && panelId === 'filters') {
      setPendingFilters(appliedFilters);
    }
    setSidebarOpen(panelId);
  }, [sidebarOpen, pendingFilters, appliedFilters, setAppliedFilters]);

  // ── Mobile drawer handler — defers filter apply until the drawer closes ─────
  const handleMobileFiltersOpenChange = useCallback((open: boolean) => {
    if (!open && mobileFiltersOpen) {
      // Commit deferred filters on close
      setAppliedFilters(pendingFilters);
      setGamesOffset(0);
    }
    if (open && !mobileFiltersOpen) {
      setPendingFilters(appliedFilters);
    }
    setMobileFiltersOpen(open);
  }, [mobileFiltersOpen, pendingFilters, appliedFilters, setAppliedFilters]);

  // ── Category selection handler ──────────────────────────────────────────────

  const handleCategorySelect = useCallback((category: EndgameClass) => {
    // Select category, reset pagination, and scroll to top — user navigates via link icon
    setSelectedCategory(category);
    setGamesOffset(0);
    window.scrollTo(0, 0);
  }, []);

  // ── Stats tab content ──────────────────────────────────────────────────────

  // Summary line + collapsible explaining endgame concepts and metric limitations
  const showPerfSection = !!(perfData && perfData.endgame_wdl.total > 0);
  const showClockPressure = !!(clockPressureData && clockPressureData.rows.length > 0);
  const showTimePressureChart = !!(timePressureChartData && timePressureChartData.total_endgame_games > 0);
  const showTimeline = !!(timelineData && timelineData.overall.length > 0);

  const statisticsContent = (
    <div className="flex flex-col gap-4">
      {overviewLoading ? (
        <div className="charcoal-texture rounded-md p-12 flex items-center justify-center">
          <p className="text-muted-foreground">Loading endgame analytics...</p>
        </div>
      ) : statsData && statsData.categories.length > 0 ? (
        <>
          {/* ── Endgame Overall Performance ── */}
          {showPerfSection && (
            <>
              <h2 className="text-lg font-semibold text-foreground mt-2">Endgame Overall Performance</h2>
              <Accordion type="single" collapsible>
                <AccordionItem value="concepts" className="charcoal-texture rounded-md px-4" data-testid="endgame-concepts-trigger">
                  <AccordionTrigger className="text-foreground justify-start flex-none gap-2 **:data-[slot=accordion-trigger-icon]:ml-0 **:data-[slot=accordion-trigger-icon]:order-first">
                    <HelpCircle className="h-4 w-4 text-brand-brown/70 shrink-0 order-last" />
                    Endgame statistics concepts
                  </AccordionTrigger>
                  <AccordionContent className="text-muted-foreground space-y-2">
                    <p>
                      <strong>Endgame phase:</strong> positions where the total count of major and minor pieces
                      (queens, rooks, bishops, knights) across both sides is at most 6. Kings and pawns are not
                      counted. This follows the Lichess definition. A game is only counted as having an endgame
                      phase if it spans at least 3 full moves (6 half-moves) in the endgame. Shorter tactical
                      transitions through endgame-like material are treated as no endgame.
                    </p>
                    <p>
                      <strong>Endgame types:</strong> Rook, Minor Piece (bishops/knights), Pawn (king and pawns only),
                      Queen, and Mixed (two or more piece types).
                    </p>
                    <p>
                      <strong>Endgame sequence:</strong> a continuous stretch of at least 3 full moves (6 half-moves)
                      spent in a single endgame type. A single game can produce multiple sequences. For example,
                      a rook endgame where the rooks get traded becomes a pawn endgame, giving that game one rook
                      sequence and one pawn sequence. Sequences drive the Endgame Type Breakdown, so a game can appear
                      under more than one type.
                    </p>
                    <p>
                      <strong>Conversion:</strong> percentage of games where you entered the endgame with a
                      material advantage of at least {MATERIAL_ADVANTAGE_POINTS} point (persisted
                      for at least {PERSISTENCE_MOVES} full moves) and went on to win.
                      Measures how well you close out winning endgames.
                    </p>
                    <p>
                      <strong>Recovery:</strong> percentage of games where you entered the endgame with a
                      material deficit of at least {MATERIAL_ADVANTAGE_POINTS} point (persisted for
                      at least {PERSISTENCE_MOVES} full moves) and drew or won. Measures how well you defend losing
                      endgames.
                    </p>
                    <p>
                      Conversion and Recovery rates usually reflect your performance against opponents at your rating
                      level. As your rating changes, you face stronger or weaker opponents, so trends may not
                      directly indicate improvement or stagnation in absolute terms. If you often play against
                      stronger or weaker opponents, set the Opponent Strength filter to "Similar" to adjust your
                      analysis.
                    </p>
                  </AccordionContent>
                </AccordionItem>
              </Accordion>
              <div className="charcoal-texture rounded-md p-4">
                <EndgamePerformanceSection data={perfData} scoreGap={scoreGapData} />
              </div>
              {scoreGapData && scoreGapData.timeline.length > 0 && (
                <div className="charcoal-texture rounded-md p-4">
                  <ScoreDiffTimelineChart
                    timeline={scoreGapData.timeline}
                    window={scoreGapData.timeline_window}
                  />
                </div>
              )}
              {scoreGapData && (
                <>
                  <h2 className="text-lg font-semibold text-foreground mt-2">Endgame Metrics and ELO</h2>
                  <div className="charcoal-texture rounded-md p-4">
                    <EndgameScoreGapSection data={scoreGapData} />
                  </div>
                  <div
                    className="charcoal-texture rounded-md p-4"
                    data-testid="endgame-elo-timeline-section"
                  >
                    <EndgameEloTimelineSection
                      data={eloTimelineData}
                      isLoading={overviewLoading}
                      isError={overviewError}
                    />
                  </div>
                </>
              )}
            </>
          )}

          {/* ── Time Pressure ── */}
          {(showClockPressure || showTimePressureChart) && (
            <>
              <h2 className="text-lg font-semibold text-foreground mt-2">Time Pressure</h2>
              {showClockPressure && (
                <>
                  <div className="charcoal-texture rounded-md p-4">
                    <EndgameClockPressureSection data={clockPressureData} />
                  </div>
                  {clockPressureData && clockPressureData.timeline.length > 0 && (
                    <div className="charcoal-texture rounded-md p-4">
                      <ClockDiffTimelineChart
                        timeline={clockPressureData.timeline}
                        window={clockPressureData.timeline_window}
                      />
                    </div>
                  )}
                </>
              )}
              {showTimePressureChart && (
                <div className="charcoal-texture rounded-md p-4">
                  <EndgameTimePressureSection data={timePressureChartData} />
                </div>
              )}
            </>
          )}

          {/* ── Endgame Type Breakdown ── */}
          <h2 className="text-lg font-semibold text-foreground mt-2">Endgame Type Breakdown</h2>
          <div className="charcoal-texture rounded-md p-4">
            <EndgameWDLChart
              categories={statsData.categories}
              onCategorySelect={handleCategorySelect}
            />
          </div>
          {statsData.categories.length > 0 && (
            <div className="charcoal-texture rounded-md p-4">
              <EndgameConvRecovChart categories={statsData.categories} />
            </div>
          )}
          {showTimeline && (
            <div className="charcoal-texture rounded-md p-4">
              <EndgameTimelineChart data={timelineData} />
            </div>
          )}
        </>
      ) : overviewError ? (
        <div className="flex flex-1 flex-col items-center justify-center py-12 text-center">
          <p className="mb-2 text-base font-medium text-foreground">Failed to load endgame data</p>
          <p className="text-sm text-muted-foreground">
            Something went wrong. Please try again in a moment.
          </p>
        </div>
      ) : statsData && statsData.categories.length === 0 ? (
        <div className="flex flex-1 flex-col items-center justify-center py-12 text-center">
          <p className="mb-2 text-base font-medium text-foreground">No endgame data yet</p>
          <p className="mb-6 text-sm text-muted-foreground">
            No games have reached an endgame phase yet with the current filters. Try adjusting
            the time control or recency filters.
          </p>
        </div>
      ) : (
        <div className="flex flex-1 flex-col items-center justify-center py-12 text-center">
          <p className="mb-2 text-base font-medium text-foreground">No games imported yet</p>
          <p className="mb-6 text-sm text-muted-foreground">
            Import your games from chess.com or lichess to see endgame analysis.
          </p>
          <Button variant="outline" size="sm" asChild>
            <Link to="/import">Import Games</Link>
          </Button>
        </div>
      )}
    </div>
  );

  // ── Games tab content ────────────────────────────────────────────────────────

  // ── Endgame type dropdown (used in Games tab) ──────────────────────────────
  const endgameTypeDropdown = (
    <div className="flex items-center gap-2">
      <p className="text-xs text-muted-foreground whitespace-nowrap">Endgame type</p>
      <Select
        value={selectedCategory}
        onValueChange={(v) => {
          setSelectedCategory(v as EndgameClass);
          setGamesOffset(0);
        }}
      >
        <SelectTrigger size="sm" data-testid="filter-endgame-type" className="min-h-11 sm:min-h-0 w-full sm:w-[160px]">
          <SelectValue />
        </SelectTrigger>
        <SelectContent>
          {VISIBLE_ENDGAME_CLASS_ENTRIES.map(([value, label]) => (
            <SelectItem key={value} value={value}>{label}</SelectItem>
          ))}
        </SelectContent>
      </Select>
    </div>
  );

  const selectedCategoryStats = statsData?.categories.find(c => c.endgame_class === selectedCategory);

  const gamesContent = (
    <div className="flex flex-col gap-4">
      {selectedCategoryStats && selectedCategoryStats.total > 0 && (
        <div className="charcoal-texture rounded-md p-4">
          <WDLChartRow
            data={selectedCategoryStats}
            label={`${ENDGAME_CLASS_LABELS[selectedCategory]} Endgame Results`}
            barHeight="h-6"
            testId="wdl-endgame-games"
          />
        </div>
      )}
      {endgameTypeDropdown}
      {gamesLoading ? (
        <div className="flex items-center justify-center py-12">
          <p className="text-muted-foreground">Loading games...</p>
        </div>
      ) : gamesError ? (
        <div className="flex flex-1 flex-col items-center justify-center py-12 text-center">
          <p className="mb-2 text-base font-medium text-foreground">Failed to load games</p>
          <p className="text-sm text-muted-foreground">
            Something went wrong. Please try again in a moment.
          </p>
        </div>
      ) : gamesData && gamesData.games.length === 0 ? (
        <div className="flex flex-1 flex-col items-center justify-center py-12 text-center">
          <p className="mb-2 text-base font-medium text-foreground">No games matched</p>
          <p className="text-sm text-muted-foreground">
            Try adjusting the time control, platform, or recency filters.
          </p>
        </div>
      ) : gamesData ? (
        <GameCardList
          games={gamesData.games}
          matchedCount={gamesData.matched_count}
          totalGames={statsData?.endgame_games ?? gamesData.matched_count}
          offset={gamesOffset}
          limit={PAGE_SIZE}
          onPageChange={setGamesOffset}
          matchLabel={statsData ? (
            <>
              {gamesData.matched_count} of {statsData.endgame_games}{' '}
              ({(gamesData.matched_count / statsData.endgame_games * 100).toFixed(1)}%){' '}
              games with an endgame matched
            </>
          ) : undefined}
        />
      ) : null}
    </div>
  );

  // ── Render ───────────────────────────────────────────────────────────────────

  if (needsRedirect) {
    return <Navigate to="/endgames/stats" replace />;
  }

  if (needsLegacyRedirect) {
    return <Navigate to="/endgames/stats" replace />;
  }

  return (
    <div data-testid="endgames-page" className="flex min-h-0 flex-1 flex-col bg-background">
      <main className="mx-auto w-full max-w-7xl flex-1 px-4 py-2 md:py-6 md:px-6">

        {/* Desktop: sidebar strip + filter panel + content */}
        <SidebarLayout
          panels={[
            {
              id: 'filters',
              label: 'Filters',
              icon: <SlidersHorizontal className="h-5 w-5" />,
              notificationDot: modifiedDotNode,
              content: (
                <div className="p-3">
                  <FilterPanel
                    filters={pendingFilters}
                    onChange={setPendingFilters}
                    showDeferredApplyHint
                  />
                </div>
              ),
            },
          ]}
          activePanel={sidebarOpen}
          onActivePanelChange={handleSidebarOpenChange}
        >
          <Tabs value={activeTab} onValueChange={(val) => navigate(`/endgames/${val}`)}>
            <TabsList variant="brand" className="w-full" data-testid="endgames-tabs">
              <TabsTrigger value="stats" data-testid="tab-stats" className="flex-1">
                <BarChart2Icon className="mr-1.5 h-4 w-4" />
                Stats
              </TabsTrigger>
              <TabsTrigger value="games" data-testid="tab-games" className="flex-1">
                <Gamepad2Icon className="mr-1.5 h-4 w-4" />
                Games
              </TabsTrigger>
            </TabsList>
            <TabsContent value="stats" className="mt-4">
              {statisticsContent}
            </TabsContent>
            <TabsContent value="games" className="mt-4">
              {gamesContent}
            </TabsContent>
          </Tabs>
        </SidebarLayout>

        {/* Mobile: single column */}
        <div className="md:hidden flex flex-col min-w-0">
          <Tabs value={activeTab} onValueChange={(val) => { navigate(`/endgames/${val}`); window.scrollTo({ top: 0 }); }}>
            {/* Sticky sub-navigation + filter button */}
            <div className="sticky top-0 z-20 flex items-center gap-2 h-[52px] bg-white/20 backdrop-blur-md rounded-md px-1 py-1" data-testid="endgames-mobile-control-row">
              <TabsList variant="brand" className="flex-1 !h-full !p-0" data-testid="endgames-tabs-mobile">
                <TabsTrigger value="stats" className="flex-1" data-testid="tab-stats-mobile">
                  <BarChart2Icon className="mr-1.5 h-4 w-4" />
                  Stats
                </TabsTrigger>
                <TabsTrigger value="games" className="flex-1" data-testid="tab-games-mobile">
                  <Gamepad2Icon className="mr-1.5 h-4 w-4" />
                  Games
                </TabsTrigger>
              </TabsList>
              <Tooltip content="Open filters" side="left">
                <Button
                  variant="ghost"
                  size="icon"
                  className="relative h-11 w-11 shrink-0 bg-toggle-active text-toggle-active-foreground hover:bg-toggle-active/80"
                  onClick={() => setMobileFiltersOpen(true)}
                  data-testid="btn-open-filter-drawer"
                  aria-label="Open filters"
                >
                  <SlidersHorizontal className="h-4 w-4" />
                  {isModified && (
                    <span
                      className="absolute top-0.5 right-0.5 flex h-2.5 w-2.5"
                      data-testid="filters-modified-dot-mobile"
                      aria-hidden="true"
                    >
                      {isPulsing && (
                        <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-brand-brown opacity-75" />
                      )}
                      <span className="relative inline-flex h-2.5 w-2.5 rounded-full bg-brand-brown" />
                    </span>
                  )}
                </Button>
              </Tooltip>
            </div>

            {/* Filter drawer */}
            <Drawer open={mobileFiltersOpen} onOpenChange={handleMobileFiltersOpenChange} direction="right">
              <DrawerContent className="!w-full sm:!w-3/4 !bottom-auto !rounded-bl-xl max-h-[85vh]" data-testid="drawer-filter-sidebar">
                <DrawerHeader className="flex flex-row items-center justify-between">
                  <DrawerTitle>Filters</DrawerTitle>
                  <Tooltip content="Close filters">
                    <DrawerClose asChild>
                      <Button variant="ghost" size="icon" aria-label="Close filters" data-testid="btn-close-filter-drawer">
                        <X className="h-4 w-4" />
                      </Button>
                    </DrawerClose>
                  </Tooltip>
                </DrawerHeader>
                <div className="overflow-y-auto flex-1 p-4 space-y-4">
                  <FilterPanel
                    filters={pendingFilters}
                    onChange={setPendingFilters}
                    showDeferredApplyHint
                  />
                </div>
              </DrawerContent>
            </Drawer>

            <TabsContent value="stats" className="mt-4">
              {statisticsContent}
            </TabsContent>
            <TabsContent value="games" className="mt-4">
              {gamesContent}
            </TabsContent>
          </Tabs>
        </div>
      </main>
    </div>
  );
}
