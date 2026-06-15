import { useEffect, useRef, useState } from 'react';

/** Minimum scroll delta (px) to flip direction — prevents jitter on small movements. */
const SCROLL_DELTA_THRESHOLD = 8;

/** Scroll position threshold (px) at which we always consider the page "at top". */
const AT_TOP_THRESHOLD = 4;

/**
 * Returns 'up' when the user is scrolling up or at the top of the page,
 * and 'down' when scrolling down past SCROLL_DELTA_THRESHOLD.
 *
 * Uses a passive scroll listener + requestAnimationFrame to avoid thrashing.
 * Sub-threshold deltas are ignored to prevent jitter from small scroll events.
 */
export function useScrollDirection(): 'up' | 'down' {
  const [direction, setDirection] = useState<'up' | 'down'>('up');
  const prevScrollY = useRef(typeof window !== 'undefined' ? window.scrollY : 0);
  const ticking = useRef(false);

  useEffect(() => {
    const handleScroll = () => {
      if (ticking.current) return;

      ticking.current = true;
      requestAnimationFrame(() => {
        ticking.current = false;
        const currentY = window.scrollY;
        const prev = prevScrollY.current;
        const delta = currentY - prev;

        if (currentY <= AT_TOP_THRESHOLD) {
          // Always show at top
          setDirection('up');
          prevScrollY.current = currentY;
        } else if (delta > SCROLL_DELTA_THRESHOLD) {
          // Scrolling down past threshold
          setDirection('down');
          prevScrollY.current = currentY;
        } else if (delta < -SCROLL_DELTA_THRESHOLD) {
          // Scrolling up past threshold
          setDirection('up');
          prevScrollY.current = currentY;
        }
        // Sub-threshold delta: no direction change, no prevScrollY update
      });
    };

    window.addEventListener('scroll', handleScroll, { passive: true });

    return () => {
      window.removeEventListener('scroll', handleScroll);
      ticking.current = false;
    };
  }, []);

  return direction;
}
