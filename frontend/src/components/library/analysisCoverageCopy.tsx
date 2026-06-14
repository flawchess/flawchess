/**
 * Shared constants for game analysis coverage UX (Phase 118).
 *
 * Exported as a component-free module so it can be imported by both badge
 * tooltips and full-width empty states without tripping react-refresh's
 * only-export-components rule.
 */

/** Coverage ratio below which the guest sign-up CTA appears (D-118-09). */
export const LOW_COVERAGE_THRESHOLD = 0.8;

/** Popover body copy for the EvalCoverageBadge info popover. */
export const ANALYSIS_COVERAGE_INFO_COPY =
  'Full Stockfish analysis lets FlawChess classify blunders, mistakes, and inaccuracies. ' +
  'We analyze your most recent games automatically in the background, and staying active ' +
  'on FlawChess keeps your games near the front of the queue. ' +
  'To analyze one game right away, use the "Analyze" button on its card.';
