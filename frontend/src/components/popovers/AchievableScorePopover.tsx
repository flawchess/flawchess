import * as React from 'react';
import { Popover as PopoverPrimitive } from 'radix-ui';
import { HelpCircle } from 'lucide-react';
import { cn } from '@/lib/utils';

interface AchievableScorePopoverProps {
  /** Default: "popover-trigger-achievable-score". Override only if multiple
   *  instances must coexist (none today). */
  testId?: string;
  ariaLabel?: string;
  /** Extra classes for the trigger span (e.g. positioning). */
  triggerClassName?: string;
}

// Phase 83 (D-09, D-10): hover/tap-activated popover that explains the
// "Achievable score" bullet next to the entry-eval bullet on tile 1 of
// EndgameStartVsEndSection. Thin wrapper around radix Popover, mirrors
// ScoreConfidencePopover hover handling. Body copy is hard-coded D-10
// verbatim — no bodyCopy prop (RESEARCH Open Question 1). See D-10 in
// 83-CONTEXT.md for the list of disallowed framings; the lint test at
// __tests__/AchievableScorePopover.test.tsx pins the contract.
export function AchievableScorePopover({
  testId = 'popover-trigger-achievable-score',
  ariaLabel = 'What is Achievable score?',
  triggerClassName,
}: AchievableScorePopoverProps = {}) {
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
            <p>
              This is what a 2300+ rated player would score from your endgame-entry
              positions. The score is calculated from your Endgame entry eval,
              using the Lichess winning chances formula.
            </p>
            <p>
              The Lichess curve is fitted on 2300+ rapid games, so scoring a little below this
              baseline from positive evals is normal at lower ratings. Compare this
              against your achieved Endgame score in the other tile.
            </p>
          </div>
        </PopoverPrimitive.Content>
      </PopoverPrimitive.Portal>
    </PopoverPrimitive.Root>
  );
}
