/**
 * Phase 88 — Per-TC card for the Time Pressure section. Renders 5 horizontal
 * bullet rows stacked vertically:
 *   1. Clock Gap bullet (mean (my_clock - opp_clock) / base_clock at endgame entry).
 *   2–5. Score-Delta bullets for the 4 visible quintiles (Q0..Q3 only; Q4 = 80-100%
 *        clock remaining is hidden — low-signal tail per CONTEXT §2 A-4, 2026-05-17).
 *        Backend keeps emitting all 5 quintiles; the Q4 filter is purely frontend.
 *
 * Sparse handling:
 *   - card.total < MIN_GAMES_PER_TC_CARD → return null (TC hidden entirely).
 *   - bin.n === 0 → dash + "no games" label, no bullet glyph; slot preserved for uniform height.
 *   - 0 < bin.n < MIN_GAMES_PER_PRESSURE_BIN → dimmed bullet at UNRELIABLE_OPACITY + n=X chip.
 *   - bin.n >= MIN_GAMES_PER_PRESSURE_BIN → full opacity; triple-gate font coloring.
 *
 * Triple-gate font coloring fires only when:
 *   n >= MIN_GAMES_PER_PRESSURE_BIN AND isConfident(deriveLevel(p, n)) AND delta outside neutral band.
 */

import type { CSSProperties } from 'react';

import { MiniBulletChart } from '@/components/charts/MiniBulletChart';
import { MetricStatPopover } from '@/components/popovers/MetricStatPopover';
import { InfoPopover } from '@/components/ui/info-popover';
import {
  CLOCK_GAP_NEUTRAL_MIN,
  CLOCK_GAP_NEUTRAL_MAX,
  MIN_GAMES_PER_TC_CARD,
  MIN_GAMES_PER_PRESSURE_BIN,
  NEUTRAL_TIMEOUT_THRESHOLD,
  getPressureBinBand,
} from '@/generated/endgameZones';
import {
  PRESSURE_DELTA_CENTER,
  PRESSURE_DELTA_DOMAIN,
  CLOCK_GAP_DOMAIN,
  clampDeltaCi,
  pressureDeltaZoneColor,
} from '@/lib/pressureBulletConfig';
import { isConfident } from '@/lib/significance';
import { UNRELIABLE_OPACITY, ZONE_DANGER, ZONE_SUCCESS } from '@/lib/theme';
import type { ClockGapBullet, PressureQuintileBullet, TimePressureTcCard } from '@/types/endgames';
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

/**
 * Qualitative pressure labels for the 4 visible quintiles (Plan 88-13 A-4).
 * Backend's `bin.quintile_label` (raw "0-20%" range string) is intentionally
 * not surfaced anywhere in the UI — these labels replace it.
 * Q4 (80-100%) is filtered out at the parent map() and never reaches a row,
 * so it has no entry here.
 */
const PRESSURE_LABELS: Record<0 | 1 | 2 | 3, string> = {
  0: 'High Pressure (0-20%)',
  1: 'Medium Pressure (20-40%)',
  2: 'Low Pressure (40-60%)',
  3: 'Very Low Pressure (60-80%)',
};

/** Highest displayed quintile index; Q4 (80-100%) is filtered out for display. */
const MAX_VISIBLE_QUINTILE_INDEX = 3;

/**
 * Return the qualitative pressure label for `quintile_index ∈ [0, 3]`, or `null`
 * for any out-of-range index. The parent filter already drops Q4, so this is a
 * defense-in-depth type-narrowing helper for the row components.
 */
function pressureLabel(quintileIndex: number): string | null {
  if (quintileIndex === 0 || quintileIndex === 1 || quintileIndex === 2 || quintileIndex === 3) {
    return PRESSURE_LABELS[quintileIndex];
  }
  return null;
}

// ─── Sub-components ──────────────────────────────────────────────────────────

interface ClockGapRowProps {
  gap: ClockGapBullet;
  tc: TimePressureTcCard['tc'];
}

