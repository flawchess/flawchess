/**
 * Pure math and vocabulary for the Library Stats you-vs-opponents gap bar
 * (Phase 239, sketch 010 round 5). No React: the GapBar, GapPopover and the
 * "What stands out" ranking all read from here so they never disagree.
 *
 * Sign convention: the API's gap is you minus opponents per 100 moves / games, so a
 * NEGATIVE gap means FEWER flaws, which is good. The bar flips it visually: zero is the
 * centre and better (negative) is drawn to the RIGHT, matching the Endgame percentile
 * bar where right is good.
 */

import { GAUGE_NEUTRAL, ZONE_DANGER, ZONE_SUCCESS } from '@/lib/theme';

/** The wider side of the benchmark band reaches this far (in %) from the centre. */
const GAP_BAND_HALF_POS = 25;
/** The outermost dot position, in % from either edge: the dot never touches the edge. */
export const GAP_EDGE_POS = 3;
export const GAP_CENTRE = 50;
/** Distance from the band edge to the saturated edge position, in % of the track. */
const GAP_OUTER_SPAN = GAP_CENTRE - GAP_BAND_HALF_POS - GAP_EDGE_POS;
/** Below this magnitude the gap reads as "same". */
const GAP_SAME_EPSILON = 0.005;
/** What gapWords returns for a gap below GAP_SAME_EPSILON. */
export const GAP_SAME_WORD = 'same';
/** Number formatting: at or above this magnitude one decimal, at or above the next none. */
const GAP_WORD_ONE_DP_FROM = 1;
const GAP_WORD_ZERO_DP_FROM = 10;

export type GapVerdict = 'better' | 'typical' | 'worse';

/**
 * View model of one you-vs-opponent cell (camelCase so the components never import
 * API types; the page adapts each payload bullet to it).
 */
export interface GapCell {
  /** you - opponents; null when neither side has a flaw to compare. */
  delta: number | null;
  zoneLo: number;
  zoneHi: number;
  /** False for an unviable family (D-11): no band, no verdict. */
  hasZone: boolean;
  /** Fewer flaws than the sample minimum (D-12): no verdict, row is faded by its container. */
  lowSample: boolean;
  youRate: number | null;
  oppRate: number | null;
  ciLow: number | null;
  ciHigh: number | null;
  pValue: number | null;
  youEvents: number;
  oppEvents: number;
}

/**
 * Position (0-100, % from the left) of a gap on the zero-centred track. Linear inside
 * the band (the wider band side maps to GAP_BAND_HALF_POS), then saturating with
 * 1 - e^-x (x in band widths) so large gaps approach the edge without clipping.
 */
export function gapPosition(delta: number, zoneLo: number, zoneHi: number): number {
  const s = Math.max(Math.abs(zoneLo), Math.abs(zoneHi));
  const a = Math.abs(delta);
  // Fewer flaws (negative gap) is better and is drawn to the right.
  const sign = delta < 0 ? 1 : -1;
  if (s === 0) {
    // A band collapsed onto zero has no scale: only a zero gap sits at the centre,
    // any other gap goes to the saturated edge on its side.
    return a === 0 ? GAP_CENTRE : GAP_CENTRE + sign * (GAP_BAND_HALF_POS + GAP_OUTER_SPAN);
  }
  let off: number;
  if (a <= s) {
    off = (GAP_BAND_HALF_POS * a) / s;
  } else {
    // A zero-width band (hi === lo) falls back to s for the saturation width.
    const width = zoneHi - zoneLo > 0 ? zoneHi - zoneLo : s;
    off = GAP_BAND_HALF_POS + GAP_OUTER_SPAN * (1 - Math.exp(-(a - s) / width));
  }
  return GAP_CENTRE + sign * off;
}

/** Lower is better for every flaw metric. */
export function gapVerdict(delta: number, zoneLo: number, zoneHi: number): GapVerdict {
  if (delta < zoneLo) return 'better';
  if (delta > zoneHi) return 'worse';
  return 'typical';
}

/** The verdict a cell may show; null when it must show none (zoneless, low sample, no gap). */
export function effectiveVerdict(cell: GapCell): GapVerdict | null {
  if (!cell.hasZone || cell.lowSample || cell.delta === null) return null;
  return gapVerdict(cell.delta, cell.zoneLo, cell.zoneHi);
}

/**
 * Dot position of a cell. A zoneless cell has no benchmark band, so it is positioned
 * against an undrawn virtual band of half-width max(you, opponents): the dot shows the
 * gap relative to the larger rate.
 */
export function cellPosition(cell: GapCell): number {
  if (cell.delta === null) return GAP_CENTRE;
  if (cell.hasZone) return gapPosition(cell.delta, cell.zoneLo, cell.zoneHi);
  const half = Math.max(cell.youRate ?? 0, cell.oppRate ?? 0);
  return gapPosition(cell.delta, -half, half);
}

/** Left offset and width (in %) of the drawn benchmark band; null for a zoneless cell. */
export function bandRange(cell: GapCell): { leftPct: number; widthPct: number } | null {
  if (!cell.hasZone) return null;
  // zoneHi is on the left (more flaws = worse), zoneLo on the right.
  const leftPct = gapPosition(cell.zoneHi, cell.zoneLo, cell.zoneHi);
  const rightPct = gapPosition(cell.zoneLo, cell.zoneLo, cell.zoneHi);
  return { leftPct, widthPct: rightPct - leftPct };
}

/** 12.3 -> "12", 1.74 -> "1.7", 0.419 -> "0.42". */
export function formatGapNumber(value: number): string {
  const magnitude = Math.abs(value);
  if (magnitude >= GAP_WORD_ZERO_DP_FROM) return value.toFixed(0);
  if (magnitude >= GAP_WORD_ONE_DP_FROM) return value.toFixed(1);
  return value.toFixed(2);
}

/** "1.7 fewer", "0.42 more" or "same". */
export function gapWords(delta: number): string {
  if (Math.abs(delta) < GAP_SAME_EPSILON) return GAP_SAME_WORD;
  return `${formatGapNumber(Math.abs(delta))} ${delta < 0 ? 'fewer' : 'more'}`;
}

/**
 * Signed number for the popover footer, with a typographic minus: "−0.66", "+0.25".
 * Two decimals below 10 (so a CI bound of -1.0028 reads "−1.00", not "−1.0"), none above.
 */
export function formatSignedGap(value: number): string {
  const sign = value > 0 ? '+' : value < 0 ? '−' : '';
  const magnitude = Math.abs(value);
  return `${sign}${magnitude >= GAP_WORD_ZERO_DP_FROM ? magnitude.toFixed(0) : magnitude.toFixed(2)}`;
}

/** Dot and word colour: green better, red worse, blue for typical or no verdict. */
export function gapVerdictColor(verdict: GapVerdict | null): string {
  if (verdict === 'better') return ZONE_SUCCESS;
  if (verdict === 'worse') return ZONE_DANGER;
  return GAUGE_NEUTRAL;
}
