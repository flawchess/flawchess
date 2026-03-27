/**
 * Centralized theme constants.
 * Board square colors, primary accent colors, WDL colors, gauge zone colors, etc.
 * — single source of truth so branding changes only need one edit.
 */

// Board square colors (warm wood tones)
export const BOARD_DARK_SQUARE = '#B68965';
export const BOARD_LIGHT_SQUARE = '#F0DAB7';

export const darkSquareStyle = { backgroundColor: BOARD_DARK_SQUARE } as const;
export const lightSquareStyle = { backgroundColor: BOARD_LIGHT_SQUARE } as const;

/**
 * Tailwind classes for branded primary buttons.
 * Hex values must be written as literals here (not interpolated from constants)
 * because Tailwind scans source files at build time and can't resolve dynamic strings.
 * Update both the class string and the constants below when changing button colors.
 */
export const PRIMARY_BUTTON_CLASS = 'bg-[#8B5E3C] hover:bg-[#6B4226] text-white';

// WDL colors — used in all win/draw/loss visualizations
// Richer base colors; the glass overlay softens them visually when applied
export const WDL_WIN = 'oklch(0.50 0.14 145)';
export const WDL_DRAW = 'oklch(0.60 0.02 260)';
export const WDL_LOSS = 'oklch(0.50 0.15 25)';

// Glass-effect overlay: white highlight fading to transparent
// Applied as backgroundImage on WDL bar segments for a polished look
export const GLASS_OVERLAY =
  'linear-gradient(to bottom, rgba(255,255,255,0.35) 0%, rgba(255,255,255,0.05) 60%, rgba(0,0,0,0.05) 100%)';

// Semantic gauge zone colors — reuse WDL red/green, amber matched in brightness
export const GAUGE_DANGER = WDL_LOSS;                    // red zone (same as loss)
export const GAUGE_WARNING = 'oklch(0.50 0.14 80)';     // amber zone (L/C match WDL)
export const GAUGE_SUCCESS = WDL_WIN;                    // green zone (same as win)

/** A single zone in a semicircle gauge — fraction-based bounds and fill color. */
export interface GaugeZone {
  from: number; // 0-1 fraction
  to: number;   // 0-1 fraction
  color: string;
}

/** Default gauge zone array (danger/warning/success) used when no custom zones are provided. */
export const DEFAULT_GAUGE_ZONES: GaugeZone[] = [
  { from: 0,    to: 0.6,  color: GAUGE_DANGER },
  { from: 0.6,  to: 0.8,  color: GAUGE_WARNING },
  { from: 0.8,  to: 1.0,  color: GAUGE_SUCCESS },
];

// Minimum games required for reliable stats — rows/charts below this threshold are dimmed
export const MIN_GAMES_FOR_RELIABLE_STATS = 10;

// Opacity applied to stats/charts with unreliable data (below MIN_GAMES_FOR_RELIABLE_STATS)
export const UNRELIABLE_OPACITY = 0.5;
