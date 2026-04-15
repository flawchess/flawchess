/**
 * Centralized theme constants.
 * Board square colors, primary accent colors, WDL colors, semantic zone colors, etc.
 * — single source of truth so branding changes only need one edit.
 */

// Board square colors (warm wood tones)
export const BOARD_DARK_SQUARE = '#B68965';
export const BOARD_LIGHT_SQUARE = '#F0DAB7';

export const darkSquareStyle = { backgroundColor: BOARD_DARK_SQUARE } as const;
export const lightSquareStyle = { backgroundColor: BOARD_LIGHT_SQUARE } as const;

// WDL colors — used in all win/draw/loss visualizations
// Richer base colors; the glass overlay softens them visually when applied
export const WDL_WIN = 'oklch(0.50 0.14 145)';
export const WDL_DRAW = 'oklch(0.60 0.02 260)';
export const WDL_LOSS = 'oklch(0.50 0.15 25)';

// Glass-effect overlay: white highlight fading to transparent
// Applied as backgroundImage on WDL bar segments for a polished look
export const GLASS_OVERLAY =
  'linear-gradient(to bottom, rgba(255,255,255,0.35) 0%, rgba(255,255,255,0.05) 60%, rgba(0,0,0,0.05) 100%)';

// Semantic zone colors — reuse WDL red/green, amber/blue matched in brightness
export const ZONE_DANGER = WDL_LOSS;                    // red zone (same as loss)
export const ZONE_WARNING = 'oklch(0.50 0.14 80)';      // amber zone (L/C match WDL)
export const ZONE_NEUTRAL = 'oklch(0.50 0.14 260)';     // blue zone (L/C match WDL)
export const ZONE_SUCCESS = WDL_WIN;                    // green zone (same as win)

// Endgame gauge zone colors — fixed per-bucket thresholds.
// Blue marks the "typical skill-cohort range" for each bucket; red below,
// green above. The Diff column + bullet chart in the same section still
// carry the peer-relative verdict against the user's actual opponents.
// The two signals can disagree when the opponent pool is unusual (e.g.
// filtered by opponent strength) — that disagreement is informative,
// not a bug.
export const GAUGE_DANGER = WDL_LOSS;                   // red zone
export const GAUGE_SUCCESS = WDL_WIN;                   // green zone
export const GAUGE_PEER = 'oklch(0.55 0.18 260)';       // blue peer-match zone (matches MY_SCORE_COLOR / Recovery line)

export interface GaugeZone {
  from: number;  // 0..1
  to: number;    // 0..1
  color: string; // CSS color
}

// Fallback used only when a caller omits the `zones` prop on EndgameGauge.
// All current callers pass explicit bucket-specific zones.
export const DEFAULT_GAUGE_ZONES: GaugeZone[] = [
  { from: 0, to: 0.4, color: GAUGE_DANGER },
  { from: 0.4, to: 0.6, color: GAUGE_PEER },
  { from: 0.6, to: 1.0, color: GAUGE_SUCCESS },
];

// Minimum games required for reliable stats — rows/charts below this threshold are dimmed
export const MIN_GAMES_FOR_RELIABLE_STATS = 10;

// Opacity applied to stats/charts with unreliable data (below MIN_GAMES_FOR_RELIABLE_STATS)
export const UNRELIABLE_OPACITY = 0.5;

// Modified-filter indicator dot — signals "current query uses non-default filters".
// Uses brand brown to differentiate from the existing red onboarding-hint dot.
// Tailwind classes (referenced in components): bg-brand-brown, text-brand-brown.
// The raw oklch is here for any JS-side usage (currently none).
export const FILTER_MODIFIED_DOT = 'oklch(0.55 0.08 55)'; // brand brown mid

// Time Pressure chart line colors (Phase 55)
// Blue for user's score line — same hue as recovery line in EndgameConvRecovChart
export const MY_SCORE_COLOR = 'oklch(0.55 0.18 260)';
// Red for opponent's score line — same as WDL_LOSS
export const OPP_SCORE_COLOR = WDL_LOSS;
