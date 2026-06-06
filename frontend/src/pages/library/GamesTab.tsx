import { useState, useCallback, useMemo, useRef, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { SlidersHorizontal, X } from 'lucide-react';
import { SidebarLayout } from '@/components/layout/SidebarLayout';
import { Button } from '@/components/ui/button';
import { Drawer, DrawerContent, DrawerHeader, DrawerTitle, DrawerClose } from '@/components/ui/drawer';
import {
  DEFAULT_FILTERS,
  areFiltersEqual,
  FILTER_DOT_FIELDS,
} from '@/components/filters/FilterPanel';
import { LibraryFilterPanel } from '@/components/filters/LibraryFilterPanel';
import { LibraryGameCardList } from '@/components/results/LibraryGameCardList';
import { useFilterStore } from '@/hooks/useFilterStore';
import { useLibraryGames } from '@/hooks/useLibrary';
import { useUserProfile } from '@/hooks/useUserProfile';
import type { FilterState } from '@/components/filters/FilterPanel';

// ─── Constants ────────────────────────────────────────────────────────────────

const PAGE_SIZE = 20;

// ─── Component ────────────────────────────────────────────────────────────────

/**
 * GamesTab — the Library Games subtab root.
 *
 * Composes LibraryFilterPanel (desktop sidebar / mobile drawer) + LibraryGameCardList,
 * wiring useLibraryGames to the shared filter + local severityFilter state.
 * FlawStatsPanel lives on the Stats tab (GlobalStats.tsx).
 *
 * Desktop layout: SidebarLayout with LibraryFilterPanel in the sidebar.
 * Mobile layout: sticky "Filters" button opening a right Drawer containing
 * LibraryFilterPanel, then the game list.
 *
 * Filter interaction per UI-SPEC:
 * - Desktop: filters apply live (on change).
 * - Mobile: filters apply on drawer close.
 *
 * State management:
 * - appliedFilters: drives useLibraryGames (shared, from useFilterStore).
 * - pendingFilters: tracks edits in the desktop sidebar / mobile drawer.
 * - severityFilter: separate local state (NOT part of FilterState), wired to
 *   useLibraryGames only (decision 5).
 * - offset: page state, reset to 0 on any filter/severity change.
 */
export function GamesTab() {
  // ── Filter state ─────────────────────────────────────────────────────────────
  const [appliedFilters, setAppliedFilters] = useFilterStore();
  const [pendingFilters, setPendingFilters] = useState<FilterState>(appliedFilters);

  // Sync pending -> applied when the filter store changes from another page/tab
  useEffect(() => {
    setPendingFilters(appliedFilters);
  }, [appliedFilters]);

  // ── Severity filter (separate local state — NOT part of FilterState) ─────────
  const [severityFilter, setSeverityFilter] = useState<('blunder' | 'mistake')[]>([]);

  // ── Pagination state ─────────────────────────────────────────────────────────
  const [offset, setOffset] = useState(0);

  // ── Mobile drawer state ──────────────────────────────────────────────────────
  const [mobileFiltersOpen, setMobileFiltersOpen] = useState(false);

  // ── Desktop sidebar state ────────────────────────────────────────────────────
  const [sidebarOpen, setSidebarOpen] = useState<string | null>(null);

  // ── Modified-filters indicator ───────────────────────────────────────────────
  // The dot reflects APPLIED filters + severity (what the backend is filtering by).
  const isModified = useMemo(
    () =>
      !areFiltersEqual(appliedFilters, DEFAULT_FILTERS, FILTER_DOT_FIELDS) ||
      severityFilter.length > 0,
    [appliedFilters, severityFilter],
  );
  const [isPulsing, setIsPulsing] = useState(false);
  const pulseTimeoutRef = useRef<number | null>(null);
  const prevAppliedRef = useRef(appliedFilters);

  useEffect(() => {
    if (prevAppliedRef.current !== appliedFilters) {
      prevAppliedRef.current = appliedFilters;
      setIsPulsing(true);
      if (pulseTimeoutRef.current !== null) {
        window.clearTimeout(pulseTimeoutRef.current);
      }
      pulseTimeoutRef.current = window.setTimeout(() => {
        setIsPulsing(false);
        pulseTimeoutRef.current = null;
      }, 1000);
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

  // ── Handlers ─────────────────────────────────────────────────────────────────

  // Desktop sidebar: defers filter apply until the panel closes.
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

  // Mobile drawer: defers filter apply until the drawer closes.
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

  // Severity filter change — reset pagination.
  const handleSeverityChange = useCallback((severity: ('blunder' | 'mistake')[]) => {
    setSeverityFilter(severity);
    setOffset(0);
  }, []);

  // Severity filter change for pending (mobile) — does NOT reset offset yet;
  // offset resets when the drawer closes and pending is committed to applied.
  const handlePendingSeverityChange = useCallback(
    (severity: ('blunder' | 'mistake')[]) => {
      setSeverityFilter(severity);
    },
    [],
  );

  // ── Data queries ─────────────────────────────────────────────────────────────
  // severityFilter is scoped to games only (decision 5); FlawStatsPanel moved to Stats tab.
  const {
    data: gamesData,
    isLoading: gamesLoading,
    isError: gamesError,
  } = useLibraryGames(appliedFilters, severityFilter, offset, PAGE_SIZE);

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
  const filterPanelContent = (
    <div className="p-4">
      <LibraryFilterPanel
        filters={pendingFilters}
        onChange={(filters) => {
          setPendingFilters(filters);
          // Desktop live apply
          setAppliedFilters(filters);
          setOffset(0);
        }}
        severityFilter={severityFilter}
        onSeverityChange={handleSeverityChange}
      />
    </div>
  );

  const sidebarPanels = [
    {
      id: 'filters',
      label: 'Filters',
      icon: <SlidersHorizontal className="h-4 w-4" />,
      content: filterPanelContent,
      notificationDot: modifiedDotNode,
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

      {/* Mobile layout: sticky filter button + Drawer + stacked content */}
      <div className="md:hidden flex flex-col gap-4">
        {/* Sticky row with Filters button */}
        <div className="sticky top-0 z-20 flex justify-end py-2 bg-background/80 backdrop-blur-sm">
          <Button
            variant="brand-outline"
            className="relative"
            onClick={() => setMobileFiltersOpen(true)}
            aria-label="Open filters"
            data-testid="btn-filters"
          >
            <SlidersHorizontal className="mr-2 h-4 w-4" />
            Filters
            {modifiedDotNode}
          </Button>
        </div>

        {/* Filter drawer */}
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
                severityFilter={severityFilter}
                onSeverityChange={handlePendingSeverityChange}
                showDeferredApplyHint
              />
            </div>
          </DrawerContent>
        </Drawer>

        {/* Stacked main content (mobile) */}
        {mainContent}
      </div>
    </div>
  );
}
