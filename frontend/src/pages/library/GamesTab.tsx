import { useState, useCallback, useMemo, useEffect, useRef } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import { Link } from 'react-router-dom';
import { SlidersHorizontal, Tags, X } from 'lucide-react';
import { SidebarLayout } from '@/components/layout/SidebarLayout';
import { Button } from '@/components/ui/button';
import { LoadError } from '@/components/ui/load-error';
import { EmptyState } from '@/components/ui/empty-state';
import { Drawer, DrawerContent, DrawerHeader, DrawerTitle, DrawerClose } from '@/components/ui/drawer';
import {
  DEFAULT_FILTERS,
  areFiltersEqual,
  FILTER_DOT_FIELDS,
} from '@/components/filters/FilterPanel';
import { LibraryFilterPanel } from '@/components/filters/LibraryFilterPanel';
import { FlawFilterControl } from '@/components/filters/FlawFilterControl';
import { FilterActions } from '@/components/filters/FilterActions';
import { usePulseOnChange, ModifiedDot } from '@/components/filters/FilterModifiedDot';
import { LibraryGameCardList } from '@/components/results/LibraryGameCardList';
import { useFilterStore } from '@/hooks/useFilterStore';
import {
  useFlawFilterStore,
  DEFAULT_FLAW_FILTER,
  isFlawFilterNonDefault,
} from '@/hooks/useFlawFilterStore';
import { useLibraryGames } from '@/hooks/useLibrary';
import { useUserProfile } from '@/hooks/useUserProfile';
import { useEvalCoverage, EVAL_COVERAGE_POLL_INTERVAL_MS } from '@/hooks/useEvalCoverage';
import type { FilterState } from '@/components/filters/FilterPanel';
import type { FlawFilterState } from '@/hooks/useFlawFilterStore';

// ─── Constants ────────────────────────────────────────────────────────────────

const PAGE_SIZE = 20;

// ─── Component ────────────────────────────────────────────────────────────────

/**
 * GamesTab — the Library Games subtab root.
 *
 * Composes two separate filter panels (game-metadata + Tags/flaw filter) +
 * LibraryGameCardList, wiring useLibraryGames to the shared filter + shared flaw
 * filter state. FlawStatsPanel lives on the Stats tab (GlobalStats.tsx).
 *
 * Desktop layout: SidebarLayout with two strip panels — "Filters" (game metadata,
 * LibraryFilterPanel) and "Tags" (severity + tags, FlawFilterControl + FilterActions).
 * Mobile layout: two sticky buttons each opening their own right Drawer, then the
 * game list.
 *
 * Filter interaction — staged Apply-only model:
 * - Edits mutate pending/draft state only; nothing commits to the shared store until Apply.
 * - Apply = commit pending to store + close panel (desktop strip / mobile drawer).
 * - Closing any other way (X, outside-click, strip toggle) discards the draft.
 *
 * State management:
 * - appliedFilters: drives useLibraryGames (committed store value).
 * - pendingFilters: tracks game-metadata draft edits.
 * - flawFilter: shared cross-tab committed state from useFlawFilterStore (D-04).
 * - pendingFlawFilter: Tags panel draft (both desktop and mobile).
 * - offset: page state, reset to 0 on any Apply.
 */
