/**
 * PercentileChip — Phase 94 (PCTL-03 / PCTL-04 / PCTL-05),
 *                  Phase 94.2 Plan 05 (PCTL-08 / PCTL-09),
 *                  Phase 94.3 Plan 06 (TPCTL-06 / TPCTL-07).
 *
 * Inline pill chip that surfaces a user's cohort percentile against the
 * global CDF on the chipped metric rows. Banded color from theme.ts and a
 * Radix popover shell (hover + tap) with one popover body per metric-named
 * flavor.
 *
 * Phase 94.2 (D-4): popover body discloses 4 bullets per metric —
 *   1. benchmark composition,
 *   2. recent-games basis,
 *   3. filter independence,
 *   4. per-metric rating-correlation framing calibrated per Cohen's d
 *      (see reports/benchmarks-gap-metrics-percentile-candidacy.md).
 * This is the sanctioned exception to feedback_popover_copy_minimalism —
 * see feedback_percentile_chip_tooltip_disclosure (project memory).
 *
 * Phase 94.3 (D-2, D-3, D-13): flavor enum widened from 4 to 16 variants
 * (12 per-(metric × TC) chips for Time Pressure family). A flavor-bound
 * DIRECTION_BY_FLAVOR map drives a direction axis (`higher_is_better` is the
 * only direction used today — the `lower_is_better` plumbing is kept intact
 * for future inverse-metric chips). For per-TC flavors (any flavor with a
 * TC suffix), bullets 1 and 2 become TC-scoped per D-13; bullet 4 carries
 * per-(metric × TC) copy lifted verbatim from Plan A's candidacy report.
 *
 * Phase 94.3 UAT correction: net_flag_rate was originally mapped to
 * `lower_is_better` but the metric is (timeout_wins − timeout_losses) / total,
 * so higher IS better. The DB percentile was correct all along; only the
 * chip direction map was wrong. Now all 16 flavors are `higher_is_better`.
 *
 * Trigger is the chip itself (D-01) — no adjacent HelpCircle. Popover shell
 * mechanics mirror MetricStatPopover (HOVER_OPEN_DELAY_MS=100, identical
 * Portal + Content side="top" sideOffset={4} + animation classes).
 */

import * as React from 'react';
import { Popover as PopoverPrimitive } from 'radix-ui';

import { cn } from '@/lib/utils';
import { GAUGE_NEUTRAL, ZONE_DANGER, ZONE_SUCCESS } from '@/lib/theme';

const HOVER_OPEN_DELAY_MS = 100;
const PERCENTILE_BAND_LOW = 25;
const PERCENTILE_BAND_HIGH = 75;
const PERCENTILE_MEDIAN = 50; // ≤ → "Bottom X%", > → "Top X%"
const MIN_PERCENT = 1; // floor for label formatter — prevents "Top 0%" / "Bottom 0%" at edge percentiles

// Sole hard-coded color in this component. Justification: the chip's text
// renders in near-white on top of all three band colors (red / blue / green).
// It is a chip-internal "text-on-fill" convention, not a semantic theme token,
// so it does not earn a theme.ts entry.
const CHIP_TEXT_COLOR = 'oklch(0.98 0 0)';

// ── D-4 popover-body copy constants ────────────────────────────────────────
// Three always-present blocks (benchmark composition, recent-games basis,
// filter independence) + one per-metric rating-correlation block calibrated
// per Cohen's d from reports/benchmarks-gap-metrics-percentile-candidacy.md.
const COPY_RECENT_GAMES_BASIS =
  'Uses your most recent 1000 rated games per time control, played against opponents of similar strength (+/-100 ELO) over the last 3 years.';
const COPY_FILTER_INDEPENDENCE = 'UI filters do not affect this percentile.';

/**
 * Phase 94.3 D-13: per-TC variant of `COPY_RECENT_GAMES_BASIS`. When called
 * with a TC name, returns the TC-scoped wording for bullet 2; called with
 * `undefined`, returns the original pooled-across-TC wording. Keeps both
 * call paths grep-able under one helper.
 */
function recentGamesBasisFor(tc: string | undefined): string {
  if (tc === undefined) return COPY_RECENT_GAMES_BASIS;
  return `Uses your most recent 1000 rated games in ${tc} (last 36 months), played against opponents of similar strength (+/-100 ELO).`;
}

