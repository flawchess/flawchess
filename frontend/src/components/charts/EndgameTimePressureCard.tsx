/**
 * Phase 88 — Per-TC card for the Time Pressure section.
 *
 * SC-2 (Phase 88.4): Three-column header row (You / Gap+info / Opp) sits
 * ABOVE the Clock Gap bullet chart. Net flag rate row stays below the bullet.
 * The old "Clock Gap: X% <info>" label row and the ThreeStatRow (You/Opp/Net)
 * are replaced by ClockGapHeaderRow + NetFlagRateRow.
 *
 * SC-3 (Phase 88.4): The four stacked per-bucket Score-Gap bullet rows
 * (QuintileRow/EmptyBinRow) are replaced by a single ScoreGapByTimePressureChart.
 *
 * Sparse handling (card level only):
 *   - card.total < MIN_GAMES_PER_TC_CARD → return null (TC hidden entirely).
 */

import { Swords } from 'lucide-react';

import { MiniBulletChart } from '@/components/charts/MiniBulletChart';
import { PercentileChip, type PercentileChipFlavor } from '@/components/charts/PercentileChip';
import { ScoreGapByTimePressureChart } from '@/components/charts/ScoreGapByTimePressureChart';
import { TimeControlIcon } from '@/components/icons/TimeControlIcon';
import { MetricStatPopover } from '@/components/popovers/MetricStatPopover';
import { InfoPopover } from '@/components/ui/info-popover';
import {
  CLOCK_GAP_NEUTRAL_MIN,
  CLOCK_GAP_NEUTRAL_MAX,
  MIN_GAMES_PER_TC_CARD,
  MIN_GAMES_PER_PRESSURE_BIN,
  NEUTRAL_TIMEOUT_THRESHOLD,
} from '@/generated/endgameZones';
import { CLOCK_GAP_DOMAIN, clampDeltaCi } from '@/lib/pressureBulletConfig';
import { isConfident } from '@/lib/significance';
import { ZONE_DANGER, ZONE_SUCCESS } from '@/lib/theme';
import type { ClockGapBullet, TimePressureTcCard } from '@/types/endgames';
import { deriveLevel } from './EndgameOverallShared';

// MIN_GAMES_PER_TC_CARD and MIN_GAMES_PER_PRESSURE_BIN are imported from
// @/generated/endgameZones (codegen-mirrored from app/services/endgame_zones.py).

// Human-readable time-control labels.
const TC_LABELS: Record<'bullet' | 'blitz' | 'rapid' | 'classical', string> = {
  bullet: 'Bullet',
  blitz: 'Blitz',
  rapid: 'Rapid',
  classical: 'Classical',
};

// ── Phase 94.3 Plan 06: typed TC→flavor dispatch dicts ─────────────────────
// TypeScript cannot infer Literal types from template-literal concatenation
// (e.g. `\`clock_gap_${card.tc}\``), so a typed map per chip metric keeps the
// PercentileChip `flavor` prop strictly typed without `as` casts. Mirrors the
// backend's `_TC_TO_METRIC_KEYS` dispatch pattern in
// app/services/endgame_service.py.
type TcKey = TimePressureTcCard['tc'];
const CLOCK_GAP_FLAVOR_BY_TC: Record<TcKey, PercentileChipFlavor> = {
  bullet: 'clock_gap_bullet',
  blitz: 'clock_gap_blitz',
  rapid: 'clock_gap_rapid',
  classical: 'clock_gap_classical',
};
const NET_FLAG_RATE_FLAVOR_BY_TC: Record<TcKey, PercentileChipFlavor> = {
  bullet: 'net_flag_rate_bullet',
  blitz: 'net_flag_rate_blitz',
  rapid: 'net_flag_rate_rapid',
  classical: 'net_flag_rate_classical',
};
const TIME_PRESSURE_SCORE_GAP_FLAVOR_BY_TC: Record<TcKey, PercentileChipFlavor> = {
  bullet: 'time_pressure_score_gap_bullet',
  blitz: 'time_pressure_score_gap_blitz',
  rapid: 'time_pressure_score_gap_rapid',
  classical: 'time_pressure_score_gap_classical',
};

// ─── Sub-components ──────────────────────────────────────────────────────────

/**
 * Format the "X%" cell content for the You/Opp avg time cells.
 * Returns an em-dash when the pct is null (legacy imports without clock
 * data). pct is a fraction (0..1) multiplied by 100 for display. The raw
 * seconds were dropped from the cell post-UAT (88.4) — the percentage of
 * starting time carries the signal; the absolute seconds added noise.
 */
