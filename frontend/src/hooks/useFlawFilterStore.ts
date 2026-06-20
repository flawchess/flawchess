import { useSyncExternalStore, useCallback } from 'react';
import type { FlawTag } from '@/types/library';
import type { TacticFamily } from '@/lib/tacticComparisonMeta';
import type { TacticOrientation } from '@/types/library';
import type { TacticDepthPreset } from '@/lib/tacticDepth';
import { DEPTH_PRESET_INTERMEDIATE_MAX } from '@/lib/tacticDepth';

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
   * Active depth preset label (Phase 129 TACUI-06, D-02).
   * Always-on; default = 'intermediate'. Drives isFlawFilterNonDefault.
   */
  tacticDepthPreset: TacticDepthPreset;
  /**
   * Half-ply maxMoves API value (Phase 129 TACUI-06, D-03).
   * 1:1 with the DB column. null = no cap (Advanced).
   * Default = DEPTH_PRESET_INTERMEDIATE_MAX (6 half-plies = 3 full moves).
   */
  tacticDepthMax: number | null;
}

export const DEFAULT_FLAW_FILTER: FlawFilterState = {
  severity: [],
  tags: [],
  tacticFamilies: [],
  tacticOrientation: 'either',
  tacticDepthPreset: 'intermediate',
  tacticDepthMax: DEPTH_PRESET_INTERMEDIATE_MAX,
};

/**
 * True when the flaw filter actually narrows the result set — any tag selected,
 * severity narrowed to exactly one tier, orientation not 'either', or depth preset
 * not 'intermediate'. Empty severity (both shown) and both tiers selected (also both
 * shown) are NOT narrowing.
 *
 * CRITICAL (D-02): the depth filter is always-on. isFlawFilterNonDefault returns
 * true only when the depth PRESET is not intermediate — never merely because it
 * is set. The filter-dot does not light at the default Either + Intermediate state.
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
    // Phase 129: depth non-default (not 'intermediate' preset) lights the dot.
    // NOT the tacticDepthMax value — the preset is the canonical default signal.
    (filter.tacticDepthPreset ?? 'intermediate') !== 'intermediate'
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