/**
 * Returns the "bottom/top X%" framing used in popover bullet 1, mirroring the
 * chip-face logic in `formatTopXPercent`: pct ≤ 50 → "bottom X%", pct > 50 →
 * "top (100−X)%" for `higher_is_better`; symmetrically inverted for
 * `lower_is_better`. Both branches floor at 1% so the popover never reads
 * "bottom 0%" / "top 0%" at edge percentiles.
 */
function formatBottomOrTopPhrase(
  pct: number,
  direction: PercentileChipDirection,
): { kind: 'bottom' | 'top'; value: number } {
  const isLowHalf = pct <= PERCENTILE_MEDIAN;
  const isBottom =
    direction === 'higher_is_better' ? isLowHalf : !isLowHalf;
  const rawValue = isLowHalf ? pct : 100 - pct;
  return { kind: isBottom ? 'bottom' : 'top', value: Math.max(MIN_PERCENT, Math.round(rawValue)) };
}

/**
 * 16 metric-named flavor variants. The original 4 (kebab-case) map 1:1 to
 * Phase 94.2 ΔES chips; the 12 new (snake_case) map 1:1 to backend metric
 * IDs for the Phase 94.3 per-TC Time Pressure family. The case mismatch is
 * intentional (RESEARCH §Pattern 7): backend↔flavor grep stays trivial for
 * the new variants without churning the existing 4.
 */
export type PercentileChipFlavor =
  | 'score-gap'
  | 'achievable'
  | 'parity'
  | 'conversion'
  // Phase 94.3 per-(metric × TC) flavors (CONTEXT.md D-7).
  | 'time_pressure_score_gap_bullet'
  | 'time_pressure_score_gap_blitz'
  | 'time_pressure_score_gap_rapid'
  | 'time_pressure_score_gap_classical'
  | 'clock_gap_bullet'
  | 'clock_gap_blitz'
  | 'clock_gap_rapid'
  | 'clock_gap_classical'
  | 'net_flag_rate_bullet'
  | 'net_flag_rate_blitz'
  | 'net_flag_rate_rapid'
  | 'net_flag_rate_classical';

/** Phase 94.3 D-2: chip direction axis. `lower_is_better` flips text
 *  formatter and band color. */
export type PercentileChipDirection = 'higher_is_better' | 'lower_is_better';

// Canonical user-facing metric labels per flavor. Single source of truth so the
// rating-note copy below cannot drift from the names rendered in card headers,
// tooltips, and aria labels.
export const PERCENTILE_METRIC_LABELS = {
  'score-gap': 'Endgame Score Gap',
  achievable: 'Achievable Score Gap',
  parity: 'Parity Score Gap',
  conversion: 'Conversion Score Gap',
  // Phase 94.3 per-TC labels — user-readable, mirror the parent metric name
  // with the TC suffix in parens.
  time_pressure_score_gap_bullet: 'Time Pressure Score Gap (bullet)',
  time_pressure_score_gap_blitz: 'Time Pressure Score Gap (blitz)',
  time_pressure_score_gap_rapid: 'Time Pressure Score Gap (rapid)',
  time_pressure_score_gap_classical: 'Time Pressure Score Gap (classical)',
  clock_gap_bullet: 'Clock Gap (bullet)',
  clock_gap_blitz: 'Clock Gap (blitz)',
  clock_gap_rapid: 'Clock Gap (rapid)',
  clock_gap_classical: 'Clock Gap (classical)',
  net_flag_rate_bullet: 'Net Flag Rate (bullet)',
  net_flag_rate_blitz: 'Net Flag Rate (blitz)',
  net_flag_rate_rapid: 'Net Flag Rate (rapid)',
  net_flag_rate_classical: 'Net Flag Rate (classical)',
} as const satisfies Record<PercentileChipFlavor, string>;

// Per-metric rating-correlation framing (lower Cohen's d → more rating-invariant).
// Phase 94.2 originals:
const COPY_RATING_NOTE_SCORE_GAP =
  `${PERCENTILE_METRIC_LABELS['score-gap']} is mostly independent of rating, so this reflects endgame ability separate from overall strength.`;
