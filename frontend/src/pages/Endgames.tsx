import { useState, useCallback, useEffect, useMemo, useRef } from 'react';
import { useNavigate, useLocation, useSearchParams, Navigate } from 'react-router';
import { SlidersHorizontal, BarChart2Icon, SwordsIcon } from 'lucide-react';
import { SidebarLayout, type SidebarPanelConfig } from '@/components/layout/SidebarLayout';
import { Button } from '@/components/ui/button';
import { LoadError } from '@/components/ui/load-error';
import { EmptyState } from '@/components/ui/empty-state';
import { MobileFilterDrawer } from '@/components/filters/MobileFilterDrawer';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Tabs, TabsList, TabsTrigger, TabsContent } from '@/components/ui/tabs';
import { InfoPopover } from '@/components/ui/info-popover';
import { FilterPanel, DEFAULT_FILTERS, areFiltersEqual, FILTER_DOT_FIELDS, resetFilterState } from '@/components/filters/FilterPanel';
import { FilterActions } from '@/components/filters/FilterActions';
import { useFilterStore } from '@/hooks/useFilterStore';
import {
  ENDGAME_CLASS_TO_SLUG,
  HIDDEN_ENDGAME_CLASSES,
} from '@/lib/endgameMetrics';
import { GameCardList } from '@/components/results/GameCardList';
import { PositionResultsPanel } from '@/components/charts/PositionResultsPanel';
import { EndgameStatsTab } from '@/components/endgames/EndgameStatsTab';
import { useEndgameStats, useEndgameGames } from '@/hooks/useEndgames';
import { trackFeature } from '@/lib/analytics';
import { EvalCoverageHeader } from '@/components/EvalCoverageHeader';
import { useReadiness } from '@/hooks/useReadiness';
import { EndgamesProcessingState } from '@/components/EndgamesProcessingState';
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

// HIDDEN_ENDGAME_CLASSES lifted to @/lib/endgameMetrics in Phase 87 Plan 03 so
// TypeTable and this page share one source of truth (pawnless
// is hidden everywhere). Classification stays in the DB so re-enabling does
// not require a reimport.

const VISIBLE_ENDGAME_CLASS_ENTRIES = (
  Object.entries(ENDGAME_CLASS_LABELS) as [EndgameClass, string][]
).filter(([value]) => !HIDDEN_ENDGAME_CLASSES.has(value));

const DEFAULT_ENDGAME_CLASS: EndgameClass = 'mixed';

// Phase 87 (D-08, SEC3-02): inverse of ENDGAME_CLASS_TO_SLUG so the
// /endgames/games?type=<slug> deep-link can pre-seed the selected category on
// page load (shareable URLs, browser back/forward). Built once at module scope.
const SLUG_TO_ENDGAME_CLASS: Record<string, EndgameClass> = Object.fromEntries(
  (Object.entries(ENDGAME_CLASS_TO_SLUG) as [EndgameClass, string][]).map(
    ([cls, slug]) => [slug, cls],
  ),
);

const TAB_INFO: Record<'stats' | 'games', { aria: string; text: string }> = {
  stats: {
    aria: 'About Endgame Stats',
    text: 'Performance metrics, conversion and recovery rates, and time-pressure analysis for your endgames.',
  },
  games: {
    aria: 'About Endgame Games',
    text: 'A list of your games that reached the Endgame Phase, matching your current filter settings.',
  },
};

