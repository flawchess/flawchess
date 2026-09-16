/**
 * mobileBoardControls — a tiny cross-tree store for "a page below the layout
 * wants the mobile bottom bar to show board controls instead of the main nav
 * buttons" (Quick 260809-g0n: Train free-move mode, matching the /analysis
 * mobile footer's board-controls treatment).
 *
 * A module-level store (not context) because the writer and the reader live
 * in unrelated subtrees: `ProtectedLayout` (App.tsx) wraps the router
 * `Outlet`, so it cannot receive props/context from a page component below
 * it. Mirrors `lib/playActive.ts`'s shape and rationale.
 */

import { useEffect, useSyncExternalStore } from 'react';

export interface MobileBoardControls {
  onBack: () => void;
  onForward: () => void;
  /**
   * Phase 223 (BOTVOICE-05, D-10): optional because the bot game's
   * four-action payload (Resign/Back/Forward/Flip) has no reset control.
   * Every other publisher (Train, Analysis, Openings) still supplies it.
   */
  onReset?: () => void;
  onFlip: () => void;
  canGoBack: boolean;
  canGoForward: boolean;
  /** Optional alongside `onReset` — see that field's comment. */
  canReset?: boolean;
  /**
   * Phase 223 (BOTVOICE-05, D-10): presence (not a default) is the signal
   * `MobileBottomBar` uses to swap in the bot game's four-action bar instead
   * of the shared `BoardControls` row — deliberately NOT given a NOOP
   * default below, unlike every other field, because a default would make
   * `onResign != null` true for every publisher and always render the bot
   * bar.
   */
  onResign?: () => void;
  /**
   * Quick 260916: the bot game's user-side draw offer, alongside `onResign`.
   * Optional and defaultless for the same reason as `onResign` — only the
   * bot game publishes it; the bot bar is the only reader.
   */
  onOfferDraw?: () => void;
  /** Net disabled state of the bot bar's Draw action (see `onOfferDraw`). */
  offerDrawDisabled?: boolean;
}

const NOOP_PAYLOAD: MobileBoardControls = Object.freeze({
  onBack: () => {},
  onForward: () => {},
  onReset: () => {},
  onFlip: () => {},
  canGoBack: false,
  canGoForward: false,
  canReset: false,
});

let payload: MobileBoardControls | null = null;
const listeners = new Set<() => void>();

function setPayload(next: MobileBoardControls | null): void {
  if (payload === next) return;
  payload = next;
  listeners.forEach((listener) => listener());
}

function subscribe(listener: () => void): () => void {
  listeners.add(listener);
  return () => listeners.delete(listener);
}

/** The published board-controls payload, or null when nothing is published. */
export function useMobileBoardControls(): MobileBoardControls | null {
  return useSyncExternalStore(subscribe, () => payload);
}

/**
 * Publishes `controls` for the lifetime of the calling component (null while
 * unmounted, on unmount, or whenever the caller passes null — e.g. Train
 * leaving free-move mode). The effect's dependency array lists only the
 * destructured primitives/callbacks, never `controls` itself, whose identity
 * changes every render and would otherwise loop the store write against the
 * App re-render it triggers.
 */
export function usePublishMobileBoardControls(controls: MobileBoardControls | null): void {
  const {
    onBack = NOOP_PAYLOAD.onBack,
    onForward = NOOP_PAYLOAD.onForward,
    onReset = NOOP_PAYLOAD.onReset,
    onFlip = NOOP_PAYLOAD.onFlip,
    canGoBack = NOOP_PAYLOAD.canGoBack,
    canGoForward = NOOP_PAYLOAD.canGoForward,
    canReset = NOOP_PAYLOAD.canReset,
    // No default — undefined is the meaningful "not the bot bar" value.
    onResign,
    onOfferDraw,
    offerDrawDisabled,
  } = controls ?? {};
  const hasControls = controls != null;

  useEffect(() => {
    if (!hasControls) return;
    setPayload({
      onBack,
      onForward,
      onReset,
      onFlip,
      canGoBack,
      canGoForward,
      canReset,
      onResign,
      onOfferDraw,
      offerDrawDisabled,
    });
    return () => setPayload(null);
  }, [
    hasControls,
    onBack,
    onForward,
    onReset,
    onFlip,
    canGoBack,
    canGoForward,
    canReset,
    onResign,
    onOfferDraw,
    offerDrawDisabled,
  ]);
}
