/**
 * Desktop custom-range popover (Phase 92 Plan 05 — D-03/D-04/D-05/D-17).
 *
 * Renders a Radix `PopoverContent` containing a two-month range Calendar.
 * The Popover itself is controlled from FilterPanel.tsx via the `open`/`onOpenChange`
 * props; FilterPanel wraps the Select in `<PopoverAnchor asChild>` so the content
 * appears anchored to the Select trigger.
 *
 * Auto-close (D-05): when both `from` and `to` are picked, `onChange` is called
 * and `onOpenChange(false)` fires immediately — no explicit Apply button needed.
 *
 * Single-bound (D-17): the user may pick only `from` or only `to`; the component
 * does not force a full range before committing.
 */

import { format } from 'date-fns';
import type { DateRange } from 'react-day-picker';
import { Calendar } from '@/components/ui/calendar';
import { PopoverContent } from '@/components/ui/popover';

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
  /** Whether the popover is open — controlled externally by FilterPanel. */
  open: boolean;
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
    // Auto-close (D-05): close as soon as both bounds are confirmed.
    if (next?.from && next?.to) {
      onOpenChange(false);
    }
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
        data-testid="custom-range-calendar"
      />
    </PopoverContent>
  );
}