function formatPct(pct: number | null): string {
  if (pct === null) return '—';
  return `${Math.round(pct * 100)}%`;
}

/**
 * Format the net flag rate as a signed, integer-rounded percentage.
 * rate is a fraction (0.005 = 0.5%) multiplied by 100 for display.
 * Always shows a sign except for 0%.
 */
function formatNetTimeoutRate(rate: number): string {
  const pct = Math.round(rate * 100);
  if (pct === 0) return '0%';
  const sign = pct > 0 ? '+' : '';
  return `${sign}${pct}%`;
}

/**
 * Return a zone color for the net flag rate, or `undefined` when the rate is
 * within the neutral band. `rate` is a fraction (0.005 = 0.5%);
 * `NEUTRAL_TIMEOUT_THRESHOLD = 5.0` is in PERCENT units (codegen-emitted from
 * app/services/endgame_zones.py). We multiply rate by 100 before comparing —
 * the unit mismatch is intentional and tested explicitly (Plan 88-14 B-1 lock).
 */
function tintForNetTimeoutRate(rate: number): string | undefined {
  const pct = rate * 100;
  if (pct > NEUTRAL_TIMEOUT_THRESHOLD) return ZONE_SUCCESS;
  if (pct < -NEUTRAL_TIMEOUT_THRESHOLD) return ZONE_DANGER;
  return undefined;
}

/**
 * Header row rendered ABOVE the Clock Gap bullet.
 * Single left-aligned inline stat: "You: x% • Opp: y% • Gap: z% <info>"
 * with the Clock Gap percentile chip pushed to the right edge.
 * Preserves the triple-gate font-tinting from the old ClockGapRow.
 */
function ClockGapHeaderRow({ gap, card }: { gap: ClockGapBullet; card: TimePressureTcCard }) {
  // Preserve font-tinting logic from ClockGapRow (triple-gate).
  const level = deriveLevel(gap.p_value, gap.n);
  const neutralMin = CLOCK_GAP_NEUTRAL_MIN;
  const neutralMax = CLOCK_GAP_NEUTRAL_MAX;
  const isInColoredZone = gap.mean_diff_pct >= neutralMax || gap.mean_diff_pct <= neutralMin;
  const showFontColor = gap.n >= MIN_GAMES_PER_PRESSURE_BIN && isConfident(level) && isInColoredZone;
  const signedPct = Math.round(gap.mean_diff_pct * 100);
  const formattedGapValue = `${gap.mean_diff_pct >= 0 ? '+' : ''}${signedPct}%`;

  const fontColor = showFontColor
    ? gap.mean_diff_pct >= neutralMax
      ? ZONE_SUCCESS
      : ZONE_DANGER
    : undefined;

  return (
    <div
      className="flex items-center gap-1 text-sm tabular-nums mb-2"
      data-testid={`time-pressure-card-${card.tc}-clock-gap-header`}
    >
      <span data-testid={`time-pressure-card-${card.tc}-my-avg-time`}>
        You: <span className="font-semibold">{formatPct(card.user_avg_pct)}</span>
      </span>
      <span className="text-muted-foreground">•</span>
      <span data-testid={`time-pressure-card-${card.tc}-opp-avg-time`}>
        Opp: <span className="font-semibold">{formatPct(card.opp_avg_pct)}</span>
      </span>
      <span className="text-muted-foreground">•</span>
      <span>
        Gap:{' '}
        <span
          className="font-semibold"
          style={fontColor ? { color: fontColor } : undefined}
          data-testid={`time-pressure-card-${card.tc}-clock-gap-value`}
        >
          {formattedGapValue}
        </span>
      </span>
      <MetricStatPopover
        name="Clock Gap"
        explanation="Your average clock advantage over your opponent when the endgame begins, as a share of the starting time. Positive means you entered the endgame with more time on your clock."
        value={gap.mean_diff_pct}
        baseline={0}
        unit="percent"
        gameCount={gap.n}
        level={level}
        pValue={gap.p_value}
        vocabulary="score"
        neutralLower={neutralMin}
        neutralUpper={neutralMax}
        baselineLabel="0%"
        methodology={
          <>
            Mean of (user_clock − opp_clock) / base_clock at endgame entry.<br />
            Test: one-sample z-test vs 0.<br />
            Confidence interval: 95% normal-approx.
          </>
        }
        testId={`time-pressure-card-${card.tc}-clock-gap-info`}
        ariaLabel="What is Clock Gap?"
      />
      {/* Phase 94.3 (TPCTL-06): Clock Gap percentile chip, right-aligned.
          `ml-auto` pushes the chip to the row's right edge. Gated on
          `!= null` to honor the backend inclusion-floor contract — a null
          percentile suppresses the chip silently. */}
      {card.clock_gap_percentile != null && (
        <span className="ml-auto">
          <PercentileChip
            percentile={card.clock_gap_percentile}
            flavor={CLOCK_GAP_FLAVOR_BY_TC[card.tc]}
            metricLabel="Clock Gap"
            testId={`time-pressure-card-${card.tc}-clock-gap-chip`}
          />
        </span>
      )}
    </div>
  );
}

