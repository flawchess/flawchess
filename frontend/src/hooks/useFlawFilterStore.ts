import { useSyncExternalStore, useCallback } from 'react';
import type { FlawTag } from '@/types/library';
import type { TacticFamily } from '@/lib/tacticComparisonMeta';
import type { TacticOrientation } from '@/types/library';
import { DEFAULT_TACTIC_DEPTH_VALUE } from '@/lib/tacticDepth';

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
  /**
   * Tactic-motif families to NARROW to (Phase 126). Off by default (empty = no
   * filter, like the tag families); selecting one or more families restricts the
   * flaw list to flaws whose detected motif is in those families.
   */
  tacticFamilies: TacticFamily[];
  /**
   * Tactic orientation filter (Phase 129 TACUI-06). Default 'either' (show both
   * missed and allowed tactics). 'missed' restricts to missed-tactic flaws only;
   * 'allowed' restricts to allowed-tactic flaws only.
   */
  tacticOrientation: TacticOrientation;
  /**
   * Inclusive tactic-depth range bounds (0-based ply, 0..11) — Quick 260620-l5k
   * (Phase 130). The depth filter is always-on; the default range is the
   * High preset / full range {0, 11} (Quick 260621-sm8). min === max is valid (e.g. {0, 0}).
   */
  tacticDepthMin: number;
  tacticDepthMax: number;
  /**
   * "Has gem" / "has great" toggles (FILT-01, D-05, Phase 175) — independent
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
 * True when the flaw filter actually narrows the result set — any tag selected,
 * severity narrowed to exactly one tier, orientation not 'either', or depth preset
 * not 'medium'. Empty severity (both shown) and both tiers selected (also both
 * shown) are NOT narrowing.
 *
 * CRITICAL (D-02): the depth filter is always-on. isFlawFilterNonDefault returns
 * true only when the depth RANGE differs from the High/full-range default {0, 11} —
 * never merely because it is set. The filter-dot does not light at the default
 * Either + High/full-range state (Quick 260621-sm8: changed from Medium {0, 5}).
 *
 * Single source of truth for filter-dot indicators (Games + Flaws tabs) and the
 * games-query gate, so the default never drifts across call sites.
 */
export function isFlawFilterNonDefault(filter: FlawFilterState): boolean {
  return (
    filter.tags.length > 0 ||
    filter.severity.length === 1 ||
    // Optional-chained: defensive against partial filter objects (e.g. older
    // persisted/mocked state predating the tacticFamilies field).
    (filter.tacticFamilies?.length ?? 0) > 0 ||
    // Phase 129: orientation non-default (not 'either') lights the dot.
    (filter.tacticOrientation ?? 'either') !== 'either' ||
    // Quick 260620-l5k / 260621-sm8: depth range non-default (≠ High/full-range {0, 11}) lights the dot.
    (filter.tacticDepthMin ?? DEFAULT_TACTIC_DEPTH_VALUE.min) !== DEFAULT_TACTIC_DEPTH_VALUE.min ||
    (filter.tacticDepthMax ?? DEFAULT_TACTIC_DEPTH_VALUE.max) !== DEFAULT_TACTIC_DEPTH_VALUE.max ||
    // Phase 175 (FILT-01, D-05): either "has gem" or "has great" toggle narrows the result set.
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
