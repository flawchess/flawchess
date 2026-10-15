/**
 * Shared constants for game analysis coverage UX (Phase 118).
 *
 * Exported as a component-free module so it can be imported by both badge
 * tooltips and full-width empty states without tripping react-refresh's
 * only-export-components rule.
 */

/** Coverage ratio below which the guest sign-up CTA appears (D-118-09). */
export const LOW_COVERAGE_THRESHOLD = 0.8;

/**
 * Coverage ratio (per selected TC) below which the Library Stats basis line is tinted and
 * says the numbers are still moving. Not 1.0: a drain stuck on a game or two would
 * otherwise keep "still updating" up forever on a library that is effectively done.
 */
export const COVERAGE_UPDATING_THRESHOLD = 0.98;

/** Basis-line hint for a signed-up user whose games are still being analyzed. */
export const COVERAGE_UPDATING_HINT = 'Stats below update as analysis continues.';

/** Basis-line hint for a guest: no background analysis, so nothing is "updating". */
export const COVERAGE_GUEST_HINT = 'Only analyzed games are counted.';

/** Popover body copy for the EvalCoverageBadge info popover. */
export const ANALYSIS_COVERAGE_INFO_COPY =
  'Full Stockfish analysis lets FlawChess classify blunders, mistakes, and inaccuracies. ' +
  'To analyze a single game right away, use the "Analyze" button on its card. ' +
  'Signing up unlocks automatic background analysis of all your games — no per-game clicking needed.';
