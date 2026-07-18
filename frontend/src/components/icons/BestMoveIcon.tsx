/**
 * Best-move badge icon — a filled white star on a dark-green (`MOVE_QUALITY_BEST`)
 * dot, marking a "best move" (Phase 179 Plan 02, D-04, quick 260717-rbn's
 * `best_move_tier === 'best'`): the played move identity-equals the engine's
 * stored best move, out of book, not gem/great. The star (not a checkmark)
 * matches the on-board best badge in `boardMarkers.tsx`, keeping the glyph
 * identical across the move list and the board.
 *
 * Shape-compatible with `GemIconProps`/`GreatMoveIconProps` (`className`,
 * `style`, `aria-hidden`) so it drops into the same Move Stats table row as
 * the gem/great badges and severity glyphs.
 *
 * Hand-drawn (matching `GreatMoveIcon`'s from-scratch-glyph approach) rather
 * than a lucide import — no lucide "star on a circle" primitive matches
 * the self-colored badge shape these components share.
 */

import type { CSSProperties } from 'react';

import { BEST_STAR_POINTS } from '@/lib/bestGlyph';
import { MOVE_QUALITY_BEST } from '@/lib/theme';

export interface BestMoveIconProps {
  className?: string;
  style?: CSSProperties;
  'aria-hidden'?: boolean | 'true' | 'false';
}

/** A filled white star on a dark-green dot — the "best move" badge. */
export function BestMoveIcon({
  className,
  style,
  'aria-hidden': ariaHidden = true,
}: BestMoveIconProps) {
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
      <title>Best move</title>
      <circle cx="12" cy="12" r="11" fill={MOVE_QUALITY_BEST} />
      {/* Hand-drawn 5-pointed filled star (shared with the on-board best badge
          via BEST_STAR_POINTS) — outer r≈7.5, inner r≈3, centered at 12,12. */}
      <polygon
        points={BEST_STAR_POINTS}
        fill="#fff"
        stroke="#fff"
        strokeWidth="0.6"
        strokeLinejoin="round"
      />
    </svg>
  );
}
