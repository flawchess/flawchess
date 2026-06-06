/**
 * Frontend mirror of app/services/flaws_service.py threshold constants.
 * Source of truth is the Python module. Keep in sync manually.
 *
 * When thresholds change in flaws_service.py, update this file to match.
 *
 * Note: Severity drop thresholds (INACCURACY_DROP=0.05, MISTAKE_DROP=0.10, BLUNDER_DROP=0.15)
 * are omitted here; they mirror flaws_service.py but are not referenced by tag copy or any
 * frontend consumer yet. Add exports when they are first consumed.
 */

// Tempo thresholds — relative to base_time_seconds.
/** Fraction of base time below which a move is "low clock" */
export const TIME_PRESSURE_CLOCK_FRACTION = 0.05;
/** Absolute clock seconds fallback for low-clock detection */
export const TIME_PRESSURE_CLOCK_ABS_SECONDS = 30;
/** Fraction of base time below which a move is "hasty" */
export const HASTY_MOVE_FRACTION = 0.01;
/** Absolute seconds fallback for hasty-move detection */
export const HASTY_MOVE_ABS_SECONDS = 5;

// Result-changing thresholds.
/** Expected-score threshold for "winning" zone */
export const RESULT_WIN_THRESHOLD = 0.70;
/** Expected-score threshold for "at least drawing" zone */
export const RESULT_DRAW_THRESHOLD = 0.40;
