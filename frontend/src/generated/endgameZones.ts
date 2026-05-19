// AUTO-GENERATED — do not edit by hand.
// Source: app/services/endgame_zones.py
// Regenerate with: uv run python scripts/gen_endgame_zones_ts.py

import { ZONE_DANGER, ZONE_NEUTRAL, ZONE_SUCCESS } from "@/lib/theme";

export type MaterialBucket = "conversion" | "parity" | "recovery";

export interface GaugeZone {
  from: number;
  to: number;
}

export const FIXED_GAUGE_ZONES: Record<MaterialBucket, GaugeZone[]> = {
  conversion: [
    { from: 0, to: 0.65 },
    { from: 0.65, to: 0.77 },
    { from: 0.77, to: 1.0 },
  ],
  parity: [
    { from: 0, to: 0.45 },
    { from: 0.45, to: 0.55 },
    { from: 0.55, to: 1.0 },
  ],
  recovery: [
    { from: 0, to: 0.24 },
    { from: 0.24, to: 0.36 },
    { from: 0.36, to: 1.0 },
  ],
};

export const NEUTRAL_PCT_THRESHOLD = 5.0;
export const NEUTRAL_TIMEOUT_THRESHOLD = 5.0;
export const SCORE_GAP_NEUTRAL_MIN = -0.1;
export const SCORE_GAP_NEUTRAL_MAX = 0.1;
export const ACHIEVABLE_SCORE_GAP_NEUTRAL_MIN = -0.05;
export const ACHIEVABLE_SCORE_GAP_NEUTRAL_MAX = 0.05;
// Phase 87.1 (SEED-016 D-04): per-span, per-type Score Gap neutral band.
// User-facing label: "Endgame Type Score Gap" (concepts) / "Score Gap" (card row).
// Internal registry key is `endgame_type_achievable_score_gap` for math-family grep.
export const ENDGAME_TYPE_SCORE_GAP_NEUTRAL_MIN = -0.04;
export const ENDGAME_TYPE_SCORE_GAP_NEUTRAL_MAX = 0.04;
// Phase 87.2 (D-02): per-bucket Section 2 ΔES Score Gap neutral bands.
export const SECTION2_SCORE_GAP_CONV_NEUTRAL_MIN = -0.11;
export const SECTION2_SCORE_GAP_CONV_NEUTRAL_MAX = 0.0;
export const SECTION2_SCORE_GAP_PARITY_NEUTRAL_MIN = -0.04;
export const SECTION2_SCORE_GAP_PARITY_NEUTRAL_MAX = 0.04;
export const SECTION2_SCORE_GAP_RECOV_NEUTRAL_MIN = 0.01;
export const SECTION2_SCORE_GAP_RECOV_NEUTRAL_MAX = 0.11;
// Phase 87.4 (D-05): SECTION2_SCORE_GAP_SKILL_NEUTRAL_* emission dropped
// alongside the Endgame Skill concept retirement.

// Phase 83 D-14/D-17: per-user entry_expected_score cohort band.
// Source: reports/benchmarks-2026-05-11.md §7 (pooled IQR aligned with
// endgame_score band for visual parity with the §0 final-score zone).
export const ENTRY_EXPECTED_SCORE_NEUTRAL_MIN = 0.45;
export const ENTRY_EXPECTED_SCORE_NEUTRAL_MAX = 0.55;

/**
 * Pick the zone color for the EG-entry expected-score bullet relative to the
 * cohort neutral band. Pure presentation — gating on confidence happens in the
 * consumer (mirrors endgameEntryEvalZoneColor).
 */
export function entryExpectedScoreZoneColor(value: number): string {
  if (value >= ENTRY_EXPECTED_SCORE_NEUTRAL_MAX) return ZONE_SUCCESS;
  if (value <= ENTRY_EXPECTED_SCORE_NEUTRAL_MIN) return ZONE_DANGER;
  return ZONE_NEUTRAL;
}

