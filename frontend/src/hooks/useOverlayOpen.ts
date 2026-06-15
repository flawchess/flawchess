import { useEffect, useState } from 'react';

/**
 * Selector for overlay elements (radix Dialog, Sheet, Drawer, and any dialog role).
 * Radix sets data-slot attributes on its content components.
 * This covers all flawchess overlay surfaces: filter/bookmark drawers, feedback modal,
 * mobile more drawer, install prompt, and any other radix Dialog/Drawer.
 */
const OVERLAY_SELECTOR = '[role="dialog"], [data-slot="dialog-content"], [data-slot="drawer-content"]';

function isOverlayPresent(): boolean {
  if (typeof document === 'undefined') return false;
  return document.querySelector(OVERLAY_SELECTOR) !== null;
}

/**
 * Returns true when any overlay (Dialog, Sheet, Drawer, bottom sheet) is currently
 * open in the DOM, false otherwise.
 *
 * Uses a MutationObserver on document.body (childList + subtree) so the signal
 * updates whenever radix overlays portal in or out of the document body.
 * The observer is disconnected on unmount.
 */
export function useOverlayOpen(): boolean {
  const [overlayOpen, setOverlayOpen] = useState<boolean>(() => isOverlayPresent());

  useEffect(() => {
    const update = () => {
      setOverlayOpen(isOverlayPresent());
    };

    const observer = new MutationObserver(update);
    observer.observe(document.body, { childList: true, subtree: true });

    // Initial check in case an overlay is already open when we mount
    update();

    return () => {
      observer.disconnect();
    };
  }, []);

  return overlayOpen;
}
