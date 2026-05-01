// AUTO-GENERATED — do not edit by hand.
// Source: app/services/endgame_zones.py
// Regenerate with: uv run python scripts/gen_endgame_zones_ts.py

export type MaterialBucket = "conversion" | "parity" | "recovery";

export interface GaugeZone {
  from: number;
  to: number;
}

export const FIXED_GAUGE_ZONES: Record<MaterialBucket, GaugeZone[]> = {
  conversion: [
    { from: 0, to: 0.65 },
    { from: 0.65, to: 0.75 },
    { from: 0.75, to: 1.0 },
  ],
  parity: [
    { from: 0, to: 0.45 },
    { from: 0.45, to: 0.55 },
    { from: 0.55, to: 1.0 },
  ],
  recovery: [
    { from: 0, to: 0.25 },
    { from: 0.25, to: 0.4 },
    { from: 0.4, to: 1.0 },
  ],
};

export const ENDGAME_SKILL_ZONES: GaugeZone[] = [
  { from: 0, to: 0.45 },
  { from: 0.45, to: 0.55 },
  { from: 0.55, to: 1.0 },
];

export const NEUTRAL_PCT_THRESHOLD = 5.0;
export const NEUTRAL_TIMEOUT_THRESHOLD = 5.0;
export const SCORE_GAP_NEUTRAL_MIN = -0.1;
export const SCORE_GAP_NEUTRAL_MAX = 0.1;

// Per-endgame-class typical bands for Conversion and Recovery.
// Source: reports/benchmarks-2026-05-01.md (pooled p25/p75 per class).
// Each entry: { conversion: [lower, upper], recovery: [lower, upper] }.
// Wrap with colorizeGaugeZones() before passing to EndgameGauge (same
// pattern as FIXED_GAUGE_ZONES in EndgameScoreGapSection).
export const PER_CLASS_GAUGE_ZONES = {
  rook: { conversion: [0.65, 0.75], recovery: [0.28, 0.38] },
  minor_piece: { conversion: [0.63, 0.73], recovery: [0.31, 0.41] },
  pawn: { conversion: [0.67, 0.77], recovery: [0.26, 0.36] },
  queen: { conversion: [0.73, 0.83], recovery: [0.2, 0.3] },
  mixed: { conversion: [0.65, 0.75], recovery: [0.28, 0.38] },
  pawnless: { conversion: [0.7, 0.8], recovery: [0.21, 0.31] },
} as const;

export type EndgameClassKey = keyof typeof PER_CLASS_GAUGE_ZONES;
