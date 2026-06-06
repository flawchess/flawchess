import {
  FAM_TEMPO_LOW_CLOCK,
  FAM_TEMPO_IMPATIENT,
  FAM_TEMPO_CONSIDERED,
  FAM_TEMPO_UNMEASURED,
  FAM_OPPORTUNITY,
  FAM_IMPACT,
  PHASE_OPENING,
  PHASE_MIDDLEGAME,
  PHASE_ENDGAME,
} from '@/lib/theme';
import type { TagDistribution } from '@/types/library';

// ─── Helpers ─────────────────────────────────────────────────────────────────

/** Format a rate fraction as a percentage string (e.g. 0.31 → "31%"). */
function formatPct(rate: number): string {
  return `${Math.round(rate * 100)}%`;
}

// ─── Sub-components ───────────────────────────────────────────────────────────

interface RateBarRowProps {
  label: string;
  rate: number;
  fill: string;
}

/**
 * Single label | track | value row used in the sub-columns.
 * Track is 8px tall; fill is sized to `rate * 100`%.
 * Guard: rate is clamped to [0, 1] so zero totalMbFlaws yields 0%-width bars.
 */
function RateBarRow({ label, rate, fill }: RateBarRowProps) {
  const pct = Math.min(1, Math.max(0, rate));

  return (
    <div className="grid grid-cols-[auto_1fr_auto] items-center gap-2">
      <span className="text-sm text-muted-foreground font-bold whitespace-nowrap">{label}</span>
      <div
        className="h-2 rounded-full overflow-hidden"
        style={{ background: 'oklch(1 0 0 / 7%)' }}
      >
        <div
          className="h-2 rounded-full"
          style={{ width: `${pct * 100}%`, background: fill }}
        />
      </div>
      <span className="text-sm font-bold">{formatPct(pct)}</span>
    </div>
  );
}

interface SubColumnProps {
  heading: string;
  testId: string;
  children: React.ReactNode;
}

function SubColumn({ heading, testId, children }: SubColumnProps) {
  return (
    <div className="flex flex-col gap-2" data-testid={testId}>
      <p className="text-sm font-bold text-muted-foreground">{heading}</p>
      {children}
    </div>
  );
}

// ─── Tempo stacked bar ────────────────────────────────────────────────────────

interface TempoSegment {
  key: string;
  label: string;
  count: number;
  color: string;
}

interface TempoStackedBarProps {
  tagDistribution: TagDistribution;
  totalMbFlaws: number;
}

function TempoStackedBar({ tagDistribution, totalMbFlaws }: TempoStackedBarProps) {
  const { tempo } = tagDistribution;

  const lowClockCount = tempo['low-clock'] ?? 0;
  const impatientCount = tempo['impatient'] ?? 0;
  const consideredCount = tempo['considered'] ?? 0;
  const measuredSum = lowClockCount + impatientCount + consideredCount;
  const unmeasuredCount = Math.max(0, totalMbFlaws - measuredSum);

  const segments: TempoSegment[] = [
    { key: 'low-clock', label: 'Low-clock', count: lowClockCount, color: FAM_TEMPO_LOW_CLOCK },
    { key: 'impatient', label: 'Impatient', count: impatientCount, color: FAM_TEMPO_IMPATIENT },
    { key: 'considered', label: 'Considered', count: consideredCount, color: FAM_TEMPO_CONSIDERED },
  ];

  // Include unmeasured segment only when non-zero (per UI-SPEC).
  if (unmeasuredCount > 0) {
    segments.push({ key: 'unmeasured', label: 'Unmeasured', count: unmeasuredCount, color: FAM_TEMPO_UNMEASURED });
  }

  // Guard against zero total — render 0%-width segments.
  const safeTotal = totalMbFlaws > 0 ? totalMbFlaws : 1;

  return (
    <div className="mt-2">
      <p className="text-sm font-bold mb-2">Tempo split of mistakes + blunders</p>
      {/* Stacked bar */}
      <div
        className="flex h-[14px] rounded-full overflow-hidden w-full"
        data-testid="tempo-stacked-bar"
      >
        {segments.map((seg) => (
          <div
            key={seg.key}
            style={{
              width: `${(seg.count / safeTotal) * 100}%`,
              background: seg.color,
              flexShrink: 0,
            }}
          />
        ))}
      </div>
      {/* Legend */}
      <div className="flex flex-wrap gap-x-4 gap-y-1 mt-2">
        {segments.map((seg) => (
          <span key={seg.key} className="inline-flex items-center gap-1.5 text-sm text-muted-foreground">
            <span
              className="inline-block h-2 w-2 rounded-full shrink-0"
              style={{ background: seg.color }}
              aria-hidden="true"
            />
            {seg.label} {formatPct(seg.count / safeTotal)}
          </span>
        ))}
      </div>
    </div>
  );
}

