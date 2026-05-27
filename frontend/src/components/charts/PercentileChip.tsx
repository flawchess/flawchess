/**
 * PercentileChip — Phase 94.4 peer-relative rewrite.
 *
 * Per CONTEXT D-06: chip face renders a `BadgePercent` lucide icon followed by
 * the bare integer (e.g. icon + "23") — the icon distinguishes a percentile
 * rank from raw percent values elsewhere in the UI. NO direction word (no
 * "Top X%" / "Bottom X%"). NO flame icons. Color band (red < p25 / neutral
 * p25-p75 / green > p75) carries direction. `MIN_PERCENT = 1` floor and p99
 * ceiling preserved per D-06a. `aria-label` preserves a direction word and the
 * legacy `p23` token for screen readers per D-06b.
 *
 * Per CONTEXT D-07: tooltip body is 4 bullets per chip:
 *   1. Cohort framing (anchor + TC, inline; per-TC vs aggregated phrasing).
 *   2. Recent-games basis (TC-scoped per Plan 05; vs +/-100 Elo opponents).
 *   3. Filter independence (kept verbatim from 94.3, `COPY_FILTER_INDEPENDENCE`).
 *   4. Rating-anchor disclosure (Lichess vs chess.com source; chess.com sources
 *      with `chesscomRawRating` get the ChessGoals-snapshot conversion form).
 *
 * Per CONTEXT D-07a: the 16-variant flavor enum collapses to 8 (5 page-level
 * aggregated + 3 per-TC families). All 8 flavors are `higher_is_better`
 * post-94.4 — `DIRECTION_BY_FLAVOR`, `RATING_NOTE_BY_FLAVOR`, all 12
 * `COPY_RATING_NOTE_*` constants, and `formatTopXPercent` retire. Net Flag
 * Rate's inversion is handled at the data layer (Plan 04) — its CDF is
 * already inverted so the chip stays `higher_is_better`.
 *
 * Per CONTEXT D-05a: Recovery Score Gap chip is RESCUED under peer-relative
 * (same-rated cohort comparison normalises the opponent-rating confound that
 * drove the v1 drop). A new `recovery` flavor is added.
 *
 * HARD CONSTRAINT — NO FLAME ICON. `Flame` from `lucide-react` MUST NOT be
 * imported here. No tier thresholds (no `TIER_BREAKPOINTS`, no `p90`/`p95`/`p99`
 * icon overlays). Flame logic was removed in commit `6766898c` and remains
 * forbidden. Vitest Test 9 explicitly asserts NO flame icon at every
 * percentile in [1, 23, 50, 75, 90, 95, 99] as the regression guard.
 *
 * Trigger is the chip itself (D-01) — no adjacent HelpCircle. Popover shell
 * mechanics mirror MetricStatPopover (HOVER_OPEN_DELAY_MS=100, identical
 * Portal + Content side="top" sideOffset={4} + animation classes).
 */

import * as React from 'react';
import { Popover as PopoverPrimitive } from 'radix-ui';
import { BadgePercent } from 'lucide-react';

import { cn } from '@/lib/utils';
import { GAUGE_NEUTRAL, ZONE_DANGER, ZONE_SUCCESS } from '@/lib/theme';

const HOVER_OPEN_DELAY_MS = 100;
const PERCENTILE_BAND_LOW = 25;
const PERCENTILE_BAND_HIGH = 75;
const PERCENTILE_MEDIAN = 50; // < → "bottom" in aria-label; >= → "top"
const MIN_PERCENT = 1; // floor — no "p0"
const MAX_PERCENT = 99; // ceiling — no "p100"
const PERCENTILE_ICON_SIZE_PX = 14; // matches text-sm (14px) line height

// Sole hard-coded color in this component. Justification: the chip's text
// renders in near-white on top of all three band colors (red / blue / green).
// It is a chip-internal "text-on-fill" convention, not a semantic theme token,
// so it does not earn a theme.ts entry.
const CHIP_TEXT_COLOR = 'oklch(0.98 0 0)';

// Phase 94.3 D-3: kept verbatim from the post-94.3 module — preserves the
// existing UI filter-independence promise on the chip's 3rd bullet.
const COPY_FILTER_INDEPENDENCE = 'UI filters do not affect this percentile.';

// Phase 94.4 D-07 bullet 4: ChessGoals-snapshot conversion disclosure. The
// snapshot date is the date the rating conversion table was captured; it ships
// frozen with this build. Updating it is a CHIP_TEXT-style content change.
// Reads in the rendered bullet 4 as: "... via ChessGoals snapshot 2026-05-26."
const CHESSGOALS_SNAPSHOT_DATE = '2026-05-26';