function ClockGapRow({ gap, tc }: ClockGapRowProps) {
  const level = deriveLevel(gap.p_value, gap.n);
  const neutralMin = CLOCK_GAP_NEUTRAL_MIN;
  const neutralMax = CLOCK_GAP_NEUTRAL_MAX;
  const isInColoredZone = gap.mean_diff_pct >= neutralMax || gap.mean_diff_pct <= neutralMin;
  const showFontColor = gap.n >= MIN_GAMES_PER_PRESSURE_BIN && isConfident(level) && isInColoredZone;
  const signedPct = (gap.mean_diff_pct * 100).toFixed(1);
  const formattedValue = `${gap.mean_diff_pct >= 0 ? '+' : ''}${signedPct}%`;

  // Pick zone color for font tinting.
  const fontColor = showFontColor
    ? gap.mean_diff_pct >= neutralMax
      ? ZONE_SUCCESS
      : ZONE_DANGER
    : undefined;

  return (
    <div
      className="flex flex-col gap-1"
      data-testid={`time-pressure-card-${tc}-clock-gap`}
    >
      <span className="flex items-center gap-1 text-sm tabular-nums w-full">
        <span className="text-muted-foreground">Clock gap:</span>
        <span
          className="font-semibold"
          style={fontColor ? { color: fontColor } : undefined}
          data-testid={`time-pressure-card-${tc}-clock-gap-value`}
        >
          {formattedValue}
        </span>
        <span className="text-muted-foreground text-sm">({gap.n} games)</span>
        <MetricStatPopover
          name="Clock Gap"
          explanation="Average clock time advantage at endgame entry: (your clock − opponent clock) / starting clock. Positive means you entered with more time."
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
          testId={`time-pressure-card-${tc}-clock-gap-info`}
          ariaLabel="What is Clock Gap?"
        />
      </span>
      <div
        className="min-w-0 tabular-nums"
        data-testid={`time-pressure-card-${tc}-clock-gap-bullet`}
      >
        <MiniBulletChart
          value={gap.mean_diff_pct}
          center={0}
          neutralMin={neutralMin}
          neutralMax={neutralMax}
          domain={CLOCK_GAP_DOMAIN}
          ciLow={gap.ci_low != null ? clampDeltaCi(gap.ci_low) : undefined}
          ciHigh={gap.ci_high != null ? clampDeltaCi(gap.ci_high) : undefined}
          ariaLabel={`Clock gap: ${formattedValue}`}
        />
      </div>
    </div>
  );
}

interface QuintileRowProps {
  bin: PressureQuintileBullet;
  tc: TimePressureTcCard['tc'];
}