const COPY_RATING_NOTE_ACHIEVABLE =
  `${PERCENTILE_METRIC_LABELS.achievable} mildly correlates with rating.`;
const COPY_RATING_NOTE_PARITY = `${PERCENTILE_METRIC_LABELS.parity} mildly correlates with rating.`;
const COPY_RATING_NOTE_CONVERSION =
  `${PERCENTILE_METRIC_LABELS.conversion} tracks rating strongly: stronger players tend to score higher here because they blunder less when up material.`;

// Phase 94.3 per-(metric × TC) rating-correlation copy. Lifted verbatim from
// reports/benchmarks-gap-metrics-percentile-candidacy.md §"Time Pressure
// metric family (Phase 94.3)" → "12-cell tier table" → "Tooltip 4th-bullet
// copy" column. Per the candidacy report, all 4 net_flag_rate_{tc} cells land
// in the same "mild coupling" tier (d ∈ [0.24, 0.32]); copy varies only in
// the TC token and the per-TC nuance noted in the report.
const COPY_RATING_NOTE_TPSG_BULLET =
  'This bullet score-gap partly tracks rating, so stronger players tend to absorb time pressure better; positive = you score higher under pressure than your opponents do.';
const COPY_RATING_NOTE_TPSG_BLITZ =
  'This blitz score-gap partly tracks rating, so stronger players tend to score higher under pressure; positive = you outperform your opponents when the clock burns.';
const COPY_RATING_NOTE_TPSG_RAPID =
  'This rapid score-gap tracks rating strongly: stronger players score much higher under pressure; positive = you outperform your opponents when the clock burns.';
const COPY_RATING_NOTE_TPSG_CLASSICAL =
  'This classical score-gap is not measured against enough players to characterise; positive = you outperform your opponents when the clock burns.';
const COPY_RATING_NOTE_CLOCK_BULLET =
  'This bullet clock-management gap is mostly independent of rating; positive = you reach endgames with more clock left than your opponents do.';
const COPY_RATING_NOTE_CLOCK_BLITZ =
  'This blitz clock-management gap slightly tracks rating; positive = you reach endgames with more clock left than your opponents do.';
const COPY_RATING_NOTE_CLOCK_RAPID =
  'This rapid clock-management gap is mostly independent of rating; positive = you reach endgames with more clock left than your opponents do.';
const COPY_RATING_NOTE_CLOCK_CLASSICAL =
  'This classical clock-management gap is mostly independent of rating; positive = you reach endgames with more clock left than your opponents do.';
const COPY_RATING_NOTE_NFR_BULLET =
  'At bullet, net flag rate slightly tracks rating (stronger players win more on time than they lose); positive = your opponents flag more than you do.';
const COPY_RATING_NOTE_NFR_BLITZ =
  'At blitz, net flag rate slightly tracks rating; positive = your opponents flag more than you do.';
const COPY_RATING_NOTE_NFR_RAPID =
  'At rapid, net flag rate slightly tracks rating; positive = your opponents flag more than you do.';
const COPY_RATING_NOTE_NFR_CLASSICAL =
  'At classical, net flag rate slightly tracks rating; positive = your opponents flag more than you do.';

// Exhaustive flavor → rating-note lookup. `satisfies` gives a compile-time
// guarantee every variant has a copy string; adding a 17th flavor without
// a copy entry would fail tsc.
const RATING_NOTE_BY_FLAVOR = {
  'score-gap': COPY_RATING_NOTE_SCORE_GAP,
  achievable: COPY_RATING_NOTE_ACHIEVABLE,
  parity: COPY_RATING_NOTE_PARITY,
  conversion: COPY_RATING_NOTE_CONVERSION,
  time_pressure_score_gap_bullet: COPY_RATING_NOTE_TPSG_BULLET,
  time_pressure_score_gap_blitz: COPY_RATING_NOTE_TPSG_BLITZ,
  time_pressure_score_gap_rapid: COPY_RATING_NOTE_TPSG_RAPID,
  time_pressure_score_gap_classical: COPY_RATING_NOTE_TPSG_CLASSICAL,
  clock_gap_bullet: COPY_RATING_NOTE_CLOCK_BULLET,
  clock_gap_blitz: COPY_RATING_NOTE_CLOCK_BLITZ,
  clock_gap_rapid: COPY_RATING_NOTE_CLOCK_RAPID,
  clock_gap_classical: COPY_RATING_NOTE_CLOCK_CLASSICAL,
  net_flag_rate_bullet: COPY_RATING_NOTE_NFR_BULLET,
  net_flag_rate_blitz: COPY_RATING_NOTE_NFR_BLITZ,
  net_flag_rate_rapid: COPY_RATING_NOTE_NFR_RAPID,
  net_flag_rate_classical: COPY_RATING_NOTE_NFR_CLASSICAL,
} as const satisfies Record<PercentileChipFlavor, string>;

