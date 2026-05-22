/**
 * Mobile custom-range nested drawer (Phase 92 Plan 05 — D-06/D-07/D-08/D-17).
 *
 * Renders a `DrawerNested` (vaul NestedRoot) layered over the FilterPanel drawer
 * with a single-month range Calendar and an explicit Apply CTA.
 *
 * Mobile UX differs from desktop in one critical way:
 * - Desktop (CustomRangePopover): commits the range on every Calendar click and
 *   auto-closes when both bounds are set (D-05).
 * - Mobile (this component): maintains a local `localRange` state; the parent
 *   receives the committed range ONLY when the user taps Apply (D-07). Backdrop
 *   dismiss silently discards the in-progress selection (D-08) because vaul's
 *   default `onOpenChange(false)` from an outside tap never calls `onChange`.
 */

import { useEffect, useState } from 'react';
import type { DateRange } from 'react-day-picker';
import { Calendar } from '@/components/ui/calendar';
import {
  DrawerNested,
  DrawerContent,
  DrawerHeader,
  DrawerTitle,
} from '@/components/ui/drawer';
import { Button } from '@/components/ui/button';

interface CustomRangeDrawerProps {
  /** Currently committed custom range (null = nothing committed yet). */
  value: { from?: Date; to?: Date } | null;
  /** Called ONLY when the user taps Apply — not on every Calendar pick. */
  onChange: (range: { from?: Date; to?: Date } | null) => void;
  /** Whether the drawer is open — controlled externally by FilterPanel. */
  open: boolean;
  /** Controlled open-change callback. Backdrop dismiss fires this with false. */
  onOpenChange: (open: boolean) => void;
}

export function CustomRangeDrawer({
  value,
  onChange,
  open,
  onOpenChange,
}: CustomRangeDrawerProps) {
  // localRange is the in-progress selection; it is NOT committed to the parent
  // until the user taps Apply. Backdrop dismiss (D-08) discards it by design
  // because we never call onChange from the backdrop path.
  // Convert FilterState.customRange to DateRange: `from` must be present (even if undefined).
  const [localRange, setLocalRange] = useState<DateRange | undefined>(
    value ? { from: value.from, to: value.to } : undefined,
  );

  // Resync local in-progress selection whenever the committed value changes
  // from outside (e.g. Reset Filters in the parent panel clears customRange to
  // null, or a sibling popover commit races with a mobile/desktop breakpoint
  // flip). Without this effect the drawer stays mounted (vaul NestedRoot keeps
  // the subtree alive while open=false), so reopening then tapping Apply would
  // silently re-commit a stale local selection and override the external
  // change. Compare on getTime() rather than reference so memoised preset
  // ranges don't trigger spurious resets. Preserves D-08 backdrop-dismiss
  // semantics because the effect fires only when the *committed* value
  // changes, not on every keystroke.
  useEffect(() => {
    setLocalRange(value ? { from: value.from, to: value.to } : undefined);
  }, [value?.from?.getTime(), value?.to?.getTime(), value === null]);

  const handleSelect = (range: DateRange | undefined) => {
    setLocalRange(range);
  };

  const handleApply = () => {
    // Commit to parent and close (D-07).
    // Convert DateRange back to FilterState.customRange shape.
    const committed: { from?: Date; to?: Date } | null = localRange
      ? { from: localRange.from, to: localRange.to }
      : null;
    onChange(committed);
    onOpenChange(false);
  };

  return (
    // DrawerNested must be inside an existing Drawer (the FilterPanel drawer).
    // vaul's NestedRoot handles focus lock and scroll isolation automatically.
    <DrawerNested open={open} onOpenChange={onOpenChange}>
      <DrawerContent data-testid="drawer-custom-range">
        <DrawerHeader>
          <DrawerTitle className="text-sm font-medium">Custom date range</DrawerTitle>
        </DrawerHeader>

        <div className="px-4 pb-2">
          <Calendar
            mode="range"
            selected={localRange}
            onSelect={handleSelect}
            numberOfMonths={1}
            data-testid="custom-range-calendar"
          />
        </div>

        {/* Apply CTA (D-07): primary action, disabled until at least a `from` bound is set. */}
        <div className="px-4 pb-6">
          <Button
            type="button"
            variant="default"
            size="lg"
            className="w-full min-h-11 sm:min-h-0"
            data-testid="btn-apply-custom-range"
            disabled={!localRange?.from}
            onClick={handleApply}
          >
            Apply
          </Button>
        </div>
      </DrawerContent>
    </DrawerNested>
  );
}