function QuintileRow({ bin, tc }: QuintileRowProps) {
  // Phase 88.1 WR-03/IN-06: use the typed helper instead of an unsafe non-null
  // assertion on a Record index. Returns null for out-of-range quintile_index;
  // we early-return the row in that case rather than rendering with a bogus band.
  const neutralBand = getPressureBinBand(tc, bin.quintile_index);
  if (!neutralBand) return null;

  // Plan 88-13 A-4: source the displayed label from PRESSURE_LABELS (qualitative
  // names), not bin.quintile_label (raw "0-20%" range string). The parent filter
  // already drops Q4; null-guard handles any out-of-range index defensively.
  const displayLabel = pressureLabel(bin.quintile_index);
  if (displayLabel === null) return null;

  const level = deriveLevel(bin.p_value, bin.n);
  const isInColoredZone = bin.delta >= neutralBand.max || bin.delta <= neutralBand.min;
  const showFontColor =
    bin.n >= MIN_GAMES_PER_PRESSURE_BIN && isConfident(level) && isInColoredZone;
  const fontColor = showFontColor
    ? pressureDeltaZoneColor(bin.delta, neutralBand.min, neutralBand.max)
    : undefined;

  const isDimmed = bin.n > 0 && bin.n < MIN_GAMES_PER_PRESSURE_BIN;
  const binStyle: CSSProperties | undefined = isDimmed
    ? { opacity: UNRELIABLE_OPACITY }
    : undefined;

  const signedDelta = `${bin.delta >= 0 ? '+' : ''}${(bin.delta * 100).toFixed(1)}%`;
  const oppPct =
    bin.opp_score != null ? `${(bin.opp_score * 100).toFixed(1)}%` : 'n/a';

  return (
    <div
      className="flex flex-col gap-1"
      style={binStyle}
      data-testid={`time-pressure-card-${tc}-bin-${bin.quintile_index}`}
    >
      <span className="flex items-center gap-1 text-sm tabular-nums w-full">
        <span className="text-muted-foreground">{displayLabel}:</span>
        <span
          className="font-semibold"
          style={fontColor ? { color: fontColor } : undefined}
          data-testid={`time-pressure-card-${tc}-bin-${bin.quintile_index}-value`}
        >
          {signedDelta}
        </span>
        {isDimmed && (
          <span
            className="text-muted-foreground text-sm"
            data-testid={`time-pressure-card-${tc}-bin-${bin.quintile_index}-n`}
          >
            n={bin.n}
          </span>
        )}
        <MetricStatPopover
          name={`Score Delta (${displayLabel})`}
          explanation={`Your score vs. your opponents' score when you had ${displayLabel} of your clock remaining at endgame entry, compared against the matching opponent-clock quintile in the same games. Positive = you outperformed your opponents.`}
          value={bin.delta}
          baseline={0}
          unit="percent"
          gameCount={bin.n}
          level={level}
          pValue={bin.p_value}
          vocabulary="score"
          neutralLower={neutralBand.min}
          neutralUpper={neutralBand.max}
          baselineLabel={oppPct}
          methodology={
            <>
              delta = user_score − opp_score (W+0.5D/N).<br />
              Each side bucketed by its own clock remaining at endgame entry.<br />
              Test: independent two-sample test; same filtered games.<br />
              CI: 95% normal-approximation on the difference.
            </>
          }
          testId={`time-pressure-card-${tc}-bin-${bin.quintile_index}-info`}
          ariaLabel={`What is Score Delta at ${displayLabel}?`}
        />
      </span>
      <div
        className="min-w-0 tabular-nums"
        data-testid={`time-pressure-card-${tc}-bin-${bin.quintile_index}-bullet`}
      >
        <MiniBulletChart
          value={bin.delta}
          center={PRESSURE_DELTA_CENTER}
          neutralMin={neutralBand.min}
          neutralMax={neutralBand.max}
          domain={PRESSURE_DELTA_DOMAIN}
          ciLow={bin.ci_low != null ? clampDeltaCi(bin.ci_low) : undefined}
          ciHigh={bin.ci_high != null ? clampDeltaCi(bin.ci_high) : undefined}
          ariaLabel={`Score delta at ${displayLabel}: ${signedDelta}`}
        />
      </div>
    </div>
  );
}

interface EmptyBinRowProps {
  bin: PressureQuintileBullet;
  tc: TimePressureTcCard['tc'];
}

function EmptyBinRow({ bin, tc }: EmptyBinRowProps) {
  // Plan 88-13 A-4: use qualitative pressure label instead of bin.quintile_label.
  const displayLabel = pressureLabel(bin.quintile_index);
  if (displayLabel === null) return null;
  return (
    <div
      className="flex flex-col gap-1"
      data-testid={`time-pressure-card-${tc}-bin-${bin.quintile_index}-empty`}
    >
      <span className="flex items-center gap-1 text-sm w-full">
        <span className="text-muted-foreground">{displayLabel}:</span>
        <span
          className="text-muted-foreground text-sm"
          aria-label="no games"
        >
          &mdash;
        </span>
        <span className="text-muted-foreground text-sm">no games</span>
      </span>
      {/* Empty slot to preserve uniform row height across the TC grid. */}
      <div className="h-5 w-full" aria-hidden="true" />
    </div>
  );
}

// ─── Plan 88-14 (A-3): top-zone 3-stat row ──────────────────────────────────

/**
 * Format "Ns%" + "(Ns)" cell content for the My/Opp avg time cells.
 * Returns an em-dash when either input is null (legacy imports without
 * clock data). pct is a fraction (0..1) — multiplied by 100 here for display.
 */
function formatPctSecs(pct: number | null, secs: number | null): string {
  if (pct === null || secs === null) return '—';
  return `${Math.round(pct * 100)}% (${Math.round(secs).toLocaleString()}s)`;
}

/**
 * Format the net flag rate as a signed percentage with one decimal point.
 * rate is a fraction (0.005 = 0.5%) — multiplied by 100 here for display.
 * Always shows a sign except for 0.0%.
 */
