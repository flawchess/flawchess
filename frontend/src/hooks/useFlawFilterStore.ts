import { useSyncExternalStore, useCallback } from 'react';
import type { FlawTag } from '@/types/library';

// ─── State shape ─────────────────────────────────────────────────────────────

export interface FlawFilterState {
  /** Severity tiers to display. Default: both M+B. */
  severity: ('blunder' | 'mistake')[];
  /** Tag predicates (AND across families, OR within family). Default: empty (no filter). */
  tags: FlawTag[];
}

export const DEFAULT_FLAW_FILTER: FlawFilterState = {
  severity: ['blunder', 'mistake'],
  tags: [],
};

/**
 * True when the flaw filter differs from DEFAULT_FLAW_FILTER — any tag selected,
 * or severity not exactly the default M+B set. Single source of truth for the
 * "non-default" predicate used by the filter-dot indicators (Games + Flaws tabs)
 * and the FlawFilterControl clear affordance, so the default never drifts across
 * call sites.
 */
export function isFlawFilterNonDefault(filter: FlawFilterState): boolean {
  return (
    filter.tags.length > 0 ||
    filter.severity.length !== DEFAULT_FLAW_FILTER.severity.length ||
    !filter.severity.includes('blunder') ||
    !filter.severity.includes('mistake')
  );
}

// ─── Module-level shared state ───────────────────────────────────────────────

// Module-level shared flaw filter state — survives page navigations within the SPA.
// Mirrors useFilterStore.ts pattern: useSyncExternalStore, no Zustand.
let currentFlawFilter: FlawFilterState = { ...DEFAULT_FLAW_FILTER };
const listeners = new Set<() => void>();

function subscribe(listener: () => void): () => void {
  listeners.add(listener);
  return () => {
    listeners.delete(listener);
  };
}

function getSnapshot(): FlawFilterState {
  return currentFlawFilter;
}

type FlawFilterUpdater = FlawFilterState | ((prev: FlawFilterState) => FlawFilterState);

function setFlawFilter(next: FlawFilterUpdater): void {
  currentFlawFilter = typeof next === 'function' ? next(currentFlawFilter) : next;
  for (const listener of listeners) {
    listener();
  }
}

// ─── Hook ─────────────────────────────────────────────────────────────────────

/**
 * Shared flaw-filter store that persists across page navigations.
 * Uses useSyncExternalStore for React-safe subscription to module-level state.
 * Setter supports both direct values and updater functions (like useState).
 *
 * Mirrors useFilterStore.ts — no Zustand, zero new dependencies.
 */
export function useFlawFilterStore(): readonly [FlawFilterState, (next: FlawFilterUpdater) => void] {
  const state = useSyncExternalStore(subscribe, getSnapshot);
  const update = useCallback((next: FlawFilterUpdater) => setFlawFilter(next), []);
  return [state, update] as const;
}
