/**
 * Facepalm filter: units, presets and API mapping.
 *
 * UNIT: the slider handles are whole percents 0..100 in steps of FACEPALM_STEP.
 * Both handles are sent to the API as they read: inclusive floored integer
 * percents, matching the whole percent the Facepalm chip shows. Because both
 * bounds are inclusive and land on multiples of 5, neighbouring presets share
 * their boundary percent (a 30% blunder is in both Low and Mid).
 *
 * The 30 / 70 preset cutoffs are UI constants (D-09). They are unrelated to the
 * blunder-check drill cut.
 *
 * The filter is a two-handle RANGE [min, max]. All (0..100) is the default and
 * filters nothing: at All no facepalm param is sent (D-04), so the request and
 * the react-query key are unchanged. Cloned in spirit from tacticDepth.ts.
 */

import { TAC_ALLOWED, TAC_ALLOWED_BG, TAC_ALLOWED_BORDER, TAC_MISSED, TAC_MISSED_BG } from '@/lib/theme';
import type { FacepalmType } from '@/types/library';

// ─── Named constants (no magic numbers) ─────────────────────────────────────

/** Slider domain minimum (whole percent). */
export const FACEPALM_PCT_MIN = 0;

/** Slider domain maximum (whole percent). */
export const FACEPALM_PCT_MAX = 100;

/** Slider step in whole percents. */
export const FACEPALM_STEP = 5;

/** Low / Mid boundary, included in both (whole percent, UI cutoff, D-09). */
const FACEPALM_MID_CUTOFF = 30;

/**
 * Mid / High boundary, included in both (whole percent, UI cutoff, D-09). It is also the stats
 * cut: the Flaws Timeline facepalm band and the Facepalm rows name it. The backend FACEPALM_STATS_MIN is
 * pinned to the same 70% by test.
 */
export const FACEPALM_HIGH_CUTOFF = 70;

/**
 * 257 D-20: the info popovers of the Facepalm blunders card and the Flaws Timeline facepalm
 * band. What a facepalm blunder is, plus the training pointer ("trains you to spot them", not a
 * promise to reduce them: no training effect is measured). No link, since a hover popover cannot
 * be pinned to click it.
 */
const FACEPALM_DEFINITION = `blunders that should have been easy to see for a player at your level`;
const FACEPALM_TRAINING = 'Blunder Check trains you to spot them before you move.';
export const FACEPALM_CARD_INFO = `Facepalm blunders are ${FACEPALM_DEFINITION}: our model gives them a facepalm score of ${FACEPALM_HIGH_CUTOFF}% or more. ${FACEPALM_TRAINING}`;
/** Shown in place of the comparison when too few of either side's blunders are scored. */
export const FACEPALM_LOW_COVERAGE_NOTE =
  'Not enough blunders in these games have a facepalm score yet to compare you with your opponents.';
export const FACEPALM_TIMELINE_INFO = `The darker band shows facepalm blunders: ${FACEPALM_DEFINITION} (facepalm score of ${FACEPALM_HIGH_CUTOFF}% or more). ${FACEPALM_TRAINING}`;

/**
 * What the facepalm score means, in one sentence. Shared by the score popover
 * (FacepalmExplanation) and the Facepalm Score filter info, so the two never drift.
 * `byOpponent` switches "your level" to "their level" for the opponent's blunders.
 */
export function facepalmScoreMeaning(byOpponent = false): string {
  const level = byOpponent ? 'their' : 'your';
  return `A high facepalm score tells you the blunder should have been easy to see for a player at ${level} level, a low one that it was probably hard to see.`;
}

/** Multiplier turning a 0..1 score into a percent. */
const FACEPALM_PCT_SCALE = 100;

/** Default preset: the full range, which filters nothing. */
export const FACEPALM_DEFAULT_PRESET = 'all' as const;

// ─── Types ────────────────────────────────────────────────────────────────────

export type FacepalmPreset = 'all' | 'low' | 'mid' | 'high';

/**
 * Slider handle positions in whole percents in [FACEPALM_PCT_MIN, FACEPALM_PCT_MAX].
 * min === max is valid (e.g. {40, 40} = blunders showing exactly 40%).
 */
export interface FacepalmValue {
  min: number;
  max: number;
}

// ─── Presets ────────────────────────────────────────────────────────────────

export const PRESET_RANGES: Record<FacepalmPreset, FacepalmValue> = {
  all: { min: FACEPALM_PCT_MIN, max: FACEPALM_PCT_MAX },
  low: { min: FACEPALM_PCT_MIN, max: FACEPALM_MID_CUTOFF },
  mid: { min: FACEPALM_MID_CUTOFF, max: FACEPALM_HIGH_CUTOFF },
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

/** True unless the handles sit at the full range (All). */
export function isFacepalmNarrowed(value: FacepalmValue): boolean {
  return value.min !== FACEPALM_PCT_MIN || value.max !== FACEPALM_PCT_MAX;
}

/**
 * Summary text for the active range: `All` at the full range, otherwise
 * `${min}-${max}%` (or `${min}%` when both ends are equal) in the same units
 * the API receives.
 */
export function formatFacepalmSummary(value: FacepalmValue): string {
  if (!isFacepalmNarrowed(value)) return PRESET_LABELS[FACEPALM_DEFAULT_PRESET];
  return value.min === value.max ? `${value.min}%` : `${value.min}-${value.max}%`;
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
  return { min_facepalm_pct: value.min, max_facepalm_pct: value.max };
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

/**
 * True when a blunder's score makes it a facepalm blunder (the "???" badge): the floored chip
 * percent reaches FACEPALM_HIGH_CUTOFF, the same cut the KPI tile, card and timeline band count.
 */
export function isFacepalmBlunder(score: number | null | undefined): boolean {
  return score != null && toFacepalmPct(score) >= FACEPALM_HIGH_CUTOFF;
}

// ─── Facepalm type tint (257 D-08) ──────────────────────────────────────────

/** Inline colours of a type-tinted Facepalm chip. */
export interface FacepalmTypeStyle {
  color: string;
  bg: string;
  border: string;
}

/** 257 D-10: short type name, shown lower-cased in aria-labels and the eval-chart tooltip. */
export const FACEPALM_TYPE_LABEL: Record<FacepalmType, string> = {
  missed_win: 'Missed win',
  allowed_loss: 'Allowed loss',
};

/**
 * 257 D-10: what the type means, in one mover-neutral sentence (so the opponent variant needs no
 * second wording). No probability words (D-05). Read as `${LABEL}: ${SENTENCE}`.
 */
export const FACEPALM_TYPE_SENTENCE: Record<FacepalmType, string> = {
  missed_win: 'the best move won material or led to checkmate, and was not played.',
  allowed_loss: 'the move gave away material or allowed checkmate.',
};

/**
 * 257 D-08: teal for a missed win, crimson for an allowed loss, the same hues as the tactic chips
 * of the same orientation. The missed border is the full teal and the allowed border the
 * lower-alpha crimson (the TacticMotifChip convention, which keeps the crimson fill legible).
 */
export const FACEPALM_TYPE_STYLE: Record<FacepalmType, FacepalmTypeStyle> = {
  missed_win: { color: TAC_MISSED, bg: TAC_MISSED_BG, border: TAC_MISSED },
  allowed_loss: { color: TAC_ALLOWED, bg: TAC_ALLOWED_BG, border: TAC_ALLOWED_BORDER },
};
