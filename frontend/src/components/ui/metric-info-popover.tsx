/**
 * The shared hover/tap info popover for metric rows (Endgame percentile rows,
 * Library gap rows): a lucide Search trigger, 100ms hover-open delay, Radix Portal +
 * Content side="top" sideOffset 4. The body is the caller's children.
 *
 * text-xs is allowed here: frontend/CLAUDE.md exempts short, transient, opt-in info
 * popover bodies from the text-sm floor.
 *
 * The `testId` becomes the Umami `popover-open` target via `popoverTargetFromTestId`,
 * so callers must build it only from metric keys and TC segments, never free values.
 */

import * as React from 'react';
import type { ReactNode } from 'react';
import { Popover as PopoverPrimitive } from 'radix-ui';
import { Search } from 'lucide-react';
import { useTrackedPopoverOpen } from '@/hooks/useTrackedOpen';
import { cn } from '@/lib/utils';

const HOVER_OPEN_DELAY_MS = 100;

interface MetricInfoPopoverProps {
  /** Trigger testid; the content gets `${testId}-popover`. */
  testId: string;
  ariaLabel: string;
  children: ReactNode;
}

export function MetricInfoPopover({ testId, ariaLabel, children }: MetricInfoPopoverProps) {
  const [open, setOpen] = useTrackedPopoverOpen(testId);
  const hoverTimeout = React.useRef<ReturnType<typeof setTimeout> | null>(null);

  // Clear a pending hover-open timer on unmount so it cannot fire setOpen late.
  React.useEffect(() => {
    return () => {
      if (hoverTimeout.current) clearTimeout(hoverTimeout.current);
    };
  }, []);

  const handleMouseEnter = (): void => {
    if (hoverTimeout.current) clearTimeout(hoverTimeout.current);
    hoverTimeout.current = setTimeout(() => setOpen(true), HOVER_OPEN_DELAY_MS);
  };

  const handleMouseLeave = (): void => {
    if (hoverTimeout.current) {
      clearTimeout(hoverTimeout.current);
      hoverTimeout.current = null;
    }
    setOpen(false);
  };

  return (
    <PopoverPrimitive.Root open={open} onOpenChange={setOpen}>
      <PopoverPrimitive.Trigger asChild>
        <span
          role="button"
          tabIndex={0}
          aria-label={ariaLabel}
          data-testid={testId}
          className="inline-flex cursor-pointer items-center text-brand-brown-light/70 hover:text-brand-brown focus:outline-none focus-visible:ring-2 focus-visible:ring-ring"
          onMouseEnter={handleMouseEnter}
          onMouseLeave={handleMouseLeave}
        >
          <Search className="h-4 w-4" />
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
          data-testid={`${testId}-popover`}
          className={cn(
            'z-50 max-w-xs rounded-md border-0 outline-none bg-foreground px-3 py-1.5 text-xs text-background',
            'data-[state=open]:animate-in data-[state=open]:fade-in-0 data-[state=open]:zoom-in-95',
            'data-[state=closed]:animate-out data-[state=closed]:fade-out-0 data-[state=closed]:zoom-out-95',
            'data-[side=bottom]:slide-in-from-top-2 data-[side=left]:slide-in-from-right-2',
            'data-[side=right]:slide-in-from-left-2 data-[side=top]:slide-in-from-bottom-2',
          )}
        >
          {children}
        </PopoverPrimitive.Content>
      </PopoverPrimitive.Portal>
    </PopoverPrimitive.Root>
  );
}
