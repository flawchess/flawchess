import { FilterPanel, DEFAULT_FILTERS } from '@/components/filters/FilterPanel';
import { FlawFilterControl } from '@/components/filters/FlawFilterControl';
import { FilterActions } from '@/components/filters/FilterActions';
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
  /** Called when Apply is clicked — commits pending state and closes the panel */
  onApply: () => void;
  /** Shared flaw filter state (severity × tags). Required only when showFlawFilter is true. */
  flawFilter?: FlawFilterState;
  /** Called when the flaw filter changes (severity or tags). Required only when showFlawFilter is true. */
  onFlawFilterChange?: (next: FlawFilterState) => void;
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
 *
 * Desktop: rendered inside a <aside> sidebar.
 * Mobile: rendered inside the Drawer (same component, no separate mobile copy).
 * The `h-11 sm:h-7` touch-target height is preserved on both form factors.
 *
 * Staged-apply model: edits update the caller's pending state only; Apply commits
 * pending to the store and closes the panel.
 */
export function LibraryFilterPanel({
  filters,
  onChange,
  onApply,
  flawFilter,
  onFlawFilterChange,
  showFlawFilter = true,
}: LibraryFilterPanelProps) {
  // Reset game-metadata filters only — flaw filter has its own Reset in the Tags panel.
  const handleReset = () => {
    onChange({ ...DEFAULT_FILTERS, color: filters.color, customRange: null });
  };

  // Only render the flaw control when requested AND its handlers are supplied. The
  // Flaws subtab hosts the flaw filter in a separate sidebar panel, so it passes
  // showFlawFilter={false} here and renders FlawFilterControl on its own.
  const flawControl =
    showFlawFilter && flawFilter && onFlawFilterChange ? (
      <>
        {/* FlawFilterControl — severity × tag-family toggle above standard filters (D-01) */}
        <FlawFilterControl
          severity={flawFilter.severity}
          tags={flawFilter.tags}
          onSeverityChange={(severity) => onFlawFilterChange({ ...flawFilter, severity })}
          onTagChange={(tags) => onFlawFilterChange({ ...flawFilter, tags })}
        />

        <div className="border-t border-border/40" />
      </>
    ) : null;

  return (
    <div className="space-y-3">
      {flawControl}

      {/* Standard metadata filters (time control, platform, recency, more).
          hideReset=true: LibraryFilterPanel owns the Reset+Apply footer below. */}
      <FilterPanel
        filters={filters}
        onChange={onChange}
        visibleFilters={LIBRARY_GAMES_FILTERS}
        hideReset
      />

      {/* Reset + Apply footer — Reset clears game-metadata FilterState only (D-01) */}
      <FilterActions
        onReset={handleReset}
        onApply={onApply}
      />
    </div>
  );
}
