import { useState, useCallback, useMemo, useEffect } from 'react';
import { SlidersHorizontal } from 'lucide-react';
import { SidebarLayout } from '@/components/layout/SidebarLayout';
import { Button } from '@/components/ui/button';
import { MobileFilterDrawer } from '@/components/filters/MobileFilterDrawer';
import { InfoPopover } from '@/components/ui/info-popover';
import { Card, CardHeader, CardBody } from '@/components/ui/card';
import { FilterPanel, DEFAULT_FILTERS, areFiltersEqual, FILTER_DOT_FIELDS, resetFilterState } from '@/components/filters/FilterPanel';
import { FilterActions } from '@/components/filters/FilterActions';
import { usePulseOnChange, ModifiedDot } from '@/components/filters/FilterModifiedDot';
import { useFilterStore } from '@/hooks/useFilterStore';
import { useGameCountValue } from '@/hooks/useGameCount';
import { NoHumanRatedGamesState, shouldShowNoHumanRatedGames } from '@/components/ui/no-human-rated-games-state';
import { useGlobalStats, useRatingHistory } from '@/hooks/useStats';
import {
  LibraryStatsSections,
  LibraryStatsTcSwitch,
} from '@/components/library/stats/LibraryStatsSections';
import { GlobalStatsCharts } from '@/components/stats/GlobalStatsCharts';
import { EvalCoverageHeader } from '@/components/EvalCoverageHeader';
import { RatingChart } from '@/components/stats/RatingChart';
import { useUserProfile } from '@/hooks/useUserProfile';
import type { ReactNode } from 'react';
import type { FilterState } from '@/components/filters/FilterPanel';
import type { GlobalStatsResponse } from '@/types/stats';

// SEED-163 2d: extracted to a standalone function (rather than inlined
// booleans in GlobalStatsPage) so its branches count toward THIS function's
// complexity, not GlobalStatsPage's — that page is already at the eslint
// `complexity` per-file baseline (frontend/CLAUDE.md: fix new breaches, don't
// widen the baseline).
function computeGlobalStatsNoHumanRatedGames(
  globalStats: GlobalStatsResponse | undefined,
  filters: FilterState,
  gameCount: number | null,
): boolean {
  if (!globalStats) return false;
  const hasAnyRows = globalStats.by_time_control.length > 0 || globalStats.by_color.length > 0;
  if (hasAnyRows) return false;
  return shouldShowNoHumanRatedGames(filters, gameCount);
}

// Same rationale as computeGlobalStatsNoHumanRatedGames above: moves the
// loading/empty/content branching out of GlobalStatsPage's own complexity
// count.
function renderGlobalStatsContent(
  isLoading: boolean,
  noHumanRatedGames: boolean,
  gameCount: number | null,
  sectionsContent: ReactNode,
): ReactNode {
  if (isLoading) return <div className="text-muted-foreground">Loading...</div>;
  if (noHumanRatedGames) return <NoHumanRatedGamesState totalGames={gameCount} />;
  return sectionsContent;
}

