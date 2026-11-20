/**
 * Per-severity glyph spec (symbol, dot color, glyph font-size in the 24-unit
 * viewBox). Single source of truth for the React badge components
 * (SeverityGlyphIcon) and the analysis/mini board SVG corner markers
 * (boardMarkers), so the two never drift. Lives in a plain module (not the icon
 * component file) to satisfy react-refresh's component-only-export rule.
 */

import type { FlawSeverity } from '@/types/library';
import { SEV_BLUNDER, SEV_MISTAKE, SEV_INACCURACY, SEV_FACEPALM } from '@/lib/theme';

export interface GlyphSpec {
  symbol: string;
  color: string;
  fontSize: number;
  /**
   * Draw `count` overlapping copies of `symbol`, `offset` viewBox units apart, each outlined
   * `outline` units wide in the dot color so the overlaps stay readable (GlyphText).
   */
  stack?: { count: number; offset: number; outline: number };
}

export const SEVERITY_GLYPH: Record<FlawSeverity, GlyphSpec> = {
  blunder: { symbol: '??', color: SEV_BLUNDER, fontSize: 17 },
  mistake: { symbol: '?', color: SEV_MISTAKE, fontSize: 19 },
  inaccuracy: { symbol: '?!', color: SEV_INACCURACY, fontSize: 17 },
};

/**
 * Facepalm blunder (a blunder scoring >= FACEPALM_HIGH_CUTOFF): "???" on a dark red dot. Not a
 * PGN NAG (the set stops at "??"), but the informal "???" reads as "worse than a blunder" to
 * chess players. Same font size as "??"; the three marks overlap to fit the same round slot.
 */
export const FACEPALM_GLYPH: GlyphSpec = {
  symbol: '?',
  color: SEV_FACEPALM,
  fontSize: SEVERITY_GLYPH.blunder.fontSize,
  stack: { count: 3, offset: 5.5, outline: 1.5 },
};
