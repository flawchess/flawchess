import { cn } from '@/lib/utils';
import { Button } from '@/components/ui/button';
import { FilterPanel, DEFAULT_FILTERS } from '@/components/filters/FilterPanel';
import type { FilterState } from '@/components/filters/FilterPanel';

// ─── Constants ───────────────────────────────────────────────────────────────

/**
 * Filter fields shown on the Games surface. Omits `matchSide` (color/matchSide)
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
  /** Separate severity filter — NOT part of FilterState (D-07 / UI-SPEC) */
  severityFilter: ('blunder' | 'mistake')[];
  /** Called when the severity filter changes */
  onSeverityChange: (severity: ('blunder' | 'mistake')[]) => void;
  /** When true, shows the deferred-apply hint below Reset (mobile drawer usage) */
  showDeferredApplyHint?: boolean;
}

// ─── Component ────────────────────────────────────────────────────────────────

/**
 * LibraryFilterPanel composes the existing FilterPanel with the Games-surface
 * `visibleFilters` (omitting color/matchSide) and prepends a boolean
 * "Show games with:" severity toggle section above it.
 *
 * The severity filter is kept as a separate prop (not added to FilterState) per
 * UI-SPEC §"Mistake-severity filter" and the D-07 design decision.
 *
 * Desktop: rendered inside a <aside> sidebar.
 * Mobile: rendered inside the Drawer (same component, no separate mobile copy).
 * The `h-11 sm:h-7` touch-target height is preserved on both form factors.
 */
export function LibraryFilterPanel({
  filters,
  onChange,
  severityFilter,
  onSeverityChange,
  showDeferredApplyHint = false,
}: LibraryFilterPanelProps) {
  const toggleSeverity = (level: 'blunder' | 'mistake') => {
    if (severityFilter.includes(level)) {
      onSeverityChange(severityFilter.filter((s) => s !== level));
    } else {
      onSeverityChange([...severityFilter, level]);
    }
  };

  const handleReset = () => {
    onChange({ ...DEFAULT_FILTERS, color: filters.color, customRange: null });
    onSeverityChange([]);
  };

  return (
    <div className="space-y-3">
      {/* Severity filter — "Show games with:" toggle above the standard filters */}
      <div className="flex flex-col gap-2">
        <p className="text-sm text-muted-foreground">Show games with:</p>
        <div className="flex gap-2">
          <button
            type="button"
            className={cn(
              'h-11 sm:h-7 px-3 rounded border text-sm font-bold transition-colors',
              severityFilter.includes('blunder')
                ? 'border-toggle-active bg-toggle-active text-toggle-active-foreground'
                : 'border-border bg-inactive-bg text-muted-foreground',
            )}
            aria-pressed={severityFilter.includes('blunder')}
            data-testid="filter-severity-blunder"
            onClick={() => toggleSeverity('blunder')}
          >
            Blunders
          </button>
          <button
            type="button"
            className={cn(
              'h-11 sm:h-7 px-3 rounded border text-sm font-bold transition-colors',
              severityFilter.includes('mistake')
                ? 'border-toggle-active bg-toggle-active text-toggle-active-foreground'
                : 'border-border bg-inactive-bg text-muted-foreground',
            )}
            aria-pressed={severityFilter.includes('mistake')}
            data-testid="filter-severity-mistake"
            onClick={() => toggleSeverity('mistake')}
          >
            Mistakes
          </button>
        </div>
      </div>

      {/* Standard metadata filters (time control, platform, recency, more).
          hideReset=true: LibraryFilterPanel owns the Reset button below so it
          can clear both FilterState and severityFilter together. */}
      <FilterPanel
        filters={filters}
        onChange={onChange}
        visibleFilters={LIBRARY_GAMES_FILTERS}
        showDeferredApplyHint={showDeferredApplyHint}
        hideReset
      />

      {/* Reset Filters — clears both FilterState and severityFilter */}
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
