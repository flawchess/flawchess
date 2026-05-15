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

export const ENDGAME_SKILL_ZONES: GaugeZone[] = [
  { from: 0, to: 0.47 },
  { from: 0.47, to: 0.55 },
  { from: 0.55, to: 1.0 },
];

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
export const SECTION2_SCORE_GAP_CONV_NEUTRAL_MIN = -0.05;
export const SECTION2_SCORE_GAP_CONV_NEUTRAL_MAX = 0.05;
export const SECTION2_SCORE_GAP_PARITY_NEUTRAL_MIN = -0.05;
export const SECTION2_SCORE_GAP_PARITY_NEUTRAL_MAX = 0.05;
export const SECTION2_SCORE_GAP_RECOV_NEUTRAL_MIN = -0.05;
export const SECTION2_SCORE_GAP_RECOV_NEUTRAL_MAX = 0.05;
export const SECTION2_SCORE_GAP_SKILL_NEUTRAL_MIN = -0.05;
export const SECTION2_SCORE_GAP_SKILL_NEUTRAL_MAX = 0.05;

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
  rook: { conversion: [0.65, 0.75], recovery: [0.26, 0.36], achievable_score_gap: [-0.05, 0.04] },
  minor_piece: { conversion: [0.63, 0.73], recovery: [0.31, 0.41], achievable_score_gap: [-0.04, 0.06] },
  pawn: { conversion: [0.67, 0.79], recovery: [0.23, 0.34], achievable_score_gap: [-0.04, 0.05] },
  queen: { conversion: [0.73, 0.83], recovery: [0.2, 0.3], achievable_score_gap: [-0.05, 0.05] },
  mixed: { conversion: [0.65, 0.75], recovery: [0.28, 0.38], achievable_score_gap: [-0.03, 0.04] },
  pawnless: { conversion: [0.7, 0.8], recovery: [0.21, 0.31], achievable_score_gap: [-0.04, 0.04] },
} as const;

export type EndgameClassKey = keyof typeof PER_CLASS_GAUGE_ZONES;
