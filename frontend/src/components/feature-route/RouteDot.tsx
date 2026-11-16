import { cn } from '@/lib/utils';
import { ROUTE_DOT_COLOR_CLASS } from '@/lib/theme';

export type RouteDotVariant = 'corner' | 'mobile-nav';

/**
 * The one pulsating feature-route dot (pulsing ring plus solid core).
 *
 * The parent must be `relative`. The desktop header is overflow-hidden, so the
 * `corner` offsets stay non-negative. `corner` is the desktop geometry used by
 * nav items, drawer rows, subtabs and controls; `mobile-nav` is the bottom-bar
 * geometry. Always aria-hidden: the dot is decorative.
 */
export function RouteDot({ testid, variant }: { testid: string; variant: RouteDotVariant }) {
  const mobile = variant === 'mobile-nav';
  return (
    <span
      className={mobile ? 'absolute top-1.5 right-[30%] flex h-2 w-2' : 'absolute top-0.5 right-0.5 flex h-2.5 w-2.5'}
      data-testid={testid}
      aria-hidden="true"
    >
      <span className={cn('absolute inline-flex h-full w-full animate-ping rounded-full opacity-75', ROUTE_DOT_COLOR_CLASS)} />
      <span className={cn('relative inline-flex rounded-full', ROUTE_DOT_COLOR_CLASS, mobile ? 'h-2 w-2' : 'h-2.5 w-2.5')} />
    </span>
  );
}
