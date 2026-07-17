/**
 * Good-move badge glyph spec (fill color). Single source of truth for the
 * good badge, consumed by the analysis board's SVG corner marker
 * (`boardMarkers`'s `SquareMarker.good` branch), the same "one record, one
 * consumer" shape as `gemGlyph.ts`'s `GEM_GLYPH` / `greatGlyph.ts`'s
 * `GREAT_GLYPH` / `bookGlyph.ts`'s `BOOK_GLYPH` / `bestGlyph.ts`'s
 * `BEST_GLYPH` (Quick 260717-rbn). Lives in a plain module (not a component
 * file) to satisfy react-refresh's component-only-export rule (mirrors
 * gemGlyph.ts's own rationale).
 *
 * Reuses `MOVE_QUALITY_GOOD` (Phase 151.1's Moves-by-Rating light-green
 * "clean non-best move" quality color) rather than declaring a parallel
 * duplicate constant — the semantic meaning ("a clean, non-flawed move") is
 * identical, so there is exactly one source of truth for this hue (CLAUDE.md
 * "Theme constants in theme.ts"). Visually distinguishable from BEST_GLYPH
 * (dark vs light green), and from the gem/great violet/blue accents.
 */

import { MOVE_QUALITY_GOOD } from '@/lib/theme';

export const GOOD_GLYPH: { color: string } = {
  color: MOVE_QUALITY_GOOD,
};
