/**
 * Per-severity glyph spec (symbol, dot color, glyph font-size in the 24-unit
 * viewBox). Single source of truth for the React badge components
 * (SeverityGlyphIcon) and the analysis/mini board SVG corner markers
 * (boardMarkers), so the two never drift. Lives in a plain module (not the icon
 * component file) to satisfy react-refresh's component-only-export rule.
 */

import type { FlawSeverity } from '@/types/library';
import { SEV_BLUNDER, SEV_MISTAKE, SEV_INACCURACY } from '@/lib/theme';

export const SEVERITY_GLYPH: Record<FlawSeverity, { symbol: string; color: string; fontSize: number }> = {
  blunder: { symbol: '??', color: SEV_BLUNDER, fontSize: 17 },
  mistake: { symbol: '?', color: SEV_MISTAKE, fontSize: 19 },
  inaccuracy: { symbol: '?!', color: SEV_INACCURACY, fontSize: 17 },
};
