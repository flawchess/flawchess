import type { ReactNode } from 'react';
import {
  PERCENTILE_MEDIAN_TICK,
  PERCENTILE_TRACK,
  PERCENTILE_TYPICAL_BAND,
} from '@/lib/theme';
import {
  GAP_CENTRE,
  GAP_SAME_WORD,
  bandRange,
  cellPosition,
  effectiveVerdict,
  gapVerdictColor,
  gapWords,
  type GapCell,
} from '@/lib/gapBar';
import { cn } from '@/lib/utils';

const COPY_NO_FLAWS = 'No flaws yet';

interface GapBarProps {
  cell: GapCell;
  testId: string;
  /** The popover trigger, rendered after the words. Omit for a gap-less cell. */
  trailing?: ReactNode;
  /**
   * 'inline' puts the words right of the track; 'stacked' puts them above it, top left on
   * desktop and top right on phones (the Most common tactics table).
   */
  layout?: GapBarLayout;
  /** Stacked only: a phone-only label on the words line, left of the right-aligned words. */
  mobileLabel?: ReactNode;
}

type GapBarLayout = 'inline' | 'stacked';

/**
 * The one visual of the Library Stats tab (D-00a): a zero-centred track with the
 * benchmark band (symmetric around 0, D-15), a zero tick, and a dot. Lower (fewer flaws,
 * better) is to the left (D-14). The gap reads in words next to or above the bar (D-00b): green or
 * red for a significant better or worse, plain foreground for typical or a gap that could
 * be chance (D-14). A zoneless cell draws no band (D-11) and is coloured only when its gap
 * is significant (D-16).
 */
export function GapBar({ cell, testId, trailing, layout = 'inline', mobileLabel }: GapBarProps) {
  if (cell.delta === null) {
    return (
      <p className="text-sm text-muted-foreground" data-testid={`${testId}-empty`}>
        {COPY_NO_FLAWS}
      </p>
    );
  }

  const verdict = effectiveVerdict(cell);
  const color = gapVerdictColor(verdict);
  const band = bandRange(cell);
  const words = gapWords(cell.delta);
  const colored = verdict === 'better' || verdict === 'worse';
  // IN-03: "same flaws than your opponents" was ungrammatical; "same" takes "as".
  const ariaLabel =
    words === GAP_SAME_WORD
      ? `${words} flaws as your opponents`
      : `${words} flaws than your opponents`;

  const stacked = layout === 'stacked';
  const wordsEl = (
    <span
      className={cn(
        'whitespace-nowrap text-sm font-semibold tabular-nums',
        stacked ? 'ml-auto md:ml-0' : 'min-w-24 text-right',
        !colored && 'text-foreground',
      )}
      style={colored ? { color } : undefined}
      data-testid={`${testId}-words`}
    >
      {words}
    </span>
  );
  const track = (
    <div
      className="relative h-2.5 flex-1 rounded-full"
      style={{ backgroundColor: PERCENTILE_TRACK }}
      role="img"
      aria-label={ariaLabel}
      data-testid={`${testId}-track`}
    >
      {band && (
        <div
          className="absolute inset-y-0 rounded-sm"
          style={{
            left: `${band.leftPct}%`,
            width: `${band.widthPct}%`,
            backgroundColor: PERCENTILE_TYPICAL_BAND,
          }}
          data-testid={`${testId}-band`}
        />
      )}
      <div
        className="absolute -inset-y-[3px] w-px"
        style={{ left: `${GAP_CENTRE}%`, backgroundColor: PERCENTILE_MEDIAN_TICK }}
        data-testid={`${testId}-zero`}
      />
      <div
        className="absolute top-1/2 size-4 -translate-x-1/2 -translate-y-1/2 rounded-full border-2 border-background"
        style={{ left: `${cellPosition(cell)}%`, backgroundColor: color }}
        data-testid={`${testId}-dot`}
      />
    </div>
  );

  if (stacked) {
    return (
      <div className="flex flex-col gap-2" data-testid={testId}>
        <div className="flex items-center gap-2">
          {mobileLabel && <div className="md:hidden">{mobileLabel}</div>}
          {wordsEl}
          {trailing}
        </div>
        <div className="flex">{track}</div>
      </div>
    );
  }

  return (
    <div className="flex items-center gap-3" data-testid={testId}>
      {track}
      {wordsEl}
      {trailing}
    </div>
  );
}

interface GapGateSlotProps {
  analyzedN: number;
  gate: number;
  testId: string;
}

/** The muted line standing in for the bars when a TC has fewer analyzed games than the gate (D-03). */
export function GapGateSlot({ analyzedN, gate, testId }: GapGateSlotProps) {
  return (
    <p className="text-sm text-muted-foreground" data-testid={testId}>
      Not enough analyzed games yet ({analyzedN} of {gate})
    </p>
  );
}
