import type { OpponentStrengthPreset, OpponentStrengthRange } from '@/types/api';

// Slider domain (in Elo gap, opponent − user). Endpoints are unbounded:
// reaching SLIDER_MIN/MAX on a handle is equivalent to `null` (no filter
// on that side).
export const SLIDER_MIN = -200;
export const SLIDER_MAX = 200;
export const SLIDER_STEP = 50;

// Inclusive threshold defining "stronger" vs "similar" vs "weaker". Matches
// app/core/opponent_strength.py PRESET_THRESHOLD.
export const PRESET_THRESHOLD = 50;

export const ANY_RANGE: OpponentStrengthRange = { min: null, max: null };

export const PRESET_RANGES: Record<OpponentStrengthPreset, OpponentStrengthRange> = {
  any: ANY_RANGE,
  stronger: { min: PRESET_THRESHOLD, max: null },
  similar: { min: -PRESET_THRESHOLD, max: PRESET_THRESHOLD },
  weaker: { min: null, max: -PRESET_THRESHOLD },
};

export const PRESET_LABELS: Record<OpponentStrengthPreset, string> = {
  any: 'Any',
  stronger: 'Stronger',
  similar: 'Similar',
  weaker: 'Weaker',
};

export const PRESET_ORDER: OpponentStrengthPreset[] = ['any', 'stronger', 'similar', 'weaker'];

/**
 * Detect which preset the given range corresponds to, or null when the range
 * is custom (matches no preset exactly).
 */
export function derivePreset(range: OpponentStrengthRange): OpponentStrengthPreset | null {
  for (const preset of PRESET_ORDER) {
    const r = PRESET_RANGES[preset];
    if (r.min === range.min && r.max === range.max) return preset;
  }
  return null;
}

/** Inverse of derivePreset — preset name → range. */
export function presetToRange(preset: OpponentStrengthPreset): OpponentStrengthRange {
  return PRESET_RANGES[preset];
}

/**
 * Convert a slider tuple [lo, hi] (in domain [SLIDER_MIN, SLIDER_MAX]) into
 * an OpponentStrengthRange where extreme endpoints map to `null` (unbounded).
 */
export function sliderToRange(lo: number, hi: number): OpponentStrengthRange {
  return {
    min: lo <= SLIDER_MIN ? null : lo,
    max: hi >= SLIDER_MAX ? null : hi,
  };
}

/**
 * Inverse: range → slider tuple, clamping null to the slider extremes.
 */
export function rangeToSlider(range: OpponentStrengthRange): [number, number] {
  return [range.min ?? SLIDER_MIN, range.max ?? SLIDER_MAX];
}

/** True when the range filter is active (i.e. not "Any"). */
export function isRangeActive(range: OpponentStrengthRange): boolean {
  return range.min !== null || range.max !== null;
}

/**
 * Format a single bound for the summary line. `null` becomes `≤−200` or
 * `≥+200` to communicate the unbounded semantics; finite values are signed.
 */
function formatBound(value: number, signed: boolean): string {
  // Use the proper minus sign (U+2212) for negatives so the signed format
  // matches the slider tick labels.
  if (value < 0) return `−${Math.abs(value)}`;
  if (signed && value > 0) return `+${value}`;
  return `${value}`;
}

/**
 * Compact summary text for the active range. Returns the preset name when one
 * matches, else a formatted range like `−50 … +200` or `≤−100 … +50`.
 */
export function formatRangeSummary(range: OpponentStrengthRange): string {
  const preset = derivePreset(range);
  if (preset) return PRESET_LABELS[preset];

  const minLabel = range.min === null ? `≤${formatBound(SLIDER_MIN, false)}` : formatBound(range.min, true);
  const maxLabel = range.max === null ? `≥+${SLIDER_MAX}` : formatBound(range.max, true);
  return `${minLabel} … ${maxLabel}`;
}

/**
 * Build the API query params for the opponent-gap filter. Returns an empty
 * object when both bounds are null so unbounded filters don't appear in the
 * query string at all.
 */
export function rangeToQueryParams(
  range: OpponentStrengthRange,
): { opponent_gap_min?: number; opponent_gap_max?: number } {
  const params: { opponent_gap_min?: number; opponent_gap_max?: number } = {};
  if (range.min !== null) params.opponent_gap_min = range.min;
  if (range.max !== null) params.opponent_gap_max = range.max;
  return params;
}
