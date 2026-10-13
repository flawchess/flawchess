import { cn } from '@/lib/utils';
import {
  GAUGE_NEUTRAL,
  PERCENTILE_MEDIAN_TICK,
  PERCENTILE_TRACK,
  PERCENTILE_TYPICAL_BAND,
} from '@/lib/theme';
import type { RankStatus } from '@/types/endgames';
import {
  PERCENTILE_MEDIAN,
  PERCENTILE_TYPICAL_HIGH,
  PERCENTILE_TYPICAL_LOW,
  displayPercentile,
  formatOrdinal,
  percentileBandColor,
} from './rankedMetrics';

const COPY_PENDING = 'Analyzing your games, this fills in once evaluations finish';
const COPY_UNRANKED = 'Not ranked yet';

/** The slot copy for a cell without a percentile; null for a ranked cell. */
function rankStatusText(
  status: RankStatus,
  floorN: number,
  floorRequired: number,
): string | null {
  switch (status) {
    case 'below_floor':
      return `Not enough games to rank yet (${floorN} of ${floorRequired})`;
    case 'pending':
      return COPY_PENDING;
    case 'unranked':
      return COPY_UNRANKED;
    case 'ranked':
      return null;
  }
}

interface RankStatusLineProps {
  status: RankStatus;
  floorN: number;
  floorRequired: number;
  testId?: string;
  className?: string;
}

/**
 * The muted line that stands in for the percentile bar when a cell has no
 * percentile (D-09 below floor, D-11 pending / not ranked yet). No dot, no
 * drift or "updating" state (D-08). Renders nothing for a ranked cell.
 */
export function RankStatusLine({
  status,
  floorN,
  floorRequired,
  testId,
  className,
}: RankStatusLineProps) {
  const text = rankStatusText(status, floorN, floorRequired);
  if (text === null) return null;
  return (
    <p className={cn('text-sm text-muted-foreground', className)} data-testid={testId}>
      {text}
    </p>
  );
}

interface PercentileBarProps {
  status: RankStatus;
  /** Set only when status === 'ranked'. */
  percentile: number | null;
  /** Binding count and floor, shown in the below-floor slot ("18 of 30"). */
  floorN: number;
  floorRequired: number;
  /** 99% significance of the value vs its null (D-14); red/green needs it. */
  significant: boolean;
  testId: string;
}

/**
 * One 0-100 percentile axis (D-00a): the 25-75 band shaded, a median tick at 50
 * and a dot at the peer percentile, colored red below 25, blue 25-75, green above
 * 75, but only when the value is significant (Phase 239 D-14); otherwise blue. The
 * ordinal on the right shares the dot's color. The metric value itself is rendered
 * elsewhere, uncolored; the dot is the only verdict and carries no icon. Cells
 * without a percentile show their status line in the same slot instead.
 */
export function PercentileBar({
  status,
  percentile,
  floorN,
  floorRequired,
  significant,
  testId,
}: PercentileBarProps) {
  if (status !== 'ranked') {
    return (
      <RankStatusLine
        status={status}
        floorN={floorN}
        floorRequired={floorRequired}
        testId={testId}
      />
    );
  }
  if (percentile === null) return null;

  const shown = displayPercentile(percentile);
  const bandColor = significant ? percentileBandColor(shown) : GAUGE_NEUTRAL;
  return (
    <div className="flex items-center gap-3" data-testid={testId}>
      <div
        className="relative h-2.5 flex-1 rounded-full"
        style={{ backgroundColor: PERCENTILE_TRACK }}
        data-testid={`${testId}-track`}
      >
        <div
          className="absolute inset-y-0 rounded-sm"
          style={{
            left: `${PERCENTILE_TYPICAL_LOW}%`,
            width: `${PERCENTILE_TYPICAL_HIGH - PERCENTILE_TYPICAL_LOW}%`,
            backgroundColor: PERCENTILE_TYPICAL_BAND,
          }}
          data-testid={`${testId}-band`}
        />
        <div
          className="absolute -inset-y-[3px] w-px"
          style={{ left: `${PERCENTILE_MEDIAN}%`, backgroundColor: PERCENTILE_MEDIAN_TICK }}
          data-testid={`${testId}-median`}
        />
        <div
          className="absolute top-1/2 size-4 -translate-x-1/2 -translate-y-1/2 rounded-full border-2 border-background"
          style={{ left: `${shown}%`, backgroundColor: bandColor }}
          data-testid={`${testId}-dot`}
        />
      </div>
      <span
        className="min-w-11 text-right text-sm font-semibold tabular-nums"
        style={{ color: bandColor }}
        data-testid={`${testId}-number`}
      >
        {formatOrdinal(shown)}
      </span>
    </div>
  );
}
