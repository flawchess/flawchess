import * as React from 'react';
import { Popover as PopoverPrimitive } from 'radix-ui';
import { HelpCircle } from 'lucide-react';
import { cn } from '@/lib/utils';
import { WdlConfidenceTooltip } from './WdlConfidenceTooltip';
import { OPENING_INSIGHTS_CONFIDENCE_COPY } from './OpeningInsightsBlock';

type ConfidenceLevel = 'low' | 'medium' | 'high';

interface ScoreConfidencePopoverProps {
  level: ConfidenceLevel;
  pValue: number;
  score: number;
  gameCount: number;
  testId: string;
  ariaLabel?: string;
  /** Extra classes for the trigger span (e.g. positioning). */
  triggerClassName?: string;
}

// Hover- and tap-activated popover for the current-position score-vs-50%
// bullet chart confidence details. Trigger is a HelpCircle (?) icon so the
// bullet stays interaction-free. Mirrors BulletConfidencePopover but renders
// WdlConfidenceTooltip instead of EvalConfidenceTooltip.
export function ScoreConfidencePopover({
  level,
  pValue,
  score,
  gameCount,
  testId,
  ariaLabel = 'Show score confidence details',
  triggerClassName,
}: ScoreConfidencePopoverProps) {
  const [open, setOpen] = React.useState(false);
  const hoverTimeout = React.useRef<ReturnType<typeof setTimeout> | null>(null);

  const handleMouseEnter = () => {
    hoverTimeout.current = setTimeout(() => setOpen(true), 100);
  };

  const handleMouseLeave = () => {
    if (hoverTimeout.current) clearTimeout(hoverTimeout.current);
    setOpen(false);
  };

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
          <div className="space-y-2">
            <WdlConfidenceTooltip
              level={level}
              pValue={pValue}
              score={score}
              gameCount={gameCount}
            />
            <div className="border-t border-background/20 pt-2 space-y-2">
              <p>
                <strong>Score</strong> is your win rate plus half your draw rate. When your score is below 45% or above 55% over at least 10 games, a statistical test is conducted to determine how likely the difference occurred by chance.
              </p>
              {OPENING_INSIGHTS_CONFIDENCE_COPY}
            </div>
          </div>
        </PopoverPrimitive.Content>
      </PopoverPrimitive.Portal>
    </PopoverPrimitive.Root>
  );
}
