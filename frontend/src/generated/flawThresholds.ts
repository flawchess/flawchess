// AUTO-GENERATED — do not edit by hand.
// Source: app/services/flaws_service.py, app/services/eval_utils.py
// Regenerate with: uv run python scripts/gen_flaw_thresholds_ts.py

export const WINNING_LINE_ES = 0.6762;
export const LOSING_LINE_ES = 0.3238;
export const FROM_WINNING_ES = 0.7511;
export const SQUANDERED_EXIT_ES = 0.591;
export const TIME_PRESSURE_CLOCK_FRACTION = 0.05;
export const TIME_PRESSURE_CLOCK_ABS_SECONDS = 30.0;
export const HASTY_MOVE_FRACTION = 0.01;
export const HASTY_MOVE_ABS_SECONDS = 5.0;

// Expected-score drop tiers + sigmoid inputs for live move classification
// (Quick w8k item 4 — classifying freely-played moves with the live engine).
export const INACCURACY_DROP = 0.05;
export const MISTAKE_DROP = 0.1;
export const BLUNDER_DROP = 0.15;
export const MATE_CP_EQUIVALENT = 1000;
export const LICHESS_K = 0.00368208;
