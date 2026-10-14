/**
 * Pure math and vocabulary for the Library Stats you-vs-opponents gap bar
 * (Phase 239, sketch 010 round 5). No React: the GapBar and GapPopover both read from
 * here so they never disagree.
 *
 * Sign convention: the API's gap is you minus opponents per 100 moves / games, so a
 * NEGATIVE gap means FEWER flaws, which is good. The bar follows the number line: zero
 * is the centre and lower (better) gaps are drawn to the LEFT (Phase 239 D-14, UAT).
 *
 * Verdicts need significance (D-14): a gap outside the band whose 99% CI still covers 0
 * renders neutral like a typical one, and the popover says it could be chance.
 */

import {
  GAP_HEATMAP_NEUTRAL_FILL,
  GAP_HEATMAP_TINT_MAX_PERCENT,
  GAP_HEATMAP_TINT_MIN_PERCENT,
  GAUGE_NEUTRAL,
  ZONE_DANGER,
  ZONE_SUCCESS,
} from '@/lib/theme';

/** The benchmark band edge sits this far (in %) from the centre (bands are symmetric since D-15). */
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
/** What a gap cell shows when neither side has a flaw to compare (the bars and the heatmap). */
export const GAP_EMPTY_WORDS = 'No flaws yet';
/** The axis caption under the bars: fewer flaws (better) sit left on every gap bar. */
export const GAP_AXIS_LABELS = ['better', 'worse'] as const;
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
  /** The 99% CI on the gap excludes 0 (D-14): only then may an out-of-band gap be coloured. */
  significant: boolean;
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
 * the band (its half-width maps to GAP_BAND_HALF_POS), then saturating with 1 - e^-x
 * (x in band widths) so large gaps approach the edge without clipping. Bands are
 * symmetric since D-15; the max() over both sides only keeps an asymmetric band sane.
 */
export function gapPosition(delta: number, zoneLo: number, zoneHi: number): number {
  const s = Math.max(Math.abs(zoneLo), Math.abs(zoneHi));
  const a = Math.abs(delta);
  // Number line: fewer flaws (negative gap, better) is drawn to the left (D-14 flip).
  const sign = delta < 0 ? -1 : 1;
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

/** The band verdict before the significance gate; null without a band or a gap. */
function rawVerdict(cell: GapCell): GapVerdict | null {
  if (!cell.hasZone || cell.delta === null) return null;
  return gapVerdict(cell.delta, cell.zoneLo, cell.zoneHi);
}

/**
 * The verdict a cell shows; null when it has none. An out-of-band gap that is not
 * significant reads 'typical' (D-14): neutral dot and words. A zoneless cell (D-11) has
 * no band to be outside of, so it is judged on significance alone (D-16): better or worse
 * when its 99% CI excludes 0, no verdict otherwise.
 */
export function effectiveVerdict(cell: GapCell): GapVerdict | null {
  // Defensive: all four shown tactic families have bands today, but a §5 refresh could drop one.
  if (!cell.hasZone && cell.delta !== null) {
    if (!cell.significant) return null;
    return cell.delta < 0 ? 'better' : 'worse';
  }
  const raw = rawVerdict(cell);
  if (raw === null || raw === 'typical') return raw;
  return cell.significant ? raw : 'typical';
}

/** True when the gap is outside the band but not significant: it could be chance (D-14). */
export function isChanceGap(cell: GapCell): boolean {
  const raw = rawVerdict(cell);
  return raw !== null && raw !== 'typical' && !cell.significant;
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
  // zoneLo (fewer flaws, better) is on the left, zoneHi on the right.
  const leftPct = gapPosition(cell.zoneLo, cell.zoneLo, cell.zoneHi);
  const rightPct = gapPosition(cell.zoneHi, cell.zoneLo, cell.zoneHi);
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

export type GapHeatmapTint = 'better' | 'worse' | 'neutral';

/** The verdicts that tint a heatmap cell: a significant gap, in either direction. */
function isTintedVerdict(verdict: GapVerdict | null): verdict is 'better' | 'worse' {
  return verdict === 'better' || verdict === 'worse';
}

/**
 * The heatmap's tint scale: the largest |gap| among the SIGNIFICANT cells, 0 when none is.
 * Scaling against the strongest significant cell, not every cell, is deliberate: a large
 * non-significant gap (a rare combination with huge variance) would otherwise dim every
 * real signal, and the strongest significant cell must come out clearly saturated.
 */
export function gapHeatmapScale(cells: readonly GapCell[]): number {
  let scale = 0;
  for (const c of cells) {
    if (c.delta !== null && isTintedVerdict(effectiveVerdict(c))) {
      scale = Math.max(scale, Math.abs(c.delta));
    }
  }
  return scale;
}

/** Tint percent: linear from the floor to the max with |gap| / scale (max when scale is 0). */
function heatmapPercent(delta: number, scale: number): number {
  const share = scale <= 0 ? 1 : Math.min(1, Math.abs(delta) / scale);
  return Math.round(
    GAP_HEATMAP_TINT_MIN_PERCENT +
      (GAP_HEATMAP_TINT_MAX_PERCENT - GAP_HEATMAP_TINT_MIN_PERCENT) * share,
  );
}

/**
 * Background of one heatmap cell. Only a cell with a better/worse effectiveVerdict (a
 * significant gap, D-16 for zoneless cells) is tinted; every other cell, including a
 * large non-significant gap and a null gap, is neutral.
 */
export function gapHeatmapFill(
  cell: GapCell,
  scale: number,
): { tint: GapHeatmapTint; background: string } {
  const verdict = effectiveVerdict(cell);
  if (cell.delta === null || !isTintedVerdict(verdict)) {
    return { tint: 'neutral', background: GAP_HEATMAP_NEUTRAL_FILL };
  }
  const percent = heatmapPercent(cell.delta, scale);
  return {
    tint: verdict,
    background: `color-mix(in oklch, ${gapVerdictColor(verdict)} ${percent}%, transparent)`,
  };
}
