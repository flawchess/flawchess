import * as React from 'react';
import { Popover as PopoverPrimitive } from 'radix-ui';
import { HelpCircle } from 'lucide-react';
import { cn } from '@/lib/utils';
// Phase 85.1 Plan 03 (IN-02): import the canonical ConfidenceLevel type from
// scoreConfidence instead of re-declaring it locally.
import type { ConfidenceLevel } from '@/lib/scoreConfidence';

const CONFIDENCE_LABEL: Record<ConfidenceLevel, string> = {
  low: 'Low',
  medium: 'Medium',
  high: 'High',
};

// Mirrors WdlConfidenceTooltip's zone boundaries (arrowColor.ts): scores in
// (0.45, 0.55) are neutral; >=0.55 is a strength, <=0.45 a weakness.
const NEUTRAL_LOWER = 0.45;
const NEUTRAL_UPPER = 0.55;

type Verdict = 'strength' | 'weakness' | 'difference';

function pickVerdict(score: number): Verdict {
  if (score >= NEUTRAL_UPPER) return 'strength';
  if (score <= NEUTRAL_LOWER) return 'weakness';
  return 'difference';
}

function headline(level: ConfidenceLevel, score: number): string {
  if (level === 'low') return 'Inconclusive.';
  const verdict = pickVerdict(score);
  const lead = level === 'high' ? 'Likely' : 'Possibly';
  if (verdict === 'difference') return `${lead} a real difference from the 50% baseline.`;
  return `${lead} a real ${verdict}.`;
}

interface AchievableScorePopoverProps {
  /** Achievable score as a fraction in [0, 1]. */
  score: number;
  /** Sample size (number of endgame-entry positions). */
  gameCount: number;
  /** Wilson confidence bucket derived from the backend p-value. */
  level: ConfidenceLevel;
  /** Raw p-value from the backend (Wilson score test vs 50%). Null when
   *  the bucket-row sample size is below the reliability gate
   *  (PVALUE_RELIABILITY_MIN_N = 10) — the "(p = …)" segment is omitted in
   *  that case. */
  pValue: number | null;
  /** Default: "popover-trigger-achievable-score". Override only if multiple
   *  instances must coexist (none today). */
  testId?: string;
  ariaLabel?: string;
  /** Extra classes for the trigger span (e.g. positioning). */
  triggerClassName?: string;
}

// Phase 83 (D-09, D-10): hover/tap-activated popover that explains the
// "Achievable score" bullet next to the entry-eval bullet in Card 2 of
// EndgameOverallPerformanceSection (formerly EndgameStartVsEndSection tile 1,
// redesigned in Phase 85). Mirrors WdlConfidenceTooltip's stats-first
// layout, with a shortened Lichess-formula context paragraph appended.
// The D-10 forbidden-framing contract is pinned by
// __tests__/AchievableScorePopover.test.tsx.
export function AchievableScorePopover({
  score,
  gameCount,
  level,
  pValue,
  testId = 'popover-trigger-achievable-score',
  ariaLabel = 'What is Achievable Score?',
  triggerClassName,
}: AchievableScorePopoverProps) {
  const [open, setOpen] = React.useState(false);
  const hoverTimeout = React.useRef<ReturnType<typeof setTimeout> | null>(null);

  const handleMouseEnter = () => {
    hoverTimeout.current = setTimeout(() => setOpen(true), 100);
  };

  const handleMouseLeave = () => {
    if (hoverTimeout.current) clearTimeout(hoverTimeout.current);
    setOpen(false);
  };

  const scorePct = (score * 100).toFixed(1);
  const diffPct = Math.abs(score * 100 - 50).toFixed(1);
  const direction = score >= 0.5 ? 'above' : 'below';

  return (
    <PopoverPrimitive.Root open={open} onOpenChange={setOpen}>
      <PopoverPrimitive.Trigger asChild>
        <span
          role="button"
          tabIndex={0}
          className={cn(
            'inline-flex items-center text-brand-brown-light/70 hover:text-brand-brown focus:outline-none cursor-pointer',
            triggerClassName,
          )}
          aria-label={ariaLabel}
          data-testid={testId}
          onMouseEnter={handleMouseEnter}
          onMouseLeave={handleMouseLeave}
        >
          <HelpCircle className="h-4 w-4" />
        </span>
      </PopoverPrimitive.Trigger>
      <PopoverPrimitive.Portal>
        <PopoverPrimitive.Content
          side="top"
          sideOffset={4}
          onMouseEnter={() => {
            if (hoverTimeout.current) clearTimeout(hoverTimeout.current);
          }}
          onMouseLeave={handleMouseLeave}
          className={cn(
            'z-50 max-w-xs rounded-md border-0 outline-none bg-foreground px-3 py-1.5 text-xs text-background',
            'data-[state=open]:animate-in data-[state=open]:fade-in-0 data-[state=open]:zoom-in-95',
            'data-[state=closed]:animate-out data-[state=closed]:fade-out-0 data-[state=closed]:zoom-out-95',
            'data-[side=bottom]:slide-in-from-top-2 data-[side=left]:slide-in-from-right-2',
            'data-[side=right]:slide-in-from-left-2 data-[side=top]:slide-in-from-bottom-2',
          )}
        >
          <div className="text-left space-y-1">
            <p>
              {diffPct === '0.0' ? (
                <>
                  <strong>{scorePct}% Achievable Score</strong> over {gameCount} games, at the 50% baseline.
                </>
              ) : (
                <>
                  <strong>{scorePct}% Achievable Score</strong> over {gameCount} games, {diffPct}% {direction} the 50% baseline.
                </>
              )}
            </p>
            <p>
              {/* pValue is null when bucket-row sample size is below the
                  reliability gate (PVALUE_RELIABILITY_MIN_N = 10). Omit the
                  "(p = …)" segment in that case so the prose stays clean. */}
              <strong>{headline(level, score)}</strong> {CONFIDENCE_LABEL[level]} confidence
              {pValue !== null ? ` (p = ${pValue.toFixed(3)})` : ''}.
            </p>
            <p>
              What a 2300+ rated player would score from your endgame-entry positions
              against a peer of similar rating, via the Lichess expected-score formula.
              Compare against your Endgame Score.
            </p>
            <p className="opacity-70 italic">
              Score: wins + ½ draws.<br />
              Test: two-sided Wilson score test vs 50%.<br />
              Confidence interval: Wilson 95% (whiskers).
            </p>
          </div>
        </PopoverPrimitive.Content>
      </PopoverPrimitive.Portal>
    </PopoverPrimitive.Root>
  );
}
