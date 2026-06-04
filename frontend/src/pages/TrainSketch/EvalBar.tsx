import { WDL_WIN, WDL_LOSS, GLASS_OVERLAY } from '@/lib/theme';

interface EvalBarProps {
  /** User-POV expected score in [0, 1]. */
  expectedScore: number;
  /** Short caption under the percentage (e.g. "after Bxf7+"). */
  caption?: string;
}

/**
 * Minimal vertical eval bar for the Train prototype. The real app has no
 * reusable eval-bar component yet, so this is a throwaway visual: the user's
 * win expectancy fills from the bottom in green, the remainder reads as the
 * opponent's share.
 */
export function EvalBar({ expectedScore, caption }: EvalBarProps) {
  const pct = Math.round(Math.min(Math.max(expectedScore, 0), 1) * 100);
  const favored = pct >= 50;
  return (
    <div className="flex flex-col items-center gap-2" data-testid="train-eval-bar">
      <div className="relative h-72 w-4 overflow-hidden rounded-full bg-charcoal ring-1 ring-foreground/15">
        <div
          className="absolute right-0 bottom-0 left-0"
          style={{ height: `${pct}%`, backgroundColor: WDL_WIN, backgroundImage: GLASS_OVERLAY }}
        />
      </div>
      <span
        className="text-sm font-semibold tabular-nums"
        style={{ color: favored ? WDL_WIN : WDL_LOSS }}
      >
        {pct}%
      </span>
      {caption ? <span className="text-sm text-muted-foreground">{caption}</span> : null}
    </div>
  );
}
