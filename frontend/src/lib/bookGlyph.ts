/**
 * Book (opening-theory) badge glyph spec (fill color). Single source of truth
 * for the book badge, consumed by both the React `BookIcon` component and the
 * analysis board's SVG corner marker (`boardMarkers`'s `SquareMarker.book`
 * branch), so the two never drift — the same "one record, two consumers"
 * shape as `gemGlyph.ts`'s `GEM_GLYPH` (Phase 172, SEED-106 D-08). Lives in a
 * plain module (not the icon component file) to satisfy react-refresh's
 * component-only-export rule (mirrors gemGlyph.ts's own rationale).
 */

import { BOOK_MARKER_COLOR } from '@/lib/theme';

export const BOOK_GLYPH: { color: string } = {
  color: BOOK_MARKER_COLOR,
};
