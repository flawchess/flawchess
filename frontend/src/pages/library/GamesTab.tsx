import { useState, useCallback, useMemo, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { SlidersHorizontal, Tags, X } from 'lucide-react';
import { SidebarLayout } from '@/components/layout/SidebarLayout';
import { Button } from '@/components/ui/button';
import { Drawer, DrawerContent, DrawerHeader, DrawerTitle, DrawerClose } from '@/components/ui/drawer';
import {
  DEFAULT_FILTERS,
  areFiltersEqual,
  FILTER_DOT_FIELDS,
} from '@/components/filters/FilterPanel';
import { LibraryFilterPanel } from '@/components/filters/LibraryFilterPanel';
import { FlawFilterControl } from '@/components/filters/FlawFilterControl';
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
import type { FilterState } from '@/components/filters/FilterPanel';
import type { FlawFilterState } from '@/hooks/useFlawFilterStore';

// ─── Constants ────────────────────────────────────────────────────────────────

const PAGE_SIZE = 20;

// ─── Component ────────────────────────────────────────────────────────────────

/**
 * GamesTab — the Library Games subtab root.
 *
 * Composes two separate filter panels (game-metadata + flaw filter) +
 * LibraryGameCardList, wiring useLibraryGames to the shared filter + shared flaw
 * filter state. FlawStatsPanel lives on the Stats tab (GlobalStats.tsx).
 *
 * Desktop layout: SidebarLayout with two strip panels — "Filters" (game metadata,
 * LibraryFilterPanel with showFlawFilter=false) and "Flaw filters" (severity + tags,
 * FlawFilterControl).
 * Mobile layout: two sticky buttons each opening their own right Drawer, then the
 * game list.
 *
 * Filter interaction per UI-SPEC:
 * - Desktop: both panels apply live (on change).
 * - Mobile: both drawers apply on close. The flaw filter buffers edits in
 *   pendingFlawFilter and commits to the store when its drawer closes.
 *
 * State management:
 * - appliedFilters: drives useLibraryGames (shared, from useFilterStore).
 * - pendingFilters: tracks game-metadata edits in the desktop sidebar / mobile drawer.
 * - flawFilter: shared cross-tab state from useFlawFilterStore (D-04).
 *   Games tab does NOT URL-sync (D-04 — Phase 107 precedent).
 * - pendingFlawFilter: buffers mobile flaw-drawer edits until close.
 * - offset: page state, reset to 0 on any filter/flaw-filter change.
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
  // Games tab does NOT URL-sync (D-04). State is read/written via the shared
  // useFlawFilterStore so switching Games↔Flaws preserves the selection in memory.
  const [flawFilter, setFlawFilter] = useFlawFilterStore();

  // Pending flaw filter buffer for the mobile drawer — desktop applies live, mobile
  // commits to the store on drawer close (apply-on-close), mirroring game-metadata.
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
  // The dots reflect APPLIED filters + flaw filter (what the backend is filtering by).
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

  // Desktop sidebar: defers game-metadata apply until the panel closes. The flaw
  // panel applies live, so it needs no pending-buffer handling here.
  const handleSidebarOpenChange = useCallback(
    (panelId: string | null) => {
      if (sidebarOpen === 'filters' && panelId !== 'filters') {
        setAppliedFilters(pendingFilters);
        setOffset(0);
      }
      if (sidebarOpen !== 'filters' && panelId === 'filters') {
        setPendingFilters(appliedFilters);
      }
      setSidebarOpen(panelId);
    },
    [sidebarOpen, pendingFilters, appliedFilters, setAppliedFilters],
  );

  // Mobile game-filters drawer: defers apply until the drawer closes.
  const handleMobileFiltersOpenChange = useCallback(
    (open: boolean) => {
      if (!open && mobileFiltersOpen) {
        setAppliedFilters(pendingFilters);
        setOffset(0);
      }
      if (open && !mobileFiltersOpen) {
        setPendingFilters(appliedFilters);
      }
      setMobileFiltersOpen(open);
    },
    [mobileFiltersOpen, pendingFilters, appliedFilters, setAppliedFilters],
  );

  // Mobile flaw-filters drawer: buffers edits and commits to the store on close.
  const handleMobileFlawFiltersOpenChange = useCallback(
    (open: boolean) => {
      if (!open && mobileFlawFiltersOpen) {
        setFlawFilter(pendingFlawFilter);
        setOffset(0);
      }
      if (open && !mobileFlawFiltersOpen) {
        setPendingFlawFilter(flawFilter);
      }
      setMobileFlawFiltersOpen(open);
    },
    [mobileFlawFiltersOpen, pendingFlawFilter, flawFilter, setFlawFilter],
  );

  // Flaw filter change (desktop live) — reset pagination (D-04).
  const handleFlawFilterChange = useCallback(
    (next: FlawFilterState) => {
      setFlawFilter(next);
      setOffset(0);
    },
    [setFlawFilter],
  );

  // Clear flaw filter only (desktop live) — does not reset game-metadata filters (D-01).
  const handleClearFlawFilter = useCallback(() => {
    setFlawFilter(DEFAULT_FLAW_FILTER);
    setOffset(0);
  }, [setFlawFilter]);

  // ── Data queries ─────────────────────────────────────────────────────────────
  // flawFilter passes both severity and tags to the migrated endpoint (D-04).
  const {
    data: gamesData,
    isLoading: gamesLoading,
    isError: gamesError,
  } = useLibraryGames(appliedFilters, flawFilter, offset, PAGE_SIZE);

  // User's total imported games across all platforms — used as the count-row denominator
  // ("N of {totalImported} games"). Distinct from matchedCount (games matching filters).
  // The API response has no total field; the profile already carries the real total.
  const { data: profile } = useUserProfile();
  const totalImported =
    profile != null ? profile.chess_com_game_count + profile.lichess_game_count : 0;

  // ── Derived state for empty-state decisions ───────────────────────────────────
  const totalGames = totalImported;
  const matchedCount = gamesData?.matched_count ?? 0;
  const games = gamesData?.games ?? [];

  // No games at all for this user.
  const noGamesImported = !gamesLoading && !gamesError && totalGames === 0;
  // Filters matched nothing but there ARE games.
  const noMatchedGames = !gamesLoading && !gamesError && totalGames > 0 && matchedCount === 0;

  // ── Sidebar panel config (SidebarLayout) ────────────────────────────────────
  // Game-metadata panel (no flaw control — it lives in its own panel below).
  const gameFilterPanelContent = (
    <div className="p-4">
      <LibraryFilterPanel
        filters={pendingFilters}
        onChange={(filters) => {
          setPendingFilters(filters);
          // Desktop live apply
          setAppliedFilters(filters);
          setOffset(0);
        }}
        showFlawFilter={false}
      />
    </div>
  );

  // Flaw-filter panel (severity + tags). Desktop applies live to the store.
  const flawFilterPanelContent = (
    <div className="p-4">
      <FlawFilterControl
        severity={flawFilter.severity}
        tags={flawFilter.tags}
        onSeverityChange={(severity) => handleFlawFilterChange({ ...flawFilter, severity })}
        onTagChange={(tags) => handleFlawFilterChange({ ...flawFilter, tags })}
        onClear={handleClearFlawFilter}
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
      id: 'flaw-filters',
      label: 'Flaw filters',
      icon: <Tags className="h-4 w-4" />,
      content: flawFilterPanelContent,
      notificationDot: flawDotNode,
    },
  ];

  // ── Main content ─────────────────────────────────────────────────────────────

  const mainContent = (
    <div className="flex flex-col gap-8">
      {/* Games error state */}
      {gamesError && (
        <p className="text-sm text-muted-foreground">
          Failed to load games. Something went wrong. Please try again in a moment.
        </p>
      )}

      {/* No games imported empty state */}
      {noGamesImported && (
        <div className="flex flex-col items-center gap-3 py-8 text-center">
          <p className="text-base font-bold">No games imported yet</p>
          <p className="text-sm text-muted-foreground">
            Import your games from chess.com or lichess to start analyzing.
          </p>
          <Button asChild variant="default" size="sm">
            <Link to="/library/import">Import Games</Link>
          </Button>
        </div>
      )}

      {/* Filters match nothing empty state */}
      {noMatchedGames && (
        <div className="flex flex-col items-center gap-2 py-8 text-center">
          <p className="text-base font-bold">No games matched</p>
          <p className="text-sm text-muted-foreground">Try adjusting the filters.</p>
        </div>
      )}

      {/* Game card list — only show when there are matched games and no error */}
      {!gamesError && matchedCount > 0 && (
        <LibraryGameCardList
          games={games}
          matchedCount={matchedCount}
          total={totalGames}
          offset={offset}
          limit={PAGE_SIZE}
          onPageChange={setOffset}
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
        {/* Sticky row with separate Filters + Flaw filters buttons */}
        <div className="sticky top-0 z-20 flex justify-end gap-2 py-2 bg-background/80 backdrop-blur-sm">
          <Button
            variant="brand-outline"
            className="relative"
            onClick={() => setMobileFiltersOpen(true)}
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
            onClick={() => setMobileFlawFiltersOpen(true)}
            aria-label="Open flaw filters"
            data-testid="btn-flaw-filters"
          >
            <Tags className="mr-2 h-4 w-4" />
            Flaw filters
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
                showFlawFilter={false}
                showDeferredApplyHint
              />
            </div>
          </DrawerContent>
        </Drawer>

        {/* Flaw-filters drawer — applies on close (apply-on-close buffer) */}
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
              <DrawerTitle>Flaw filters</DrawerTitle>
              <DrawerClose asChild>
                <Button
                  variant="ghost"
                  size="icon"
                  aria-label="Close flaw filters"
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
                  setPendingFlawFilter({ ...pendingFlawFilter, severity })
                }
                onTagChange={(tags) => setPendingFlawFilter({ ...pendingFlawFilter, tags })}
                onClear={() => setPendingFlawFilter(DEFAULT_FLAW_FILTER)}
              />
              <p
                className="text-sm italic leading-tight text-muted-foreground"
                data-testid="flaw-filter-deferred-apply-hint"
              >
                <span className="font-semibold text-foreground/80">Tip:</span> Filter changes apply
                on closing the filters panel.
              </p>
            </div>
          </DrawerContent>
        </Drawer>

        {/* Stacked main content (mobile) */}
        {mainContent}
      </div>
    </div>
  );
}