/**
 * Phase 94.3 D-2: direction axis per flavor. Post-UAT correction: all 16
 * flavors map to `higher_is_better` (net_flag_rate was incorrectly flipped
 * to `lower_is_better` in the original plan; see file-top docstring).
 * `satisfies Record<...>` is non-negotiable per RESEARCH §Pitfall 3 —
 * without it a future flavor addition could silently miss the map.
 * Consumers MUST bind through `PercentileChipDirection` (not infer) so the
 * `lower_is_better` branches remain reachable at the type level — see
 * `PercentileChipPopoverBody` and the chip body for the explicit annotation.
 */
export const DIRECTION_BY_FLAVOR = {
  'score-gap': 'higher_is_better',
  achievable: 'higher_is_better',
  parity: 'higher_is_better',
  conversion: 'higher_is_better',
  time_pressure_score_gap_bullet: 'higher_is_better',
  time_pressure_score_gap_blitz: 'higher_is_better',
  time_pressure_score_gap_rapid: 'higher_is_better',
  time_pressure_score_gap_classical: 'higher_is_better',
  clock_gap_bullet: 'higher_is_better',
  clock_gap_blitz: 'higher_is_better',
  clock_gap_rapid: 'higher_is_better',
  clock_gap_classical: 'higher_is_better',
  // Phase 94.3 UAT correction: net_flag_rate is `higher_is_better`. The
  // metric is (timeout_wins − timeout_losses) / total_endgame_games, so a
  // positive (higher) value means the user wins more on time than they lose.
  // The percentile stored in the DB is already correct (ascending sort);
  // the original Plan-F direction flip was the bug.
  net_flag_rate_bullet: 'higher_is_better',
  net_flag_rate_blitz: 'higher_is_better',
  net_flag_rate_rapid: 'higher_is_better',
  net_flag_rate_classical: 'higher_is_better',
} as const satisfies Record<PercentileChipFlavor, PercentileChipDirection>;

/**
 * Extracts the TC suffix from a per-TC flavor (e.g. `clock_gap_bullet` →
 * `'bullet'`). Returns `undefined` for the 4 original Phase 94.2 flavors so
 * callers can branch on per-TC vs pooled-across-TC framing.
 */
function tcFromFlavor(flavor: PercentileChipFlavor): string | undefined {
  const suffixes = ['bullet', 'blitz', 'rapid', 'classical'] as const;
  for (const tc of suffixes) {
    if (flavor.endsWith(`_${tc}`)) return tc;
  }
  return undefined;
}

export interface PercentileChipProps {
  /** Backend cohort percentile in [0, 100]. Callers gate on `!= null` before rendering. */
  percentile: number;
  /** Routes the popover copy + direction axis. One value per chipped metric. */
  flavor: PercentileChipFlavor;
  /** Used in aria-label and (optionally) popover heading. */
  metricLabel: string;
  /** Becomes data-testid on the trigger; popover Content uses `${testId}-popover`. */
  testId: string;
}

function deriveBandColor(pct: number, direction: PercentileChipDirection): string {
  if (direction === 'lower_is_better') {
    // Low raw pct = fewer net timeouts = good (green); high raw pct = bad (red).
    if (pct < PERCENTILE_BAND_LOW) return ZONE_SUCCESS;
    if (pct > PERCENTILE_BAND_HIGH) return ZONE_DANGER;
    return GAUGE_NEUTRAL;
  }
  // higher_is_better — Phase 94.2 logic preserved verbatim.
  if (pct < PERCENTILE_BAND_LOW) return ZONE_DANGER;
  if (pct > PERCENTILE_BAND_HIGH) return ZONE_SUCCESS;
  return GAUGE_NEUTRAL;
}

