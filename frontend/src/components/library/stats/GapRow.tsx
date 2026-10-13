import type { ReactNode } from 'react';
import type { GapCell } from '@/lib/gapBar';
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
 * the words. The bar owns the verdict and its significance gate (D-14).
 */
export function GapRow({ label, hint, cell, popover, testId }: GapRowProps) {
  return (
    <div className="space-y-1" data-testid={testId}>
      <div>
        <div className="font-semibold">{label}</div>
        <div className="text-sm text-muted-foreground">{hint}</div>
      </div>
      <GapBar cell={cell} testId={`${testId}-bar`} trailing={popover} />
    </div>
  );
}
