import { useSyncExternalStore, useCallback } from 'react';
import type { FlawSeverityFilter, FlawTag } from '@/types/library';
import type { TacticFamily } from '@/lib/tacticComparisonMeta';
import type { TacticOrientation } from '@/types/library';
import { DEFAULT_TACTIC_DEPTH_VALUE } from '@/lib/tacticDepth';
import { isSeverityNarrowed } from '@/lib/flawSeverityFilter';

// ─── State shape ─────────────────────────────────────────────────────────────

export interface FlawFilterState {
  /**
   * Flaw tags (facepalm / blunder / mistake) to NARROW to, combined with OR. Empty
   * or all three selected = everything shown (the default, same "select to narrow"
   * semantic as the tag families). 'blunder' means the blunders that are not
   * facepalms. See isSeverityNarrowed in lib/flawSeverityFilter.ts.
   */
  severity: FlawSeverityFilter[];
  /** Tag predicates (AND across families, OR within family). Default: empty (no filter). */
  tags: FlawTag[];
  /**
   * Tactic-motif families to NARROW to. Off by default (empty = no
   * filter, like the tag families); selecting one or more families restricts the
   * flaw list to flaws whose detected motif is in those families.
   */
  tacticFamilies: TacticFamily[];
  /**
   * Tactic orientation filter. Default 'either' (show both
   * missed and allowed tactics). 'missed' restricts to missed-tactic flaws only;
   * 'allowed' restricts to allowed-tactic flaws only.
   */
  tacticOrientation: TacticOrientation;
  /**
   * Inclusive tactic-depth range bounds (0-based ply, 0..11). The depth
   * filter is always-on; the default range is the All preset / full range
   * {0, 11}. min === max is valid (e.g. {0, 0}).
   */
  tacticDepthMin: number;
  tacticDepthMax: number;
  /**
   * "Has gem" / "has great" toggles — independent
   * booleans narrowing the Library games list to games containing at least one
   * stored user-move gem/great (union when both are true, per the backend's
   * has_gem/has_great EXISTS composition). Default false (no filter).
   */
  hasGem: boolean;
  hasGreat: boolean;
}

export const DEFAULT_FLAW_FILTER: FlawFilterState = {
  severity: [],
  tags: [],
  tacticFamilies: [],
  tacticOrientation: 'either',
  tacticDepthMin: DEFAULT_TACTIC_DEPTH_VALUE.min,
  tacticDepthMax: DEFAULT_TACTIC_DEPTH_VALUE.max,
  hasGem: false,
  hasGreat: false,
};

/**
 * True when the flaw filter actually narrows the result set — any tag or tactic
 * family selected, one or two of the three severity tags selected, orientation not
 * 'either', depth range not the full default, or has-gem/has-great on. Empty severity
 * and all three tags selected (both show everything) are NOT narrowing; two tags that
 * leave one out (e.g. blunder + mistake, which excludes facepalms) are.
 *
 * CRITICAL: the depth filter is always-on. isFlawFilterNonDefault returns
 * true only when the depth RANGE differs from the All/full-range default {0, 11} —
 * never merely because it is set. The filter-dot does not light at the default
 * Either + All/full-range state.
 *
 * Single source of truth for filter-dot indicators (Games + Flaws tabs) and the
 * games-query gate, so the default never drifts across call sites.
 */
export function isFlawFilterNonDefault(filter: FlawFilterState): boolean {
  return (
    filter.tags.length > 0 ||
    isSeverityNarrowed(filter.severity) ||
    // Optional-chained: defensive against partial filter objects (e.g. test mocks).
    (filter.tacticFamilies?.length ?? 0) > 0 ||
    // Orientation non-default (not 'either') lights the dot.
    (filter.tacticOrientation ?? 'either') !== 'either' ||
    // Depth range non-default (≠ All/full-range {0, 11}) lights the dot.
    (filter.tacticDepthMin ?? DEFAULT_TACTIC_DEPTH_VALUE.min) !== DEFAULT_TACTIC_DEPTH_VALUE.min ||
    (filter.tacticDepthMax ?? DEFAULT_TACTIC_DEPTH_VALUE.max) !== DEFAULT_TACTIC_DEPTH_VALUE.max ||
    // A stale object still carrying the removed facepalm range fields is read as
    // default: the range filter no longer exists, so its fields are never inspected.
    // Either "has gem" or "has great" toggle narrows the result set.
    (filter.hasGem ?? false) ||
    (filter.hasGreat ?? false)
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
