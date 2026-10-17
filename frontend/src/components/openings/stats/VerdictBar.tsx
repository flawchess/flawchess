import type { ReactNode } from 'react';
import {
  PERCENTILE_MEDIAN_TICK,
  PERCENTILE_TRACK,
  PERCENTILE_TYPICAL_BAND,
  SIDE_SWATCH_BLACK,
  SIDE_SWATCH_WHITE,
  VERDICT_ZERO_TICK,
} from '@/lib/theme';
import { GAP_CENTRE, gapVerdictColor, type GapVerdict } from '@/lib/gapBar';
import { verdictBandRange, verdictPosition } from '@/lib/openingVerdict';
import { cn } from '@/lib/utils';

interface VerdictBarProps {
  /** value minus the track centre (eval: minus the colour baseline; score: minus 50%). Higher is right. */
  delta: number;
  /** Half-width of the typical band, same unit as delta. */
  band: number;
  verdict: GapVerdict;
  /** The raw value as text, shown right of the words row. */
  valueText: string;
  testId: string;
  ariaLabel: string;
  /** Draws a faint dashed tick (eval: the 0 = equal position, i.e. minus the baseline). */
  zeroTickDelta?: number;
  /** Draws a small white/black square on the centre tick: "an average White/Black game". */
  centreSwatch?: 'white' | 'black';
  /** Top-left slot on the words row. */
  leading?: ReactNode;
  /** After the value text, typically the info popover trigger. */
  trailing?: ReactNode;
}

const SWATCH_COLOR = { white: SIDE_SWATCH_WHITE, black: SIDE_SWATCH_BLACK } as const;

/**
 * The Openings verdict visual: a track centred on the reference (the colour's average eval, or
 * 50% score), a grey typical band, and one dot. Higher is better, so better sits to the RIGHT
 * (the opposite of the Library GapBar). Green or red only when the verdict is better or worse;
 * the value text takes the same colour then, plain foreground otherwise.
 */
export function VerdictBar({
  delta,
  band,
  verdict,
  valueText,
  testId,
  ariaLabel,
  zeroTickDelta,
  centreSwatch,
  leading,
  trailing,
}: VerdictBarProps) {
  const color = gapVerdictColor(verdict);
  const coloured = verdict === 'better' || verdict === 'worse';
  const bandRange = verdictBandRange(band);

  return (
    <div className="space-y-1.5" data-testid={testId}>
      <div className="flex items-center justify-between gap-2 text-sm">
        <div className="min-w-0">{leading}</div>
        <div className="flex shrink-0 items-center gap-1">
          <span
            className={cn('whitespace-nowrap font-semibold tabular-nums', !coloured && 'text-foreground')}
            style={coloured ? { color } : undefined}
            data-testid={`${testId}-value`}
          >
            {valueText}
          </span>
          {trailing}
        </div>
      </div>
      <div
        className="relative h-2.5 rounded-full"
        style={{ backgroundColor: PERCENTILE_TRACK }}
        role="img"
        aria-label={ariaLabel}
        data-testid={`${testId}-track`}
      >
        <div
          className="absolute inset-y-0 rounded-sm"
          style={{
            left: `${bandRange.leftPct}%`,
            width: `${bandRange.widthPct}%`,
            backgroundColor: PERCENTILE_TYPICAL_BAND,
          }}
          data-testid={`${testId}-band`}
        />
        {zeroTickDelta !== undefined && (
          <div
            className="absolute -inset-y-[3px] w-0 border-l border-dashed"
            style={{
              left: `${verdictPosition(zeroTickDelta, band)}%`,
              borderColor: VERDICT_ZERO_TICK,
            }}
            data-testid={`${testId}-zero`}
          />
        )}
        <div
          className="absolute -inset-y-[3px] w-px"
          style={{ left: `${GAP_CENTRE}%`, backgroundColor: PERCENTILE_MEDIAN_TICK }}
          data-testid={`${testId}-centre`}
        />
        {centreSwatch && (
          <div
            className="absolute top-1/2 size-2 -translate-x-1/2 -translate-y-1/2 rounded-[2px] border border-foreground/40"
            style={{ left: `${GAP_CENTRE}%`, backgroundColor: SWATCH_COLOR[centreSwatch] }}
            data-testid={`${testId}-swatch`}
          />
        )}
        <div
          className="absolute top-1/2 size-4 -translate-x-1/2 -translate-y-1/2 rounded-full border-2 border-background"
          style={{ left: `${verdictPosition(delta, band)}%`, backgroundColor: color }}
          data-testid={`${testId}-dot`}
        />
      </div>
    </div>
  );
}

interface VerdictCompactProps {
  verdict: GapVerdict;
  /** The raw value as text ("56%", "+0.9"). */
  valueText: string;
  testId: string;
  /** After the value, typically the info popover trigger. */
  trailing?: ReactNode;
}

/**
 * The repertoire table's compact cell: a verdict dot, the value and the popover trigger on one
 * line. The full bar lives in the expanded row; here the dot colour carries the verdict and the
 * value is coloured only when it is a clear better / worse call.
 */
export function VerdictCompact({ verdict, valueText, testId, trailing }: VerdictCompactProps) {
  const color = gapVerdictColor(verdict);
  const coloured = verdict === 'better' || verdict === 'worse';
  return (
    <span className="inline-flex items-center gap-1.5 whitespace-nowrap" data-testid={testId}>
      <span
        className="size-2.5 shrink-0 rounded-full"
        style={{ backgroundColor: color }}
        data-testid={`${testId}-dot`}
      />
      <span
        className={cn('font-semibold tabular-nums', !coloured && 'text-foreground')}
        style={coloured ? { color } : undefined}
        data-testid={`${testId}-value`}
      >
        {valueText}
      </span>
      {trailing}
    </span>
  );
}
