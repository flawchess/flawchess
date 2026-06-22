import { useEffect, useState } from 'react';

// Library cards switch to the stacked mobile layout below Tailwind's `sm` (640px).
// On mobile the miniboard spans 40% of the viewport width; on `sm`+ it keeps the
// caller's fixed desktop size. The board needs a concrete pixel size (its arrow /
// corner-dot SVG geometry is computed as fractions of `size`), so we resolve the
// vw target to pixels here and re-resolve on resize instead of using a CSS unit.
const SM_BREAKPOINT_PX = 640;
const MOBILE_BOARD_WIDTH_FRACTION = 0.4;

function resolveSize(desktopSize: number): number {
  if (typeof window === 'undefined') return desktopSize;
  if (window.innerWidth >= SM_BREAKPOINT_PX) return desktopSize;
  return Math.round(window.innerWidth * MOBILE_BOARD_WIDTH_FRACTION);
}

/**
 * Returns the miniboard pixel size to use: `desktopSize` at `sm`+ widths, or 40%
 * of the viewport width below `sm`. Recomputes on viewport resize/orientation change.
 */
export function useMiniBoardSize(desktopSize: number): number {
  const [size, setSize] = useState(() => resolveSize(desktopSize));

  useEffect(() => {
    const update = (): void => setSize(resolveSize(desktopSize));
    update();
    window.addEventListener('resize', update);
    return () => window.removeEventListener('resize', update);
  }, [desktopSize]);

  return size;
}
