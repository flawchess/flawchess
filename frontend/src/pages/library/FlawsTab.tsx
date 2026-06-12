import { useState, useCallback, useMemo, useRef, useEffect } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
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
import { FlawCard } from '@/components/library/FlawCard';
import { NoEngineAnalysisFlawsState } from '@/components/library/NoEngineAnalysisFlawsState';
import { Pagination } from '@/components/results/Pagination';
import { useFilterStore } from '@/hooks/useFilterStore';
import {
  useFlawFilterStore,
  DEFAULT_FLAW_FILTER,
  isFlawFilterNonDefault,
} from '@/hooks/useFlawFilterStore';
import { useLibraryFlaws, useLibraryFlawStats } from '@/hooks/useLibrary';
import { useUserProfile } from '@/hooks/useUserProfile';
import type { FilterState } from '@/components/filters/FilterPanel';
import type { FlawFilterState } from '@/hooks/useFlawFilterStore';
import type { FlawTag } from '@/types/library';

// ─── Constants ────────────────────────────────────────────────────────────────

const PAGE_SIZE = 20;

// Filter-independent probe for "does the user have ANY engine-analyzed games":
// no date/TC/platform restriction, both opponent types, no flaw filter. Module
// level so the TanStack query key stays stable across renders.
const UNFILTERED_PROBE_FILTERS: FilterState = { ...DEFAULT_FILTERS, opponentType: 'both' };
const NO_FLAW_FILTER: FlawFilterState = { severity: [], tags: [] };

// ─── Component ────────────────────────────────────────────────────────────────

/**
 * FlawsTab — the Library Flaws subtab root.
 *
 * Composes two separate filter panels — "Filters" (game metadata, LibraryFilterPanel
 * with showFlawFilter=false) and "Flaw filters" (severity + tags, FlawFilterControl) —
 * + per-flaw miniboard list + Pagination, wiring useLibraryFlaws to the shared stores.
 *
 * URL sync (D-04): on mount, reads ?tag=&severity= from URL and initializes the
 * flaw filter store from them (only when params are present). On store change,
 * updates URL via replace-state (no history pollution).
 *
 * Desktop layout: SidebarLayout with two strip panels (game filters + flaw filters),
 * both applying live on change.
 * Mobile layout: two sticky buttons, each opening its own right Drawer; both apply on
 * close (the flaw filter buffers edits in pendingFlawFilter until its drawer closes).
 */
