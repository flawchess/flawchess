import * as React from 'react';

import { cn } from '@/lib/utils';

// Shared container for Recharts custom-tooltip bodies: a small floating panel with
// a subtle border, solid background, and elevated shadow. Every chart's
// ChartTooltip `content` renderer wraps its rows in this so the tooltip chrome
// lives in one place. `text-xs` is intentional here (CLAUDE.md tooltip exception);
// the one caller that needs larger type passes className="text-sm".
function ChartTooltipBox({ className, ...props }: React.ComponentProps<'div'>) {
  return (
    <div
      className={cn(
        'rounded-lg border border-border/50 bg-background px-3 py-2 text-xs shadow-xl space-y-1',
        className,
      )}
      {...props}
    />
  );
}

export { ChartTooltipBox };