// ─── Props ───────────────────────────────────────────────────────────────────

interface FlawTagDistributionProps {
  tagDistribution: TagDistribution;
  /**
   * Total mistake + blunder flaw count for the analyzed set.
   * Used to size the tempo stacked bar's unmeasured remainder.
   * When 0, all bar widths are 0% (no division error).
   */
  totalMbFlaws: number;
  /** When true (no analyzed games), show a placeholder message instead of bar rows. */
  analyzedEmpty: boolean;
}

// ─── Component ───────────────────────────────────────────────────────────────

/**
 * Zone 3: tag distribution block (UI-SPEC §Zone 3).
 *
 * Renders three sections:
 * 1. Tempo stacked bar (low-clock / impatient / considered + unmeasured remainder)
 *    — segments are NOT normalized to 100%; the unmeasured gap is honest.
 * 2. Three sub-columns (By phase / Opportunity / Impact) in a responsive grid.
 *
 * Opportunity and Impact columns read directly from the D-01 flat rate fields
 * on TagDistribution (miss_rate / lucky_escape_rate / while_ahead_rate /
 * result_changing_rate) — no client-side chip derivation, no placeholders (D-03).
 *
 * All colors from theme.ts: FAM_TEMPO_*, FAM_OPPORTUNITY, FAM_IMPACT, PHASE_*.
 * Zero-flaw guard: totalMbFlaws === 0 yields 0%-width bars; no division occurs.
 */
export function FlawTagDistribution({
  tagDistribution,
  totalMbFlaws,
  analyzedEmpty,
}: FlawTagDistributionProps) {
  const { phase_histogram, miss_rate, lucky_escape_rate, while_ahead_rate, result_changing_rate } =
    tagDistribution;

  // Safe total for phase histogram (counts in all phases).
  const phaseTotal = (phase_histogram['opening'] ?? 0)
    + (phase_histogram['middlegame'] ?? 0)
    + (phase_histogram['endgame'] ?? 0);
  const safePhaseTotal = phaseTotal > 0 ? phaseTotal : 1;

  return (
    <div
      className="rounded border border-border p-4 mt-4"
      style={{ background: 'var(--color-charcoal)' }}
      data-testid="tag-distribution-block"
    >
      <p className="text-sm font-bold">Tag distribution</p>

      {analyzedEmpty ? (
        <p className="text-sm text-muted-foreground mt-3">
          No analyzed games in the current filter
        </p>
      ) : (
        <>
          {/* Tempo stacked bar */}
          <TempoStackedBar tagDistribution={tagDistribution} totalMbFlaws={totalMbFlaws} />

          {/* Three sub-columns */}
          {/* Desktop: 3-column grid; mobile: stacked flex */}
          <div className="flex flex-col gap-3 mt-3 sm:grid sm:grid-cols-3 sm:gap-2">
            {/* 1. By phase histogram */}
            <SubColumn heading="By phase" testId="phase-histogram">
              <RateBarRow
                label="Opening"
                rate={(phase_histogram['opening'] ?? 0) / safePhaseTotal}
                fill={PHASE_OPENING}
              />
              <RateBarRow
                label="Middlegame"
                rate={(phase_histogram['middlegame'] ?? 0) / safePhaseTotal}
                fill={PHASE_MIDDLEGAME}
              />
              <RateBarRow
                label="Endgame"
                rate={(phase_histogram['endgame'] ?? 0) / safePhaseTotal}
                fill={PHASE_ENDGAME}
              />
            </SubColumn>

            {/* 2. Opportunity rates — D-01 flat fields (D-03, no placeholders) */}
            <SubColumn heading="Opportunity" testId="opportunity-rates">
              <RateBarRow label="Miss" rate={miss_rate} fill={FAM_OPPORTUNITY} />
              <RateBarRow label="Lucky-escape" rate={lucky_escape_rate} fill={FAM_OPPORTUNITY} />
            </SubColumn>

            {/* 3. Impact rates — D-01 flat fields (D-03, no placeholders) */}
            <SubColumn heading="Impact" testId="impact-rates">
              <RateBarRow label="While-ahead" rate={while_ahead_rate} fill={FAM_IMPACT} />
              <RateBarRow label="Result-changing" rate={result_changing_rate} fill={FAM_IMPACT} />
            </SubColumn>
          </div>
        </>
      )}
    </div>
  );
}
