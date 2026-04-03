import { useSyncExternalStore, useCallback } from 'react';
import { DEFAULT_FILTERS, type FilterState } from '@/components/filters/FilterPanel';

// Module-level shared filter state — survives page navigations within the SPA.
let currentFilters: FilterState = { ...DEFAULT_FILTERS };
const listeners = new Set<() => void>();

function subscribe(listener: () => void): () => void {
  listeners.add(listener);
  return () => {
    listeners.delete(listener);
  };
}

function getSnapshot(): FilterState {
  return currentFilters;
}

type FilterUpdater = FilterState | ((prev: FilterState) => FilterState);

function setFilters(next: FilterUpdater): void {
  currentFilters = typeof next === 'function' ? next(currentFilters) : next;
  for (const listener of listeners) {
    listener();
  }
}

/**
 * Shared filter store that persists across page navigations.
 * Uses useSyncExternalStore for React-safe subscription to module-level state.
 * Setter supports both direct values and updater functions (like useState).
 */
export function useFilterStore(): readonly [FilterState, (next: FilterUpdater) => void] {
  const state = useSyncExternalStore(subscribe, getSnapshot);
  const update = useCallback((next: FilterUpdater) => setFilters(next), []);
  return [state, update] as const;
}
