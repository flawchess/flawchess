/**
 * EvalBar — vertical sigmoid centipawn bar (Phase 137; Quick 260627: now follows
 * board orientation).
 *
 * The bar matches the board's perspective: the side sitting at the bottom of the
 * board occupies the bottom of the bar. In White's view (not flipped) White is at
 * the bottom; flipped to Black's view, Black is at the bottom. The numeric eval is
 * shown in the engine lines, not on the bar itself.
 */

import { cn } from '@/lib/utils';
import { EVAL_BAR_BLACK, EVAL_BAR_WHITE } from '@/lib/theme';

// Centipawns at which the bar shows ~73% dominance (logistic midpoint).
// Named constant — no magic number in the formula (CLAUDE.md).
const SIGMOID_SCALE = 400;

function cpToFraction(cp: number): number {
  return 1 / (1 + Math.exp(-cp / SIGMOID_SCALE));
}

/** Derive the fraction of the bar that should be white (0.0–1.0). */
function computeWhiteFraction(
  evalCp: number | null,
  evalMate: number | null,
  depth: number,
): number {
  if (evalMate !== null && depth >= 8) {
    if (evalMate > 0) return 1.0;
    if (evalMate < 0) return 0.0;
    return 0.5; // mate-in-0 is terminal; display as midpoint
  }
  if (evalCp !== null) return cpToFraction(evalCp);
  return 0.5; // no data yet
}

/** Derive a human-readable score string for the aria-label. */
function scoreText(evalCp: number | null, evalMate: number | null): string {
  if (evalMate !== null) {
    return evalMate >= 0 ? `M${evalMate}` : `-M${Math.abs(evalMate)}`;
  }
  if (evalCp !== null) {
    const cp = evalCp / 100;
    return cp >= 0 ? `+${cp.toFixed(2)}` : cp.toFixed(2);
  }
  return '0.00';
}

export interface EvalBarProps {
  evalCp: number | null;
  evalMate: number | null;
  depth: number;
  /**
   * Match the board orientation. When false (default, White's view) White sits at
   * the bottom of the bar; when true (Black's view) Black sits at the bottom.
   */
  flipped?: boolean;
  /** Caller (Phase 138 page shell) may override width/height via className. */
  className?: string;
}

/**
 * Renders a vertical evaluation bar whose perspective follows the board.
 * The side at the bottom of the board occupies the bottom fraction of the bar.
 */
export function EvalBar({ evalCp, evalMate, depth, flipped = false, className }: EvalBarProps) {
  const whiteFraction = computeWhiteFraction(evalCp, evalMate, depth);
  const whitePercent = `${(whiteFraction * 100).toFixed(2)}%`;
  const blackPercent = `${((1 - whiteFraction) * 100).toFixed(2)}%`;

  // White sits at the bottom in White's perspective; the bar flips with the board.
  const whiteAtBottom = !flipped;
  // Anchor each fill to the correct end so it follows the board orientation.
  const whiteEnd = whiteAtBottom ? { bottom: 0 } : { top: 0 };
  const blackEnd = whiteAtBottom ? { top: 0 } : { bottom: 0 };

  return (
    <div
      data-testid="analysis-eval-bar"
      role="img"
      aria-label={`Engine evaluation: ${scoreText(evalCp, evalMate)}`}
      className={cn(
        'relative flex flex-col border border-border rounded overflow-hidden w-5',
        className,
      )}
    >
      {/* White fill */}
      <div
        className="absolute inset-x-0 transition-[height] duration-150"
        style={{ background: EVAL_BAR_WHITE, height: whitePercent, ...whiteEnd }}
      />

      {/* Black fill */}
      <div
        className="absolute inset-x-0"
        style={{ background: EVAL_BAR_BLACK, height: blackPercent, ...blackEnd }}
      />
    </div>
  );
}
