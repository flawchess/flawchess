/**
 * PersonaEloDisclosurePopover — the D-08 measurement-disclosure popover
 * (Phase 184, CAL-05) mounted on every persona's detail-surface ELO label.
 * Mirrors `MetricStatPopover.tsx`'s exact hover/tap shell (100ms hover-open
 * delay, `PopoverPrimitive` Root/Trigger/Portal/Content, `side="top"
 * sideOffset={4}`, identical animation classes, `text-xs` body — the
 * documented CLAUDE.md popover-body exception).
 *
 * Discloses what the calibrated label means: a measured value from
 * bot-vs-engine games on FlawChess's internal anchor ladder, converted to an
 * approximate blitz scale — never a live, calibrated-against-humans rating.
 * The `isFloorRung` variant (D-06) appends the bottom-rung (~900 floor)
 * acknowledgment line: the weakest personas sit at or beyond the directly
 * measured range and are extrapolated. Per D-08, this disclosure surface
 * overrides the general popover-copy-minimalism convention (mirrors the
 * PercentileChip disclosure precedent).
 *
 * While `PERSONA_CALIBRATION_MEASURED` is false the generated labels are
 * provisional (`--bootstrap` fit: approx_blitz = rung), so BOTH the measured
 * claim and the ~900-floor line are withheld — asserting a measurement that
 * has not happened is precisely the dishonesty this surface exists to
 * prevent, and the floor line would additionally contradict the visible
 * label (a bootstrap 800-rung persona reads "~800", not "~900").
 */

import * as React from 'react';
import type { ReactElement } from 'react';
import { Popover as PopoverPrimitive } from 'radix-ui';
import { Search } from 'lucide-react';

import { PERSONA_CALIBRATION_MEASURED } from '@/generated/personaCalibration';
import { cn } from '@/lib/utils';

const HOVER_OPEN_DELAY_MS = 100;

export interface PersonaEloDisclosurePopoverProps {
  /** True for the bottom-rung (800) persona — appends the D-06 ~900
   * measured-floor acknowledgment line. */
  isFloorRung: boolean;
  ariaLabel: string;
}

export function PersonaEloDisclosurePopover({
  isFloorRung,
  ariaLabel,
}: PersonaEloDisclosurePopoverProps): ReactElement {
  const [open, setOpen] = React.useState(false);
  const hoverTimeout = React.useRef<ReturnType<typeof setTimeout> | null>(null);

  const handleMouseEnter = (): void => {
    hoverTimeout.current = setTimeout(() => setOpen(true), HOVER_OPEN_DELAY_MS);
  };

  const handleMouseLeave = (): void => {
    if (hoverTimeout.current) clearTimeout(hoverTimeout.current);
    setOpen(false);
  };

  return (
    <PopoverPrimitive.Root open={open} onOpenChange={setOpen}>
      <PopoverPrimitive.Trigger asChild>
        <span
          role="button"
          tabIndex={0}
          className="inline-flex items-center text-brand-brown-light/70 hover:text-brand-brown focus:outline-none cursor-pointer"
          aria-label={ariaLabel}
          data-testid="persona-elo-disclosure"
          onMouseEnter={handleMouseEnter}
          onMouseLeave={handleMouseLeave}
        >
          <Search className="h-4 w-4" />
        </span>
      </PopoverPrimitive.Trigger>
      <PopoverPrimitive.Portal>
        <PopoverPrimitive.Content
          side="top"
          sideOffset={4}
          onMouseEnter={() => {
            if (hoverTimeout.current) clearTimeout(hoverTimeout.current);
          }}
          onMouseLeave={handleMouseLeave}
          data-testid="persona-elo-disclosure-content"
          className={cn(
            'z-50 max-w-xs rounded-md border-0 outline-none bg-foreground px-3 py-1.5 text-xs text-background',
            'data-[state=open]:animate-in data-[state=open]:fade-in-0 data-[state=open]:zoom-in-95',
            'data-[state=closed]:animate-out data-[state=closed]:fade-out-0 data-[state=closed]:zoom-out-95',
            'data-[side=bottom]:slide-in-from-top-2 data-[side=left]:slide-in-from-right-2',
            'data-[side=right]:slide-in-from-left-2 data-[side=top]:slide-in-from-bottom-2',
          )}
        >
          {PERSONA_CALIBRATION_MEASURED ? (
            <>
              <p>
                This ELO is measured in bot-vs-engine games on our internal
                anchor ladder and converted to an approximate blitz scale —
                not a live rating against real players.
              </p>
              {isFloorRung && (
                <p className="mt-1">
                  This persona sits at our measured floor (~900) — the weakest
                  rungs are extrapolated beyond the ladder&apos;s directly
                  measured range.
                </p>
              )}
            </>
          ) : (
            <p>
              This ELO is a provisional estimate from the persona&apos;s target
              strength — not yet measured. Calibration games are in progress.
            </p>
          )}
        </PopoverPrimitive.Content>
      </PopoverPrimitive.Portal>
    </PopoverPrimitive.Root>
  );
}
