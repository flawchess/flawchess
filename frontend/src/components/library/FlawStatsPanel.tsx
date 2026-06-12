import { LoadError } from '@/components/ui/load-error';
import { FlawStatsBand } from './FlawStatsBand';
import { FlawTrendChart } from './FlawTrendChart';
import { FlawComparisonGrid } from './FlawComparisonGrid';
import type { FlawStatsResponse } from '@/types/library';
import type { FilterState } from '@/components/filters/FilterPanel';
import type { FlawFilterState } from '@/hooks/useFlawFilterStore';

// ─── Helpers ─────────────────────────────────────────────────────────────────

/** Round a percentage fraction to a whole number string (e.g. 0.312 → "31"). */
function formatAnalyzedPct(pct: number): string {
  return String(Math.round(pct));
}

// ─── Denominator pill ─────────────────────────────────────────────────────────

interface FlawDenominatorPillProps {
  analyzedPct: number;
  analyzedN: number;
}

/**
 * Analyzed-coverage pill ("📊 31% analyzed · N = 124"). Rendered by the page
 * beside the "Flaw Statistics" section heading (Phase 115 UAT — the panel no
 * longer owns its own header row).
 */
export function FlawDenominatorPill({ analyzedPct, analyzedN }: FlawDenominatorPillProps) {
  return (
    <div
      className="ml-auto inline-flex items-center gap-1 rounded-full border border-border px-3 py-1 text-sm font-bold shrink-0"
      style={{ background: 'oklch(1 0 0 / 4%)' }}
      data-testid="flaw-stats-denominator"
    >
      {analyzedN === 0 ? (
        <span className="text-muted-foreground">No analyzed games in the current filter</span>
      ) : (
        <>
          <span className="text-muted-foreground">📊</span>
          <span style={{ color: 'var(--brand-brown-highlight)', fontWeight: 700 }}>
            {formatAnalyzedPct(analyzedPct)}%
          </span>
          <span className="text-muted-foreground">analyzed · N =</span>
          <span style={{ color: 'var(--brand-brown-highlight)', fontWeight: 700 }}>
            {analyzedN}
          </span>
        </>
      )}
    </div>
  );
}

// ─── Props ───────────────────────────────────────────────────────────────────

interface FlawStatsPanelProps {
  /** API response — undefined while loading. */
  stats: FlawStatsResponse | undefined;
  isLoading: boolean;
  isError: boolean;
  /** Shared filter state — passed down to FlawComparisonGrid (Zone 3). */
  filters: FilterState;
  /** Flaw filter state — passed down to FlawComparisonGrid (Zone 3). */
  flawFilter: FlawFilterState;
}

// ─── Component ───────────────────────────────────────────────────────────────

/**
 * Flaw-Stats panel content (UI-SPEC §"Flaw-Stats Panel").
 *
 * Composes FlawStatsBand (Zone 1) + FlawTrendChart (Zone 2) + FlawComparisonGrid
 * (Zone 3). The Band is fixed to per-100-moves (Phase 115 D-02). The section
 * heading and the analyzed-coverage pill (FlawDenominatorPill) are rendered by
 * the host page (GlobalStats) — this panel is body content only (Phase 115 UAT).
 *
 * Zone 3 (FlawComparisonGrid) self-fetches and handles its own loading/error/gate
 * states — the panel's isLoading/isError chain gates only Zones 1–2.
 *
 * States:
 * - isError: shows CLAUDE.md-mandated error copy (never falls through to empty state).
 * - isLoading: lightweight skeleton placeholder.
 * - analyzed_n === 0: empty-analyzed-set state per UI-SPEC.
 * - Normal: full panel content.
 *
 * Data-fetching (useLibraryFlawStats) lives in GlobalStats (Stats tab).
 */
export function FlawStatsPanel({
  stats,
  isLoading,
  isError,
  filters,
  flawFilter,
}: FlawStatsPanelProps) {
  return (
    <div className="mt-3" aria-label="Flaw statistics" data-testid="flaw-stats-panel">
      {/* Error state — mandatory CLAUDE.md isError copy */}
      {isError && <LoadError resource="flaw statistics" />}

      {/* Loading state */}
      {!isError && isLoading && (
        <div className="space-y-3 animate-pulse">
          <div className="flex gap-2">
            {[...Array(3)].map((_, i) => (
              <div
                key={i}
                className="flex-1 min-w-[120px] h-16 rounded border border-border"
                style={{ background: 'var(--color-charcoal)' }}
              />
            ))}
          </div>
          <div className="h-48 rounded border border-border" style={{ background: 'var(--color-charcoal)' }} />
          <div className="h-32 rounded border border-border" style={{ background: 'var(--color-charcoal)' }} />
        </div>
      )}

      {/* Content — shown when not loading and not errored */}
      {!isError && !isLoading && stats !== undefined && (() => {
        const analyzedEmpty = stats.analyzed_n === 0;

        // Rolling window size (games) for the trend chart subheading.
        const windowSize = stats.trend_window;

        return (
          <>
            {/* Zone 1: Severity-rate band — fixed to per-100-moves (D-02) */}
            <FlawStatsBand
              rates={stats.rates}
              analyzedEmpty={analyzedEmpty}
            />

            {/* Zone 2: Flaws / 100 moves trend — 3 severity lines, comparison-free */}
            <FlawTrendChart
              trend={analyzedEmpty ? [] : stats.trend}
              windowSize={windowSize}
            />

            {/* Zone 3: Flaw comparison grid — self-fetches, handles own gate/loading/error */}
            <div className="mt-6">
              <FlawComparisonGrid filters={filters} flawFilter={flawFilter} />
            </div>
          </>
        );
      })()}
    </div>
  );
}
