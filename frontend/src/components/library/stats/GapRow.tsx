import type { ReactNode } from 'react';
import type { GapCell } from '@/lib/gapBar';
import { UNRELIABLE_OPACITY } from '@/lib/theme';
import { GapBar } from './GapBar';

interface GapRowProps {
  label: string;
  /** The one-line plain hint under the label. */
  hint: string;
  cell: GapCell;
  /** The Search popover trigger; callers omit it when the cell has no gap. */
  popover?: ReactNode;
  testId: string;
}

/**
 * One metric row: label with its hint, then the gap bar with the popover trigger after
 * the words. A low-sample cell (D-12) fades the whole row; the bar itself already shows
 * a neutral dot and no verdict.
 */
export function GapRow({ label, hint, cell, popover, testId }: GapRowProps) {
  return (
    <div
      className="space-y-1"
      style={cell.lowSample ? { opacity: UNRELIABLE_OPACITY } : undefined}
      data-testid={testId}
    >
      <div>
        <div className="font-semibold">{label}</div>
        <div className="text-sm text-muted-foreground">{hint}</div>
      </div>
      <GapBar cell={cell} testId={`${testId}-bar`} trailing={popover} />
    </div>
  );
}