function formatNetTimeoutRate(rate: number): string {
  const pct = rate * 100;
  if (pct === 0) return '0.0%';
  const sign = pct > 0 ? '+' : '';
  return `${sign}${pct.toFixed(1)}%`;
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

interface ThreeStatRowProps {
  card: TimePressureTcCard;
}

function ThreeStatRow({ card }: ThreeStatRowProps) {
  const tint = tintForNetTimeoutRate(card.net_timeout_rate);
  return (
    <div
      className="flex flex-wrap gap-x-4 gap-y-1 text-sm text-muted-foreground tabular-nums mt-1"
      data-testid={`time-pressure-card-${card.tc}-top-stats`}
    >
      <span data-testid={`time-pressure-card-${card.tc}-my-avg-time`}>
        My avg time:{' '}
        <span className="text-foreground">
          {formatPctSecs(card.user_avg_pct, card.user_avg_seconds)}
        </span>
      </span>
      <span data-testid={`time-pressure-card-${card.tc}-opp-avg-time`}>
        Opp avg time:{' '}
        <span className="text-foreground">
          {formatPctSecs(card.opp_avg_pct, card.opp_avg_seconds)}
        </span>
      </span>
      <span
        data-testid={`time-pressure-card-${card.tc}-net-flag-rate`}
        className="inline-flex items-center gap-1"
      >
        Net flag rate:{' '}
        {/* REVIEW.md WR-04: the tinted span on its own conveys directionality
            to sighted users only. The popover (consistent with the Clock Gap
            row above) carries the WDL convention reference so screen-reader
            users get the same context. */}
        <span style={tint ? { color: tint } : undefined}>
          {formatNetTimeoutRate(card.net_timeout_rate)}
        </span>
        <InfoPopover
          ariaLabel="What is Net flag rate?"
          testId={`time-pressure-card-${card.tc}-net-flag-rate-info`}
          side="top"
        >
          <p>
            Your opponents' flag (timeout) rate minus your own, on games in this
            time control. Positive = you flag less often than your opponents.
            Negative = you flag more often.
          </p>
        </InfoPopover>
      </span>
    </div>
  );
}

// ─── Main component ──────────────────────────────────────────────────────────

export function EndgameTimePressureCard({ card }: { card: TimePressureTcCard }) {
  // TC-level hide: not enough games to show any meaningful data for this TC.
  if (card.total < MIN_GAMES_PER_TC_CARD) return null;

  const tcLabel = TC_LABELS[card.tc];

  return (
    <div
      className="charcoal-texture rounded-md p-4"
      data-testid={`time-pressure-card-${card.tc}`}
      role="group"
      aria-label={`${tcLabel} time pressure breakdown`}
    >
      <h3 className="text-base font-semibold mb-3 inline-flex items-center gap-1">
        <span>{tcLabel}</span>
        <InfoPopover
          ariaLabel={`${tcLabel} time pressure info`}
          testId={`time-pressure-card-${card.tc}-title-info`}
          side="top"
        >
          How your chess score changes with the clock remaining at endgame entry,
          from High Pressure (0-20% clock left) to Very Low Pressure (60-80% clock
          left). The 80-100% (minimum pressure) bin is intentionally hidden as a
          low-signal tail. The top zone summarises overall clock state and flag
          rate; the bullets below break score performance down by clock remaining.
        </InfoPopover>
        <span
          className="ml-1 text-sm text-muted-foreground tabular-nums font-normal"
          data-testid={`time-pressure-card-${card.tc}-total`}
        >
          ({card.total.toLocaleString()} games)
        </span>
      </h3>

      <div className="flex flex-col gap-4">
        {/* Plan 88-14 A-3: top zone — Clock Gap bullet + 3-stat row. */}
        <div data-testid={`time-pressure-card-${card.tc}-top-zone`}>
          <ClockGapRow gap={card.clock_gap} tc={card.tc} />
          <ThreeStatRow card={card} />
        </div>

        {/* Visual separator between top zone and per-quintile bullets. */}
        <div className="border-t border-border/40" aria-hidden="true" />

        {card.quintiles
          // Plan 88-13 A-4: hide the Q4 (80-100% clock remaining) row entirely.
          // Backend still emits 5 quintiles; the asymmetry is intentional per
          // CONTEXT §2 clarification #2.
          .filter((bin) => bin.quintile_index <= MAX_VISIBLE_QUINTILE_INDEX)
          .map((bin) =>
            bin.n === 0 ? (
              <EmptyBinRow key={bin.quintile_index} bin={bin} tc={card.tc} />
            ) : (
              <QuintileRow key={bin.quintile_index} bin={bin} tc={card.tc} />
            ),
          )}
      </div>
    </div>
  );
}
