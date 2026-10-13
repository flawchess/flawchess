import { useEffect, useRef, useState } from 'react';

/**
 * Whether a `position: sticky` element is currently pinned. Put the returned ref on a
 * 1px sentinel directly before the sticky element (in the same container); `topOffsetPx`
 * is the sticky element's `top`. Pinned = the sentinel has scrolled above that offset.
 */
export function useIsPinned<T extends HTMLElement>(topOffsetPx: number) {
  const sentinelRef = useRef<T>(null);
  const [isPinned, setIsPinned] = useState(false);

  useEffect(() => {
    const sentinel = sentinelRef.current;
    // jsdom has no IntersectionObserver; the element then simply never reports pinned.
    if (!sentinel || typeof IntersectionObserver === 'undefined') return;
    const observer = new IntersectionObserver(
      ([entry]) => {
        if (!entry) return;
        setIsPinned(!entry.isIntersecting && entry.boundingClientRect.top < topOffsetPx);
      },
      { rootMargin: `-${topOffsetPx}px 0px 0px 0px` },
    );
    observer.observe(sentinel);
    return () => observer.disconnect();
  }, [topOffsetPx]);

  return [sentinelRef, isPinned] as const;
}