/**
 * SC-2: Slim row holding only the surviving "Net flag rate:" stat.
 * Extracted from the old ThreeStatRow; the You/Opp stats moved to ClockGapHeaderRow.
 */
function NetFlagRateRow({ card }: { card: TimePressureTcCard }) {
  const tint = tintForNetTimeoutRate(card.net_timeout_rate);
  return (
    <div
      className="flex text-sm text-muted-foreground tabular-nums mt-3"
      data-testid={`time-pressure-card-${card.tc}-net-flag-rate-row`}
    >
      <span
        data-testid={`time-pressure-card-${card.tc}-net-flag-rate`}
        className="inline-flex items-center gap-1"
      >
        Net flag rate:{' '}
        {/* REVIEW.md WR-04: the tinted span on its own conveys directionality
            to sighted users only. The popover carries the WDL convention
            reference so screen-reader users get the same context. */}
        <span style={tint ? { color: tint } : undefined}>
          {formatNetTimeoutRate(card.net_timeout_rate)}
        </span>
        <InfoPopover
          ariaLabel="What is Net flag rate?"
          testId={`time-pressure-card-${card.tc}-net-flag-rate-info`}
          side="top"
        >
          <p>
            <strong>Net flag rate:</strong> how often you run out of time
            compared to your opponents. Positive = you flag less often than
            them; negative = you flag more often.
          </p>
        </InfoPopover>
      </span>
      {/* Phase 94.3 (TPCTL-06): Net Flag Rate percentile chip, right-aligned.
          `ml-auto` on the wrapping span pushes the chip to the row's right
          edge inside the parent flex container. Gated on `!= null` so a 0.0
          percentile (best possible — no net timeouts) still renders, while
          below-floor (null) suppresses silently — see Pitfall 7. */}
      {card.net_flag_rate_percentile != null && (
        <span className="ml-auto">
          <PercentileChip
            percentile={card.net_flag_rate_percentile}
            flavor={NET_FLAG_RATE_FLAVOR_BY_TC[card.tc]}
            metricLabel="Net Flag Rate"
            testId={`time-pressure-card-${card.tc}-net-flag-rate-chip`}
          />
        </span>
      )}
    </div>
  );
}

// ─── Main component ──────────────────────────────────────────────────────────

