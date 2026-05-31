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
 * Per CONTEXT D-07 + 260529-l1i: tooltip body is 3 bullets per chip:
 *   1. Direct percentile statement. Per-TC chips (tc !== undefined) read
 *      "…of ~{rating}-rated players in {tc}."; aggregated chips
 *      (tc === undefined) read "…of similarly-rated players, aggregated across
 *      the time controls you play." (no rating number).
 *   2. Recent-games basis. For aggregated chips, the per-TC breakdown list
 *      renders two stacked lines per renderable TC: line 1
 *      "{tc} — anchored at ~{anchor} Lichess Elo" (omitted when anchor is
 *      null), line 2 "{value} over {n} games -> {percentile} percentile".
 *   3. Filter independence (kept verbatim from 94.3, `COPY_FILTER_INDEPENDENCE`).
 *
 * 260529-l1i: the standalone bullet-4 platform-blend anchor paragraph was
 * REMOVED entirely (deliberate reversal of the Phase 94.4 D-12 amendment). The
 * rating-matching method is now conveyed only by the per-row "anchored at ~X
 * Lichess Elo" text on the aggregated chip's per-TC list.
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
import type { PerTcBreakdownOut } from '@/types/endgames';

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
  /** 260529-l1i: anchor rating named in per-TC chip bullet 1
   *  ("…of ~{anchorRating}-rated players in {tc}"). Per-TC chips pass it;
   *  aggregated chips OMIT it (their bullet 1 no longer shows a number — the
   *  per-row "anchored at ~X Lichess Elo" lines carry the anchors instead). */
  anchorRating?: number;
  /** User-facing metric label used in aria-label. */
  metricLabel: string;
  /** Becomes data-testid on the trigger; popover Content uses `${testId}-popover`. */
  testId: string;
  /** Quick task 260527-q0b: aggregated chips (tc === undefined) thread the
   *  per-TC breakdown for bullet 2 of the tooltip. Each entry renders as one
   *  line; null-percentile-above-floor entries are dropped on render. */
  perTcBreakdown?: PerTcBreakdownOut[];
  /** Quick task 260527-q0b: per-TC chips (tc !== undefined) thread the
   *  chip-cohort n_games for bullet 2's simplified framing. */
  nGames?: number | null;
  /** Quick task 260527-q0b: per-TC chips thread the chip-cohort value
   *  (PercentileRow.value) for bullet 2. May differ from the card's
   *  headline number — disclosure of the percentile basis. */
  value?: number | null;
}

// Value formatter. All flavors render as a signed integer percent ("+5%",
// "-3%") so the chip tooltip matches the corresponding metric tooltip, which
// formats every score gap / clock gap / net flag rate as `Math.round(v*100)%`
// (see EndgameMetricsByTcCard, EndgameTimePressureCard, EndgameOverallPerformanceSection).
// The raw value is a fraction (0.04 = 4 percentage points).
function formatChipValue(v: number): string {
  const pct = Math.round(v * 100);
  return `${pct >= 0 ? '+' : ''}${pct}%`;
}

// Quick task 260527-q0b: clamp a raw percentile float to the same integer
// range the chip face uses (MIN_PERCENT..MAX_PERCENT), matching the rounding
// applied by `formatPercentileValue` so the per-TC list entries cannot show
// "100 percentile" or "0 percentile".
function clampPercentInt(p: number): number {
  return Math.max(MIN_PERCENT, Math.min(MAX_PERCENT, Math.round(p)));
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
  percentile: number;
  flavor: PercentileChipFlavor;
  metricLabel: string;
  tc: TimeControlBucket | undefined;
  anchorRating: number | undefined;
  perTcBreakdown: PerTcBreakdownOut[] | undefined;
  nGames: number | null | undefined;
  value: number | null | undefined;
}

