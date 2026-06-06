import {
  SEV_BLUNDER,
  SEV_MISTAKE,
  SEV_INACCURACY,
  FAM_IMPACT,
} from '@/lib/theme';
import type { SeverityRates } from '@/types/library';

// ─── Helpers ─────────────────────────────────────────────────────────────────

/** Format a rate as a percentage string (e.g. 0.31 → "31%"). */
function formatPct(rate: number): string {
  return `${Math.round(rate * 100)}%`;
}

/** Format a per-game or per-100 rate to 2 decimal places. */
function formatRate(rate: number): string {
  return rate.toFixed(2);
}

// ─── Cell definitions ─────────────────────────────────────────────────────────

type NormalizationMode = 'per_game' | 'per_100_moves';

interface SeverityCellConfig {
  testId: string;
  color: string;
  /** Label base — suffix "/ game" or "/ 100 moves" appended for severity cells. */
  labelBase: string;
  /** Whether this cell respects the normalization toggle. */
  responsive: boolean;
}

const SEVERITY_CELLS: SeverityCellConfig[] = [
  {
    testId: 'stat-cell-blunders',
    color: SEV_BLUNDER,
    labelBase: 'Blunders',
    responsive: true,
  },
  {
    testId: 'stat-cell-mistakes',
    color: SEV_MISTAKE,
    labelBase: 'Mistakes',
    responsive: true,
  },
  {
    testId: 'stat-cell-inaccuracies',
    color: SEV_INACCURACY,
    labelBase: 'Inaccuracies',
    responsive: true,
  },
];

// ─── Props ───────────────────────────────────────────────────────────────────

interface FlawStatsBandProps {
  /** Severity rates (both per_game and per_100_moves are present). */
  rates: SeverityRates;
  /** Result-changing rate as a fraction (0–1). Not affected by normalization toggle. */
  result_changing_rate: number;
  /** Which normalization to display for B/M/I cells. */
  normalization: NormalizationMode;
  /** When true, all cells show "—" (zero analyzed games in the current filter). */
  analyzedEmpty: boolean;
}

// ─── Component ───────────────────────────────────────────────────────────────

/**
 * Zone 1: four severity-rate cells for the Flaw-Stats panel (UI-SPEC §Zone 1).
 *
 * Blunders / Mistakes / Inaccuracies cells display the per-game or per-100-moves
 * value driven by the `normalization` prop (no re-fetch — both values come from
 * the same FlawStatsResponse). The Result-changing cell always shows the fraction
 * as a percentage and is unaffected by the toggle.
 *
 * Colors imported from theme.ts: SEV_BLUNDER / SEV_MISTAKE / SEV_INACCURACY /
 * FAM_IMPACT. No hard-coded oklch values in this component.
 */
export function FlawStatsBand({
  rates,
  result_changing_rate,
  normalization,
  analyzedEmpty,
}: FlawStatsBandProps) {
  const normDict = rates[normalization];
  const suffix = normalization === 'per_game' ? '/ game' : '/ 100 moves';

  return (
    <div
      className="flex flex-wrap gap-2 mt-3"
      data-testid="flaw-stats-band"
    >
      {/* B / M / I cells — responsive to normalization toggle */}
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

      {/* Result-changing cell — always percentage, unaffected by toggle */}
      <div
        className="flex-1 min-w-[120px] rounded border border-border p-3"
        style={{ background: 'var(--color-charcoal)' }}
        data-testid="stat-cell-result-changing"
      >
        <p className="text-2xl font-bold" style={{ color: FAM_IMPACT }}>
          {analyzedEmpty ? '—' : formatPct(result_changing_rate)}
        </p>
        <p className="text-sm font-bold uppercase text-muted-foreground">
          Result-changing
        </p>
      </div>
    </div>
  );
}
