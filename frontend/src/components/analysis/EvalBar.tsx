/**
 * EvalBar — vertical white-POV sigmoid centipawn bar with a depth-gated mate
 * label (Phase 137, D-04).
 *
 * White is always at the top regardless of board orientation (D-04: no
 * `orientation` prop). The mate label is shown only when `evalMate !== null &&
 * depth >= 8` to avoid flickering early-search artefacts.
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
  /** Caller (Phase 138 page shell) may override width/height via className. */
  className?: string;
}

/**
 * Renders a fixed white-POV vertical evaluation bar.
 * White always occupies the top fraction of the bar; black the bottom.
 */
export function EvalBar({ evalCp, evalMate, depth, className }: EvalBarProps) {
  const whiteFraction = computeWhiteFraction(evalCp, evalMate, depth);
  const whitePercent = `${(whiteFraction * 100).toFixed(2)}%`;
  const blackPercent = `${((1 - whiteFraction) * 100).toFixed(2)}%`;

  const showMateLabel = evalMate !== null && depth >= 8;
  const mateIsWhiteWinning = showMateLabel && evalMate! > 0;

  return (
    <div
      data-testid="analysis-eval-bar"
      role="img"
      aria-label={`Engine evaluation: ${scoreText(evalCp, evalMate)}`}
      className={cn(
        'relative flex flex-col border border-border rounded overflow-hidden w-4',
        className,
      )}
    >
      {/* White fill — top of bar */}
      <div
        className="absolute inset-x-0 top-0 transition-[height] duration-150"
        style={{ background: EVAL_BAR_WHITE, height: whitePercent }}
      />

      {/* Black fill — bottom of bar */}
      <div
        className="absolute inset-x-0 bottom-0"
        style={{ background: EVAL_BAR_BLACK, height: blackPercent }}
      />

      {/* Mate label — depth-gated (D-04) */}
      {showMateLabel && (
        <span
          className={cn(
            'absolute left-1/2 -translate-x-1/2 text-sm font-semibold z-10',
            mateIsWhiteWinning ? 'top-2 text-black' : 'bottom-2 text-white',
          )}
        >
          M{Math.abs(evalMate!)}
        </span>
      )}
    </div>
  );
}
