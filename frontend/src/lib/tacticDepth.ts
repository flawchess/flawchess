/**
 * tacticDepth.ts — Quick 260620-l5k (Phase 130).
 *
 * UNIT (LOCKED): the slider and the API/DB value are BOTH plain depth — the
 * 0-based ply index into the winning line (`game_flaws.*_tactic_depth`). No
 * full-move ↔ half-ply conversion anymore; the slider domain IS the DB domain.
 *
 * The filter is a two-handle RANGE [min, max] over depth 0..11 (the dev-DB max
 * is 11). Mates obey the range like every other tactic (the Phase 129 D-04
 * exemption was removed). Cloned in spirit from opponentStrength.ts.
 */

// ─── Named constants (no magic numbers) ─────────────────────────────────────

/** Slider domain minimum (depth, 0-based ply). 0 is selectable on both handles. */
export const DEPTH_MIN = 0;

/** Slider domain maximum. Dev-DB max tactic depth is 11. */
export const DEPTH_MAX = 11;

/** Step size in depth units. */
export const DEPTH_STEP = 1;

/**
 * Display offset: internal/DB/API depth is 0-based (0 = immediate), but the UI
 * shows it 1-based (1..12) everywhere a user sees a number — the filter summary
 * and the depth badges on the library miniboards. Internal values, slider
 * domain, presets, and API query params stay 0-based.
 */
export const DEPTH_DISPLAY_OFFSET = 1;

/** Convert an internal 0-based depth to its user-facing 1-based number. */
export function toDisplayDepth(depth: number): number {
  return depth + DEPTH_DISPLAY_OFFSET;
}

/**
 * Decision-anchored depth offset for the ALLOWED orientation (Quick 260621-qz9).
 *
 * missed_tactic_depth and allowed_tactic_depth both store the raw 0-based detector
 * loop index within their OWN principal variation. The missed PV starts at the
 * decision board; the allowed PV is the opponent's refutation, which starts one
 * ply LATER. On the miniboards both depth badges are anchored on the same pre-flaw
 * decision board, so an allowed tactic at raw depth d sits one ply deeper than a
 * missed tactic at the same raw d. Allowed display gets this extra +1 so both
 * orientations read on one decision-anchored difficulty scale. Mirrors
 * ALLOWED_DECISION_DEPTH_OFFSET in app/repositories/library_repository.py.
 */
export const ALLOWED_DECISION_DEPTH_OFFSET = 1;

/** Orientation of a tactic depth — missed (player's line) vs allowed (opponent's). */
export type TacticDepthOrientation = 'missed' | 'allowed';

/**
 * Orientation-aware display depth: missed = raw + 1 (the plain offset); allowed =
 * raw + 1 + 1 (decision-anchored, see ALLOWED_DECISION_DEPTH_OFFSET). Use this for
 * the miniboard depth badges so allowed and missed are comparable on screen.
 */
export function toDisplayDepthForOrientation(
  depth: number,
  orientation: TacticDepthOrientation,
): number {
  const anchorOffset = orientation === 'allowed' ? ALLOWED_DECISION_DEPTH_OFFSET : 0;
  return depth + DEPTH_DISPLAY_OFFSET + anchorOffset;
}

/** Always-on depth filter; default preset is High (full range — shows everything). */
export const DEPTH_DEFAULT_PRESET = 'high' as const;

// ─── Types ────────────────────────────────────────────────────────────────────

export type TacticDepthPreset = 'low' | 'medium' | 'high';

/**
 * Depth range carried through the UI and sent to the API. Both bounds are
 * inclusive depth values in [DEPTH_MIN, DEPTH_MAX]. min === max is valid
 * (e.g. {0, 0} = depth-0 tactics only).
 */
export interface TacticDepthValue {
  min: number;
  max: number;
}

// ─── Presets ────────────────────────────────────────────────────────────────

// Raw bounds stay in stored depth units (the 0-based detector index). They are
// NOT shifted for the allowed +1 offset: that offset is applied per-orientation
// inside the backend filter (and the on-screen display), so the preset domain
// must remain the shared stored-unit scale to avoid double-counting the shift.
export const PRESET_RANGES: Record<TacticDepthPreset, TacticDepthValue> = {
  low: { min: 0, max: 1 },
  medium: { min: 0, max: 5 },
  high: { min: DEPTH_MIN, max: DEPTH_MAX },
};

/** Short preset names shown on the chips (the depth range goes in the summary). */
export const PRESET_LABELS: Record<TacticDepthPreset, string> = {
  low: 'Low',
  medium: 'Medium',
  high: 'High',
};

export const PRESET_ORDER: TacticDepthPreset[] = ['low', 'medium', 'high'];

/** Default range = High / full range (0..11). */
export const DEFAULT_TACTIC_DEPTH_VALUE: TacticDepthValue = PRESET_RANGES[DEPTH_DEFAULT_PRESET];

// ─── Helpers ──────────────────────────────────────────────────────────────────

/**
 * Derive which preset the {min, max} range matches exactly, or null when the
 * range is custom (matches no preset).
 */
export function derivePreset(min: number, max: number): TacticDepthPreset | null {
  for (const preset of PRESET_ORDER) {
    const r = PRESET_RANGES[preset];
    if (r.min === min && r.max === max) return preset;
  }
  return null;
}

/** Inverse of derivePreset — preset name → range. */
export function presetToRange(preset: TacticDepthPreset): TacticDepthValue {
  return PRESET_RANGES[preset];
}

/**
 * Convert a slider tuple [lo, hi] into a TacticDepthValue, clamping into the
 * domain. Both bounds are literal depth values (no unbounded/null endpoints).
 */
export function sliderToRange(lo: number, hi: number): TacticDepthValue {
  return {
    min: Math.max(DEPTH_MIN, Math.min(lo, hi)),
    max: Math.min(DEPTH_MAX, Math.max(lo, hi)),
  };
}

/**
 * Summary text for the active depth range. Always shows the range using the
 * 1-based display numbers (e.g. `Intermediate: 1-6`); when it matches a preset,
 * the preset name is prefixed. A custom range renders bare (`3-5`, or `4` when
 * min === max). Internal values stay 0-based; only the display is offset.
 */
export function formatDepthSummary(value: TacticDepthValue): string {
  const lo = toDisplayDepth(value.min);
  const hi = toDisplayDepth(value.max);
  const range = value.min === value.max ? `${lo}` : `${lo}-${hi}`;
  const preset = derivePreset(value.min, value.max);
  return preset ? `${PRESET_LABELS[preset]}: ${range}` : range;
}

/**
 * Build the depth API query params. Both bounds are always sent — the range is
 * always a concrete [min, max] in depth units, and the backend treats them as
 * inclusive bounds (each side individually optional server-side).
 */
export function depthToQueryParams(
  min: number,
  max: number,
): { min_tactic_depth: number; max_tactic_depth: number } {
  return { min_tactic_depth: min, max_tactic_depth: max };
}
