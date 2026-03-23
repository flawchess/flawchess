// Arrow color utility — maps WDL percentages to gradient oklch colors.
//
// Colors smoothly transition from grey to green as win rate goes from 55% to 65%,
// and from grey to red as loss rate goes from 55% to 65%. Moves with fewer than
// MIN_GAMES_FOR_COLOR games remain grey regardless of win/loss rate.
//
// Base grey endpoint: oklch(0.75 0.01 260)
// Full green:         oklch(0.45 0.16 145)
// Full red:           oklch(0.45 0.17 25)
//
// Hover variants use boosted lightness: 0.9 at grey end, 0.6 at color end.
//
// Frequency is encoded as arrow thickness (handled by ChessBoard).

const MIN_GAMES_FOR_COLOR = 10;

// Gradient range: below GRADIENT_START = grey, above GRADIENT_END = full color
const GRADIENT_START = 55; // percentage where color gradient begins (t=0)
const GRADIENT_END = 65;   // percentage where full color is reached (t=1)

// Grey oklch components (both normal and hover share chroma/hue)
const GREY_L = 0.75;
const GREY_L_HOVER = 0.9;
const GREY_C = 0.01;
const GREY_H = 260;

// Green oklch components
const GREEN_L = 0.45;
const GREEN_L_HOVER = 0.6;
const GREEN_C = 0.16;
const GREEN_H = 145;

// Red oklch components
const RED_L = 0.45;
const RED_L_HOVER = 0.6;
const RED_C = 0.17;
const RED_H = 25;

/** Clamp a value to [min, max]. */
function clamp(value: number, min: number, max: number): number {
  return Math.max(min, Math.min(max, value));
}

/** Linear interpolation between a and b at parameter t (0–1). */
function lerp(a: number, b: number, t: number): number {
  return a + (b - a) * t;
}

/** Compute gradient t value for a percentage: 0 at GRADIENT_START, 1 at GRADIENT_END. */
function gradientT(pct: number): number {
  return clamp((pct - GRADIENT_START) / (GRADIENT_END - GRADIENT_START), 0, 1);
}

/** Format an oklch color string with 2 decimal places. */
function oklch(l: number, c: number, h: number): string {
  return `oklch(${l.toFixed(2)} ${c.toFixed(2)} ${h.toFixed(1)})`;
}

/**
 * Returns an oklch CSS color string for a board arrow.
 * Colors transition smoothly from grey (at 55% win/loss) to full green/red (at 65%+).
 *
 * @param winPct    Win percentage, 0–100
 * @param lossPct   Loss percentage, 0–100
 * @param gameCount Absolute game count for this move
 * @param isHovered Whether this arrow is currently hovered
 */
export function getArrowColor(winPct: number, lossPct: number, gameCount: number, isHovered: boolean): string {
  const greyL = isHovered ? GREY_L_HOVER : GREY_L;

  // Below minimum game threshold — always grey
  if (gameCount < MIN_GAMES_FOR_COLOR) {
    return oklch(greyL, GREY_C, GREY_H);
  }

  const tWin = gradientT(winPct);
  const tLoss = gradientT(lossPct);

  // Neutral zone: both t values are 0 — return grey
  if (tWin === 0 && tLoss === 0) {
    return oklch(greyL, GREY_C, GREY_H);
  }

  // Edge case: both win and loss exceed gradient start — use the higher t value
  if (tWin >= tLoss) {
    // Green gradient
    const t = tWin;
    const greenL = isHovered ? GREEN_L_HOVER : GREEN_L;
    return oklch(
      lerp(greyL, greenL, t),
      lerp(GREY_C, GREEN_C, t),
      lerp(GREY_H, GREEN_H, t),
    );
  } else {
    // Red gradient
    const t = tLoss;
    const redL = isHovered ? RED_L_HOVER : RED_L;
    return oklch(
      lerp(greyL, redL, t),
      lerp(GREY_C, RED_C, t),
      lerp(GREY_H, RED_H, t),
    );
  }
}

/**
 * Returns a sort key for an arrow color string, used to determine rendering order.
 * Green (green-ish hue) = 0 (drawn last = on top), red = 1, grey = 2 (drawn first = bottom).
 *
 * Parses the hue and chroma from an oklch string to classify:
 * - Low chroma (< 0.05) → grey (key 2)
 * - Hue near GREEN_H (145) → green (key 0)
 * - Hue near RED_H (25) → red (key 1)
 *
 * @param color oklch CSS color string produced by getArrowColor
 */
export function arrowSortKey(color: string): number {
  const match = color.match(/oklch\(([0-9.]+)\s+([0-9.]+)\s+([0-9.]+)\)/);
  if (!match) return 2; // fallback: treat as grey

  const c = parseFloat(match[2]);
  const h = parseFloat(match[3]);

  // Near-zero chroma means grey
  if (c < 0.05) return 2;

  // Distinguish green (hue ~145) from red (hue ~25) by checking which is closer.
  // The gradient keeps hues between 25 and 260, so green hue is 145 and red hue is 25.
  const distToGreen = Math.abs(h - GREEN_H);
  const distToRed = Math.min(Math.abs(h - RED_H), Math.abs(h - RED_H + 360));

  return distToGreen <= distToRed ? 0 : 1;
}
