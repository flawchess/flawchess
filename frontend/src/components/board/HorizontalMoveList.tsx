/**
 * HorizontalMoveList — shared horizontal, wrapping SAN move list.
 *
 * The presentational shell behind the Openings move list
 * (`board/MoveList.tsx`), the bot-game move list (`bots/MoveListPanel.tsx`) and
 * the mobile VariationTree. Renders a fixed-height, horizontally-wrapping box of clickable move chips with
 * auto-scroll to the current move and click-to-jump.
 *
 * Per-move decoration (number label, punchline color, dimming, trailing severity
 * glyph) is supplied by the caller via the generic `HorizontalMoveItem` model so
 * the call sites share layout without coupling their data shapes.
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
  /** Click handler for this chip; when set it replaces `onMoveClick(ply)` (Train preview tokens). */
  onSelect?: () => void;
  /**
   * Node rendered as a sibling AFTER the move button, not inside it, so an
   * interactive child (a delete x) is never a button nested in a button.
   */
  after?: ReactNode;
  /**
   * Marks the end of a trailing run the auto-scroll should reveal along with the
   * current move (the Train preview's last token): the box scrolls so the current
   * move sits as high as needed for this item to fit, never above the top row.
   */
  scrollTail?: boolean;
}

/** Breathing room (px) kept above the current move / below the tail when scrolling. */
const SCROLL_TAIL_PADDING_PX = 4;

/**
 * Box scrollTop that keeps `active` visible while revealing as much of the run
 * ending at `tail` as fits. A plain `nearest` scroll on the two-row mobile Train
 * list would park the current move on the bottom row with the whole live
 * preview after it below the fold.
 */
function tailFollowScrollTop(box: HTMLElement, active: HTMLElement, tail: HTMLElement): number {
  const boxTop = box.getBoundingClientRect().top - box.scrollTop;
  const activeTop = active.getBoundingClientRect().top - boxTop;
  const tailBottom = tail.getBoundingClientRect().bottom - boxTop;
  const revealTail = tailBottom - box.clientHeight + SCROLL_TAIL_PADDING_PX;
  return Math.max(0, Math.min(activeTop - SCROLL_TAIL_PADDING_PX, revealTail));
}

interface HorizontalMoveListProps {
  items: HorizontalMoveItem[];
  onMoveClick: (ply: number) => void;
  /** Tailwind height classes for the scroll box. Default matches the Openings move list. */
  heightClass?: string;
  emptyText?: string;
  /** data-testid for the outer scroll box. */
  testId?: string;
  /**
   * Override the current-item highlight classes (default: `bg-primary
   * text-primary-foreground hover:bg-primary/90`). Used by callers whose
   * design system reserves a different accent for the active row (e.g. the
   * bot-game move list's brand-brown live-position highlight) without changing the shared default for existing callers.
   */
  activeItemClassName?: string;
}

export function HorizontalMoveList({
  items,
  onMoveClick,
  heightClass = 'h-12 sm:h-18',
  emptyText = 'No moves yet',
  testId,
  activeItemClassName = 'bg-primary text-primary-foreground hover:bg-primary/90',
}: HorizontalMoveListProps) {
  const activeRef = useRef<HTMLButtonElement>(null);
  const boxRef = useRef<HTMLDivElement>(null);
  const tailRef = useRef<HTMLButtonElement>(null);

  // Auto-scroll to keep the current move visible. Keyed on the current item's
  // key so it re-runs whenever the active step changes. With a scroll tail (the
  // Train preview) the box itself scrolls so the tail shows too.
  const currentKey = items.find((item) => item.isCurrent)?.key ?? null;
  const hasTail = items.some((item) => item.scrollTail);
  useEffect(() => {
    const active = activeRef.current;
    const tail = tailRef.current;
    const box = boxRef.current;
    if (active && tail && box) {
      const top = tailFollowScrollTop(box, active, tail);
      // jsdom has no Element.scrollTo; plain assignment keeps the position right there.
      if (typeof box.scrollTo === 'function') box.scrollTo({ top, behavior: 'smooth' });
      else box.scrollTop = top;
      return;
    }
    active?.scrollIntoView({ block: 'nearest', behavior: 'smooth' });
  }, [currentKey, hasTail]);

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
      ref={boxRef}
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
              ref={item.isCurrent ? activeRef : item.scrollTail ? tailRef : undefined}
              onClick={() => (item.onSelect ? item.onSelect() : onMoveClick(item.ply))}
              data-testid={item.testId}
              aria-label={item.ariaLabel}
              aria-current={item.isCurrent ? 'step' : undefined}
              className={cn(
                'inline-flex items-center gap-0.5 rounded px-1 py-0.5 font-mono transition-colors hover:bg-accent',
                item.isCurrent && activeItemClassName,
                item.dimmed && !item.isCurrent && 'text-muted-foreground',
              )}
              // Punchline color only when not the active step (the primary
              // highlight owns the look when current).
              style={item.color && !item.isCurrent ? { color: item.color } : undefined}
            >
              <span>{item.san}</span>
              {item.trailing}
            </button>
            {item.after}
          </span>
        ))}
      </div>
    </div>
  );
}
