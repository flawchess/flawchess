/**
 * Book (opening-theory) badge icon — a white lucide `BookOpen` icon on a
 * muted slate-blue (`BOOK_GLYPH`) dot, marking a ply within known opening
 * theory (Phase 172, SEED-106 D-08): `opening_ply_count` earns itself twice
 * — it gates the background gem sweep AND marks theory plies with this
 * badge on every surface gems already render.
 *
 * Shape-compatible with `SeverityGlyphIconProps` / `GemIconProps`
 * (`className`, `style`, `aria-hidden`) so it drops into the same move-list
 * call sites (VariationTree's `BlunderIcon`/`MistakeIcon`/`GemIcon`) as the
 * severity glyphs and the gem badge. Non-interactive, glance-only — no
 * popover, no click target, no data-testid, mirroring `BlunderIcon`/
 * `MistakeIcon` rather than `GemMoveBadge`.
 *
 * `BookOpen` is the codebase's established "opening" glyph (nav, Import,
 * GameCard/LibraryGameCard opening-name rows, tagVisuals.ts,
 * flawComparisonMeta.ts) — reused here (not the plain `Book`) so "book
 * marker" and "opening" read as the same concept everywhere in the app.
 */

import type { CSSProperties } from 'react';
import { BookOpen } from 'lucide-react';

import { BOOK_GLYPH } from '@/lib/bookGlyph';

export interface BookIconProps {
  className?: string;
  style?: CSSProperties;
  'aria-hidden'?: boolean | 'true' | 'false';
}

/** A white lucide `BookOpen` on a muted slate-blue dot — the "book marker" badge. */
export function BookIcon({
  className,
  style,
  'aria-hidden': ariaHidden = true,
}: BookIconProps) {
  return (
    <svg
      xmlns="http://www.w3.org/2000/svg"
      viewBox="0 0 24 24"
      className={className}
      style={style}
      aria-hidden={ariaHidden}
      role="img"
    >
      {/* Accessible name (mirrors GemIcon's 163-REVIEW IN-02 fix): aria-hidden
          defaults to true, but a caller passing false would otherwise expose an
          UNNAMED role="img" to screen readers — the badge conveys meaning only
          via color/shape. */}
      <title>Opening theory</title>
      <circle cx="12" cy="12" r="11" fill={BOOK_GLYPH.color} />
      <BookOpen x={5} y={5} width={14} height={14} stroke="#fff" />
    </svg>
  );
}
