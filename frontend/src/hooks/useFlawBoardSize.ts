import { useLayoutEffect, useRef, useState } from 'react';
import type { RefObject } from 'react';

// The board takes a bit over half of the card: a smaller one wastes the height the details and
// tags need beside it anyway, a larger one leaves their column too narrow. The minimum holds the
// three detail rows and two lines of tags at the phone text size. A multiple of 8 gives
// whole-pixel squares.
const BOARD_WIDTH_FRACTION = 0.55;
const BOARD_MIN_SIZE = 152;
const BOARD_MAX_SIZE = 216;
const BOARD_SIZE_STEP = 8;

/** Board size for a card body content width; the minimum until the width is known. */
export function flawBoardSize(contentWidth: number): number {
  const fitted = Math.floor((contentWidth * BOARD_WIDTH_FRACTION) / BOARD_SIZE_STEP) * BOARD_SIZE_STEP;
  return Math.min(BOARD_MAX_SIZE, Math.max(BOARD_MIN_SIZE, fitted));
}

/**
 * Miniboard size from the card's own width, not the viewport: the grid decides how many cards
 * share a row. MiniBoard needs concrete pixels for its arrow geometry, so CSS units won't do.
 */
export function useFlawBoardSize(): { ref: RefObject<HTMLDivElement | null>; boardSize: number } {
  const ref = useRef<HTMLDivElement>(null);
  const [boardSize, setBoardSize] = useState(BOARD_MIN_SIZE);

  useLayoutEffect(() => {
    const el = ref.current;
    if (!el) return;
    const update = (): void => setBoardSize(flawBoardSize(el.clientWidth));
    update();
    const observer = new ResizeObserver(update);
    observer.observe(el);
    return () => observer.disconnect();
  }, []);

  return { ref, boardSize };
}
