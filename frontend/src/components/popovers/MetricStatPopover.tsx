/**
 * MetricStatPopover — Radix popover SHELL around MetricStatTooltip, used by
 * all 6 tooltips in the "Endgame Overall Performance" section. Mirrors the
 * hover/tap pattern of ScoreGapPopover / AchievableScorePopover /
 * BulletConfidencePopover (100ms hover-open timeout, Portal + Content
 * side="top"/sideOffset=4, identical animation classes).
 *
 * Font-size note: Content className keeps `text-xs` to match every other
 * hover-popover in the app (ScoreGapPopover, AchievableScorePopover,
 * BulletConfidencePopover, OpeningStatsCard popovers). The CLAUDE.md
 * "minimum text-sm" rule is honored everywhere else; the popover layer is the
 * single intentional exception, kept consistent across the consolidation.
 *
 * Quick task 260514-i3l.
 */

import * as React from 'react';
import { Popover as PopoverPrimitive } from 'radix-ui';
import { Search } from 'lucide-react';

import { cn } from '@/lib/utils';

import {
  MetricStatTooltip,
  type MetricStatTooltipProps,
} from './MetricStatTooltip';

const HOVER_OPEN_DELAY_MS = 100;

export interface MetricStatPopoverProps extends MetricStatTooltipProps {
  testId: string;
  ariaLabel: string;
  /** Extra classes for the trigger span (e.g. positioning). */
  triggerClassName?: string;
  // isPending and pendingCount are inherited from MetricStatTooltipProps and forwarded
  // to MetricStatTooltip via the {...tooltipProps} spread (Phase 91 Plan 07).
}

export function MetricStatPopover({
  testId,
  ariaLabel,
  triggerClassName,
  ...tooltipProps
}: MetricStatPopoverProps) {
  const [open, setOpen] = React.useState(false);
  const hoverTimeout = React.useRef<ReturnType<typeof setTimeout> | null>(null);

  const handleMouseEnter = (): void => {
    hoverTimeout.current = setTimeout(() => setOpen(true), HOVER_OPEN_DELAY_MS);
  };

  const handleMouseLeave = (): void => {
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
          className={cn(
            'z-50 max-w-xs rounded-md border-0 outline-none bg-foreground px-3 py-1.5 text-xs text-background',
            'data-[state=open]:animate-in data-[state=open]:fade-in-0 data-[state=open]:zoom-in-95',
            'data-[state=closed]:animate-out data-[state=closed]:fade-out-0 data-[state=closed]:zoom-out-95',
            'data-[side=bottom]:slide-in-from-top-2 data-[side=left]:slide-in-from-right-2',
            'data-[side=right]:slide-in-from-left-2 data-[side=top]:slide-in-from-bottom-2',
          )}
        >
          <MetricStatTooltip {...tooltipProps} />
        </PopoverPrimitive.Content>
      </PopoverPrimitive.Portal>
    </PopoverPrimitive.Root>
  );
}
