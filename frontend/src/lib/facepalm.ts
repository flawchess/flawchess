/**
 * Facepalm filter: units, presets and API mapping.
 *
 * UNIT: the slider handles are whole percents 0..100 in steps of FACEPALM_STEP.
 * The upper handle covers its whole 5% bucket, so the API upper bound is the
 * handle plus (STEP - 1), except at 100 (D-10). The API speaks inclusive floored
 * integer percents, matching the whole percent the Facepalm chip shows.
 *
 * The 30 / 70 preset cutoffs are UI constants (D-09). They are unrelated to the
 * blunder-check drill cut.
 *
 * The filter is a two-handle RANGE [min, max]. All (0..100) is the default and
 * filters nothing: at All no facepalm param is sent (D-04), so the request and
 * the react-query key are unchanged. Cloned in spirit from tacticDepth.ts.
 */

// ─── Named constants (no magic numbers) ─────────────────────────────────────

/** Slider domain minimum (whole percent). */
export const FACEPALM_PCT_MIN = 0;

/** Slider domain maximum (whole percent). */
export const FACEPALM_PCT_MAX = 100;

/** Slider step in whole percents. */
export const FACEPALM_STEP = 5;

/** Lower edge of the Mid preset (whole percent, UI cutoff, D-09). */
const FACEPALM_MID_CUTOFF = 30;

/** Lower edge of the High preset (whole percent, UI cutoff, D-09). */
const FACEPALM_HIGH_CUTOFF = 70;

/** Multiplier turning a 0..1 score into a percent. */
const FACEPALM_PCT_SCALE = 100;

/** Default preset: the full range, which filters nothing. */
export const FACEPALM_DEFAULT_PRESET = 'all' as const;

// ─── Types ────────────────────────────────────────────────────────────────────

export type FacepalmPreset = 'all' | 'low' | 'mid' | 'high';

/**
 * Slider handle positions in whole percents in [FACEPALM_PCT_MIN, FACEPALM_PCT_MAX].
 * min === max is valid (e.g. {40, 40} = the 40..44% bucket).
 */
export interface FacepalmValue {
  min: number;
  max: number;
}

// ─── Presets ────────────────────────────────────────────────────────────────

export const PRESET_RANGES: Record<FacepalmPreset, FacepalmValue> = {
  all: { min: FACEPALM_PCT_MIN, max: FACEPALM_PCT_MAX },
  low: { min: FACEPALM_PCT_MIN, max: FACEPALM_MID_CUTOFF - FACEPALM_STEP },
  mid: { min: FACEPALM_MID_CUTOFF, max: FACEPALM_HIGH_CUTOFF - FACEPALM_STEP },
  high: { min: FACEPALM_HIGH_CUTOFF, max: FACEPALM_PCT_MAX },
};

/** Short preset names shown on the chips (the range goes in the summary). */
export const PRESET_LABELS: Record<FacepalmPreset, string> = {
  all: 'All',
  low: 'Low',
  mid: 'Mid',
  high: 'High',
};

export const PRESET_ORDER: FacepalmPreset[] = ['all', 'low', 'mid', 'high'];

/** Default range = All (0..100). */
export const DEFAULT_FACEPALM_VALUE: FacepalmValue = PRESET_RANGES[FACEPALM_DEFAULT_PRESET];

// ─── Helpers ──────────────────────────────────────────────────────────────────

/** Which preset the {min, max} handles match exactly, or null for a custom range. */
export function derivePreset(min: number, max: number): FacepalmPreset | null {
  for (const preset of PRESET_ORDER) {
    const r = PRESET_RANGES[preset];
    if (r.min === min && r.max === max) return preset;
  }
  return null;
}

/** Inverse of derivePreset: preset name to handle range. */
export function presetToRange(preset: FacepalmPreset): FacepalmValue {
  return PRESET_RANGES[preset];
}

/** Convert a slider tuple [lo, hi] into a FacepalmValue, clamping into the domain and ordering. */
export function sliderToRange(lo: number, hi: number): FacepalmValue {
  return {
    min: Math.max(FACEPALM_PCT_MIN, Math.min(lo, hi)),
    max: Math.min(FACEPALM_PCT_MAX, Math.max(lo, hi)),
  };
}

/**
 * Upper end of the range as shown and sent to the API: the upper handle covers its
 * whole bucket (handle + STEP - 1), except at the domain maximum where it is 100.
 */
export function displayUpper(hi: number): number {
  return hi >= FACEPALM_PCT_MAX ? FACEPALM_PCT_MAX : hi + FACEPALM_STEP - 1;
}

/** True unless the handles sit at the full range (All). */
export function isFacepalmNarrowed(value: FacepalmValue): boolean {
  return value.min !== FACEPALM_PCT_MIN || value.max !== FACEPALM_PCT_MAX;
}

/**
 * Summary text for the active range: `All` at the full range, otherwise
 * `${min}-${upper}%` (or `${min}%` when both ends are equal) in the same units
 * the API receives.
 */
export function formatFacepalmSummary(value: FacepalmValue): string {
  if (!isFacepalmNarrowed(value)) return PRESET_LABELS[FACEPALM_DEFAULT_PRESET];
  const upper = displayUpper(value.max);
  return value.min === upper ? `${value.min}%` : `${value.min}-${upper}%`;
}

/**
 * Build the facepalm API query params: empty at the full range (D-04, so the
 * request and cache key do not change), else inclusive floored percents.
 */
export function facepalmToQueryParams(value: FacepalmValue): {
  min_facepalm_pct?: number;
  max_facepalm_pct?: number;
} {
  if (!isFacepalmNarrowed(value)) return {};
  return { min_facepalm_pct: value.min, max_facepalm_pct: displayUpper(value.max) };
}

/**
 * Whole percent shown in the Facepalm chip and its popover for a raw 0..1 score.
 * Rounded DOWN so the chip percent always lies in the band the filter puts the
 * flaw in (0.697 shows 69% and sits in Mid); the API compares the same
 * double-widened value against k/100. Clamped to the slider domain.
 */
export function toFacepalmPct(score: number): number {
  const pct = Math.floor(score * FACEPALM_PCT_SCALE);
  return Math.max(FACEPALM_PCT_MIN, Math.min(FACEPALM_PCT_MAX, pct));
}
