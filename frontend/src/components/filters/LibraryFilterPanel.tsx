import { Button } from '@/components/ui/button';
import { FilterPanel, DEFAULT_FILTERS } from '@/components/filters/FilterPanel';
import { FlawFilterControl } from '@/components/filters/FlawFilterControl';
import type { FilterState } from '@/components/filters/FilterPanel';
import type { FlawFilterState } from '@/hooks/useFlawFilterStore';

// ─── Constants ───────────────────────────────────────────────────────────────

/**
 * Filter fields shown on the Games/Flaws surface. Omits `matchSide` (color/matchSide)
 * because the Games subtab shows all colors; no opening/position filter needed.
 *
 * Using the same literal type as FilterPanel's internal FilterField union.
 */
type FilterField = 'timeControl' | 'platform' | 'rated' | 'opponent' | 'opponentStrength' | 'recency' | 'playedAs';

const LIBRARY_GAMES_FILTERS: FilterField[] = [
  'playedAs',
  'timeControl',
  'platform',
  'opponent',
  'opponentStrength',
  'rated',
  'recency',
];

// ─── Props ────────────────────────────────────────────────────────────────────

interface LibraryFilterPanelProps {
  /** Shared filter state (time control, platform, recency, etc.) */
  filters: FilterState;
  /** Called when the shared filter state changes */
  onChange: (filters: FilterState) => void;
  /** Shared flaw filter state (severity × tags). Required only when showFlawFilter is true. */
  flawFilter?: FlawFilterState;
  /** Called when the flaw filter changes (severity or tags). Required only when showFlawFilter is true. */
  onFlawFilterChange?: (next: FlawFilterState) => void;
  /** Called when "Clear flaw filter" is clicked. Required only when showFlawFilter is true. */
  onClearFlawFilter?: () => void;
  /** When true, shows the deferred-apply hint below Reset (mobile drawer usage) */
  showDeferredApplyHint?: boolean;
  /**
   * When false, render only the game-metadata filters and omit the FlawFilterControl
   * (used by the Flaws subtab, which hosts the flaw filter in its own separate panel).
   * Default true so existing callers (Games subtab) keep the combined layout.
   */
  showFlawFilter?: boolean;
}

// ─── Component ────────────────────────────────────────────────────────────────

/**
 * LibraryFilterPanel composes FlawFilterControl (severity × tag-family multi-select)
 * ABOVE the existing FilterPanel (game-metadata: platform/TC/rated/recency/opponent).
 *
 * D-01: the boolean severity toggle is removed; FlawFilterControl replaces it.
 * The "Clear flaw filter" affordance in FlawFilterControl is separate from the
 * "Reset Filters" button which clears game-metadata filters only.
 *
 * Desktop: rendered inside a <aside> sidebar.
 * Mobile: rendered inside the Drawer (same component, no separate mobile copy).
 * The `h-11 sm:h-7` touch-target height is preserved on both form factors.
 */
export function LibraryFilterPanel({
  filters,
  onChange,
  flawFilter,
  onFlawFilterChange,
  onClearFlawFilter,
  showDeferredApplyHint = false,
  showFlawFilter = true,
}: LibraryFilterPanelProps) {
  // Reset game-metadata filters only — flaw filter has its own "Clear" affordance (D-01)
  const handleReset = () => {
    onChange({ ...DEFAULT_FILTERS, color: filters.color, customRange: null });
  };

  // Only render the flaw control when requested AND its handlers are supplied. The
  // Flaws subtab hosts the flaw filter in a separate sidebar panel, so it passes
  // showFlawFilter={false} here and renders FlawFilterControl on its own.
  const flawControl =
    showFlawFilter && flawFilter && onFlawFilterChange && onClearFlawFilter ? (
      <>
        {/* FlawFilterControl — "Show flaws with:" severity × tag-family toggle above standard filters (D-01) */}
        <FlawFilterControl
          severity={flawFilter.severity}
          tags={flawFilter.tags}
          onSeverityChange={(severity) => onFlawFilterChange({ ...flawFilter, severity })}
          onTagChange={(tags) => onFlawFilterChange({ ...flawFilter, tags })}
          onClear={onClearFlawFilter}
        />

        <div className="border-t border-border/40" />
      </>
    ) : null;

  return (
    <div className="space-y-3">
      {flawControl}

      {/* Standard metadata filters (time control, platform, recency, more).
          hideReset=true: LibraryFilterPanel owns the Reset button below so it
          can clearly scope the reset to game-metadata only (not flaw filter). */}
      <FilterPanel
        filters={filters}
        onChange={onChange}
        visibleFilters={LIBRARY_GAMES_FILTERS}
        showDeferredApplyHint={showDeferredApplyHint}
        hideReset
      />

      {/* Reset Filters — clears game-metadata FilterState only (not flaw filter — D-01) */}
      <div className="pt-2 border-t border-border/40">
        <Button
          type="button"
          variant="brand-outline"
          size="lg"
          className="w-full min-h-11 sm:min-h-0"
          data-testid="btn-reset-filters"
          onClick={handleReset}
        >
          Reset Filters
        </Button>
      </div>
    </div>
  );
}
