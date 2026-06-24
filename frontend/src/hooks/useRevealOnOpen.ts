import { useCallback, useRef } from 'react';

// Gap left above the revealed section header so it isn't flush against the
// scroll container's top edge. Matches the panels' p-4 top inset.
const REVEAL_TOP_PADDING_PX = 16;

/** Find the nearest ancestor that actually scrolls vertically, or null if none. */
function findScrollableParent(el: HTMLElement | null): HTMLElement | null {
  let node = el?.parentElement ?? null;
  while (node) {
    const overflowY = getComputedStyle(node).overflowY;
    if ((overflowY === 'auto' || overflowY === 'scroll') && node.scrollHeight > node.clientHeight) {
      return node;
    }
    node = node.parentElement;
  }
  return null;
}

/**
 * useRevealOnOpen — when a collapsible section expands, smoothly scroll the nearest
 * scrollable ancestor (the mobile filter drawer's body) so the section header sits
 * near the top, bringing the freshly revealed content and the section headers below
 * it into view.
 *
 * No-op when nothing scrolls (desktop panels that already fit), so it never yanks
 * the page. Honors `prefers-reduced-motion`. Defensive against jsdom (guards
 * matchMedia / scrollTo) so it is safe to call from unit-tested components.
 *
 * Usage:
 *   const { ref, reveal } = useRevealOnOpen<HTMLDivElement>();
 *   // attach ref to the section wrapper (header + collapsible content)
 *   onClick={() => { const next = !open; setOpen(next); reveal(next); }}
 */
export function useRevealOnOpen<T extends HTMLElement>() {
  const ref = useRef<T>(null);

  const reveal = useCallback((willOpen: boolean) => {
    // Only scroll when expanding — collapsing shrinks content, no reveal needed.
    if (!willOpen || typeof window === 'undefined') return;

    // Defer until after the expanded content has been laid out so the scroll
    // container's scrollHeight reflects the newly visible rows.
    window.requestAnimationFrame(() => {
      const el = ref.current;
      if (!el) return;
      const scroller = findScrollableParent(el);
      if (!scroller || typeof scroller.scrollTo !== 'function') return;

      const delta = el.getBoundingClientRect().top - scroller.getBoundingClientRect().top;
      const prefersReduced = window.matchMedia?.('(prefers-reduced-motion: reduce)').matches;
      scroller.scrollTo({
        top: scroller.scrollTop + delta - REVEAL_TOP_PADDING_PX,
        behavior: prefersReduced ? 'auto' : 'smooth',
      });
    });
  }, []);

  return { ref, reveal };
}
