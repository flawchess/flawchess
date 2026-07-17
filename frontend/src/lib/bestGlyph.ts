/**
 * Best-move badge glyph spec (fill color). Single source of truth for the
 * best badge, consumed by the analysis board's SVG corner marker
 * (`boardMarkers`'s `SquareMarker.best` branch), the same "one record, one
 * consumer" shape as `gemGlyph.ts`'s `GEM_GLYPH` / `greatGlyph.ts`'s
 * `GREAT_GLYPH` / `bookGlyph.ts`'s `BOOK_GLYPH` (Quick 260717-rbn). Lives in
 * a plain module (not a component file) to satisfy react-refresh's
 * component-only-export rule (mirrors gemGlyph.ts's own rationale).
 *
 * Reuses `MOVE_QUALITY_BEST` (Phase 151.1's Moves-by-Rating dark-green "best
 * candidate" quality color) rather than declaring a parallel duplicate
 * constant — the semantic meaning ("the engine's best move") is identical,
 * so there is exactly one source of truth for this hue (CLAUDE.md "Theme
 * constants in theme.ts").
 */

import { MOVE_QUALITY_BEST } from '@/lib/theme';

export const BEST_GLYPH: { color: string } = {
  color: MOVE_QUALITY_BEST,
};