function formatTopXPercent(pct: number, direction: PercentileChipDirection): string {
  if (direction === 'lower_is_better') {
    // Raw percentile is position in ascending sort by raw value — for
    // lower_is_better, low pct = top of cohort. So pct ≤ 50 → "Top pct%",
    // pct > 50 → "Bottom (100−pct)%".
    if (pct <= PERCENTILE_MEDIAN) return `Top ${Math.max(MIN_PERCENT, Math.round(pct))}%`;
    return `Bottom ${Math.max(MIN_PERCENT, Math.round(100 - pct))}%`;
  }
  // higher_is_better — pct is the user's rank. pct ≤ 50 → user is in the
  // bottom half ("Bottom pct%"); pct > 50 → user is in the top (100−pct)%.
  if (pct <= PERCENTILE_MEDIAN) return `Bottom ${Math.max(MIN_PERCENT, Math.round(pct))}%`;
  return `Top ${Math.max(MIN_PERCENT, Math.round(100 - pct))}%`;
}

function PercentileChipPopoverBody({
  flavor,
  metricLabel,
  percentile,
}: {
  flavor: PercentileChipFlavor;
  metricLabel: string;
  percentile: number;
}): React.ReactElement {
  // Cast widens the `as const`-narrowed map value to the full direction union
  // so the `lower_is_better` branch below stays type-reachable while every
  // flavor currently maps to `higher_is_better`. See `DIRECTION_BY_FLAVOR`.
  const direction = DIRECTION_BY_FLAVOR[flavor] as PercentileChipDirection;
  const ratingNote = RATING_NOTE_BY_FLAVOR[flavor];
  const tc = tcFromFlavor(flavor);
  const isLowerBetter = direction === 'lower_is_better';
  // Phase 94.3 D-3: Net Flag chips prepend a "Lower is better" line. Only
  // ever fires for `lower_is_better` flavors (none today after the UAT fix).
  const lowerBetterLine = isLowerBetter && tc !== undefined
    ? `Lower is better — you have fewer net timeouts than most ${tc} players.`
    : null;
  // Bullet 1 mirrors the chip face: "bottom X%" below the median, "top X%"
  // above. The cohort scope reads as "in <tc>" for the 12 per-TC flavors and
  // "of all ELO ratings and time controls" for the 4 pooled (Phase 94.2)
  // flavors so the wording stays accurate against what the percentile spans.
  const phrase = formatBottomOrTopPhrase(percentile, direction);
  const cohortScope = tc !== undefined
    ? `the benchmarked Lichess players in ${tc}`
    : 'the benchmarked Lichess players of all ELO ratings and time controls';
  const bullet1 = `Your ${metricLabel} is among the ${phrase.kind} ${phrase.value}% of ${cohortScope}.`;
  return (
    <div className="space-y-1.5">
      {lowerBetterLine !== null && <p>{lowerBetterLine}</p>}
      <p>{bullet1}</p>
      <p>{recentGamesBasisFor(tc)}</p>
      <p>{COPY_FILTER_INDEPENDENCE}</p>
      <p>{ratingNote}</p>
    </div>
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

  const direction = DIRECTION_BY_FLAVOR[flavor];
  const label = formatTopXPercent(percentile, direction);
  const bandColor = deriveBandColor(percentile, direction);

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
            // min-w-[6.5rem] sized so the longest label ("Bottom 50%") fits
            // comfortably at text-sm. justify-center keeps shorter labels
            // (e.g. "Top 1%") visually balanced inside the chip.
            'inline-flex items-center justify-center gap-1 rounded-full px-2 py-0.5 text-sm font-normal cursor-pointer min-w-[6.5rem]',
            'focus:outline-none focus-visible:ring-2 focus-visible:ring-ring',
          )}
          style={{ backgroundColor: bandColor, color: CHIP_TEXT_COLOR }}
        >
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
            flavor={flavor}
            metricLabel={metricLabel}
            percentile={percentile}
          />
        </PopoverPrimitive.Content>
      </PopoverPrimitive.Portal>
    </PopoverPrimitive.Root>
  );
}
