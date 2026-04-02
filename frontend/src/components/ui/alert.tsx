import * as React from 'react';
import { cva, type VariantProps } from 'class-variance-authority';
import { Info, AlertTriangle, AlertCircle, CheckCircle2 } from 'lucide-react';

import { cn } from '@/lib/utils';

const alertVariants = cva(
  'flex gap-3 rounded-md border px-4 py-3 text-sm',
  {
    variants: {
      variant: {
        info: 'border-border bg-muted/50 text-muted-foreground',
        warning: 'border-amber-500/30 bg-amber-500/10 text-amber-700 dark:text-amber-400',
        error: 'border-destructive/30 bg-destructive/10 text-destructive',
        success: 'border-emerald-500/30 bg-emerald-500/10 text-emerald-700 dark:text-emerald-400',
      },
    },
    defaultVariants: {
      variant: 'info',
    },
  }
);

const VARIANT_ICONS = {
  info: Info,
  warning: AlertTriangle,
  error: AlertCircle,
  success: CheckCircle2,
} as const;

function Alert({
  className,
  variant = 'info',
  children,
  ...props
}: React.ComponentProps<'div'> & VariantProps<typeof alertVariants>) {
  const Icon = VARIANT_ICONS[variant!];

  return (
    <div
      role="alert"
      data-slot="alert"
      className={cn(alertVariants({ variant }), className)}
      {...props}
    >
      <Icon className="h-4 w-4 mt-0.5 shrink-0" />
      <div className="space-y-1">{children}</div>
    </div>
  );
}

export { Alert };
