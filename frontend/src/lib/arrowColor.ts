// Arrow color utility — maps win percentage to oklch color string.
//
// Anchor colors match the WDL chart (WDLBar.tsx):
//   green = oklch(0.45 0.16 145)
//   grey  = oklch(0.55 0.01 260)
//   red   = oklch(0.45 0.17 25)

interface OklchColor {
  L: number;
  C: number;
  H: number;
}

const GREEN: OklchColor = { L: 0.45, C: 0.16, H: 145 };
const GREY: OklchColor = { L: 0.55, C: 0.01, H: 260 };
const RED: OklchColor = { L: 0.45, C: 0.17, H: 25 };

const LIGHTNESS_HOVER_BOOST = 0.15;

function lerp(a: number, b: number, t: number): number {
  return a + (b - a) * t;
}

function lerpColor(from: OklchColor, to: OklchColor, t: number): OklchColor {
  return {
    L: lerp(from.L, to.L, t),
    C: lerp(from.C, to.C, t),
    H: lerp(from.H, to.H, t),
  };
}

function winPctToColor(winPct: number): OklchColor {
  if (winPct >= 66) return GREEN;
  if (winPct <= 33) return RED;

  if (winPct <= 50) {
    // Interpolate red -> grey (winPct 33..50)
    const t = (winPct - 33) / 17;
    return lerpColor(RED, GREY, t);
  } else {
    // Interpolate grey -> green (winPct 50..66)
    const t = (winPct - 50) / 16;
    return lerpColor(GREY, GREEN, t);
  }
}

/**
 * Returns an oklch CSS color string for a board arrow.
 *
 * @param winPct   Win percentage, 0–100
 * @param opacity  Frequency-based opacity, 0–1 (ignored when isHovered=true)
 * @param isHovered Whether this arrow is currently hovered
 */
export function getArrowColor(winPct: number, opacity: number, isHovered: boolean): string {
  const color = winPctToColor(winPct);

  if (isHovered) {
    const L = Math.min(1, color.L + LIGHTNESS_HOVER_BOOST);
    return `oklch(${L} ${color.C} ${color.H})`;
  }

  return `oklch(${color.L} ${color.C} ${color.H} / ${opacity})`;
}
