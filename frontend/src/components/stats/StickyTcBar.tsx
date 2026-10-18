import type { ReactNode } from 'react';
import { useIsPinned } from '@/hooks/useIsPinned';
import { cn } from '@/lib/utils';

/** The desktop bar's sticky `top` (md:top-2 / lg:top-2): the buttons pin 8px below the viewport edge. */
const DESKTOP_TOP_PX = 8;

/** Where the page switches to its desktop layout: md for Library and Endgames, lg for Openings. */
type DesktopBreakpoint = 'md' | 'lg';

// Static class strings per breakpoint so Tailwind sees every utility in the source.
const DESKTOP_BAR_CLASS: Record<DesktopBreakpoint, string> = {
  md: 'md:pointer-events-none md:top-2 md:-mb-8 md:flex md:h-8 md:justify-end md:bg-transparent md:py-0 md:backdrop-blur-none',
  lg: 'lg:pointer-events-none lg:top-2 lg:-mb-8 lg:flex lg:h-8 lg:justify-end lg:bg-transparent lg:py-0 lg:backdrop-blur-none',
};
const DESKTOP_STRIP_CLASS: Record<DesktopBreakpoint, string> = {
  md: 'md:block',
  lg: 'lg:block',
};

interface StickyTcBarProps {
  /** The time-control switch. */
  children: ReactNode;
  /** Render the bar below md too; false when the page pins the switch elsewhere on mobile. */
  showOnMobile?: boolean;
  desktopBreakpoint?: DesktopBreakpoint;
  testId: string;
}

/**
 * Sticky container for a stats page's one time-control switch. Place it as the first child
 * of a wrapper around exactly the TC-driven sections: stickiness ends with that wrapper.
 *
 * Desktop: the bar takes no layout height (h-8 -mb-8) and overlays the right end of the
 * first section's heading row, which must be `md:h-8` (`lg:h-8` with desktopBreakpoint "lg"),
 * the desktop button height, so the switch is centred on the title. Only the switch pins on scroll, never the title. The
 * full-width blur strip is drawn only while pinned: at rest it would dim the title below.
 *
 * Mobile (showOnMobile): an ordinary in-flow sticky row with the blur strip, since a long
 * section title and four TC buttons do not fit on one 360px row.
 */
export function StickyTcBar({
  children,
  showOnMobile = true,
  desktopBreakpoint = 'md',
  testId,
}: StickyTcBarProps) {
  const [sentinelRef, isPinned] = useIsPinned<HTMLDivElement>(DESKTOP_TOP_PX);
  return (
    <>
      <div ref={sentinelRef} className="-mb-px h-px" aria-hidden="true" />
      <div
        className={cn(
          'sticky top-0 z-20 items-center py-2 bg-background/80 backdrop-blur-sm',
          DESKTOP_BAR_CLASS[desktopBreakpoint],
          showOnMobile ? 'flex' : 'hidden',
        )}
        data-testid={testId}
      >
        {isPinned && (
          // -inset-y-2: the strip spans 8px above and below the buttons, like the mobile
          // row's py-2, without changing the bar's own (zero) layout height.
          <div
            className={cn(
              'absolute inset-x-0 -inset-y-2 hidden bg-background/80 backdrop-blur-sm',
              DESKTOP_STRIP_CLASS[desktopBreakpoint],
            )}
          />
        )}
        <div className="pointer-events-auto relative">{children}</div>
      </div>
    </>
  );
}
