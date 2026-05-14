import * as React from 'react';
import { Popover as PopoverPrimitive } from 'radix-ui';
import { HelpCircle } from 'lucide-react';
import { cn } from '@/lib/utils';
import {
  SCORE_GAP_NEUTRAL_MAX,
  SCORE_GAP_NEUTRAL_MIN,
} from '@/generated/endgameZones';
import type { ConfidenceLevel } from '@/lib/scoreConfidence';

const CONFIDENCE_LABEL: Record<ConfidenceLevel, string> = {
  low: 'Low',
  medium: 'Medium',
  high: 'High',
};

type Verdict = 'strength' | 'weakness' | 'difference';

function pickVerdict(value: number): Verdict {
  if (value >= SCORE_GAP_NEUTRAL_MAX) return 'strength';
  if (value <= SCORE_GAP_NEUTRAL_MIN) return 'weakness';
  return 'difference';
}

function headline(level: ConfidenceLevel, value: number): string {
  if (level === 'low') return 'Inconclusive.';
  const verdict = pickVerdict(value);
  const lead = level === 'high' ? 'Likely' : 'Possibly';
  if (verdict === 'difference') return `${lead} a real difference from the 0% baseline.`;
  return `${lead} a real ${verdict}.`;
}

interface ScoreGapPopoverProps {
  /** Label used in the stats line — e.g. "Achievable Score Gap". */
  label: string;
  /** Signed gap value on a 0-1 scale (e.g. 0.07 = +7%). */
  value: number;
  /** Sample size for the test (paired n, or total games for two-sample). */
  gameCount: number;
  /** Confidence bucket derived from the backend p-value. */
  level: ConfidenceLevel;
  /** Raw p-value from the backend. Null when below the reliability gate
   *  (PVALUE_RELIABILITY_MIN_N = 10) — the "(p = …)" segment is omitted then. */
  pValue: number | null;
  testId: string;
  ariaLabel: string;
  /** Description prose explaining what the gap measures (what / how to read). */
  description: React.ReactNode;
  /** Italic footer with method notes (score formula, test, CI). */
  footer: React.ReactNode;
}

export function ScoreGapPopover({
  label,
  value,
  gameCount,
  level,
  pValue,
  testId,
  ariaLabel,
  description,
  footer,
}: ScoreGapPopoverProps) {
  const [open, setOpen] = React.useState(false);
  const hoverTimeout = React.useRef<ReturnType<typeof setTimeout> | null>(null);

  const handleMouseEnter = () => {
    hoverTimeout.current = setTimeout(() => setOpen(true), 100);
  };

  const handleMouseLeave = () => {
    if (hoverTimeout.current) clearTimeout(hoverTimeout.current);
    setOpen(false);
  };

  const valuePct = (value * 100).toFixed(1);
  const sign = value >= 0 ? '+' : '';
  const diffPct = Math.abs(value * 100).toFixed(1);
  const direction = value >= 0 ? 'above' : 'below';

  return (
    <PopoverPrimitive.Root open={open} onOpenChange={setOpen}>
      <PopoverPrimitive.Trigger asChild>
        <span
          role="button"
          tabIndex={0}
          className="inline-flex items-center text-brand-brown-light/70 hover:text-brand-brown focus:outline-none cursor-pointer"
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
                  <strong>{sign}{valuePct}% {label}</strong> over {gameCount} games, at the 0% baseline.
                </>
              ) : (
                <>
                  <strong>{sign}{valuePct}% {label}</strong> over {gameCount} games, {diffPct}% {direction} the 0% baseline.
                </>
              )}
            </p>
            <p>
              <strong>{headline(level, value)}</strong> {CONFIDENCE_LABEL[level]} confidence
              {pValue !== null ? ` (p = ${pValue.toFixed(3)})` : ''}.
            </p>
            <p>{description}</p>
            <p className="opacity-70 italic">{footer}</p>
          </div>
        </PopoverPrimitive.Content>
      </PopoverPrimitive.Portal>
    </PopoverPrimitive.Root>
  );
}
