import * as React from 'react';
import { cn } from '@/lib/utils';

interface ChipColumnProps {
  /** Small section label shown above the chips (e.g. "Allowed", "Context"). */
  label: string;
  /** Optional test id on the column container. */
  testId?: string;
  /** When true, the column has nothing to show and is omitted entirely (no label, no
   *  placeholder) so empty Missed/Allowed/Context sections don't clutter the layout. */
  isEmpty?: boolean;
  /** Optional node pinned to the right edge of the label row (e.g. a legend tooltip
   *  icon), so each column's explanations sit next to its own label rather than inline
   *  among the chips. */
  labelTrailing?: React.ReactNode;
  /** Optional node rendered below the chips, inside the column lane (e.g. the desktop
   *  Explore button pinned to the Missed column). Renders even when the column is empty,
   *  so the control stays visible regardless of whether the column has chips. */
  footer?: React.ReactNode;
  /**
   * Keep the mobile inline layout (label + chips share one flex-wrap line) at EVERY
   * breakpoint instead of stacking into a column at md+. Used by the /analysis tags
   * panel, whose narrow right-column rail reads better with chips floated beside their
   * label than in three cramped columns.
   */
  inline?: boolean;
  children?: React.ReactNode;
}

/**
 * Quick 260620-sep follow-up: a labeled chip container used for the Games-card
 * "Allowed" / "Missed" / "Context" columns. Lightweight on purpose — a small uppercase
 * section label over a flex-wrap chip row, no Card chrome (borders/shadow would clutter
 * the already-dense card). The parent lays these out in a responsive grid so they span
 * 1/3 width each on wide viewports and stack vertically when narrow.
 */
export function ChipColumn({
  label,
  testId,
  isEmpty,
  labelTrailing,
  footer,
  inline = false,
  children,
}: ChipColumnProps) {
  // Empty columns are omitted entirely rather than showing a "—" placeholder — an empty
  // Missed/Allowed/Context section adds no information and just clutters the card/rail.
  if (isEmpty) return null;
  return (
    // Mobile: label + chips share one flex-wrap line (tags float beside the label). Desktop
    // (md+): label stacks above the chips so the 3-column grid reads as labeled columns.
    // The md breakpoint matches the game card's mobile→desktop body switch (Quick 260625).
    // `inline` pins the mobile layout at every width (the /analysis tags rail).
    <div
      className={cn(
        'flex flex-wrap items-center gap-x-1.5 gap-y-1 min-w-0',
        !inline && 'md:flex-col md:items-start',
      )}
      data-testid={testId}
    >
      {/* Mobile: fix the label+icon container to one width (icon stays next to the label),
          so the chips start at the same x across all three rows (Missed/Allowed/Context).
          Desktop (md+): reset to auto width since the label stacks above its chips. */}
      <div className={cn('flex w-24 shrink-0 items-center gap-1.5', !inline && 'md:w-auto')}>
        <span className="text-sm font-medium text-muted-foreground">{label}</span>
        {labelTrailing}
      </div>
      {/* Mobile: `contents` dissolves this wrapper so each chip is a direct flex item of the
          outer row, wrapping individually beside the label. Desktop (md+): a real flex row. */}
      <div className={cn('contents', !inline && 'md:flex md:flex-wrap md:items-center md:gap-1.5')}>
        {children}
      </div>
      {footer}
    </div>
  );
}
