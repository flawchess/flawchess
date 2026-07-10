/**
 * Gem badge glyph spec (fill color). Single source of truth for the gem
 * badge, consumed by both the React `GemIcon` component and the analysis
 * board's SVG corner marker (`boardMarkers`'s `SquareMarker.gem` branch), so
 * the two never drift — the same "one record, two consumers" shape as
 * `severityGlyph.ts`'s `SEVERITY_GLYPH`. Lives in a plain module (not the
 * icon component file) to satisfy react-refresh's component-only-export
 * rule (mirrors severityGlyph.ts's own rationale).
 *
 * Unlike `SEVERITY_GLYPH`, gem has no text `symbol` — it renders as an SVG
 * icon (lucide's `Gem`), not a NAG character like "??"/"?"/"!?".
 */

import { MAIA_ACCENT } from '@/lib/theme';

export const GEM_GLYPH: { color: string } = {
  color: MAIA_ACCENT,
};