function PercentileChipPopoverBody({
  percentile,
  flavor,
  metricLabel,
  tc,
  anchorRating,
  perTcBreakdown,
  nGames,
  value,
}: PopoverBodyProps): React.ReactElement {
  // Bullet 1 phrases the chip's percentile as a direct statement using the
  // chip face value verbatim (no 100-pct flip), so the tooltip number always
  // echoes the visible chip number. Above the median ("better than X%")
  // foregrounds the positive framing; at/below the median ("in the bottom
  // X%") preserves the legacy framing so low percentiles aren't sugar-coated.
  // Per-TC chips append "in {tc}"; aggregated chips append the multi-TC
  // framing from CONTEXT D-07b.
  const clampedPct = Math.max(MIN_PERCENT, Math.min(MAX_PERCENT, Math.round(percentile)));
  const phrasing =
    clampedPct > PERCENTILE_MEDIAN
      ? `better than ${clampedPct}%`
      : `in the bottom ${clampedPct}%`;
  // 260529-l1i: bullet 1 diverges by chip type.
  //   - Per-TC chip (tc !== undefined): keeps the "~{anchor}-rated players in
  //     {tc}" clause — the chip is scoped to one TC with one anchor. The chip's
  //     own value is woven into the sentence (formatted as percent, matching the
  //     adjacent metric tooltip) so the user reads their number and its rank in
  //     one statement; omitted when the caller did not thread `value`.
  //   - Aggregated chip (tc === undefined): drops the rating number; the
  //     per-row "anchored at ~X Lichess Elo" lines in bullet 2 carry the
  //     per-TC anchors instead.
  const valueFragment = value != null ? ` ${formatChipValue(value)}` : '';
  const bullet1 =
    tc !== undefined ? (
      <>
        Your <em>recent</em> {metricLabel}
        {valueFragment} is {phrasing} of ~{anchorRating}-rated players in {tc}.
      </>
    ) : (
      <>
        Your <em>recent</em> {metricLabel} is {phrasing} of similarly-rated players, aggregated
        across the time controls you play.
      </>
    );
  // Quick task 260527-q0b: bullet 2 rewrite. Two code paths:
  //   - tc === undefined (aggregated chip): render a leading line + per-TC list.
  //     Each per-TC entry obeys the 4 branches documented on PerTcBreakdownOut.
  //   - tc !== undefined (per-TC chip): render a single line with the chip-cohort
  //     n_games. The chip's value now lives in bullet 1, not here.
  // Fall back to the prior single-line copy when the caller did not thread the
  // new fields so older fixtures + test harnesses keep rendering.
  const bullet2 = ((): React.ReactElement => {
    if (tc !== undefined) {
      if (nGames != null) {
        return (
          <>
            Based on {nGames} of your recent {tc} games over the last 36 months, vs opponents
            within +/-100 Elo.
          </>
        );
      }
      return (
        <>
          Based on your most recent 3000 rated games in {tc} over the last 36 months, vs
          opponents within +/-100 Elo.
        </>
      );
    }
    // Aggregated path. Drop entries where percentile is null but value is
    // present (CDF out-of-range — backend honest, frontend dropping per
    // CONTEXT). Defensive drop on n_games == 0.
    const renderable = (perTcBreakdown ?? []).filter((entry) => {
      if (entry.n_games <= 0) return false;
      if (entry.value != null && entry.percentile == null) return false;
      return true;
    });
    if (renderable.length === 0) {
      return (
        <>
          Based on your most recent 3000 rated games per time control over the last 36 months,
          vs opponents within +/-100 Elo.
        </>
      );
    }
    return (
      <>
        Based on a weighted average of {metricLabel} percentiles from up to 3000 games per time
        control over the last 36 months. Only games vs opponents within +/-100 Elo are used:
        <ul className="mt-1 list-disc pl-4">
          {renderable.map((entry) => {
            if (entry.value == null) {
              return <li key={entry.tc}>{entry.tc}: insufficient games</li>;
            }
            // value != null && percentile != null (other case dropped above).
            // 260529-l1i: two stacked lines — the anchor label line (only when
            // entry.anchor is present, defensive null guard) then the stats
            // line. Both wrapped in block spans so they stack inside the <li>.
            const pInt = entry.percentile != null ? clampPercentInt(entry.percentile) : 0;
            return (
              <li key={entry.tc}>
                {entry.anchor != null && (
                  <span
                    className="block"
                    data-testid={`percentile-chip-anchor-${entry.tc}`}
                  >
                    {entry.tc} — anchored at ~{entry.anchor} Lichess Elo
                  </span>
                )}
                <span className="block">
                  {formatChipValue(entry.value)} over {entry.n_games} games -&gt; {pInt}{' '}
                  percentile
                </span>
              </li>
            );
          })}
        </ul>
      </>
    );
  })();
  // Time-Pressure Score Gap only: a brief note explaining that the metric is
  // computed from the two leftmost datapoints on the adjacent chart (the 10%
  // and 30% buckets, i.e. endgames entered with under 40% of the starting
  // clock). Anchors the chip percentile to the visible chart so the user can
  // see what raw values fed the percentile rank.
  const bulletMetricNote =
    flavor === 'time-pressure-score-gap'
      ? "Computed from the chart's 10% and 30% datapoints (endgames entered with under 40% of your clock): your average score in those buckets minus your opponents' average score against you, when they were under the same pressure."
      : null;
  const bullet3 = COPY_FILTER_INDEPENDENCE;
  // 260529-l1i: bullet 4 (the standalone platform-blend anchor paragraph) was
  // removed entirely. The rating-matching method is now conveyed only by the
  // per-row "anchored at ~X Lichess Elo" lines in the aggregated chip's bullet 2.
  return (
    <div className="space-y-1.5">
      <p>{bullet1}</p>
      {bulletMetricNote !== null && <p>{bulletMetricNote}</p>}
      <div>{bullet2}</div>
      <p>{bullet3}</p>
    </div>
  );
}

export function PercentileChip({
  percentile,
  // `flavor` routes the optional per-metric note (currently only
  // `time-pressure-score-gap` opts in to explain the 10%/30% bucket
  // derivation). All other flavors render the standard 3-bullet body.
  flavor,
  tc,
  anchorRating,
  metricLabel,
  testId,
  perTcBreakdown,
  nGames,
  value,
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
            // Fixed h-5 (= 20px = text-sm default line-height) so the chip
            // occupies exactly one line of text-sm. This keeps any row that
            // hosts the chip the same height as a chip-less row — preventing
            // misalignment of charts below adjacent (chipped vs un-chipped)
            // rows in side-by-side metric tiles.
            'inline-flex items-center justify-center gap-0.5 rounded-full px-2 h-5 text-sm font-normal leading-none cursor-pointer min-w-[3rem]',
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
            percentile={percentile}
            flavor={flavor}
            metricLabel={metricLabel}
            tc={tc}
            anchorRating={anchorRating}
            perTcBreakdown={perTcBreakdown}
            nGames={nGames}
            value={value}
          />
        </PopoverPrimitive.Content>
      </PopoverPrimitive.Portal>
    </PopoverPrimitive.Root>
  );
}
