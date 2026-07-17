/**
 * Great-move badge glyph spec (fill color). Single source of truth for the
 * great badge, consumed by both the React `GreatMoveIcon` component and the
 * analysis board's SVG corner marker (`boardMarkers`'s `SquareMarker.great`
 * branch), so the two never drift — the same "one record, two consumers"
 * shape as `gemGlyph.ts`'s `GEM_GLYPH` / `bookGlyph.ts`'s `BOOK_GLYPH` (Phase
 * 175, SEED-108). Lives in a plain module (not the icon component file) to
 * satisfy react-refresh's component-only-export rule (mirrors gemGlyph.ts's
 * own rationale).
 *
 * Unlike `SEVERITY_GLYPH`, great has no text `symbol` — it renders as a
 * custom SVG "!" glyph (not a lucide icon; D-02 — chess.com's "Great Move"
 * mark has no direct lucide equivalent), matching `GreatMoveIcon.tsx`.
 */

import { GREAT_ACCENT } from '@/lib/theme';

export const GREAT_GLYPH: { color: string } = {
  color: GREAT_ACCENT,
};
