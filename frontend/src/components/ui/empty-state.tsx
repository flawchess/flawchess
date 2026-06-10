import * as React from 'react';

import { cn } from '@/lib/utils';

// Centered "nothing here yet" state: a heading, optional subtitle, and an
// optional action (usually an Import button). Two layouts capture the two
// established treatments in the app:
//   - 'page'  : full-height centered block that fills a tab/route (Openings,
//               Endgames). flex-1 + justify-center + py-12, medium-weight heading.
//   - 'inline': in-flow block stacked among other content (Library Games/Flaws).
//               py-8, bold heading.
// The action is passed as a ReactNode so callers keep control of the button
// variant (page states use a brown outline, library states use the solid CTA).
interface EmptyStateProps extends React.HTMLAttributes<HTMLDivElement> {
  title: string;
  subtitle?: React.ReactNode;
  /** Optional call-to-action, e.g. an Import <Button>. Caller owns its variant. */
  action?: React.ReactNode;
  /** 'inline' (default) for in-flow blocks; 'page' for full-tab centered states. */
  layout?: 'page' | 'inline';
}

function EmptyState({
  title,
  subtitle,
  action,
  layout = 'inline',
  className,
  ...props
}: EmptyStateProps) {
  return (
    <div
      className={cn(
        'flex flex-col items-center text-center',
        layout === 'page' ? 'flex-1 justify-center py-12' : 'py-8',
        className,
      )}
      {...props}
    >
      <p className={cn('text-base', layout === 'page' ? 'font-medium text-foreground' : 'font-bold')}>
        {title}
      </p>
      {subtitle && <p className="mt-2 text-sm text-muted-foreground">{subtitle}</p>}
      {action && <div className="mt-4">{action}</div>}
    </div>
  );
}

export { EmptyState };
