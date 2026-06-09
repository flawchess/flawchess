import * as React from 'react';

import { cn } from '@/lib/utils';

// Canonical data-loading error state. CLAUDE.md mandates the exact copy
// "Failed to load {X}. Something went wrong. Please try again in a moment."
// for every useQuery isError branch — this component is the single source of
// that sentence so the wording can't drift across call sites.
const TRAILER = 'Something went wrong. Please try again in a moment.';

interface LoadErrorProps extends React.HTMLAttributes<HTMLElement> {
  /** Name of the resource that failed to load, e.g. "games", "endgame data". */
  resource: string;
  /**
   * 'inline' (default): a single muted paragraph carrying the full sentence —
   * for error states slotted above/inside existing content.
   * 'centered': bold heading + muted subtitle in a centered, padded column —
   * for full-panel error states that replace a chart or list.
   */
  variant?: 'inline' | 'centered';
}

function LoadError({ resource, variant = 'inline', className, ...props }: LoadErrorProps) {
  if (variant === 'centered') {
    return (
      <div
        className={cn(
          'flex flex-1 flex-col items-center justify-center py-12 text-center',
          className,
        )}
        {...props}
      >
        <p className="mb-2 text-base font-medium text-foreground">Failed to load {resource}</p>
        <p className="text-sm text-muted-foreground">{TRAILER}</p>
      </div>
    );
  }
  return (
    <p className={cn('text-sm text-muted-foreground', className)} {...props}>
      Failed to load {resource}. {TRAILER}
    </p>
  );
}

export { LoadError };
