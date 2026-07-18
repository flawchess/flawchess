/**
 * Good-move badge icon — a white checkmark on a light-green (`MOVE_QUALITY_GOOD`)
 * dot, marking a "good move" (Phase 179 Plan 02, D-04, quick 260717-rbn's
 * `best_move_tier === 'good'`): the mover-POV expected-score drop is below
 * `INACCURACY_DROP`, out of book, not best/gem/great.
 *
 * A checkmark on light green, paired with `BestMoveIcon`'s star on dark green
 * — the star/check + dark/light-green pairing mirrors chess.com's Best/Good and
 * matches the on-board best/good badges in `boardMarkers.tsx`. Shape-compatible
 * with `GemIconProps`/`GreatMoveIconProps` (`className`, `style`, `aria-hidden`).
 */

import type { CSSProperties } from 'react';

import { MOVE_QUALITY_GOOD } from '@/lib/theme';

export interface GoodMoveIconProps {
  className?: string;
  style?: CSSProperties;
  'aria-hidden'?: boolean | 'true' | 'false';
}

/** A white checkmark on a light-green dot — the "good move" badge. */
export function GoodMoveIcon({
  className,
  style,
  'aria-hidden': ariaHidden = true,
}: GoodMoveIconProps) {
  return (
    <svg
      xmlns="http://www.w3.org/2000/svg"
      viewBox="0 0 24 24"
      className={className}
      style={style}
      aria-hidden={ariaHidden}
      role="img"
    >
      {/* Accessible name (mirrors GemIcon's 163-REVIEW IN-02 fix). */}
      <title>Good move</title>
      <circle cx="12" cy="12" r="11" fill={MOVE_QUALITY_GOOD} />
      <polyline
        points="7.5,12.5 10.5,15.5 16.5,8.5"
        fill="none"
        stroke="#fff"
        strokeWidth="2.2"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}
