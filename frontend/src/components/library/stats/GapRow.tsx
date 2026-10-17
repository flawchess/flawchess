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
 * One metric row: the label, then the gap bar with the hint on the words line and the
 * popover trigger after the words. From md up the hint sits top left, level with the words,
 * above a full-width bar. The bar owns the verdict and its significance gate.
 */
export function GapRow({ label, hint, cell, popover, testId }: GapRowProps) {
  return (
    <div data-testid={testId}>
      <div className="font-semibold">{label}</div>
      <GapBar
        cell={cell}
        testId={`${testId}-bar`}
        trailing={popover}
        leading={<div className="text-sm text-muted-foreground">{hint}</div>}
      />
    </div>
  );
}