/**
 * Time-control bucket Literal — mirrors the backend `TimeControlBucket` Literal
 * (`Literal["bullet", "blitz", "rapid", "classical"]`) so chip callers can
 * pass values from `EndgameOverviewResponse.rating_anchors` keys directly.
 */
export type TimeControlBucket = 'bullet' | 'blitz' | 'rapid' | 'classical';

/**
 * 8-value flavor enum per CONTEXT D-07a + RESEARCH Pattern 7. The 12
 * composite TC-suffixed flavors (post-94.3) RETIRED. Per-TC chips now thread
 * the TC through an optional `tc` prop; the flavor names the metric family.
 */
export type PercentileChipFlavor =
  | 'score-gap'
  | 'achievable'
  | 'parity'
  | 'conversion'
  | 'recovery' // NEW — rescued under peer-relative per CONTEXT D-05a
  | 'time-pressure-score-gap'
  | 'clock-gap'
  | 'net-flag-rate';

export interface PercentileChipProps {
  /** Backend cohort percentile in [0, 100]. Caller gates on `!= null` before rendering. */
  percentile: number;
  /** Routes popover copy. One value per chipped metric family. */
  flavor: PercentileChipFlavor;
  /** Required for per-TC chips (`time-pressure-score-gap`, `clock-gap`, `net-flag-rate`).
   *  Page-level aggregated chips (`score-gap`, `achievable`, `parity`, `conversion`,
   *  `recovery`) omit this prop — the chip is aggregated across TCs and the tooltip
   *  frames as multi-TC. */
  tc?: TimeControlBucket;
  /** Anchor rating disclosed in popover bullet 4. Always the Lichess-equivalent
   *  (post-conversion for chess.com sources). */
  anchorRating: number;
  /** Which platform's games produced the anchor — drives bullet 4's wording. */
  anchorSource: 'lichess' | 'chesscom';
  /** Raw chess.com rating pre-conversion; populated when `anchorSource === 'chesscom'`.
   *  When omitted on a chess.com source, bullet 4 falls back to the simpler form. */
  chesscomRawRating?: number;
  /** User-facing metric label used in aria-label. */
  metricLabel: string;
  /** Becomes data-testid on the trigger; popover Content uses `${testId}-popover`. */
  testId: string;
}

/**
 * Bare chip-face formatter — integer string clamped to `[MIN_PERCENT, MAX_PERCENT]`.
 * The leading `BadgePercent` icon rendered alongside conveys "percentile rank";
 * the chip text is now just the number. aria-label still emits the legacy `p23`
 * token for screen readers (see ariaRounded below).
 */
function formatPercentileValue(pct: number): string {
  const rounded = Math.max(MIN_PERCENT, Math.min(MAX_PERCENT, Math.round(pct)));
  return String(rounded);
}

/**
 * Single-branch band-color resolver. All 8 flavors are `higher_is_better`
 * post-94.4 per CONTEXT D-07a (Net Flag Rate's inversion is handled at the
 * Plan 04 CDF-gen layer — its cohort CDF is already inverted, so smaller raw
 * values map to higher percentiles).
 */
function deriveBandColor(pct: number): string {
  if (pct < PERCENTILE_BAND_LOW) return ZONE_DANGER;
  if (pct > PERCENTILE_BAND_HIGH) return ZONE_SUCCESS;
  return GAUGE_NEUTRAL;
}

interface PopoverBodyProps {
  tc: TimeControlBucket | undefined;
  anchorRating: number;
  anchorSource: 'lichess' | 'chesscom';
  chesscomRawRating: number | undefined;
}

function PercentileChipPopoverBody({
  tc,
  anchorRating,
  anchorSource,
  chesscomRawRating,
}: PopoverBodyProps): React.ReactElement {
  // Per-TC chips use `${tc}` inline; aggregated chips use the multi-TC framing
  // from CONTEXT D-07b ("aggregated across the time controls you play").
  const bullet1 =
    tc !== undefined
      ? `Compared to other ~${anchorRating}-rated players in ${tc}.`
      : `Compared to other ~${anchorRating}-rated players, aggregated across the time controls you play.`;
  const bullet2 =
    tc !== undefined
      ? `Based on your most recent 1000 rated games in ${tc} over the last 36 months, vs opponents within +/-100 Elo.`
      : `Based on your most recent 1000 rated games per time control over the last 36 months, vs opponents within +/-100 Elo.`;
  const bullet3 = COPY_FILTER_INDEPENDENCE;
  // CONTEXT D-07 bullet 4: dominant-TC anchor disclosure. For aggregated chips
  // (`tc === undefined`), the bullet still names the dominant TC's anchor inline;
  // bullet 1's "aggregated across the time controls you play" carries the
  // honest multi-TC framing. See Plan 05c W4 deferral — the "+ N other TCs"
  // footnote is deferred to a v1.1 tooltip rev.
  const tcOrAgg = tc ?? 'rating per time control';
  let bullet4: string;
  if (anchorSource === 'lichess') {
    bullet4 = `Anchored on your Lichess ${tcOrAgg} (${anchorRating}).`;
  } else if (chesscomRawRating !== undefined) {
    bullet4 = `Anchored on your chess.com ${tcOrAgg} (${chesscomRawRating} -> ${anchorRating} Lichess-equivalent via ChessGoals snapshot ${CHESSGOALS_SNAPSHOT_DATE}).`;
  } else {
    bullet4 = `Anchored on your chess.com ${tcOrAgg} (${anchorRating}).`;
  }
  return (
    <div className="space-y-1.5">
      <p>{bullet1}</p>
      <p>{bullet2}</p>
      <p>{bullet3}</p>
      <p>{bullet4}</p>
    </div>
  );
}