export function EndgamesPage() {
  const { tier2, pendingCount, totalCount } = useReadiness();
  const location = useLocation();
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();

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
  // The Games tab reads the filtered per-category stats (and the match label total)
  // from GET /endgames/stats (Phase 238 D-01); the Stats tab never sees the filters.
  // Both Games-tab queries run only while that tab is active: the filtered GROUP BY is
  // expensive and the Stats tab never reads it (Phase 238 review FE-IN-03).
  const gamesTabActive = tier2 && activeTab === 'games';
  const { data: rawStatsData } = useEndgameStats(appliedFilters, { enabled: gamesTabActive });

  const statsData = useMemo(() => {
    if (!rawStatsData) return rawStatsData;
    return {
      ...rawStatsData,
      categories: rawStatsData.categories.filter(
        (c) => !HIDDEN_ENDGAME_CLASSES.has(c.endgame_class),
      ),
    };
  }, [rawStatsData]);
  const { data: gamesData, isLoading: gamesLoading, isError: gamesError } = useEndgameGames(
    selectedCategory,
    appliedFilters,
    gamesOffset,
    PAGE_SIZE,
    { enabled: gamesTabActive },
  );

  // ── Desktop sidebar handler — staged Apply-only model ────────────────────────
  // On open: snapshot committed filters as pending draft.
  // On close without Apply: discard the draft (do NOT commit).
  const handleSidebarOpenChange = useCallback((panelId: string | null) => {
    if (sidebarOpen !== 'filters' && panelId === 'filters') {
      setPendingFilters(appliedFilters);
    }
    setSidebarOpen(panelId);
  }, [sidebarOpen, appliedFilters]);

  // ── Desktop Apply handler — commits pending to store, fires pulse, closes panel ──
  const handleDesktopFiltersApply = useCallback(() => {
    setAppliedFilters(pendingFilters);
    setGamesOffset(0);
    setSidebarOpen(null);
  }, [pendingFilters, setAppliedFilters, setGamesOffset]);

  // ── Mobile drawer handler — staged Apply-only model ───────────────────────────
  // On open: snapshot committed filters as pending draft.
  // On close without Apply: discard the draft (do NOT commit).
  const handleMobileFiltersOpenChange = useCallback((open: boolean) => {
    if (open && !mobileFiltersOpen) {
      setPendingFilters(appliedFilters);
    }
    setMobileFiltersOpen(open);
  }, [mobileFiltersOpen, appliedFilters]);

  // ── Mobile Apply handler — commits pending to store, fires pulse, closes drawer ──
  const handleMobileFiltersApply = useCallback(() => {
    setAppliedFilters(pendingFilters);
    setGamesOffset(0);
    setMobileFiltersOpen(false);
  }, [pendingFilters, setAppliedFilters, setGamesOffset]);

  // ── Filter UI is hidden on the Stats tab (Phase 238 D-02) ───────────────────
  // Entering the Stats tab closes any open desktop panel / mobile drawer. Only the
  // open flags reset: the applied-filter setter is never called and the pending draft
  // is never committed, so the filter store is exactly as it was when the user returns
  // to the Games tab.
  useEffect(() => {
    if (activeTab === 'stats') {
      setSidebarOpen(null);
      setMobileFiltersOpen(false);
    }
  }, [activeTab]);

  // ── Category selection handler ──────────────────────────────────────────────

  const handleCategorySelect = useCallback((category: EndgameClass) => {
    setSelectedCategory(category);
    setGamesOffset(0);
    window.scrollTo(0, 0);
  }, []);

  // Phase 87 (D-08, SEC3-02): `?type=<slug>` URL hydration so shareable
  // deep-links into /endgames/games?type=rook pre-seed the type filter on page
  // load and on subsequent SPA navigations. Unknown / malformed slugs are
  // ignored (T-87-07 mitigation: validate against SLUG_TO_ENDGAME_CLASS).
  useEffect(() => {
    const slug = searchParams.get('type');
    if (!slug) return;
    const parsed = SLUG_TO_ENDGAME_CLASS[slug];
    if (parsed && parsed !== selectedCategory) {
      setSelectedCategory(parsed);
      setGamesOffset(0);
    }
    // selectedCategory intentionally omitted from deps: this effect only
    // *seeds* state from URL on mount + URL change; user-driven category
    // selection through handleCategorySelect should not retrigger it.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [searchParams]);

// ── Stats tab content ──────────────────────────────────────────────────────

  // The Stats tab owns its data, insights state and sections (Phase 238); the
  // page only tells it whether the Tier-2 queries may fire and where the per-type
  // games links should navigate. It takes no filter state (D-01).
  const statisticsContent = (
    <EndgameStatsTab tier2={tier2} onCategorySelect={handleCategorySelect} />
  );

  // ── Games tab content ────────────────────────────────────────────────────────

  // ── Endgame type dropdown (used in Games tab) ──────────────────────────────
  const endgameTypeDropdown = (
    <div className="flex items-center gap-2">
      <p className="text-xs text-muted-foreground whitespace-nowrap">Endgame Type</p>
      <Select
        value={selectedCategory}
        onValueChange={(v) => {
          const category = v as EndgameClass;
          setSelectedCategory(category);
          setGamesOffset(0);
          trackFeature('filter-change', { target: 'endgame-type', value: category });
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
      {selectedCategoryStats && (
        <PositionResultsPanel
          stats={selectedCategoryStats}
          evalBaselinePawns={selectedCategoryStats.eval_baseline_pawns}
          filterColor="white"
          label={`${ENDGAME_CLASS_LABELS[selectedCategory]} Endgame Results`}
          className=""
          evalContext="endgame-entry"
        />
      )}
      {endgameTypeDropdown}
      {gamesLoading ? (
        <div className="flex items-center justify-center py-12">
          <p className="text-muted-foreground">Loading games...</p>
        </div>
      ) : gamesError ? (
        <LoadError variant="centered" resource="games" />
      ) : gamesData && gamesData.games.length === 0 ? (
        <EmptyState
          layout="page"
          title="No games matched"
          subtitle="Try adjusting the time control, platform, or recency filters."
        />
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

  // The Games-tab filter panel (D-02: the Stats tab renders no filter UI at all).
  const filtersPanel: SidebarPanelConfig = {
    id: 'filters',
    label: 'Filters',
    icon: <SlidersHorizontal className="h-5 w-5" />,
    notificationDot: modifiedDotNode,
    content: (
      <div className="p-3">
        {/* 'playedAs' omitted: endgame queries ignore color/playedAs entirely
            (see useEndgames "no color per D-02"), so the control was a no-op here. */}
        <FilterPanel
          filters={pendingFilters}
          onChange={setPendingFilters}
          visibleFilters={['timeControl', 'platform', 'opponent', 'opponentStrength', 'rated', 'recency']}
          hideReset
        />
      </div>
    ),
    // Reset/Apply pinned to the panel bottom, below the scrolling filters
    // (mirrors the mobile drawer's pinned footer).
    footer: (
      <div className="px-3 pb-3">
        <FilterActions
          onReset={() => setPendingFilters(resetFilterState(pendingFilters))}
          onApply={handleDesktopFiltersApply}
        />
      </div>
    ),
  };

  // An empty list makes SidebarLayout skip the strip entirely on the Stats tab.
  const desktopPanels: SidebarPanelConfig[] = activeTab === 'games' ? [filtersPanel] : [];

  // ── Render ───────────────────────────────────────────────────────────────────

  // Whole-page lock until Tier 2 (D-01/D-02): uniform for first-import and
  // incremental import — the nav link stays enabled but the page shows the
  // processing state. No forced navigation; unlock is reactive once tier2=true.
  if (!tier2) {
    return <EndgamesProcessingState pendingCount={pendingCount} totalCount={totalCount} />;
  }

  if (needsRedirect) {
    return <Navigate to="/endgames/stats" replace />;
  }

  if (needsLegacyRedirect) {
    return <Navigate to="/endgames/stats" replace />;
  }

  return (
    <div data-testid="endgames-page" className="flex min-h-0 flex-1 flex-col bg-background">
      <main className="mx-auto w-full max-w-7xl flex-1 px-4 py-2 pb-20 md:py-6 md:pb-6 md:px-6">

        {/* Desktop: full-width subnav above the sidebar strip + content (Phase 111 —
            matches the Library page; the subnav spans both the strip and content
            instead of sitting only over the content column). Tabs wraps SidebarLayout
            so TabsContent keeps its Tabs context while TabsList renders full-width above. */}
        <Tabs
          value={activeTab}
          onValueChange={(val) => navigate(`/endgames/${val}`)}
          className="hidden md:flex"
        >
          <EvalCoverageHeader />
          <TabsList variant="brand" className="w-full mb-4" data-testid="endgames-tabs">
            <TabsTrigger value="stats" data-testid="tab-stats" className="flex-1">
              <BarChart2Icon className="mr-1.5 h-4 w-4" />
              Stats
              {activeTab === 'stats' && (
                <span className="ml-1.5 inline-flex items-center [&>span]:text-white! [&>span:hover]:text-white/80!" onClick={(e) => e.stopPropagation()}>
                  <InfoPopover ariaLabel={TAB_INFO.stats.aria} testId="tab-stats-info" side="bottom">
                    {TAB_INFO.stats.text}
                  </InfoPopover>
                </span>
              )}
            </TabsTrigger>
            <TabsTrigger value="games" data-testid="tab-games" className="flex-1">
              <SwordsIcon className="mr-1.5 h-4 w-4" />
              Games
              {activeTab === 'games' && (
                <span className="ml-1.5 inline-flex items-center [&>span]:text-white! [&>span:hover]:text-white/80!" onClick={(e) => e.stopPropagation()}>
                  <InfoPopover ariaLabel={TAB_INFO.games.aria} testId="tab-games-info" side="bottom">
                    {TAB_INFO.games.text}
                  </InfoPopover>
                </span>
              )}
            </TabsTrigger>
          </TabsList>
          <SidebarLayout
            panels={desktopPanels}
            activePanel={sidebarOpen}
            onActivePanelChange={handleSidebarOpenChange}
          >
            <TabsContent value="stats">
              {statisticsContent}
            </TabsContent>
            <TabsContent value="games">
              {gamesContent}
            </TabsContent>
          </SidebarLayout>
        </Tabs>

        {/* Mobile: single column */}
        <div className="md:hidden flex flex-col min-w-0">
          <EvalCoverageHeader />
          <Tabs value={activeTab} onValueChange={(val) => { navigate(`/endgames/${val}`); window.scrollTo({ top: 0 }); }}>
            {/* Full-width, non-sticky sub-navigation (like the Library page). The
                filter affordance is a sticky Filters button rendered just below. */}
            <div className="flex items-center gap-2 h-[40px] rounded-md" data-testid="endgames-mobile-control-row">
              <TabsList variant="brand" className="flex-1 !h-full !p-0" data-testid="endgames-tabs-mobile">
                <TabsTrigger value="stats" className="flex-1" data-testid="tab-stats-mobile">
                  <BarChart2Icon className="mr-1.5 h-4 w-4" />
                  Stats
                  {activeTab === 'stats' && (
                    <span className="ml-1.5 inline-flex items-center [&>span]:text-white! [&>span:hover]:text-white/80!" onClick={(e) => e.stopPropagation()}>
                      <InfoPopover ariaLabel={TAB_INFO.stats.aria} testId="tab-stats-info-mobile" side="bottom">
                        {TAB_INFO.stats.text}
                      </InfoPopover>
                    </span>
                  )}
                </TabsTrigger>
                <TabsTrigger value="games" className="flex-1" data-testid="tab-games-mobile">
                  <SwordsIcon className="mr-1.5 h-4 w-4" />
                  Games
                  {activeTab === 'games' && (
                    <span className="ml-1.5 inline-flex items-center [&>span]:text-white! [&>span:hover]:text-white/80!" onClick={(e) => e.stopPropagation()}>
                      <InfoPopover ariaLabel={TAB_INFO.games.aria} testId="tab-games-info-mobile" side="bottom">
                        {TAB_INFO.games.text}
                      </InfoPopover>
                    </span>
                  )}
                </TabsTrigger>
              </TabsList>
            </div>

            {/* Mobile filter UI exists only on the Games tab (Phase 238 D-02). */}
            {activeTab === 'games' && (
              <>
                {/* Sticky Filters button, styled like the Library page. The full-width
                    subnav above is non-sticky; this button pins on scroll. */}
                <div className="sticky top-0 z-20 flex justify-end gap-2 py-2 bg-background/80 backdrop-blur-sm">
                  <Button
                    variant="brand-outline"
                    className="relative"
                    onClick={() => setMobileFiltersOpen(true)}
                    data-testid="btn-open-filter-drawer"
                    aria-label="Open filters"
                  >
                    <SlidersHorizontal className="mr-2 h-4 w-4" />
                    Filters
                    {modifiedDotNode}
                  </Button>
                </div>

                {/* Filter drawer */}
                <MobileFilterDrawer
                  open={mobileFiltersOpen}
                  onOpenChange={handleMobileFiltersOpenChange}
                  panel="filters"
                  title="Filters"
                  contentTestId="drawer-filter-sidebar"
                  closeTestId="btn-close-filter-drawer"
                  bodyClassName="space-y-4"
                  footer={
                    <FilterActions
                      onReset={() => setPendingFilters(resetFilterState(pendingFilters))}
                      onApply={handleMobileFiltersApply}
                    />
                  }
                >
                  {/* 'playedAs' omitted — see desktop panel note (no-op for endgame queries). */}
                  <FilterPanel
                    filters={pendingFilters}
                    onChange={setPendingFilters}
                    visibleFilters={['timeControl', 'platform', 'opponent', 'opponentStrength', 'rated', 'recency']}
                    hideReset
                  />
                </MobileFilterDrawer>
              </>
            )}

            {/* No sticky Filters row on the Stats tab (D-02), so the content sits
                directly under the sub-navigation at the Tabs root's `gap-2`. */}
            <TabsContent value="stats">
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