export function FlawsTab() {
  // ── URL sync setup ───────────────────────────────────────────────────────────
  const [searchParams, setSearchParams] = useSearchParams();

  // ── Filter state ─────────────────────────────────────────────────────────────
  const [appliedFilters, setAppliedFilters] = useFilterStore();
  const [pendingFilters, setPendingFilters] = useState<FilterState>(appliedFilters);

  // Sync pending -> applied when the filter store changes from another page/tab
  useEffect(() => {
    setPendingFilters(appliedFilters);
  }, [appliedFilters]);

  // ── Flaw filter (shared, URL-synced on this tab) ──────────────────────────────
  const [flawFilter, setFlawFilter] = useFlawFilterStore();

  // Mount: read URL params → initialize store (only when URL has params — D-04/OQ3)
  const didInitFromUrl = useRef(false);
  const initialSearchParams = useRef(searchParams);
  useEffect(() => {
    if (didInitFromUrl.current) return;
    didInitFromUrl.current = true;

    const urlTags = initialSearchParams.current.getAll('tag') as FlawTag[];
    const urlSeverity = initialSearchParams.current.getAll('severity') as ('blunder' | 'mistake')[];

    if (urlTags.length > 0 || urlSeverity.length > 0) {
      // Empty severity in the URL = both shown (the default narrowing-off state).
      setFlawFilter({ tags: urlTags, severity: urlSeverity });
    }
  }, [setFlawFilter]);

  // Store change → update URL (replace, not push — avoids polluting history)
  useEffect(() => {
    const params = new URLSearchParams();
    flawFilter.tags.forEach((t) => params.append('tag', t));
    if (flawFilter.severity.length < 2) {
      flawFilter.severity.forEach((s) => params.append('severity', s));
    }
    setSearchParams(params, { replace: true });
  }, [flawFilter, setSearchParams]);

  // ── Pending flaw filter draft — shared buffer for desktop Tags panel and mobile drawer ──
  const [pendingFlawFilter, setPendingFlawFilter] = useState<FlawFilterState>(flawFilter);

  // Keep the pending buffer fresh whenever the committed store changes.
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
    <ModifiedDot active={isGameModified} pulsing={gamePulsing} testId="filters-modified-dot-flaws" />
  );
  const flawDotNode = (
    <ModifiedDot active={isFlawModified} pulsing={flawPulsing} testId="flaw-filters-modified-dot" />
  );

  // ── Handlers ─────────────────────────────────────────────────────────────────

  // Desktop sidebar: on open, snapshot committed state. Close without Apply = discard draft.
  const handleSidebarOpenChange = useCallback(
    (panelId: string | null) => {
      if (sidebarOpen !== panelId && panelId === 'filters') {
        setPendingFilters(appliedFilters);
      }
      if (sidebarOpen !== panelId && panelId === 'tags') {
        setPendingFlawFilter(flawFilter);
      }
      setSidebarOpen(panelId);
    },
    [sidebarOpen, appliedFilters, flawFilter],
  );

  // Desktop game-metadata Apply: commit and close.
  const handleDesktopFiltersApply = useCallback(() => {
    setAppliedFilters(pendingFilters);
    setOffset(0);
    setSidebarOpen(null);
  }, [pendingFilters, setAppliedFilters]);

  // Desktop Tags Apply: commit and close.
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

  // Mobile Tags drawer: on open snapshot committed; Apply commits + closes.
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
  const {
    data: flawsData,
    isLoading: flawsLoading,
    isError: flawsError,
  } = useLibraryFlaws(appliedFilters, flawFilter, offset, PAGE_SIZE);

  const { data: profile } = useUserProfile();
  const totalImported =
    profile != null ? profile.chess_com_game_count + profile.lichess_game_count : 0;

  // Unfiltered flaw-stats probe — analyzed_n distinguishes "you have no
  // engine-analyzed games at all" from "your filters matched no flaws". It must
  // NOT inherit the applied filters: a filter set matching zero games would
  // yield analyzed_n=0 and falsely show the no-engine-analysis message to a
  // user who DOES have analyzed games (CLAUDE.md empty-state rule).
  const { data: statsData } = useLibraryFlawStats(UNFILTERED_PROBE_FILTERS, NO_FLAW_FILTER);

  // ── Derived state ────────────────────────────────────────────────────────────
  const totalGames = totalImported;
  const matchedCount = flawsData?.matched_count ?? 0;
  const flaws = flawsData?.flaws ?? [];

  const noGamesImported = !flawsLoading && !flawsError && totalGames === 0;
  const noMatchedFlaws =
    !flawsLoading && !flawsError && totalGames > 0 && matchedCount === 0 && flawsData != null;
  // No engine-analyzed games at all → the big "engine analysis missing" state.
  // Defaults to true while stats are loading so users with zero analyzed games
  // (the common case for this state) don't flash the filter-hint message first.
  const noAnalyzedGames = statsData == null || statsData.analyzed_n === 0;

  // ── Filter panel content ─────────────────────────────────────────────────────

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
    <div className="flex flex-col gap-6">
      {/* Error state — MANDATORY isError branch (CLAUDE.md) */}
      {flawsError && <LoadError resource="flaws" />}

      {/* No games imported empty state */}
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

      {/* Flaw list — only when not errored */}
      {!flawsError && (
        <section aria-label="Flaw results" data-testid="flaw-list">
          {flawsData != null && (
            <p className="text-sm text-muted-foreground mb-4">
              {matchedCount} flaw{matchedCount === 1 ? '' : 's'} matched
            </p>
          )}

          {noMatchedFlaws &&
            (noAnalyzedGames ? (
              <NoEngineAnalysisFlawsState />
            ) : (
              <EmptyState
                title="No flaws matched"
                subtitle="Try adjusting the flaw filter or game filters."
              />
            ))}

          {matchedCount > 0 && (
            <div
              className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4"
              data-testid="flaw-grid"
            >
              {flaws.map((flaw) => (
                <FlawCard key={`${flaw.game_id}-${flaw.ply}`} flaw={flaw} />
              ))}
            </div>
          )}

          {matchedCount > PAGE_SIZE && (
            <div className="mt-6">
              <Pagination
                currentPage={Math.floor(offset / PAGE_SIZE) + 1}
                totalPages={Math.ceil(matchedCount / PAGE_SIZE)}
                onPageChange={(page) => {
                  setOffset((page - 1) * PAGE_SIZE);
                  window.scrollTo({ top: 0 });
                }}
              />
            </div>
          )}
        </section>
      )}
    </div>
  );

  // ── Render ────────────────────────────────────────────────────────────────────

  return (
    <div data-testid="flaws-tab-content">
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
            aria-label="Open game filters"
            data-testid="btn-game-filters"
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
            data-testid="drawer-game-filter-sidebar"
          >
            <DrawerHeader className="flex flex-row items-center justify-between">
              <DrawerTitle>Filters</DrawerTitle>
              <DrawerClose asChild>
                <Button
                  variant="ghost"
                  size="icon"
                  aria-label="Close game filters"
                  data-testid="btn-close-game-filter-drawer"
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

        {/* Stacked main content (mobile) */}
        {mainContent}
      </div>
    </div>
  );
}
