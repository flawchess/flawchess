/**
 * HorizontalMoveList — shared horizontal, wrapping SAN move list.
 *
 * The presentational shell behind both the Openings move list
 * (`board/MoveList.tsx`) and the TacticLineExplorer mobile move list. Renders a
 * fixed-height, horizontally-wrapping box of clickable move chips with
 * auto-scroll to the current move and click-to-jump.
 *
 * Per-move decoration (number label, punchline color, dimming, trailing severity
 * glyph) is supplied by the caller via the generic `HorizontalMoveItem` model so
 * the two call sites share layout without coupling their data shapes.
 */

import { useEffect, useRef } from 'react';
import type { ReactNode } from 'react';
import { cn } from '@/lib/utils';

export interface HorizontalMoveItem {
  /** Stable React key. */
  key: string | number;
  /** Target passed to `onMoveClick` when the chip is clicked. */
  ply: number;
  /** Optional leading move-number label (e.g. "12." or "12..."). */
  numberLabel?: string | null;
  /** SAN text. */
  san: string;
  /** Marks the active step — gets the primary highlight + auto-scroll. */
  isCurrent?: boolean;
  /** Inline text-color override (e.g. tactic punchline color). Ignored when current. */
  color?: string;
  /** Render dimmed (payoff / lead-in context moves). Ignored when current. */
  dimmed?: boolean;
  /** Node rendered after the SAN (e.g. a severity glyph). */
  trailing?: ReactNode;
  /** data-testid for the move button. */
  testId?: string;
  ariaLabel?: string;
}

interface HorizontalMoveListProps {
  items: HorizontalMoveItem[];
  onMoveClick: (ply: number) => void;
  /** Tailwind height classes for the scroll box. Default matches the Openings move list. */
  heightClass?: string;
  emptyText?: string;
  /** data-testid for the outer scroll box. */
  testId?: string;
}

export function HorizontalMoveList({
  items,
  onMoveClick,
  heightClass = 'h-12 sm:h-18',
  emptyText = 'No moves yet',
  testId,
}: HorizontalMoveListProps) {
  const activeRef = useRef<HTMLButtonElement>(null);

  // Auto-scroll to keep the current move visible. Keyed on the current item's
  // key so it re-runs whenever the active step changes.
  const currentKey = items.find((item) => item.isCurrent)?.key ?? null;
  useEffect(() => {
    activeRef.current?.scrollIntoView({ block: 'nearest', behavior: 'smooth' });
  }, [currentKey]);

  if (items.length === 0) {
    return (
      <div
        data-testid={testId}
        className={cn(
          'overflow-y-auto thin-scrollbar rounded border border-border bg-muted/30 p-2 text-sm text-muted-foreground',
          heightClass,
        )}
      >
        {emptyText}
      </div>
    );
  }

  return (
    <div
      data-testid={testId}
      className={cn(
        'overflow-y-auto thin-scrollbar rounded border border-border bg-muted/30 p-2 text-sm',
        heightClass,
      )}
    >
      <div className="flex flex-wrap gap-x-1 gap-y-0.5">
        {items.map((item) => (
          <span key={item.key} className="flex items-center gap-0.5">
            {item.numberLabel != null && (
              <span className="text-muted-foreground select-none">{item.numberLabel}</span>
            )}
            <button
              ref={item.isCurrent ? activeRef : undefined}
              onClick={() => onMoveClick(item.ply)}
              data-testid={item.testId}
              aria-label={item.ariaLabel}
              aria-current={item.isCurrent ? 'step' : undefined}
              className={cn(
                'inline-flex items-center gap-0.5 rounded px-1 py-0.5 font-mono transition-colors hover:bg-accent',
                item.isCurrent && 'bg-primary text-primary-foreground hover:bg-primary/90',
                item.dimmed && !item.isCurrent && 'text-muted-foreground',
              )}
              // Punchline color only when not the active step (the primary
              // highlight owns the look when current).
              style={item.color && !item.isCurrent ? { color: item.color } : undefined}
            >
              <span>{item.san}</span>
              {item.trailing}
            </button>
          </span>
        ))}
      </div>
    </div>
  );
}
