/**
 * tacticDepth.ts — Phase 129 TACUI-06 (D-03).
 *
 * UNIT SPLIT (D-03, LOCKED):
 *   Slider domain:  FULL MOVES  (1..DEPTH_SLIDER_MAX_MOVES)
 *   API/DB value:   HALF-PLIES  (1:1 with the game_flaws depth column)
 *
 * The two domains are bridged by sliderToMax / maxToSlider via HALF_PLIES_PER_MOVE.
 * Every summary string, slider tick label, and thumb aria-label reads in FULL MOVES.
 * The API param max_tactic_depth receives the HALF-PLY value unchanged.
 *
 * Clone of opponentStrength.ts adapted for a single-bound depth value.
 */

// ─── Named constants (no magic numbers) ─────────────────────────────────────

/** Half-plies: 1 full move = 2 half-plies (Beginner preset). */
export const DEPTH_PRESET_BEGINNER_MAX = 2;

/** Half-plies: 3 full moves = 6 half-plies (Intermediate preset, always-on default). */
export const DEPTH_PRESET_INTERMEDIATE_MAX = 6;

/** No cap — shows all tactic depths (Advanced preset). */
export const DEPTH_PRESET_ADVANCED_MAX: null = null;

/** Minimum slider position in full moves. */
export const DEPTH_SLIDER_MIN_MOVES = 1;

/**
 * Maximum slider position in full moves.
 * 5 full moves = 10 half-plies; Phase 127 data shows near-zero counts beyond ~8 half-plies.
 * Slider at this position is equivalent to Advanced (no cap, maxMoves=null).
 */
export const DEPTH_SLIDER_MAX_MOVES = 5;

/** Step size in full moves (one move per step). */
export const DEPTH_SLIDER_STEP = 1;

/** Conversion factor: full-move (slider) to half-ply (API). */
export const HALF_PLIES_PER_MOVE = 2;

/** D-02: always-on depth filter; default preset is Intermediate. */
export const DEPTH_DEFAULT_PRESET = 'intermediate' as const;

// ─── Types ────────────────────────────────────────────────────────────────────

export type TacticDepthPreset = 'beginner' | 'intermediate' | 'advanced';

/**
 * Depth value shape carried through the UI.
 * `maxMoves` is in HALF-PLIES (despite the name "Moves") — it is the API-boundary
 * value that matches the DB column exactly. null = no cap (Advanced).
 */
export interface TacticDepthValue {
  preset: TacticDepthPreset;
  /** Half-ply API/DB value. null = no cap (Advanced). Named "maxMoves" for continuity. */
  maxMoves: number | null;
}

// ─── Helpers ──────────────────────────────────────────────────────────────────

/**
 * Derive which preset matches the given half-ply maxMoves value.
 * Returns null when no preset matches exactly (custom slider position).
 */
export function derivePreset(maxMoves: number | null): TacticDepthPreset | null {
  if (maxMoves === DEPTH_PRESET_BEGINNER_MAX) return 'beginner';
  if (maxMoves === DEPTH_PRESET_INTERMEDIATE_MAX) return 'intermediate';
  if (maxMoves === DEPTH_PRESET_ADVANCED_MAX) return 'advanced';
  return null;
}

/** Preset name to half-ply maxMoves value. Inverse of derivePreset for named presets. */
export function presetToMax(preset: TacticDepthPreset): number | null {
  switch (preset) {
    case 'beginner':
      return DEPTH_PRESET_BEGINNER_MAX;
    case 'intermediate':
      return DEPTH_PRESET_INTERMEDIATE_MAX;
    case 'advanced':
      return DEPTH_PRESET_ADVANCED_MAX;
  }
}

/**
 * Convert a full-move slider position to a half-ply maxMoves API value.
 * Slider at DEPTH_SLIDER_MAX_MOVES = Advanced (no cap = null).
 */
export function sliderToMax(sliderMoves: number): number | null {
  if (sliderMoves >= DEPTH_SLIDER_MAX_MOVES) return null;
  return sliderMoves * HALF_PLIES_PER_MOVE;
}

/**
 * Convert a half-ply maxMoves API value to a full-move slider position.
 * null (no cap) maps to DEPTH_SLIDER_MAX_MOVES.
 */
export function maxToSlider(maxMoves: number | null): number {
  if (maxMoves === null) return DEPTH_SLIDER_MAX_MOVES;
  return Math.ceil(maxMoves / HALF_PLIES_PER_MOVE);
}

/**
 * Summary text for the active depth value (reads in FULL MOVES per D-03).
 * Uses preset label when the maxMoves exactly matches a preset; Custom otherwise.
 * No em-dashes.
 */
export function formatDepthSummary(value: TacticDepthValue): string {
  const detected = derivePreset(value.maxMoves);
  switch (detected) {
    case 'beginner':
      return 'Beginner (1 move)';
    case 'intermediate':
      return 'Intermediate (≤ 3 moves deep)';
    case 'advanced':
      return 'Advanced (all)';
    default: {
      // Custom: convert half-plies to full moves for the display string.
      const fullMoves =
        value.maxMoves != null ? Math.ceil(value.maxMoves / HALF_PLIES_PER_MOVE) : DEPTH_SLIDER_MAX_MOVES;
      return `Custom (≤ ${fullMoves} moves)`;
    }
  }
}

/**
 * Build the max_tactic_depth API query param.
 * Returns empty object when maxMoves is null (Advanced/no cap — omit the param).
 * Passes the half-ply value through unchanged to the API.
 */
export function depthToQueryParam(maxMoves: number | null): { max_tactic_depth?: number } {
  if (maxMoves === null) return {};
  return { max_tactic_depth: maxMoves };
}
