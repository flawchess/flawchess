/**
 * Shared timing and color-stop constants for the deep-link highlight pulse,
 * applied in sync to:
 *  - the arrow on the chessboard (.animate-arrow-pulse, see index.css)
 *  - the highlighted row in MoveExplorer (.animate-row-highlight-pulse)
 *
 * Total pulse window = HIGHLIGHT_PULSE_ITERATIONS × HIGHLIGHT_PULSE_DURATION_MS.
 * Both keyframes are driven from these values via inline animationDuration /
 * animationIterationCount, so changing a value here re-syncs both pulses.
 */
export const HIGHLIGHT_PULSE_ITERATIONS = 7;
export const HIGHLIGHT_PULSE_DURATION_MS = 700;

/**
 * Alpha hex stops appended to a 6-digit severity hex to produce the row
 * background tint at each keyframe of `row-highlight-pulse`. Sized to mirror
 * the arrow's 0.45 → 1 → 0.75 opacity pulse, while the resting alpha (0x26 ≈
 * 15%) matches the existing `bg-blue-500/15` selection brightness so the
 * deep-link tint reads at the same intensity as the mobile-tap highlight.
 */
export const HIGHLIGHT_BG_LOW_ALPHA = '12';   //  ~7%  (≈ arrow opacity 0.45 × rest)
export const HIGHLIGHT_BG_HIGH_ALPHA = '40';  // ~25%  (peak — slightly above rest, like arrow's 1.0 vs 0.75)
export const HIGHLIGHT_BG_REST_ALPHA = '26';  // ~15%  (resting tint, matches bg-blue-500/15)
