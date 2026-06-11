import {
  SEV_BLUNDER,
  SEV_MISTAKE,
  SEV_INACCURACY,
} from '@/lib/theme';
import type { SeverityRates } from '@/types/library';

// ─── Helpers ─────────────────────────────────────────────────────────────────

/** Format a per-100 rate to 2 decimal places. */
function formatRate(rate: number): string {
  return rate.toFixed(2);
}

// ─── Cell definitions ─────────────────────────────────────────────────────────

interface SeverityCellConfig {
  testId: string;
  color: string;
  /** Label base — "/ 100 moves" suffix appended. */
  labelBase: string;
}

const SEVERITY_CELLS: SeverityCellConfig[] = [
  {
    testId: 'stat-cell-blunders',
    color: SEV_BLUNDER,
    labelBase: 'Blunders',
  },
  {
    testId: 'stat-cell-mistakes',
    color: SEV_MISTAKE,
    labelBase: 'Mistakes',
  },
  {
    testId: 'stat-cell-inaccuracies',
    color: SEV_INACCURACY,
    labelBase: 'Inaccuracies',
  },
];

// ─── Props ───────────────────────────────────────────────────────────────────

interface FlawStatsBandProps {
  /** Severity rates (both per_game and per_100_moves are present). */
  rates: SeverityRates;
  /** When true, all cells show "—" (zero analyzed games in the current filter). */
  analyzedEmpty: boolean;
}

// ─── Component ───────────────────────────────────────────────────────────────

/**
 * Zone 1: three severity-rate cells for the Flaw-Stats panel (UI-SPEC §Zone 1).
 *
 * Fixed to per-100-moves (D-02, Phase 115): the normalization toggle was removed.
 * Displays per_100_moves rates only; the "/ 100 moves" suffix is hardcoded.
 *
 * Colors imported from theme.ts: SEV_BLUNDER / SEV_MISTAKE / SEV_INACCURACY.
 * No hard-coded oklch values in this component.
 */
export function FlawStatsBand({
  rates,
  analyzedEmpty,
}: FlawStatsBandProps) {
  const normDict = rates.per_100_moves;
  const suffix = '/ 100 moves';

  return (
    <div
      className="flex flex-wrap gap-2 mt-3"
      data-testid="flaw-stats-band"
    >
      {/* B / M / I cells — per-100-moves (fixed, D-02) */}
      {SEVERITY_CELLS.map((cell) => {
        const severityKey = cell.testId === 'stat-cell-blunders'
          ? 'blunder'
          : cell.testId === 'stat-cell-mistakes'
          ? 'mistake'
          : 'inaccuracy';
        const rawRate = normDict[severityKey];
        const displayValue = analyzedEmpty || rawRate === undefined
          ? '—'
          : formatRate(rawRate);

        return (
          <div
            key={cell.testId}
            className="flex-1 min-w-[120px] rounded border border-border p-3"
            style={{ background: 'var(--color-charcoal)' }}
            data-testid={cell.testId}
          >
            <p className="text-2xl font-bold" style={{ color: cell.color }}>
              {displayValue}
            </p>
            <p className="text-sm font-bold uppercase text-muted-foreground">
              {cell.labelBase} {suffix}
            </p>
          </div>
        );
      })}

    </div>
  );
}
