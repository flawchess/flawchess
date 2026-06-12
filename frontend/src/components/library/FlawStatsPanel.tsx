import { Cpu } from 'lucide-react';
import { LoadError } from '@/components/ui/load-error';
import { InfoPopover } from '@/components/ui/info-popover';
import { FlawStatsBand } from './FlawStatsBand';
import { FlawTrendChart } from './FlawTrendChart';
import { FlawComparisonGrid } from './FlawComparisonGrid';
import type { FlawStatsResponse } from '@/types/library';
import type { FilterState } from '@/components/filters/FilterPanel';
import type { FlawFilterState } from '@/hooks/useFlawFilterStore';

// ─── Denominator pill ─────────────────────────────────────────────────────────

/** Popover copy explaining why only a subset of games is analyzed. */
const ANALYSIS_COVERAGE_COPY =
  'Full game Stockfish analysis is currently available only for games imported from Lichess that already have computer analysis enabled. Native full game analysis on FlawChess is coming soon.';

interface FlawDenominatorPillProps {
  /** Games with engine analysis in the current filter (the "x" in "x of y"). */
  analyzedN: number;
  /** Total games in the current filter (the "y" in "x of y"). */
  totalN: number;
}

/**
 * Analyzed-coverage pill ("🖥 124 of 400 Games"). Rendered by the page beside
 * the "Flaw Statistics" section heading (Phase 115 UAT — the panel no longer
 * owns its own header row). The info popover explains why coverage is partial
 * (Stockfish analysis is currently Lichess-only).
 */
export function FlawDenominatorPill({ analyzedN, totalN }: FlawDenominatorPillProps) {
  return (
    <div
      className="ml-auto inline-flex items-center gap-1.5 rounded-full border border-border px-3 py-1 text-sm font-bold shrink-0"
      style={{ background: 'oklch(1 0 0 / 4%)' }}
      data-testid="flaw-stats-denominator"
    >
      <Cpu className="h-4 w-4 shrink-0 text-amber-700" aria-hidden="true" />
      <span style={{ color: 'var(--brand-brown-highlight)', fontWeight: 700 }}>{analyzedN}</span>
      <span className="text-muted-foreground">of</span>
      <span style={{ color: 'var(--brand-brown-highlight)', fontWeight: 700 }}>{totalN}</span>
      <span className="text-muted-foreground">Games</span>
      <InfoPopover ariaLabel="About game analysis coverage" testId="flaw-stats-denominator-info">
        {ANALYSIS_COVERAGE_COPY}
      </InfoPopover>
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
