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
import { verdictBandRange, verdictPosition, verdictValueColor } from '@/lib/openingVerdict';
import { cn } from '@/lib/utils';

interface VerdictTrackProps {
  /** value minus the track centre (eval: minus the colour baseline; score: minus 50%). Higher is right. */
  delta: number;
  /** Half-width of the typical band, same unit as delta. */
  band: number;
  verdict: GapVerdict;
  /** Prefix of the track testids: `${testId}-track`, `-band`, `-zero`, `-centre`, `-swatch`, `-dot`. */
  testId: string;
  ariaLabel: string;
  /** Draws a faint dashed tick (eval: the 0 = equal position, i.e. minus the baseline). */
  zeroTickDelta?: number;
  /** Draws a small white/black square on the centre tick: "an average White/Black game". */
  centreSwatch?: 'white' | 'black';
}

interface VerdictBarProps extends VerdictTrackProps {
  /** The raw value as text, shown right of the words row. */
  valueText: string;
  /** Top-left slot on the words row. */
  leading?: ReactNode;
  /** After the value text, typically the info popover trigger. */
  trailing?: ReactNode;
}

const SWATCH_COLOR = { white: SIDE_SWATCH_WHITE, black: SIDE_SWATCH_BLACK } as const;

/**
 * The bare verdict track: centred on the reference, a grey typical band and one dot, green or
 * red only when the verdict is better or worse. Used alone where the label and value sit in
 * a separate cell (the Moves / Games Results card).
 */
export function VerdictTrack({
  delta,
  band,
  verdict,
  testId,
  ariaLabel,
  zeroTickDelta,
  centreSwatch,
}: VerdictTrackProps) {
  const bandRange = verdictBandRange(band);
  return (
    <div
      className="relative h-2.5 rounded-full"
      style={{ backgroundColor: PERCENTILE_TRACK }}
      role="img"
      aria-label={ariaLabel}
      data-testid={`${testId}-track`}
      data-verdict={verdict}
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
        style={{ left: `${verdictPosition(delta, band)}%`, backgroundColor: gapVerdictColor(verdict) }}
        data-testid={`${testId}-dot`}
      />
    </div>
  );
}

/**
 * The Openings verdict visual: a words row (label, value, popover) over a VerdictTrack.
 * Higher is better, so better sits to the RIGHT (the opposite of the Library GapBar). The value
 * text takes the verdict colour when it is better or worse, plain foreground otherwise.
 */
export function VerdictBar({
  valueText,
  leading,
  trailing,
  ...track
}: VerdictBarProps) {
  const valueColor = verdictValueColor(track.verdict);
  return (
    <div className="space-y-1.5" data-testid={track.testId} data-verdict={track.verdict}>
      <div className="flex items-center justify-between gap-2 text-sm">
        <div className="min-w-0">{leading}</div>
        <div className="flex shrink-0 items-center gap-1">
          <span
            className={cn('whitespace-nowrap font-semibold tabular-nums', !valueColor && 'text-foreground')}
            style={valueColor ? { color: valueColor } : undefined}
            data-testid={`${track.testId}-value`}
          >
            {valueText}
          </span>
          {trailing}
        </div>
      </div>
      <VerdictTrack {...track} />
    </div>
  );
}
