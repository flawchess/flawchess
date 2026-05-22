/**
 * Desktop custom-range popover (Phase 92 Plan 05 — D-03/D-04/D-17 + UAT revision).
 *
 * Renders a Radix `PopoverContent` containing a two-month range Calendar.
 * The Popover itself is controlled from FilterPanel.tsx via the `open`/`onOpenChange`
 * props; FilterPanel wraps the Select in `<PopoverAnchor asChild>` so the content
 * appears anchored to the Select trigger.
 *
 * Commit semantics (revised in UAT, supersedes D-05 auto-close):
 *   - `value`/`onChange` here drive FilterPanel's *pending* range state. The
 *     filter is only updated when the popover closes (Done, outside click,
 *     Escape) — see FilterPanel's `Popover onOpenChange` handler.
 *   - The calendar stays open after a full range is picked so the user can
 *     keep correcting until they explicitly dismiss.
 *
 * Single-bound (D-17): from-only or to-only ranges are valid commits.
 */

import { format } from 'date-fns';
import type { DateRange } from 'react-day-picker';
import { Calendar } from '@/components/ui/calendar';
import { PopoverContent } from '@/components/ui/popover';
import { Button } from '@/components/ui/button';

// ─── Calendar bounds ───────────────────────────────────────────────────────────

// Year-dropdown bounds for both desktop popover and mobile drawer. Lower bound
// is set to 2005 (predates chess.com's 2007 launch and lichess's 2010 launch),
// so any imported game's year is selectable. Upper bound is "today at app load"
// — react-day-picker only reads month/year so a stale daily value is harmless.
export const CALENDAR_MIN_DATE = new Date(2005, 0, 1);
export const CALENDAR_MAX_DATE = new Date();

// ─── Trigger-label helper ──────────────────────────────────────────────────────

/**
 * Format a custom date range for display on the Select trigger.
 *
 * Both bounds set  → `"MMM d, yyyy – MMM d, yyyy"` (en-dash, space-padded)
 * From only        → `"From MMM d, yyyy"`
 * To only          → `"Until MMM d, yyyy"` (symmetric per CONTEXT.md D-17)
 * Neither set      → `"Custom range…"` (defensive fallback)
 */
// eslint-disable-next-line react-refresh/only-export-components
export function formatCustomRangeLabel(
  range: { from?: Date; to?: Date } | null,
): string {
  if (!range) return 'Custom range…';
  const { from, to } = range;
  if (from && to) {
    return `${format(from, 'MMM d, yyyy')} – ${format(to, 'MMM d, yyyy')}`;
  }
  if (from) return `From ${format(from, 'MMM d, yyyy')}`;
  if (to) return `Until ${format(to, 'MMM d, yyyy')}`;
  return 'Custom range…';
}

// ─── Component ─────────────────────────────────────────────────────────────────

interface CustomRangePopoverProps {
  /** Currently committed custom range (null = nothing committed yet). */
  value: { from?: Date; to?: Date } | null;
  /** Called when the user picks a range (or a partial range on D-17). */
  onChange: (range: { from?: Date; to?: Date } | null) => void;
  /** Controlled open-change callback. */
  onOpenChange: (open: boolean) => void;
}

/**
 * Desktop calendar popover — renders only the `<PopoverContent>` body.
 *
 * FilterPanel is responsible for wrapping the Select in
 * `<Popover open={…}><PopoverAnchor asChild>…</PopoverAnchor>…</Popover>`
 * and rendering `<CustomRangePopover>` inside that tree so Radix can
 * position the content relative to the anchor.
 */
export function CustomRangePopover({
  value,
  onChange,
  onOpenChange,
}: CustomRangePopoverProps) {
  const handleSelect = (range: DateRange | undefined) => {
    // Convert DateRange (from: Date | undefined) to FilterState.customRange shape.
    const next: { from?: Date; to?: Date } | null = range
      ? { from: range.from, to: range.to }
      : null;
    onChange(next);
  };

  // Convert FilterState.customRange to DateRange: `from` must be present (even if undefined).
  const selected: DateRange | undefined = value
    ? { from: value.from, to: value.to }
    : undefined;

  return (
    // w-auto overrides the default w-72 (288 px) — a two-month Calendar is
    // ~580 px wide and must not be clipped. Radix collision detection keeps it
    // inside the viewport.
    <PopoverContent
      data-testid="custom-range-popover"
      className="w-auto p-0"
      align="start"
    >
      <Calendar
        mode="range"
        selected={selected}
        onSelect={handleSelect}
        numberOfMonths={2}
        // Month/year dropdowns in the caption let users jump years without
        // clicking the chevron 12× per year. Bounds keep the year list finite.
        captionLayout="dropdown"
        startMonth={CALENDAR_MIN_DATE}
        endMonth={CALENDAR_MAX_DATE}
        // With resetOnSelect, click 1 yields { from, to: undefined } (otherwise
        // addToRange sets to=from on the first click and the calendar shows a
        // bogus same-day range). Click 2 completes the range; click 3 starts
        // over.
        resetOnSelect
        data-testid="custom-range-calendar"
      />
      <div className="flex items-center justify-between gap-3 border-t border-border px-3 py-2">
        <span
          className="text-sm text-muted-foreground"
          data-testid="custom-range-selected-label"
        >
          {formatCustomRangeLabel(value)}
        </span>
        <div className="flex gap-2">
          <Button
            type="button"
            variant="brand-outline"
            size="sm"
            data-testid="btn-clear-custom-range"
            onClick={() => onChange(null)}
          >
            Clear
          </Button>
          <Button
            type="button"
            variant="default"
            size="sm"
            data-testid="btn-done-custom-range"
            onClick={() => onOpenChange(false)}
          >
            Done
          </Button>
        </div>
      </div>
    </PopoverContent>
  );
}
