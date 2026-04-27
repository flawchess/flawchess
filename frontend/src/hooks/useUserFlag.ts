import { useSyncExternalStore } from 'react';

// Generic boolean flag persisted per-user in localStorage. Used for one-shot
// "has the user seen X yet?" markers that drive the red notification dots in
// the nav and on first-use CTAs (Endgames tab visit, Generate Insights click).
// Scoped per-email so a shared browser does not bleed flag state between
// accounts.

const KEY_PREFIX = 'user_flag:';

const listeners = new Set<() => void>();

function subscribe(cb: () => void): () => void {
  listeners.add(cb);
  return () => {
    listeners.delete(cb);
  };
}

function storageKey(name: string, email: string | undefined | null): string {
  return `${KEY_PREFIX}${name}:${email ?? 'anon'}`;
}

function readFlag(name: string, email: string | undefined | null): boolean {
  try {
    return localStorage.getItem(storageKey(name, email)) === '1';
  } catch {
    return false;
  }
}

export function useUserFlag(
  name: string,
  email: string | undefined | null,
): boolean {
  return useSyncExternalStore(
    subscribe,
    () => readFlag(name, email),
    () => false,
  );
}

export function setUserFlag(
  name: string,
  email: string | undefined | null,
): void {
  const key = storageKey(name, email);
  try {
    if (localStorage.getItem(key) === '1') return;
    localStorage.setItem(key, '1');
  } catch {
    return;
  }
  listeners.forEach((l) => l());
}
