import type { ReactNode } from 'react';
import { X } from 'lucide-react';
import { Drawer, DrawerContent, DrawerHeader, DrawerTitle, DrawerClose } from '@/components/ui/drawer';
import { Button } from '@/components/ui/button';
import { Tooltip } from '@/components/ui/tooltip';
import { cn } from '@/lib/utils';

// ─── Constants ──────────────────────────────────────────────────────────────

// Right-side filter drawer: full width on phones, 3/4 on small tablets, anchored
// to the top with a rounded bottom-left corner and capped height.
const DRAWER_CONTENT_CLASS = '!w-full sm:!w-3/4 !bottom-auto !rounded-bl-xl max-h-[85vh]';

// ─── Props ──────────────────────────────────────────────────────────────────

interface MobileFilterDrawerProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  /** Drawer heading, e.g. "Filters" or "Tags". */
  title: string;
  /** Optional element rendered next to the title (e.g. an info popover). */
  titleAccessory?: ReactNode;
  /** data-testid for the DrawerContent container. */
  contentTestId: string;
  /** data-testid for the close (X) button. */
  closeTestId: string;
  /** aria-label + tooltip for the close button. Defaults to `Close ${lowercased title}`. */
  closeLabel?: string;
  /** Extra classes for the scroll body (e.g. `space-y-4`). */
  bodyClassName?: string;
  /** Scrollable filter content. */
  children: ReactNode;
  /**
   * Pinned footer slot (typically a <FilterActions/> row). Rendered outside the
   * scroll area as a non-shrinking sibling, so it stays visible while the body
   * scrolls. Omit for footer-less drawers.
   */
  footer?: ReactNode;
}

// ─── Component ──────────────────────────────────────────────────────────────

/**
 * MobileFilterDrawer — shared right-side drawer chrome for every mobile filter /
 * tag drawer (Library Games & Flaws tabs, Stats, Openings, Endgames).
 *
 * Owns the drawer container, header (title + close button), the scrolling body,
 * and the pinned footer slot. Callers pass the filter controls as `children` and
 * the Reset/Apply row as `footer`; the flex-column layout keeps the footer pinned
 * below the scroll area. Keeping `children` and `footer` as slots leaves the
 * per-surface controls and their differing reset targets at the call site.
 */
export function MobileFilterDrawer({
  open,
  onOpenChange,
  title,
  titleAccessory,
  contentTestId,
  closeTestId,
  closeLabel,
  bodyClassName,
  children,
  footer,
}: MobileFilterDrawerProps) {
  const label = closeLabel ?? `Close ${title.toLowerCase()}`;

  return (
    <Drawer open={open} onOpenChange={onOpenChange} direction="right">
      <DrawerContent className={DRAWER_CONTENT_CLASS} data-testid={contentTestId}>
        <DrawerHeader className="flex flex-row items-center justify-between">
          <DrawerTitle className={titleAccessory ? 'flex items-center gap-1' : undefined}>
            {title}
            {titleAccessory}
          </DrawerTitle>
          <Tooltip content={label}>
            <DrawerClose asChild>
              <Button variant="ghost" size="icon" aria-label={label} data-testid={closeTestId}>
                <X className="h-4 w-4" />
              </Button>
            </DrawerClose>
          </Tooltip>
        </DrawerHeader>
        <div className={cn('overflow-y-auto flex-1 p-4', bodyClassName)}>{children}</div>
        {footer != null && <div className="shrink-0 px-4 pb-4">{footer}</div>}
      </DrawerContent>
    </Drawer>
  );
}