export function EndgameTimePressureCard({
  card,
  grandTotal,
}: {
  card: TimePressureTcCard;
  /**
   * Sum of `total` across all TC cards in the section. Used to render the
   * per-card percentage in the title ("Games: X% (N)"). Optional so the card
   * stays usable from tests without forcing a fixture rewrite — when absent
   * we fall back to the count-only format. Section-level orchestrator
   * computes this once and passes it down.
   */
  grandTotal?: number;
}) {
  // TC-level hide: not enough games to show any meaningful data for this TC.
  if (card.total < MIN_GAMES_PER_TC_CARD) return null;

  const tcLabel = TC_LABELS[card.tc];
  // Percent of the user's filtered games belonging to this TC, rounded to an
  // integer. `null` when the section didn't supply a grand total or it would
  // produce a div-by-zero.
  const pctOfTotal =
    grandTotal !== undefined && grandTotal > 0
      ? Math.round((card.total / grandTotal) * 100)
      : null;

  const gap = card.clock_gap;

  return (
    <div
      className="charcoal-texture rounded-md p-4"
      data-testid={`time-pressure-card-${card.tc}`}
      role="group"
      aria-label={`${tcLabel} time pressure breakdown`}
    >
      <h3 className="text-base font-semibold mb-3 flex items-center gap-1.5">
        {/* Post-UAT: TC icon next to the label matches the filter-button
            convention. h-4 w-4 keeps icon optical weight aligned with the
            text-base heading. */}
        <TimeControlIcon timeControl={card.tc} className="h-4 w-4 shrink-0" />
        <span>{tcLabel}</span>
        {/* Post-UAT (round 2): game count right-aligned, "Games: X% (N)"
            framing with a sword icon. The percentage is this TC's share of
            the user's filtered games (computed at the section level so all
            cards share the same denominator). Falls back to "Games: N" when
            the section didn't pass a grand total. */}
        <span
          className="ml-auto inline-flex items-center gap-1 text-sm text-muted-foreground tabular-nums font-normal"
          data-testid={`time-pressure-card-${card.tc}-total`}
        >
          {pctOfTotal !== null
            ? `Games: ${pctOfTotal}% (${card.total.toLocaleString()})`
            : `Games: ${card.total.toLocaleString()}`}
          <Swords className="h-3.5 w-3.5" aria-hidden="true" />
        </span>
      </h3>

      <div className="flex flex-col gap-4">
        {/* SC-2: top section — 3-column header row + Clock Gap bullet + net flag rate.
            The ClockGapHeaderRow sits ABOVE the bullet, replacing the old label row. */}
        <div data-testid={`time-pressure-card-${card.tc}-top-zone`}>
          <ClockGapHeaderRow gap={gap} card={card} />
          <div
            className="min-w-0 tabular-nums"
            data-testid={`time-pressure-card-${card.tc}-clock-gap-bullet`}
          >
            <MiniBulletChart
              value={gap.mean_diff_pct}
              center={0}
              neutralMin={CLOCK_GAP_NEUTRAL_MIN}
              neutralMax={CLOCK_GAP_NEUTRAL_MAX}
              domain={CLOCK_GAP_DOMAIN}
              ciLow={gap.ci_low != null ? clampDeltaCi(gap.ci_low) : undefined}
              ciHigh={gap.ci_high != null ? clampDeltaCi(gap.ci_high) : undefined}
              ariaLabel={`Clock Gap: ${gap.mean_diff_pct >= 0 ? '+' : ''}${Math.round(gap.mean_diff_pct * 100)}%`}
              barColor="neutral"
            />
          </div>
          {/* Visual separator between Clock Gap bullet and Net flag rate row. */}
          <div className="border-t border-border/40 mt-3" aria-hidden="true" />
          <NetFlagRateRow card={card} />
        </div>

        {/* Visual separator between top section and score-gap chart. */}
        <div className="border-t border-border/40" aria-hidden="true" />

        {/* SC-3: Replace the four stacked per-bucket bullet rows with the
            ScoreGapByTimePressureChart (line chart with zone bands). */}
        <div>
          {/* Phase 94.3 (TPCTL-06): subtitle changed from inline-flex → flex so
              the trailing `ml-auto` Time Pressure Score Gap chip slot can push
              to the right edge. The leading label + InfoPopover still sit
              side-by-side via `items-center gap-1.5`; the chip wraps on narrow
              widths (mobile parity verified at 375px). The element changed
              from <p> to <div> because the chip's Radix popover renders a
              span[role="button"] which is invalid inside a paragraph. */}
          <div
            className="flex items-center gap-1.5 text-sm font-medium text-muted-foreground mb-2"
            data-testid={`time-pressure-card-${card.tc}-quintiles-subtitle`}
          >
            <span>Score Gap by Remaining Time</span>
            <InfoPopover
              ariaLabel={`${tcLabel} score gap by remaining time info`}
              testId={`time-pressure-card-${card.tc}-quintiles-info`}
              side="top"
            >
              <div className="space-y-2">
                <p>
                  This breaks your endgames into buckets by how much of your
                  clock was left, and in each bucket compares your score
                  against opponents who were under the <em>same amount</em> of
                  time pressure. A positive gap means you outscored
                  comparably-pressured opponents; a negative gap means they
                  outscored you.
                </p>
                <p>
                  Each marker is sized by how many of that time bucket's games were
                  yours versus your opponents'. A bigger dot means you were in this
                  time pressure situation more often than your opponents.
                </p>
              </div>
            </InfoPopover>
            {card.time_pressure_score_gap_percentile != null && (
              <span className="ml-auto">
                <PercentileChip
                  percentile={card.time_pressure_score_gap_percentile}
                  flavor={TIME_PRESSURE_SCORE_GAP_FLAVOR_BY_TC[card.tc]}
                  metricLabel="Time Pressure Score Gap"
                  testId={`time-pressure-card-${card.tc}-time-pressure-score-gap-chip`}
                />
              </span>
            )}
          </div>
          <div data-testid={`time-pressure-card-${card.tc}-score-gap-chart`}>
            <ScoreGapByTimePressureChart quintiles={card.quintiles} tc={card.tc} />
          </div>
        </div>
      </div>
    </div>
  );
}