export function PercentileChip({
  percentile,
  // `flavor` stays on PercentileChipProps as part of the typed API contract
  // (consumers pass it so type narrowing at call sites is meaningful and the
  // chip enum collapse stays grep-able from outside). It is intentionally NOT
  // destructured here: post-94.4 the 4 popover bullets are identical across
  // all 8 flavors (per CONTEXT D-07a — the per-metric rating-correlation
  // copy retired), so the body has nothing to dispatch on. Reserved for
  // future per-flavor copy variants without an API churn.
  tc,
  anchorRating,
  anchorSource,
  chesscomRawRating,
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
    // Clear any previously-scheduled open so a fast mouseenter->mouseleave->
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

  const label = formatPercentileValue(percentile);
  const bandColor = deriveBandColor(percentile);
  // aria-label preserves a direction word for screen readers per CONTEXT D-06b.
  // The rounded value uses the same clamp as the chip face so the aria-label and
  // visible text agree on edge percentiles (no "p100" / "p0" drift).
  const ariaRounded = Math.max(MIN_PERCENT, Math.min(MAX_PERCENT, Math.round(percentile)));
  const directionWord = ariaRounded < PERCENTILE_MEDIAN ? 'bottom' : 'top';
  const tcFragment = tc !== undefined ? ` in ${tc}` : '';
  const ariaLabel = `${metricLabel} percentile: p${ariaRounded}${tcFragment}, ${directionWord} of cohort`;

  return (
    <PopoverPrimitive.Root open={open} onOpenChange={setOpen}>
      <PopoverPrimitive.Trigger asChild>
        <span
          role="button"
          tabIndex={0}
          aria-label={ariaLabel}
          data-testid={testId}
          onMouseEnter={handleMouseEnter}
          onMouseLeave={handleMouseLeave}
          className={cn(
            // Icon + bare integer (e.g. "[%] 23") replaces the pre-94.4
            // "Bottom 50%" form; min-w-[3rem] keeps the chip visually balanced
            // across 1- and 2-digit values. text-sm is the CLAUDE.md minimum.
            // py-px + leading-none gives chip height ≈ icon height + 2px
            // breathing room (~16px) — middle ground between the original
            // ~24px and the bare ~14px (py-0) form.
            'inline-flex items-center justify-center gap-0.5 rounded-full px-2 py-px text-sm font-normal leading-none cursor-pointer min-w-[3rem]',
            'focus:outline-none focus-visible:ring-2 focus-visible:ring-ring',
          )}
          style={{ backgroundColor: bandColor, color: CHIP_TEXT_COLOR }}
        >
          <BadgePercent size={PERCENTILE_ICON_SIZE_PX} aria-hidden="true" />
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
            // text-xs justified by CLAUDE.md exception for hover/tap-activated
            // info tooltips (PercentileChip is the explicit reference example).
            'z-50 max-w-xs rounded-md border-0 outline-none bg-foreground px-3 py-1.5 text-xs text-background',
            'data-[state=open]:animate-in data-[state=open]:fade-in-0 data-[state=open]:zoom-in-95',
            'data-[state=closed]:animate-out data-[state=closed]:fade-out-0 data-[state=closed]:zoom-out-95',
            'data-[side=bottom]:slide-in-from-top-2 data-[side=left]:slide-in-from-right-2',
            'data-[side=right]:slide-in-from-left-2 data-[side=top]:slide-in-from-bottom-2',
          )}
        >
          <PercentileChipPopoverBody
            tc={tc}
            anchorRating={anchorRating}
            anchorSource={anchorSource}
            chesscomRawRating={chesscomRawRating}
          />
        </PopoverPrimitive.Content>
      </PopoverPrimitive.Portal>
    </PopoverPrimitive.Root>
  );
}