// Per-endgame-class typical bands for Conversion, Recovery, and Score Gap.
// Source: reports/benchmarks-2026-05-01.md (pooled p25/p75 per class).
// Phase 87.1 (SEED-016 D-04): achievable_score_gap added as a placeholder
// mirroring ENDGAME_TYPE_SCORE_GAP_NEUTRAL_MIN/MAX until §3.4.2 calibration.
// Each entry: { conversion: [lower, upper], recovery: [lower, upper],
// achievable_score_gap: [lower, upper] }.
// Wrap with colorizeGaugeZones() before passing to EndgameGauge (same
// pattern as FIXED_GAUGE_ZONES in EndgameScoreGapSection).
export const PER_CLASS_GAUGE_ZONES = {
  rook: { conversion: [0.65, 0.75], recovery: [0.26, 0.36], achievable_score_gap: [-0.05, 0.05] },
  minor_piece: { conversion: [0.63, 0.73], recovery: [0.28, 0.38], achievable_score_gap: [-0.04, 0.06] },
  pawn: { conversion: [0.67, 0.79], recovery: [0.23, 0.34], achievable_score_gap: [-0.04, 0.05] },
  queen: { conversion: [0.73, 0.83], recovery: [0.2, 0.3], achievable_score_gap: [-0.04, 0.05] },
  mixed: { conversion: [0.65, 0.75], recovery: [0.28, 0.38], achievable_score_gap: [-0.03, 0.04] },
  pawnless: { conversion: [0.7, 0.8], recovery: [0.21, 0.31], achievable_score_gap: [-0.04, 0.04] },
} as const;

export type EndgameClassKey = keyof typeof PER_CLASS_GAUGE_ZONES;

// Phase 88 D-02: per-(TC, pressure-quintile) neutral bands.
// Quintile 0 = 0-20% clock remaining (max pressure), 4 = 80-100%.
// Calibrated from reports/benchmarks-latest.md §3.3.3 (Phase 88-08, 2026-05-17).
// Sanity-rerun against opp-quintile semantics in Plan 88-12.
export const PRESSURE_BIN_SCORE_NEUTRAL_ZONES: Record<
  'bullet' | 'blitz' | 'rapid' | 'classical',
  Record<0 | 1 | 2 | 3 | 4, { min: number; max: number }>
> = {
  bullet: { 0: { min: -0.06, max: 0.06 }, 1: { min: -0.0481, max: 0.0524 }, 2: { min: -0.038, max: 0.0493 }, 3: { min: -0.0563, max: 0.06 }, 4: { min: -0.06, max: 0.06 } },
  blitz: { 0: { min: -0.06, max: 0.06 }, 1: { min: -0.0579, max: 0.06 }, 2: { min: -0.0557, max: 0.053 }, 3: { min: -0.0598, max: 0.0548 }, 4: { min: -0.06, max: 0.06 } },
  rapid: { 0: { min: -0.06, max: 0.06 }, 1: { min: -0.06, max: 0.06 }, 2: { min: -0.0563, max: 0.06 }, 3: { min: -0.0582, max: 0.06 }, 4: { min: -0.06, max: 0.06 } },
  classical: { 0: { min: -0.06, max: 0.06 }, 1: { min: -0.06, max: 0.06 }, 2: { min: -0.06, max: 0.06 }, 3: { min: -0.06, max: 0.06 }, 4: { min: -0.06, max: 0.06 } },
} as const;

// Phase 88 D-03 / Phase 88.1 WR-04: gating thresholds shared with backend.
// Source of truth: app/services/endgame_zones.py (codegen-mirrored to avoid drift).
export const MIN_GAMES_PER_TC_CARD = 20;
export const MIN_GAMES_PER_PRESSURE_BIN = 5;

/**
 * Look up the neutral band for a (TC, quintile) cell with explicit narrowing.
 * Phase 88.1 IN-06 / WR-03 — replaces the unsafe `[q as 0|1|2|3|4]!` pattern
 * with a defensive range check. Returns null if quintile is outside 0..4.
 */
export function getPressureBinBand(
  tc: 'bullet' | 'blitz' | 'rapid' | 'classical',
  quintile: number,
): { min: number; max: number } | null {
  if (quintile < 0 || quintile > 4) return null;
  const q = quintile as 0 | 1 | 2 | 3 | 4;
  const band = PRESSURE_BIN_SCORE_NEUTRAL_ZONES[tc][q];
  return band ?? null;
}

// Phase 88: Clock Gap scalar neutral band.
// Calibrated from reports/benchmarks-latest.md §3.3.1 clock-gap-% (Phase 88-08, 2026-05-17).
export const CLOCK_GAP_NEUTRAL_MIN = -0.065;
export const CLOCK_GAP_NEUTRAL_MAX = 0.047;