export function GlobalStatsPage() {
  // Filter state shared across pages — full filter set exposed on the Stats tab.
  // `filters` is the committed store value that queries read.
  // `pendingFilters` is the draft for both desktop sidebar and mobile drawer.
  const [filters, setFilters] = useFilterStore();
  const [pendingFilters, setPendingFilters] = useState<FilterState>(filters);

  // Sync pending -> committed when the filter store changes from another page/tab.
  useEffect(() => {
    setPendingFilters(filters);
  }, [filters]);

  const selectedPlatforms = filters.platforms;

  const { data: ratingData, isLoading: ratingLoading } = useRatingHistory(
    filters, selectedPlatforms, filters.opponentType, filters.opponentStrength,
  );
  const { data: globalStats, isLoading: statsLoading } = useGlobalStats(
    filters, selectedPlatforms, filters.opponentType, filters.opponentStrength,
  );

  const isLoading = ratingLoading || statsLoading;

  // SEED-163 2d: total imported-game count (all platforms), used to detect
  // when the Human+Rated defaults alone emptied the Stats population.
  const gameCount = useGameCountValue();


  const { data: profile } = useUserProfile();
  const isGuest = profile?.is_guest ?? false;

  // ── Mobile collapsible state ───────────────────────────────────────────────
  const [mobileFiltersOpen, setMobileFiltersOpen] = useState(false);

  // ── Desktop sidebar state ───────────────────────────────────────────────────
  const [sidebarOpen, setSidebarOpen] = useState<string | null>(null);

  // Desktop sidebar open-change: snapshot committed filters as pending draft on open.
  const handleSidebarOpenChange = useCallback((panel: string | null) => {
    if (panel === 'filters' && sidebarOpen !== 'filters') {
      setPendingFilters(filters);
    }
    setSidebarOpen(panel);
  }, [sidebarOpen, filters]);

  // Desktop Apply: commit pending to store and close panel.
  const handleDesktopFiltersApply = useCallback(() => {
    setFilters(pendingFilters);
    setSidebarOpen(null);
  }, [pendingFilters, setFilters]);

  // Mobile drawer: snapshot committed on open; close without Apply discards draft.
  const handleMobileFiltersOpenChange = useCallback((open: boolean) => {
    if (open && !mobileFiltersOpen) {
      setPendingFilters(filters);
    }
    setMobileFiltersOpen(open);
  }, [mobileFiltersOpen, filters]);

  // Mobile Apply: commit pending to store and close drawer.
  const handleMobileFiltersApply = useCallback(() => {
    setFilters(pendingFilters);
    setMobileFiltersOpen(false);
  }, [pendingFilters, setFilters]);

  // Modified-dot uses the uniform FILTER_DOT_FIELDS comparison (all FilterState keys except
  // `color`). The dot reflects the shared filter store — if the user set e.g. timeControls
  // on Openings, the Stats dot lights up, and clicking Reset here will clear those too
  // (global reset semantics).
  const isFiltersModified = useMemo(
    () => !areFiltersEqual(filters, DEFAULT_FILTERS, FILTER_DOT_FIELDS),
    [filters],
  );

  const filterPulsing = usePulseOnChange(filters);
  const filterDotNode = (
    <ModifiedDot
      active={isFiltersModified}
      pulsing={filterPulsing}
      testId="filters-modified-dot-mobile"
    />
  );

  const noHumanRatedGamesGlobalStats = computeGlobalStatsNoHumanRatedGames(
    globalStats, filters, gameCount,
  );

  const sectionsContent = (
    <div className="space-y-8">
      {/* ── Flaw Stats + Tactic motifs: per-TC sections sharing one TC switch (Phase 239) ── */}
      <LibraryStatsSections filters={filters} isGuest={isGuest} />

      {/* ── ELO Ratings ── */}
      {(selectedPlatforms === null ||
        selectedPlatforms.includes('chess.com') ||
        selectedPlatforms.includes('lichess')) && (
        <section data-testid="elo-ratings-section">
          <h2 className="font-brand text-lg font-semibold text-foreground mt-2">ELO Ratings</h2>
          <div className="space-y-8 mt-3">
            {(selectedPlatforms === null || selectedPlatforms.includes('chess.com')) && (
              <Card as="section" data-testid="rating-section-chess-com">
                <CardHeader data-testid="rating-chess-com-header">
                  Chess.com Rating
                  <InfoPopover ariaLabel="Chess.com rating info" testId="rating-chess-com-info" side="top">
                    Your Chess.com rating over time by time control, one point per day (your rating after the day's last game). Grey bars show how many games you played that day.
                  </InfoPopover>
                </CardHeader>
                <CardBody>
                  <RatingChart data={ratingData?.chess_com ?? []} platform="Chess.com" enabledTimeControls={filters.timeControls} />
                </CardBody>
              </Card>
            )}

            {(selectedPlatforms === null || selectedPlatforms.includes('lichess')) && (
              <Card as="section" data-testid="rating-section-lichess">
                <CardHeader data-testid="rating-lichess-header">
                  Lichess Rating
                  <InfoPopover ariaLabel="Lichess rating info" testId="rating-lichess-info" side="top">
                    Your Lichess rating over time by time control, one point per day (your rating after the day's last game). Grey bars show how many games you played that day. Lichess uses Glicko-2 ratings which start at 1500 and tend to run 200-400 points higher than Chess.com, so the two are not directly comparable.
                  </InfoPopover>
                </CardHeader>
                <CardBody>
                  <RatingChart data={ratingData?.lichess ?? []} platform="Lichess" enabledTimeControls={filters.timeControls} />
                </CardBody>
              </Card>
            )}
          </div>
        </section>
      )}

      {/* ── Results Breakdown (Results by Time Control + Results by Color) ── */}
      <section data-testid="results-breakdown-section">
        <h2 className="font-brand text-lg font-semibold text-foreground mt-2">Results Breakdown</h2>
        <div className="mt-3">
          {/* WDL charts — each card owns its own shell inside GlobalStatsCharts */}
          <GlobalStatsCharts
            byTimeControl={globalStats?.by_time_control ?? []}
            byColor={globalStats?.by_color ?? []}
            enabledTimeControls={filters.timeControls}
          />
        </div>
      </section>
    </div>
  );

  const content = renderGlobalStatsContent(
    isLoading, noHumanRatedGamesGlobalStats, gameCount, sectionsContent,
  );

  return (
    // No own max-width/padding/main wrapper: this page only renders as the Library
    // "Stats" subtab, nested inside LibraryPage's max-w-7xl container and App's <main>.
    // Wrapping again would double the horizontal padding (narrower than the Games/Flaws
    // subtabs) and nest a second <main> landmark. Plain div = same width as Games/Flaws.
    <div data-testid="global-stats-page">

        {/* Desktop: sidebar strip + filter panel + content */}
        <SidebarLayout
          panels={[
            {
              id: 'filters',
              label: 'Filters',
              icon: <SlidersHorizontal className="h-5 w-5" />,
              notificationDot: isFiltersModified ? (
                <span
                  className="absolute top-0.5 right-0.5 flex h-2.5 w-2.5"
                  data-testid="filters-modified-dot"
                  aria-hidden="true"
                >
                  <span className="relative inline-flex h-2.5 w-2.5 rounded-full bg-brand-brown" />
                </span>
              ) : undefined,
              content: (
                <div className="p-3">
                  <FilterPanel filters={pendingFilters} onChange={setPendingFilters} visibleFilters={['playedAs', 'timeControl', 'platform', 'opponent', 'opponentStrength', 'rated', 'recency']} hideReset />
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
            },
          ]}
          activePanel={sidebarOpen}
          onActivePanelChange={handleSidebarOpenChange}
        >
          <EvalCoverageHeader />
          {content}
        </SidebarLayout>

        {/* Mobile: single column */}
        <div className="md:hidden flex flex-col gap-4 min-w-0">
          <EvalCoverageHeader />
          {/* Sticky control bar: the Library Stats TC switch (left) and the filter
              button (right), one row instead of a filter-only row plus a switch per
              section. The label drops on narrow phones so four TCs still fit. */}
          <div className="sticky top-0 z-20 flex items-center gap-2 py-2 bg-background/80 backdrop-blur-sm">
            <LibraryStatsTcSwitch filters={filters} />
            <Button
              variant="brand-outline"
              // Same height as the TC buttons beside it (min-h-11 below sm, see TcSwitchButtons).
              className="relative ml-auto min-h-11 min-w-11 shrink-0 sm:min-h-0"
              onClick={() => handleMobileFiltersOpenChange(true)}
              aria-label="Open filters"
              data-testid="btn-filters"
            >
              <SlidersHorizontal className="h-4 w-4 min-[420px]:mr-2" />
              <span className="hidden min-[420px]:inline">Filters</span>
              {filterDotNode}
            </Button>
          </div>

          {/* Filter drawer — staged Apply-only */}
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
            <FilterPanel filters={pendingFilters} onChange={setPendingFilters} visibleFilters={['playedAs', 'timeControl', 'platform', 'opponent', 'opponentStrength', 'rated', 'recency']} hideReset />
          </MobileFilterDrawer>

          {content}
        </div>
    </div>
  );
}
