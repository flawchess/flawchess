import * as React from 'react';
import { Popover as PopoverPrimitive } from 'radix-ui';
import { HelpCircle } from 'lucide-react';
import { cn } from '@/lib/utils';
import { EvalConfidenceTooltip } from './EvalConfidenceTooltip';

type ConfidenceLevel = 'low' | 'medium' | 'high';

interface BulletConfidencePopoverProps {
  level: ConfidenceLevel;
  pValue: number | null | undefined;
  gameCount: number | null | undefined;
  evalMeanPawns: number | null | undefined;
  evalCiLowPawns?: number | null;
  evalCiHighPawns?: number | null;
  testId: string;
  ariaLabel?: string;
  /** Optional preface paragraph rendered above the per-row stats. */
  prefaceText?: string;
  /** Extra classes for the trigger span (e.g. positioning). */
  triggerClassName?: string;
}

// Hover- and tap-activated popover for the MG-entry bullet chart confidence
// details. Trigger is a HelpCircle (?) icon rather than the bullet itself so
// the bullet stays interaction-free.
export function BulletConfidencePopover({
  level,
  pValue,
  gameCount,
  evalMeanPawns,
  evalCiLowPawns,
  evalCiHighPawns,
  testId,
  ariaLabel = 'Show eval confidence details',
  prefaceText,
  triggerClassName,
}: BulletConfidencePopoverProps) {
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
            'data-[side=right]:slide-in-from-left-2 data-[side=top]:slide-in-from-bottom-2'
          )}
        >
          {prefaceText && <p className="mb-2">{prefaceText}</p>}
          <EvalConfidenceTooltip
            level={level}
            pValue={pValue ?? 1}
            gameCount={gameCount ?? 0}
            evalMeanPawns={evalMeanPawns ?? 0}
            evalCiLowPawns={evalCiLowPawns}
            evalCiHighPawns={evalCiHighPawns}
          />
        </PopoverPrimitive.Content>
      </PopoverPrimitive.Portal>
    </PopoverPrimitive.Root>
  );
}
