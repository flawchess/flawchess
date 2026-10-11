// AUTO-GENERATED — do not edit by hand.
// Source: app/services/endgame_zones.py
// Regenerate with: uv run python scripts/gen_endgame_zones_ts.py

// Half-width (percentage points) of the neutral band used for clock-difference
// shading on the Average Clock Difference over Time chart.
export const NEUTRAL_PCT_THRESHOLD = 5.0;

// Phase 88 D-03 / Phase 88.1 WR-04: minimum games per TC to qualify (e.g. as the primary TC).
// Source of truth: app/services/endgame_zones.py (codegen-mirrored to avoid drift).
export const MIN_GAMES_PER_TC_CARD = 20;

// Phase 98: per-(class × TC) typical ranges for Conv/Recov/ScoreGap.
// Read as plain [lower, upper] bounds (the Endgame Type Breakdown table draws them
// as the grey typical range behind each cell).
// Source: reports/benchmark/benchmarks-latest.md §3.4.1 (TC marginal p25/p75).
// Cohen's d ≈ 1.2–1.7 per class across TCs → all classes keep-separate.
// Score Gap TC d ≈ 0.07–0.18 (collapse) — four near-identical ΔES bands per
// class by design (Score Gap forced per-TC for visual consistency, D-04/D-14).
// pawnless omitted: n below per-class TC floor; hidden in the table UI.
export const PER_CLASS_TC_GAUGE_ZONES: Record<
  'rook' | 'minor_piece' | 'pawn' | 'queen' | 'mixed',
  Record<
    'bullet' | 'blitz' | 'rapid' | 'classical',
    { conversion: [number, number]; recovery: [number, number]; achievable_score_gap: [number, number] }
  >
> = {
  rook: {
    bullet: { conversion: [0.56, 0.75], recovery: [0.27, 0.43], achievable_score_gap: [-0.05, 0.05] },
    blitz: { conversion: [0.67, 0.82], recovery: [0.2, 0.37], achievable_score_gap: [-0.05, 0.05] },
    rapid: { conversion: [0.69, 0.83], recovery: [0.17, 0.3], achievable_score_gap: [-0.05, 0.05] },
    classical: { conversion: [0.74, 0.87], recovery: [0.13, 0.25], achievable_score_gap: [-0.05, 0.05] },
  },
  minor_piece: {
    bullet: { conversion: [0.51, 0.73], recovery: [0.29, 0.5], achievable_score_gap: [-0.04, 0.06] },
    blitz: { conversion: [0.64, 0.81], recovery: [0.21, 0.4], achievable_score_gap: [-0.04, 0.06] },
    rapid: { conversion: [0.68, 0.83], recovery: [0.15, 0.33], achievable_score_gap: [-0.04, 0.06] },
    classical: { conversion: [0.75, 0.89], recovery: [0.12, 0.28], achievable_score_gap: [-0.04, 0.06] },
  },
  pawn: {
    bullet: { conversion: [0.57, 0.8], recovery: [0.25, 0.46], achievable_score_gap: [-0.04, 0.05] },
    blitz: { conversion: [0.68, 0.87], recovery: [0.17, 0.36], achievable_score_gap: [-0.04, 0.05] },
    rapid: { conversion: [0.75, 0.91], recovery: [0.1, 0.28], achievable_score_gap: [-0.04, 0.05] },
    classical: { conversion: [0.8, 0.92], recovery: [0.08, 0.21], achievable_score_gap: [-0.04, 0.05] },
  },
  queen: {
    bullet: { conversion: [0.64, 0.83], recovery: [0.19, 0.36], achievable_score_gap: [-0.04, 0.05] },
    blitz: { conversion: [0.7, 0.9], recovery: [0.14, 0.31], achievable_score_gap: [-0.04, 0.05] },
    rapid: { conversion: [0.75, 0.92], recovery: [0.08, 0.25], achievable_score_gap: [-0.04, 0.05] },
    classical: { conversion: [0.88, 1.0], recovery: [0.0, 0.09], achievable_score_gap: [-0.04, 0.05] },
  },
  mixed: {
    bullet: { conversion: [0.6, 0.72], recovery: [0.3, 0.4], achievable_score_gap: [-0.03, 0.04] },
    blitz: { conversion: [0.68, 0.76], recovery: [0.25, 0.35], achievable_score_gap: [-0.03, 0.04] },
    rapid: { conversion: [0.7, 0.79], recovery: [0.23, 0.31], achievable_score_gap: [-0.03, 0.04] },
    classical: { conversion: [0.7, 0.83], recovery: [0.18, 0.3], achievable_score_gap: [-0.03, 0.04] },
  },
} as const;
