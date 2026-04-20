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
    { from: 0.25, to: 0.35 },
    { from: 0.35, to: 1.0 },
  ],
};

export const ENDGAME_SKILL_ZONES: GaugeZone[] = [
  { from: 0, to: 0.45 },
  { from: 0.45, to: 0.55 },
  { from: 0.55, to: 1.0 },
];

export const NEUTRAL_PCT_THRESHOLD = 10.0;
export const NEUTRAL_TIMEOUT_THRESHOLD = 5.0;
export const SCORE_GAP_NEUTRAL_MIN = -0.1;
export const SCORE_GAP_NEUTRAL_MAX = 0.1;
export const NOTABLE_ENDGAME_ELO_DIVERGENCE_THRESHOLD = 100;
