/**
 * Phase 88 — Per-TC card for the Time Pressure section. Renders 6 horizontal
 * bullet rows stacked vertically:
 *   1. Clock Gap bullet (mean (my_clock - opp_clock) / base_clock at endgame entry).
 *   2–6. Score-Delta bullets for the 5 quintiles (Q0 = 0-20% clock left, Q4 = 80-100%).
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
  PRESSURE_BIN_SCORE_NEUTRAL_ZONES,
  CLOCK_GAP_NEUTRAL_MIN,
  CLOCK_GAP_NEUTRAL_MAX,
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

// Minimum total endgame games in a TC for the card to render (mirrors backend gate).
const MIN_GAMES_PER_TC_CARD = 20;

// Minimum games in a quintile bin for a reliable bullet (mirrors backend gate).
const MIN_GAMES_PER_PRESSURE_BIN = 5;

// Human-readable time-control labels.
const TC_LABELS: Record<'bullet' | 'blitz' | 'rapid' | 'classical', string> = {
  bullet: 'Bullet',
  blitz: 'Blitz',
  rapid: 'Rapid',
  classical: 'Classical',
};

// ─── Sub-components ──────────────────────────────────────────────────────────

interface ClockGapRowProps {
  gap: ClockGapBullet;
  tc: TimePressureTcCard['tc'];
}

function ClockGapRow({ gap, tc }: ClockGapRowProps): JSX.Element {
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

function QuintileRow({ bin, tc }: QuintileRowProps): JSX.Element {
  const neutralBand = PRESSURE_BIN_SCORE_NEUTRAL_ZONES[tc][bin.quintile_index as 0 | 1 | 2 | 3 | 4]!;
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
  const cohortPct =
    bin.cohort_score != null ? `${(bin.cohort_score * 100).toFixed(1)}%` : 'n/a';

  return (
    <div
      className="flex flex-col gap-1"
      style={binStyle}
      data-testid={`time-pressure-card-${tc}-bin-${bin.quintile_index}`}
    >
      <span className="flex items-center gap-1 text-sm tabular-nums w-full">
        <span className="text-muted-foreground">{bin.quintile_label}:</span>
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
          name={`Score Delta (${bin.quintile_label} pressure)`}
          explanation={`Your score vs. cohort score when you had ${bin.quintile_label} of your clock remaining at endgame entry. Positive = outperformed.`}
          value={bin.delta}
          baseline={0}
          unit="percent"
          gameCount={bin.n}
          level={level}
          pValue={bin.p_value}
          vocabulary="score"
          neutralLower={neutralBand.min}
          neutralUpper={neutralBand.max}
          baselineLabel={cohortPct}
          methodology={
            <>
              delta = user_score − cohort_score (W+0.5D/N).<br />
              Test: Wilson score test vs cohort reference.<br />
              Confidence interval: Wilson 95% transplanted to delta space.
            </>
          }
          testId={`time-pressure-card-${tc}-bin-${bin.quintile_index}-info`}
          ariaLabel={`What is Score Delta at ${bin.quintile_label} pressure?`}
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
          ariaLabel={`Score delta at ${bin.quintile_label} pressure: ${signedDelta}`}
        />
      </div>
    </div>
  );
}

interface EmptyBinRowProps {
  bin: PressureQuintileBullet;
  tc: TimePressureTcCard['tc'];
}

function EmptyBinRow({ bin, tc }: EmptyBinRowProps): JSX.Element {
  return (
    <div
      className="flex flex-col gap-1"
      data-testid={`time-pressure-card-${tc}-bin-${bin.quintile_index}-empty`}
    >
      <span className="flex items-center gap-1 text-sm w-full">
        <span className="text-muted-foreground">{bin.quintile_label}:</span>
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

// ─── Main component ──────────────────────────────────────────────────────────

export function EndgameTimePressureCard({ card }: { card: TimePressureTcCard }): JSX.Element | null {
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
          How your clock position and chess score relate across {tcLabel} endgames.
          Q0 = 0-20% clock remaining (maximum pressure), Q4 = 80-100% (minimum pressure).
        </InfoPopover>
        <span
          className="ml-1 text-sm text-muted-foreground tabular-nums font-normal"
          data-testid={`time-pressure-card-${card.tc}-total`}
        >
          ({card.total.toLocaleString()} games)
        </span>
      </h3>

      <div className="flex flex-col gap-4">
        <ClockGapRow gap={card.clock_gap} tc={card.tc} />

        {card.quintiles.map((bin) =>
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
