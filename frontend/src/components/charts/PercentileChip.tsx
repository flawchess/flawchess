/**
 * PercentileChip — Phase 94 (PCTL-03 / PCTL-04 / PCTL-05).
 *
 * Inline pill chip that surfaces a user's cohort percentile against the Phase 93
 * global CDF on the 4 in-scope ΔES rows (Endgame Score Gap, Achievable Score
 * Gap, Section 2 Parity ΔES, Section 2 Conversion ΔES). Banded color from
 * theme.ts, lucide Flame stack for the top 10% / 5% / 1% tiers, Radix popover
 * shell (hover + tap) with two metric-aware copy flavors.
 *
 * Trigger is the chip itself (D-01) — no adjacent HelpCircle. Popover shell
 * mechanics mirror MetricStatPopover (HOVER_OPEN_DELAY_MS=100, identical
 * Portal + Content side="top" sideOffset={4} + animation classes).
 *
 * Wired into rows by Plan 94-03 — until then this export is intentionally
 * unused; knip will flag it as dead code in the Wave-2-only snapshot, but the
 * import lands together with Wave 3 in the same PR.
 */

import * as React from 'react';
import { Popover as PopoverPrimitive } from 'radix-ui';
import { Flame } from 'lucide-react';

import { cn } from '@/lib/utils';
import { GAUGE_NEUTRAL, ZONE_DANGER, ZONE_SUCCESS } from '@/lib/theme';

const HOVER_OPEN_DELAY_MS = 100;
const PERCENTILE_BAND_LOW = 25;
const PERCENTILE_BAND_HIGH = 75;
const FLAME_TIER_1 = 90; // top 10%
const FLAME_TIER_2 = 95; // top 5%
const FLAME_TIER_3 = 99; // top 1%
const MIN_TOP_PERCENT = 1; // floor for label formatter — prevents "Top 0%" at p99.9 (Pitfall 7)
const FLAME_ICON_SIZE_CLASS = 'h-3 w-3'; // matches existing inline-icon convention in EndgameMetricCard

// Sole hard-coded color in this component. Justification: the chip's text and
// flame icons render in near-white on top of all three band colors (red /
// blue / green). It is a chip-internal "text-on-fill" convention, not a
// semantic theme token, so it does not earn a theme.ts entry.
const CHIP_TEXT_COLOR = 'oklch(0.98 0 0)';

export type PercentileChipFlavor = 'skill-isolating' | 'improvement-focus';

export interface PercentileChipProps {
  /** Backend cohort percentile in [0, 100]. Callers gate on `!= null` before rendering. */
  percentile: number;
  /** Routes the popover copy. */
  flavor: PercentileChipFlavor;
  /** Used in aria-label and (optionally) popover heading. */
  metricLabel: string;
  /** Becomes data-testid on the trigger; popover Content uses `${testId}-popover`. */
  testId: string;
}

function deriveBandColor(pct: number): string {
  if (pct < PERCENTILE_BAND_LOW) return ZONE_DANGER;
  if (pct > PERCENTILE_BAND_HIGH) return ZONE_SUCCESS;
  return GAUGE_NEUTRAL;
}

function deriveFlameCount(pct: number): 0 | 1 | 2 | 3 {
  if (pct >= FLAME_TIER_3) return 3;
  if (pct >= FLAME_TIER_2) return 2;
  if (pct >= FLAME_TIER_1) return 1;
  return 0;
}

function formatTopXPercent(pct: number): string {
  return `Top ${Math.max(MIN_TOP_PERCENT, Math.round(100 - pct))}%`;
}

function PercentileChipPopoverBody({ flavor }: { flavor: PercentileChipFlavor }): React.ReactElement {
  if (flavor === 'skill-isolating') {
    return (
      <p>
        Where you rank vs all players. Mostly independent of rating, reveals endgame ability separate
        from overall strength. Reflects your career under matched conditions, not the current filtered
        view.
      </p>
    );
  }
  return (
    <p>
      Where you rank vs all players. Conversion tracks rating closely. If you're in the lower tiers
      here, this is one of the biggest single improvements available to your ELO. Reflects your career
      under matched conditions, not the current filtered view.
    </p>
  );
}

export function PercentileChip({
  percentile,
  flavor,
  metricLabel,
  testId,
}: PercentileChipProps): React.ReactElement {
  const [open, setOpen] = React.useState(false);
  const hoverTimeout = React.useRef<ReturnType<typeof setTimeout> | null>(null);

  // Clear any pending hover-open timer on unmount so it can't fire setOpen
  // on an unmounted component (e.g., user mouses over chip then navigates
  // away within the 100ms delay window).
  React.useEffect(() => {
    return () => {
      if (hoverTimeout.current) {
        clearTimeout(hoverTimeout.current);
        hoverTimeout.current = null;
      }
    };
  }, []);

  const handleMouseEnter = (): void => {
    // Clear any previously-scheduled open so a fast mouseenter→mouseleave→
    // mouseenter cycle doesn't orphan the first timer.
    if (hoverTimeout.current) clearTimeout(hoverTimeout.current);
    hoverTimeout.current = setTimeout(() => setOpen(true), HOVER_OPEN_DELAY_MS);
  };

  const handleMouseLeave = (): void => {
    if (hoverTimeout.current) {
      clearTimeout(hoverTimeout.current);
      hoverTimeout.current = null;
    }
    setOpen(false);
  };

  const label = formatTopXPercent(percentile);
  const bandColor = deriveBandColor(percentile);
  const flameCount = deriveFlameCount(percentile);

  return (
    <PopoverPrimitive.Root open={open} onOpenChange={setOpen}>
      <PopoverPrimitive.Trigger asChild>
        <span
          role="button"
          tabIndex={0}
          aria-label={`${metricLabel} percentile: ${label}`}
          data-testid={testId}
          onMouseEnter={handleMouseEnter}
          onMouseLeave={handleMouseLeave}
          className={cn(
            'inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-sm font-normal cursor-pointer',
            'focus:outline-none focus-visible:ring-2 focus-visible:ring-ring',
          )}
          style={{ backgroundColor: bandColor, color: CHIP_TEXT_COLOR }}
        >
          {flameCount > 0 && (
            <span className="inline-flex" aria-hidden="true">
              {Array.from({ length: flameCount }).map((_, i) => (
                <Flame
                  key={i}
                  className={FLAME_ICON_SIZE_CLASS}
                  data-testid={`${testId}-flame`}
                />
              ))}
            </span>
          )}
          <span>{label}</span>
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
          data-testid={`${testId}-popover`}
          className={cn(
            'z-50 max-w-xs rounded-md border-0 outline-none bg-foreground px-3 py-1.5 text-xs text-background',
            'data-[state=open]:animate-in data-[state=open]:fade-in-0 data-[state=open]:zoom-in-95',
            'data-[state=closed]:animate-out data-[state=closed]:fade-out-0 data-[state=closed]:zoom-out-95',
            'data-[side=bottom]:slide-in-from-top-2 data-[side=left]:slide-in-from-right-2',
            'data-[side=right]:slide-in-from-left-2 data-[side=top]:slide-in-from-bottom-2',
          )}
        >
          <PercentileChipPopoverBody flavor={flavor} />
        </PopoverPrimitive.Content>
      </PopoverPrimitive.Portal>
    </PopoverPrimitive.Root>
  );
}
