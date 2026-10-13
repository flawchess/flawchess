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
   * Where the words sit (one DOM tree for every width, placed on a 3-column grid):
   * - 'responsive' (default): right of the track on phones; top right above a full-width
   *   track from md up, with `leading` top left on the same line.
   * - 'stacked': top right above a full-width track at every width, with `leading` top left
   *   (the Most common tactics table).
   */
  layout?: GapBarLayout;
  /**
   * The top-left slot on the words line (a row's label and hint, a side label). In the
   * responsive layout it spans the full width above the bar on phones.
   */
  leading?: ReactNode;
}

type GapBarLayout = 'responsive' | 'stacked';

interface LayoutClasses {
  root: string;
  leading: string;
  track: string;
  words: string;
  trailing: string;
}

const GRID_ROOT = 'grid grid-cols-[1fr_auto_auto] items-center';

// Explicit grid placement throughout: a leading slot hidden by its caller (display: none)
// must never let the words auto-flow into the 1fr column.
const LAYOUT_CLASSES = {
  responsive: {
    root: `${GRID_ROOT} gap-x-3 md:gap-x-2 md:gap-y-2`,
    leading: '',
    track: 'col-start-1 row-start-1 md:col-span-3 md:row-start-2',
    words: 'col-start-2 row-start-1 min-w-24 text-right md:min-w-0',
    trailing: 'col-start-3 row-start-1',
  },
  responsiveLeading: {
    root: `${GRID_ROOT} gap-x-3 gap-y-1 md:gap-x-2 md:gap-y-2`,
    leading: 'col-span-3 row-start-1 md:col-span-1 md:col-start-1',
    track: 'col-start-1 row-start-2 md:col-span-3',
    words: 'col-start-2 row-start-2 min-w-24 text-right md:row-start-1 md:min-w-0',
    trailing: 'col-start-3 row-start-2 md:row-start-1',
  },
  stacked: {
    root: `${GRID_ROOT} gap-x-2 gap-y-2`,
    leading: 'col-start-1 row-start-1',
    track: 'col-span-3 row-start-2',
    words: 'col-start-2 row-start-1 text-right',
    trailing: 'col-start-3 row-start-1',
  },
} satisfies Record<string, LayoutClasses>;

function layoutClasses(layout: GapBarLayout, hasLeading: boolean): LayoutClasses {
  if (layout === 'stacked') return LAYOUT_CLASSES.stacked;
  return hasLeading ? LAYOUT_CLASSES.responsiveLeading : LAYOUT_CLASSES.responsive;
}

/**
 * The one visual of the Library Stats tab (D-00a): a zero-centred track with the
 * benchmark band (symmetric around 0, D-15), a zero tick, and a dot. Lower (fewer flaws,
 * better) is to the left (D-14). The gap reads in words beside or top right above the bar
 * (D-00b): green or red for a significant better or worse, plain foreground for typical or
 * a gap that could be chance (D-14). A zoneless cell draws no band (D-11) and is coloured only when its gap
 * is significant (D-16).
 */
export function GapBar({ cell, testId, trailing, layout = 'responsive', leading }: GapBarProps) {
  if (cell.delta === null) {
    const empty = (
      <p className="text-sm text-muted-foreground" data-testid={`${testId}-empty`}>
        {COPY_NO_FLAWS}
      </p>
    );
    return leading ? (
      <div className="space-y-1">
        {leading}
        {empty}
      </div>
    ) : (
      empty
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

  const classes = layoutClasses(layout, Boolean(leading));
  return (
    <div className={classes.root} data-testid={testId}>
      {leading && <div className={classes.leading}>{leading}</div>}
      <span
        className={cn(
          'whitespace-nowrap text-sm font-semibold tabular-nums',
          classes.words,
          !colored && 'text-foreground',
        )}
        style={colored ? { color } : undefined}
        data-testid={`${testId}-words`}
      >
        {words}
      </span>
      {trailing && <div className={cn('flex', classes.trailing)}>{trailing}</div>}
      <div
        className={cn('relative h-2.5 rounded-full', classes.track)}
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