export function GamesTab() {
  // ── Filter state ─────────────────────────────────────────────────────────────
  const [appliedFilters, setAppliedFilters] = useFilterStore();
  const [pendingFilters, setPendingFilters] = useState<FilterState>(appliedFilters);

  // Sync pending -> applied when the filter store changes from another page/tab
  useEffect(() => {
    setPendingFilters(appliedFilters);
  }, [appliedFilters]);

  // ── Flaw filter (shared cross-tab state — D-04) ───────────────────────────────
  const [flawFilter, setFlawFilter] = useFlawFilterStore();

  // Pending flaw filter draft — shared buffer for desktop Tags panel and mobile drawer.
  const [pendingFlawFilter, setPendingFlawFilter] = useState<FlawFilterState>(flawFilter);
  useEffect(() => {
    setPendingFlawFilter(flawFilter);
  }, [flawFilter]);

  // ── Pagination state ─────────────────────────────────────────────────────────
  const [offset, setOffset] = useState(0);

  // ── Mobile drawer state ──────────────────────────────────────────────────────
  const [mobileFiltersOpen, setMobileFiltersOpen] = useState(false);
  const [mobileFlawFiltersOpen, setMobileFlawFiltersOpen] = useState(false);

  // ── Desktop sidebar state ────────────────────────────────────────────────────
  const [sidebarOpen, setSidebarOpen] = useState<string | null>(null);

  // ── Modified-filters indicators (one per panel) ───────────────────────────────
  const isGameModified = useMemo(
    () => !areFiltersEqual(appliedFilters, DEFAULT_FILTERS, FILTER_DOT_FIELDS),
    [appliedFilters],
  );
  const isFlawModified = useMemo(() => isFlawFilterNonDefault(flawFilter), [flawFilter]);

  const gamePulsing = usePulseOnChange(appliedFilters);
  const flawPulsing = usePulseOnChange(flawFilter);

  const gameDotNode = (
    <ModifiedDot active={isGameModified} pulsing={gamePulsing} testId="filters-modified-dot" />
  );
  const flawDotNode = (
    <ModifiedDot active={isFlawModified} pulsing={flawPulsing} testId="flaw-filters-modified-dot" />
  );

  // ── Handlers ─────────────────────────────────────────────────────────────────

  // Desktop sidebar: on open, snapshot committed filters as pending. On close
  // without Apply (strip toggle / outside-click), do NOT commit — discard the draft
  // by re-syncing pending to committed on the next open.
  const handleSidebarOpenChange = useCallback(
    (panelId: string | null) => {
      if (sidebarOpen !== panelId && panelId === 'filters') {
        // Filters panel opening: snapshot committed state
        setPendingFilters(appliedFilters);
      }
      if (sidebarOpen !== panelId && panelId === 'tags') {
        // Tags panel opening: snapshot committed flaw state
        setPendingFlawFilter(flawFilter);
      }
      setSidebarOpen(panelId);
    },
    [sidebarOpen, appliedFilters, flawFilter],
  );

  // Desktop game-metadata Apply: commit pending to store and close the panel.
  const handleDesktopFiltersApply = useCallback(() => {
    setAppliedFilters(pendingFilters);
    setOffset(0);
    setSidebarOpen(null);
  }, [pendingFilters, setAppliedFilters]);

  // Desktop Tags Apply: commit pending flaw filter to store and close the panel.
  const handleDesktopTagsApply = useCallback(() => {
    setFlawFilter(pendingFlawFilter);
    setOffset(0);
    setSidebarOpen(null);
  }, [pendingFlawFilter, setFlawFilter]);

  // Mobile game-filters drawer: on open snapshot committed; Apply commits + closes.
  const handleMobileFiltersOpenChange = useCallback(
    (open: boolean) => {
      if (open && !mobileFiltersOpen) {
        setPendingFilters(appliedFilters);
      }
      setMobileFiltersOpen(open);
    },
    [mobileFiltersOpen, appliedFilters],
  );

  const handleMobileFiltersApply = useCallback(() => {
    setAppliedFilters(pendingFilters);
    setOffset(0);
    setMobileFiltersOpen(false);
  }, [pendingFilters, setAppliedFilters]);

  // Mobile flaw-filters drawer: on open snapshot committed; Apply commits + closes.
  const handleMobileFlawFiltersOpenChange = useCallback(
    (open: boolean) => {
      if (open && !mobileFlawFiltersOpen) {
        setPendingFlawFilter(flawFilter);
      }
      setMobileFlawFiltersOpen(open);
    },
    [mobileFlawFiltersOpen, flawFilter],
  );

  const handleMobileTagsApply = useCallback(() => {
    setFlawFilter(pendingFlawFilter);
    setOffset(0);
    setMobileFlawFiltersOpen(false);
  }, [pendingFlawFilter, setFlawFilter]);

  // ── Data queries ─────────────────────────────────────────────────────────────

  // Poll eval-coverage so the badge and games list update when analysis completes.
  // trackFullAnalysis: keep polling while the background drain works through the
  // backlog so the "N of M analyzed" badge ticks up live (no tier-2 in-flight rows
  // exist for background work — Phase 118 removed the auto-enqueue).
  const { inFlightCount, analyzedCount, totalCount, isError: isCoverageError } = useEvalCoverage({
    trackFullAnalysis: true,
  });

  const {
    data: gamesData,
    isLoading: gamesLoading,
    isError: gamesError,
  } = useLibraryGames(
    appliedFilters,
    flawFilter,
    offset,
    PAGE_SIZE,
    // Poll the games list while analysis is in-flight so cards flip from
    // "Analyzing…" to the analyzed view within a few seconds, no page reload.
    inFlightCount > 0 ? EVAL_COVERAGE_POLL_INTERVAL_MS : 0,
  );

  // Bug fix (118 UAT): the games-list poll above is gated on inFlightCount > 0,
  // so it stops the instant the last eval job completes. But that final
  // completion can land *after* the previous poll, leaving a card stranded on
  // "Analyzing…" forever (the per-game pill only clears once analysis_state
  // flips to 'analyzed', which needs one more refetch). Force exactly one final
  // refetch on the >0 → 0 transition. eval-coverage self-polls to observe the
  // transition, so we always see it even though library-games has stopped.
  const queryClient = useQueryClient();
  const prevInFlightRef = useRef(inFlightCount);
  useEffect(() => {
    const prev = prevInFlightRef.current;
    prevInFlightRef.current = inFlightCount;
    if (prev > 0 && inFlightCount === 0) {
      void queryClient.invalidateQueries({ queryKey: ['library-games'] });
    }
  }, [inFlightCount, queryClient]);

  const { data: profile } = useUserProfile();
  const isGuest = profile?.is_guest ?? false;
  const totalImported =
    profile != null ? profile.chess_com_game_count + profile.lichess_game_count : 0;

  // ── Derived state for empty-state decisions ───────────────────────────────────
  const totalGames = totalImported;
  const matchedCount = gamesData?.matched_count ?? 0;
  const games = gamesData?.games ?? [];

  const noGamesImported = !gamesLoading && !gamesError && totalGames === 0;
  const noMatchedGames = !gamesLoading && !gamesError && totalGames > 0 && matchedCount === 0;

  // ── Sidebar panel config (SidebarLayout) ────────────────────────────────────

  // Game-metadata panel — staged: edits update pending only; Apply commits.
  const gameFilterPanelContent = (
    <div className="p-4">
      <LibraryFilterPanel
        filters={pendingFilters}
        onChange={setPendingFilters}
        onApply={handleDesktopFiltersApply}
        showFlawFilter={false}
      />
    </div>
  );

  // Tags (flaw-filter) panel — staged: edits update pendingFlawFilter only; Apply commits.
  const tagsFilterPanelContent = (
    <div className="p-4 space-y-3">
      <FlawFilterControl
        severity={pendingFlawFilter.severity}
        tags={pendingFlawFilter.tags}
        onSeverityChange={(severity) =>
          setPendingFlawFilter((prev) => ({ ...prev, severity }))
        }
        onTagChange={(tags) => setPendingFlawFilter((prev) => ({ ...prev, tags }))}
      />
      <FilterActions
        resetTestId="btn-tags-reset"
        applyTestId="btn-tags-apply"
        onReset={() => setPendingFlawFilter(DEFAULT_FLAW_FILTER)}
        onApply={handleDesktopTagsApply}
      />
    </div>
  );

  const sidebarPanels = [
    {
      id: 'filters',
      label: 'Filters',
      icon: <SlidersHorizontal className="h-4 w-4" />,
      content: gameFilterPanelContent,
      notificationDot: gameDotNode,
    },
    {
      id: 'tags',
      label: 'Tags',
      icon: <Tags className="h-4 w-4" />,
      content: tagsFilterPanelContent,
      notificationDot: flawDotNode,
    },
  ];

  // ── Main content ─────────────────────────────────────────────────────────────

  const mainContent = (
    <div className="flex flex-col gap-8">
      {gamesError && <LoadError resource="games" />}

      {noGamesImported && (
        <EmptyState
          title="No games imported yet"
          subtitle="Import your games from chess.com or lichess to start analyzing."
          action={
            <Button asChild variant="default" size="sm">
              <Link to="/library/import">Import Games</Link>
            </Button>
          }
        />
      )}

      {noMatchedGames && (
        <EmptyState title="No games matched" subtitle="Try adjusting the filters." />
      )}

      {!gamesError && matchedCount > 0 && (
        <LibraryGameCardList
          games={games}
          matchedCount={matchedCount}
          total={totalGames}
          offset={offset}
          limit={PAGE_SIZE}
          onPageChange={setOffset}
          isGuest={isGuest}
          analyzedN={analyzedCount}
          totalN={totalCount}
          inFlightCount={inFlightCount}
          isCoverageError={isCoverageError}
        />
      )}
    </div>
  );

  // ── Render ────────────────────────────────────────────────────────────────────

  return (
    <div data-testid="games-tab-content">
      {/* Desktop layout: SidebarLayout */}
      <SidebarLayout
        panels={sidebarPanels}
        activePanel={sidebarOpen}
        onActivePanelChange={handleSidebarOpenChange}
      >
        {mainContent}
      </SidebarLayout>

      {/* Mobile layout: sticky filter buttons + Drawers + stacked content */}
      <div className="md:hidden flex flex-col gap-4">
        {/* Sticky row with separate Filters + Tags buttons */}
        <div className="sticky top-0 z-20 flex justify-end gap-2 py-2 bg-background/80 backdrop-blur-sm">
          <Button
            variant="brand-outline"
            className="relative"
            onClick={() => handleMobileFiltersOpenChange(true)}
            aria-label="Open filters"
            data-testid="btn-filters"
          >
            <SlidersHorizontal className="mr-2 h-4 w-4" />
            Filters
            {gameDotNode}
          </Button>
          <Button
            variant="brand-outline"
            className="relative"
            onClick={() => handleMobileFlawFiltersOpenChange(true)}
            aria-label="Open tags"
            data-testid="btn-flaw-filters"
          >
            <Tags className="mr-2 h-4 w-4" />
            Tags
            {flawDotNode}
          </Button>
        </div>

        {/* Game-filters drawer */}
        <Drawer
          open={mobileFiltersOpen}
          onOpenChange={handleMobileFiltersOpenChange}
          direction="right"
        >
          <DrawerContent
            className="!w-full sm:!w-3/4 !bottom-auto !rounded-bl-xl max-h-[85vh]"
            data-testid="drawer-filter-sidebar"
          >
            <DrawerHeader className="flex flex-row items-center justify-between">
              <DrawerTitle>Filters</DrawerTitle>
              <DrawerClose asChild>
                <Button
                  variant="ghost"
                  size="icon"
                  aria-label="Close filters"
                  data-testid="btn-close-filter-drawer"
                >
                  <X className="h-4 w-4" />
                </Button>
              </DrawerClose>
            </DrawerHeader>
            <div className="overflow-y-auto flex-1 p-4">
              <LibraryFilterPanel
                filters={pendingFilters}
                onChange={setPendingFilters}
                onApply={handleMobileFiltersApply}
                showFlawFilter={false}
              />
            </div>
          </DrawerContent>
        </Drawer>

        {/* Tags (flaw-filter) drawer — staged Apply-only */}
        <Drawer
          open={mobileFlawFiltersOpen}
          onOpenChange={handleMobileFlawFiltersOpenChange}
          direction="right"
        >
          <DrawerContent
            className="!w-full sm:!w-3/4 !bottom-auto !rounded-bl-xl max-h-[85vh]"
            data-testid="drawer-flaw-filter-sidebar"
          >
            <DrawerHeader className="flex flex-row items-center justify-between">
              <DrawerTitle>Tags</DrawerTitle>
              <DrawerClose asChild>
                <Button
                  variant="ghost"
                  size="icon"
                  aria-label="Close tags"
                  data-testid="btn-close-flaw-filter-drawer"
                >
                  <X className="h-4 w-4" />
                </Button>
              </DrawerClose>
            </DrawerHeader>
            <div className="overflow-y-auto flex-1 p-4 space-y-3">
              <FlawFilterControl
                severity={pendingFlawFilter.severity}
                tags={pendingFlawFilter.tags}
                onSeverityChange={(severity) =>
                  setPendingFlawFilter((prev) => ({ ...prev, severity }))
                }
                onTagChange={(tags) => setPendingFlawFilter((prev) => ({ ...prev, tags }))}
              />
              <FilterActions
                resetTestId="btn-tags-reset"
                applyTestId="btn-tags-apply"
                onReset={() => setPendingFlawFilter(DEFAULT_FLAW_FILTER)}
                onApply={handleMobileTagsApply}
              />
            </div>
          </DrawerContent>
        </Drawer>

        {/* Stacked main content (mobile).
            Isolate into its own stacking context (relative z-0) so a card's
            hover/touch state (z-30 in LibraryGameCard) can't paint over the
            sticky z-20 Filters/Tags bar above while scrolling. */}
        <div className="relative z-0">{mainContent}</div>
      </div>
    </div>
  );
}
