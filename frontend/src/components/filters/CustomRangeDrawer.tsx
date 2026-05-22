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

import { useState } from 'react';
import type { DateRange } from 'react-day-picker';
import { Calendar } from '@/components/ui/calendar';
import {
  CALENDAR_MIN_DATE,
  CALENDAR_MAX_DATE,
  formatCustomRangeLabel,
} from './CustomRangePopover';
import {
  DrawerNested,
  DrawerContent,
  DrawerHeader,
  DrawerTitle,
} from '@/components/ui/drawer';
import { Button } from '@/components/ui/button';

// Stable string key for a committed range. Used to detect parent-driven
// resets in the derive-state-during-render pattern (see useRef block below).
// Comparing on `getTime()` rather than Date reference ensures memoised preset
// ranges with identical timestamps don't trigger spurious local resets.
function serializeRangeKey(
  range: { from?: Date; to?: Date } | null,
): string {
  if (range === null) return 'null';
  return `${range.from?.getTime() ?? 'x'}|${range.to?.getTime() ?? 'x'}`;
}

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
  // flip). Without this resync the drawer stays mounted (vaul NestedRoot keeps
  // the subtree alive while open=false), so reopening then tapping Apply would
  // silently re-commit a stale local selection and override the external
  // change.
  //
  // We use the "adjusting state on prop change" pattern from the React docs
  // (https://react.dev/reference/react/useState#storing-information-from-previous-renders)
  // rather than a useEffect, because:
  //   (1) eslint's react-hooks/set-state-in-effect blocks the naive useEffect
  //       form, and
  //   (2) it avoids the cascading-render cost of useEffect-driven setState
  //       (React bails out of re-rendering children if setState is called
  //       during render and only the same component re-renders).
  // We track the previously-seen committed value via useState and reset
  // localRange when the bounds' getTime() (or null-ness) change. Comparing on
  // getTime() rather than reference means memoised preset ranges with the same
  // timestamps don't trigger spurious resets. D-08 backdrop-dismiss semantics
  // are preserved because we only reset on a *committed* value change, not on
  // every Calendar keystroke.
  const [prevValueKey, setPrevValueKey] = useState<string>(serializeRangeKey(value));
  const currentKey = serializeRangeKey(value);
  if (prevValueKey !== currentKey) {
    setPrevValueKey(currentKey);
    setLocalRange(value ? { from: value.from, to: value.to } : undefined);
  }

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
            // Month/year dropdowns: native <select> on mobile gives a fast
            // year-jump wheel; bounds keep the year list finite.
            captionLayout="dropdown"
            startMonth={CALENDAR_MIN_DATE}
            endMonth={CALENDAR_MAX_DATE}
            // See CustomRangePopover for rationale: without this, react-day-picker
            // sets `to = from` on the first click and the calendar shows a
            // bogus same-day range until the user clicks again.
            resetOnSelect
            data-testid="custom-range-calendar"
          />
        </div>

        {/* Live selection readout: mirrors the trigger label format. */}
        <div className="px-4 pb-2 text-sm text-muted-foreground">
          <span data-testid="custom-range-selected-label">
            {formatCustomRangeLabel(
              localRange ? { from: localRange.from, to: localRange.to } : null,
            )}
          </span>
        </div>

        {/*
          Apply CTA (D-07): primary action, disabled until at least a `from`
          bound is set. Clear unsets the in-progress calendar selection without
          closing the drawer; user must Apply (or backdrop-dismiss) to leave.
        */}
        <div className="flex gap-2 px-4 pb-6">
          <Button
            type="button"
            variant="brand-outline"
            size="lg"
            className="flex-1 min-h-11 sm:min-h-0"
            data-testid="btn-clear-custom-range"
            onClick={() => setLocalRange(undefined)}
          >
            Clear
          </Button>
          <Button
            type="button"
            variant="default"
            size="lg"
            className="flex-1 min-h-11 sm:min-h-0"
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
