import { useSyncExternalStore, useCallback } from 'react';
import type { FlawTag } from '@/types/library';

// ─── State shape ─────────────────────────────────────────────────────────────

export interface FlawFilterState {
  /**
   * Severity tiers to NARROW to. Empty = both M+B shown (the default — same
   * "select to narrow" semantic as the tag families). `['blunder']` shows
   * blunders only; selecting both is equivalent to selecting neither.
   */
  severity: ('blunder' | 'mistake')[];
  /** Tag predicates (AND across families, OR within family). Default: empty (no filter). */
  tags: FlawTag[];
}

export const DEFAULT_FLAW_FILTER: FlawFilterState = {
  severity: [],
  tags: [],
};

/**
 * True when the flaw filter actually narrows the result set — any tag selected,
 * or severity narrowed to exactly one tier. Empty severity (both shown) and both
 * tiers selected (also both shown) are NOT narrowing, matching the tag-family
 * "select to narrow" model. Single source of truth for the filter-dot indicators
 * (Games + Flaws tabs) and the games-query gate, so the default never drifts
 * across call sites.
 */
export function isFlawFilterNonDefault(filter: FlawFilterState): boolean {
  return filter.tags.length > 0 || filter.severity.length === 1;
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
