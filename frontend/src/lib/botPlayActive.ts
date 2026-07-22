/**
 * botPlayActive — a tiny cross-tree flag for "a bot game board is mounted".
 *
 * `BotsGame` (pages/Bots.tsx) marks itself active while mounted;
 * `ProtectedLayout` (App.tsx) reads the flag to suppress the mobile header
 * during play, reclaiming vertical space for the board on small screens. A
 * module-level store (not context) because the writer and reader live in
 * unrelated subtrees: the layout wraps the router `Outlet`, so it cannot
 * receive props/context from a page component below it.
 */

import { useEffect, useSyncExternalStore } from 'react';

let active = false;
const listeners = new Set<() => void>();

function setActive(next: boolean): void {
  if (active === next) return;
  active = next;
  listeners.forEach((listener) => listener());
}

function subscribe(listener: () => void): () => void {
  listeners.add(listener);
  return () => listeners.delete(listener);
}

/** Marks bot play active for the lifetime of the calling component. */
export function useMarkBotPlayActive(): void {
  useEffect(() => {
    setActive(true);
    return () => setActive(false);
  }, []);
}

/** True while a bot game board is mounted anywhere in the app. */
export function useBotPlayActive(): boolean {
  return useSyncExternalStore(subscribe, () => active);
}
