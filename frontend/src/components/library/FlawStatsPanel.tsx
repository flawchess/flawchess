import { useState } from 'react';
import { FlawStatsBand } from './FlawStatsBand';
import { FlawTrendChart } from './FlawTrendChart';
import { FlawTagDistribution } from './FlawTagDistribution';
import type { FlawStatsResponse } from '@/types/library';

// ─── Helpers ─────────────────────────────────────────────────────────────────

/** Round a percentage fraction to a whole number string (e.g. 0.312 → "31"). */
function formatAnalyzedPct(pct: number): string {
  return String(Math.round(pct));
}

// ─── Normalization toggle ─────────────────────────────────────────────────────

type NormalizationMode = 'per_game' | 'per_100_moves';

interface NormToggleProps {
  value: NormalizationMode;
  onChange: (v: NormalizationMode) => void;
}

function NormToggle({ value, onChange }: NormToggleProps) {
  return (
    <div
      className="inline-flex items-center rounded-full border border-border text-sm font-bold overflow-hidden shrink-0"
      data-testid="flaw-stats-norm-toggle"
    >
      <button
        type="button"
        className="px-3 py-1 transition-colors"
        style={
          value === 'per_game'
            ? { background: 'var(--brand-brown)', color: '#fff' }
            : { background: 'transparent', color: 'var(--color-text-muted)' }
        }
        aria-pressed={value === 'per_game'}
        data-testid="flaw-stats-toggle-game"
        onClick={() => onChange('per_game')}
      >
        per game
      </button>
      <button
        type="button"
        className="px-3 py-1 transition-colors"
        style={
          value === 'per_100_moves'
            ? { background: 'var(--brand-brown)', color: '#fff' }
            : { background: 'transparent', color: 'var(--color-text-muted)' }
        }
        aria-pressed={value === 'per_100_moves'}
        data-testid="flaw-stats-toggle-100"
        onClick={() => onChange('per_100_moves')}
      >
        per 100 moves
      </button>
    </div>
  );
}

// ─── Denominator pill ─────────────────────────────────────────────────────────

interface DenominatorPillProps {
  analyzedPct: number;
  analyzedN: number;
}

function DenominatorPill({ analyzedPct, analyzedN }: DenominatorPillProps) {
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
}

// ─── Component ───────────────────────────────────────────────────────────────

/**
 * Flaw-Stats panel shell (UI-SPEC §"Flaw-Stats Panel" and PATTERNS.md §FlawStatsPanel).
 *
 * Composes FlawStatsBand (Zone 1) + FlawTrendChart (Zone 2) + FlawTagDistribution
 * (Zone 3). The per-game/per-100 normalization toggle is local state — it drives only
 * FlawStatsBand with no re-fetch.
 *
 * States:
 * - isError: shows CLAUDE.md-mandated error copy (never falls through to empty state).
 * - isLoading: lightweight skeleton placeholder.
 * - analyzed_n === 0: empty-analyzed-set state per UI-SPEC.
 * - Normal: full panel content.
 *
 * Data-fetching (useLibraryFlawStats) lives in GlobalStats (Stats tab, quick-260606-glq).
 */
export function FlawStatsPanel({ stats, isLoading, isError }: FlawStatsPanelProps) {
  const [normalization, setNormalization] = useState<NormalizationMode>('per_game');

  return (
    <section
      className="border border-border rounded-lg p-4"
      style={{ background: 'var(--color-surface)' }}
      aria-label="Flaw statistics"
      data-testid="flaw-stats-panel"
    >
      {/* Panel header row */}
      <div className="flex flex-wrap items-center gap-3">
        <h2 className="text-lg font-bold font-brand">Flaw-Stats</h2>
        <NormToggle value={normalization} onChange={setNormalization} />
        {stats !== undefined && (
          <DenominatorPill
            analyzedPct={stats.analyzed_pct}
            analyzedN={stats.analyzed_n}
          />
        )}
      </div>

      {/* Error state — mandatory CLAUDE.md isError copy */}
      {isError && (
        <p className="text-sm text-muted-foreground mt-4">
          Failed to load flaw statistics. Something went wrong. Please try again in a moment.
        </p>
      )}

      {/* Loading state */}
      {!isError && isLoading && (
        <div className="mt-4 space-y-3 animate-pulse">
          <div className="flex gap-2">
            {[...Array(4)].map((_, i) => (
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

        // Compute totalMbFlaws from per_severity_counts (M+B only, not inaccuracy).
        const totalMbFlaws = stats.per_severity_counts.mistake + stats.per_severity_counts.blunder;

        // Window size from first trend point (all points share the same window_size).
        const firstPoint = stats.trend[0];
        const windowSize = firstPoint !== undefined ? firstPoint.window_size : 20;

        return (
          <>
            {/* Zone 1: Severity-rate band */}
            <FlawStatsBand
              rates={stats.rates}
              result_changing_rate={stats.tag_distribution.result_changing_rate}
              normalization={normalization}
              analyzedEmpty={analyzedEmpty}
            />

            {/* Zone 2: Blunders/game trend */}
            <FlawTrendChart
              trend={analyzedEmpty ? [] : stats.trend}
              windowSize={windowSize}
            />

            {/* Zone 3: Tag distribution */}
            <FlawTagDistribution
              tagDistribution={stats.tag_distribution}
              totalMbFlaws={totalMbFlaws}
              analyzedEmpty={analyzedEmpty}
            />
          </>
        );
      })()}
    </section>
  );
}
