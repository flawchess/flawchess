/**
 * Phase 97 Plan 03 — Per-TC card for the Endgame Metrics by Time Control section.
 *
 * Renders one card per time control with the Conversion / Parity / Recovery
 * trifecta laid out as three columns inside a SINGLE charcoal container,
 * separated by a vertical divider on desktop and horizontal dividers when
 * stacked on mobile (mirrors EndgameOverallPerformanceSection's two-column
 * card). Each block shows a gauge (TC-specific bands for all three metrics),
 * WDL bar, Delta-ES Score Gap bullet, and a percentile chip when the per-TC
 * percentile is available.
 *
 * Key design decisions (from 97-PATTERNS.md / 97-RESEARCH.md):
 *   - Gauge zones: TC-specific via TC_METRIC_BANDS[card.tc] for conversion,
 *     recovery AND parity (parity rate went per-TC on 2026-05-29 — each card
 *     shows that TC's §3.2.1 IQR). The parity ΔES-gap neutral band stays global
 *     (SCORE_GAP_PARITY_NEUTRAL_*); only the gauge rate band is per-TC.
 *   - Display shift: recomputed per-TC = -(lower+upper)/2 for conv/recov;
 *     0 for parity (Pitfall 3).
 *   - TC_METRIC_BANDS access is narrowed per noUncheckedIndexedAccess (Pitfall 5).
 *   - gapColor tinting uses RAW (unshifted) values; only the rendered number and
 *     neutral-band edges shift (D-04 carve-out).
 *   - Recovery popover copy uses opponent-first framing per folded todo
 *     2026-05-17-recovery-score-gap-popover-copy.md.
 *   - Per-TC percentile chips disclose the cohort rating anchor in their
 *     tooltip ("…of ~{anchor}-rated players in {tc}"), so the chip is gated on
 *     BOTH percentile != null AND anchorRating != null — matching
 *     EndgameTimePressureCard. Without an anchor the tooltip would render a
 *     broken "~-rated players" clause, so the chip is suppressed instead.
 */

import { useMemo } from 'react';

import { Cpu } from 'lucide-react';

import { EndgameGauge } from '@/components/charts/EndgameGauge';
import { MetricStatPopover } from '@/components/popovers/MetricStatPopover';
import { MiniWDLBar } from '@/components/stats/MiniWDLBar';
import { TimeControlIcon } from '@/components/icons/TimeControlIcon';
import { InfoPopover } from '@/components/ui/info-popover';
import { ZONE_DANGER, ZONE_SUCCESS, colorizeGaugeZones } from '@/lib/theme';
import { BUCKET_DISPLAY_LABELS } from '@/lib/endgameMetrics';
import { TC_METRIC_BANDS, SCORE_GAP_PARITY_NEUTRAL_MIN, SCORE_GAP_PARITY_NEUTRAL_MAX } from '@/generated/endgameZones';
import type { EndgameMetricsTcCard, PerTcBucketStats, RatingAnchorOut } from '@/types/endgames';
import type { MaterialBucket } from '@/generated/endgameZones';

import { PercentileChip } from './PercentileChip';
import { ScoreGapRow } from './EndgameOverallScoreGapRow';
import { deriveLevel } from './EndgameOverallShared';

// Human-readable time-control labels.
const TC_LABELS: Record<'bullet' | 'blitz' | 'rapid' | 'classical', string> = {
  bullet: 'Bullet',
  blitz: 'Blitz',
  rapid: 'Rapid',
  classical: 'Classical',
};

// Bucket-specific popover copy. Baseline = what a strong (2300+) player would
// score from the same positions (Lichess expected-score formula).
// Recovery uses opponent-first framing per todo 2026-05-17-recovery-score-gap-popover-copy.md:
// positive gaps are driven by opponents failing to convert, not by user skill.
const POPOVER_COPY: Record<MaterialBucket, string> = {
  conversion:
    'How your score from winning endgames compares to what a strong (2300+) player would score from the same positions, according to the Lichess expected-score formula. A negative average gap is normal for most players: converting a won endgame is a technique that keeps improving with rating, so the gap is widest below master level and narrows toward zero near 2300+. The blue zone marks the range that is typical for winning endgames.',
  parity:
    'How your score from balanced endgames compares to what a strong (2300+) player would score from the same positions, according to the Lichess expected-score formula. The blue zone marks the range that is typical for balanced endgames.',
  recovery:
    'Per-span Score Gap on endgame spans you entered behind by >= 1 pawn. Above baseline = opponents failed to convert their winning positions more often than Stockfish predicted. Not a pure skill signal, you cannot outplay an engine from a lost position on your own. The blue zone marks the range that is typical for losing endgames.',
};

// Popover content per bucket (title InfoPopover next to each block heading).
const TITLE_TOOLTIP: Record<MaterialBucket, string> = {
  conversion: 'Endgames where you were up material (Stockfish eval >= +1.0 at entry). Win rate = percentage of these endgames you won.',
  parity: 'Endgames where the position was balanced (Stockfish eval between -1.0 and +1.0 at entry). Score = (wins + 0.5 * draws) / games.',
  recovery: 'Endgames where you were down material (Stockfish eval <= -1.0 at entry). Save rate = percentage you drew or won from a losing position.',
};

// ── Sub-component: one metric block (Conversion / Parity / Recovery) ────────

interface MetricBlockProps {
  bucket: MaterialBucket;
  block: PerTcBucketStats;
  tc: 'bullet' | 'blitz' | 'rapid' | 'classical';
  gaugeZones: ReturnType<typeof colorizeGaugeZones>;
  neutralMin: number;
  neutralMax: number;
  displayShift: number;
  /** Cohort rating anchor for this TC, named in the percentile chip tooltip.
   *  When undefined the chip is suppressed (see file header). */
  anchorRating: number | undefined;
}

function MetricBlock({
  bucket,
  block,
  tc,
  gaugeZones,
  neutralMin,
  neutralMax,
  displayShift,
  anchorRating,
}: MetricBlockProps) {
  const userR =
    bucket === 'conversion'
      ? block.win_pct / 100
      : bucket === 'recovery'
        ? (block.win_pct + block.draw_pct) / 100
        : (block.rate ?? 0);
  const hasGames = block.games > 0;

  const gapN = block.score_gap_n ?? 0;
  const showGapRow = gapN > 0;
  const gapMean = block.score_gap_mean;

  const displayedValue = (gapMean ?? 0) + displayShift;
  const displayedNeutralMin = neutralMin + displayShift;
  const displayedNeutralMax = neutralMax + displayShift;
  const gapFormatted =
    gapMean != null
      ? (displayedValue >= 0 ? '+' : '') + `${Math.round(displayedValue * 100)}%`
      : '—';

  // Zone tinting uses RAW values (D-04 carve-out) so the displayed bullet
  // and the LLM zone semantics reason about the same raw Conv ΔES space.
  const gapColor: string | undefined =
    gapMean != null
      ? gapMean < neutralMin
        ? ZONE_DANGER
        : gapMean >= neutralMax
          ? ZONE_SUCCESS
          : undefined
      : undefined;
  const gapLevel = deriveLevel(block.score_gap_p_value ?? null, gapN);
  const testId = `metrics-tc-${tc}-${bucket}`;

  return (
    <div className="flex-1 min-w-0" data-testid={testId}>
      <h4 className="text-base font-semibold mb-2 inline-flex items-center gap-1">
        {BUCKET_DISPLAY_LABELS[bucket]}
        <InfoPopover
          ariaLabel={`${BUCKET_DISPLAY_LABELS[bucket]} info`}
          testId={`${testId}-title-info`}
          side="top"
        >
          {TITLE_TOOLTIP[bucket]}
        </InfoPopover>
      </h4>
      <div className="flex flex-col gap-4">
        {/* Gauge row -- opacity-50 when no games (mirrors EndgameMetricCard). */}
        <div className={`flex justify-center${hasGames ? '' : ' opacity-50'}`}>
          <EndgameGauge
            value={userR * 100}
            label={BUCKET_DISPLAY_LABELS[bucket]}
            zones={gaugeZones}
          />
        </div>

        {hasGames ? (
          <>
            {/* WDL bar row -- game count restored above the bar, per TC + metric. */}
            <div className="flex flex-col gap-2">
              <span className="flex items-center gap-2 text-sm tabular-nums w-full">
                <span className="text-muted-foreground">Win/Draw/Loss</span>
                <span
                  className="ml-auto text-muted-foreground"
                  data-testid={`${testId}-games-count`}
                >
                  {block.games.toLocaleString()} games
                </span>
              </span>
              <div className="min-w-0">
                <MiniWDLBar
                  win_pct={block.win_pct}
                  draw_pct={block.draw_pct}
                  loss_pct={block.loss_pct}
                />
              </div>
            </div>

            {/* Delta-ES Score Gap bullet -- gated on gapN > 0 */}
            {showGapRow && (
              <div data-testid={`${testId}-score-gap-bullet`}>
                <ScoreGapRow
                  label={
                    <span className="inline-flex items-center gap-1">
                      <Cpu className="h-3.5 w-3.5" aria-hidden="true" />
                      {`${BUCKET_DISPLAY_LABELS[bucket]} Score Gap:`}
                    </span>
                  }
                  value={displayedValue}
                  formatted={gapFormatted}
                  resultColor={gapColor}
                  valueTestId={`${testId}-score-gap-value`}
                  ariaLabel={`${BUCKET_DISPLAY_LABELS[bucket]} Score Gap: ${gapFormatted}`}
                  neutralMin={displayedNeutralMin}
                  neutralMax={displayedNeutralMax}
                  ciLow={block.score_gap_ci_low != null ? block.score_gap_ci_low + displayShift : undefined}
                  ciHigh={block.score_gap_ci_high != null ? block.score_gap_ci_high + displayShift : undefined}
                  chipSlot={
                    block.percentile != null && anchorRating != null ? (
                      <PercentileChip
                        percentile={block.percentile}
                        flavor={
                          bucket === 'conversion'
                            ? 'conversion'
                            : bucket === 'parity'
                              ? 'parity'
                              : 'recovery'
                        }
                        tc={tc}
                        anchorRating={anchorRating}
                        metricLabel={`${BUCKET_DISPLAY_LABELS[bucket]} Score Gap`}
                        testId={`${testId}-percentile-chip`}
                        nGames={block.percentile_n_games}
                        value={block.percentile_value}
                      />
                    ) : undefined
                  }
                  tooltip={
                    <MetricStatPopover
                      name={`${BUCKET_DISPLAY_LABELS[bucket]} Score Gap`}
                      explanation={POPOVER_COPY[bucket]}
                      value={displayedValue}
                      baseline={displayShift}
                      unit="percent"
                      gameCount={gapN}
                      level={gapLevel}
                      pValue={block.score_gap_p_value}
                      vocabulary="score"
                      neutralLower={displayedNeutralMin}
                      neutralUpper={displayedNeutralMax}
                      baselineLabel="0%"
                      methodology={
                        <>
                          Score Gap: Difference between Endgame Sequence start and end score, based on Stockfish evaluations converted to expected score.<br />
                          Test: paired one-sample z-test on per-span Delta-ES values vs 0.<br />
                          Confidence interval: 95% normal-approx on the paired diffs.
                        </>
                      }
                      testId={`${testId}-score-gap-info`}
                      ariaLabel={`What is ${BUCKET_DISPLAY_LABELS[bucket]} Score Gap?`}
                    />
                  }
                />
              </div>
            )}
          </>
        ) : (
          <p className="text-sm text-muted-foreground py-4">Not enough data yet</p>
        )}
      </div>
    </div>
  );
}

// ── Main card component ───────────────────────────────────────────────────────

interface EndgameMetricsByTcCardProps {
  card: EndgameMetricsTcCard;
  /** Per-TC cohort rating anchor (from EndgameOverviewResponse.rating_anchors).
   *  Threaded into each block's percentile chip tooltip. Undefined when this TC
   *  has no anchor — the chips then self-suppress. */
  ratingAnchor?: RatingAnchorOut;
}

export function EndgameMetricsByTcCard({ card, ratingAnchor }: EndgameMetricsByTcCardProps) {
  // Narrow TC_METRIC_BANDS[card.tc] — noUncheckedIndexedAccess requires explicit
  // narrowing since Record keys may return undefined for unknown values. card.tc
  // is the four-member literal union so the lookup is always defined, but we
  // narrow defensively to satisfy TS strict mode (Pitfall 5).
  const bands = useMemo(() => TC_METRIC_BANDS[card.tc], [card.tc]);

  const convGaugeZones = useMemo(
    () =>
      colorizeGaugeZones([
        { from: 0, to: bands.convRate[0] },
        { from: bands.convRate[0], to: bands.convRate[1] },
        { from: bands.convRate[1], to: 1.0 },
      ]),
    [bands],
  );

  const recovGaugeZones = useMemo(
    () =>
      colorizeGaugeZones([
        { from: 0, to: bands.recovRate[0] },
        { from: bands.recovRate[0], to: bands.recovRate[1] },
        { from: bands.recovRate[1], to: 1.0 },
      ]),
    [bands],
  );

  // Per-TC parity gauge zones (user request 2026-05-29): each TC's actual
  // §3.2.1 parity IQR. The parity ΔES-gap band below stays global.
  const parityGaugeZones = useMemo(
    () =>
      colorizeGaugeZones([
        { from: 0, to: bands.parityRate[0] },
        { from: bands.parityRate[0], to: bands.parityRate[1] },
        { from: bands.parityRate[1], to: 1.0 },
      ]),
    [bands],
  );

  // TC-specific display shifts: recenters the bullet on visual zero.
  // Shift = -(lower + upper) / 2 for conv/recov; 0 for parity (global symmetric band).
  const convShift = -(bands.convScoreGap[0] + bands.convScoreGap[1]) / 2;
  const recovShift = -(bands.recovScoreGap[0] + bands.recovScoreGap[1]) / 2;
  const parityShift = 0;

  const anchorRating = ratingAnchor?.anchor_rating;

  // Divider between metric blocks: a vertical rule when the blocks sit
  // side-by-side (lg+), a horizontal rule when they stack (< lg). Mirrors the
  // EndgameOverallPerformanceSection two-column card. The flex parent's default
  // align-items: stretch gives the vertical rule full column height. The lg
  // breakpoint (was xl) keeps the three metrics on one row down to tablet width.
  const divider = (
    <>
      <div className="hidden lg:block w-px bg-border/40 mx-6" aria-hidden="true" />
      <div className="block lg:hidden border-t border-border/40 my-4" aria-hidden="true" />
    </>
  );

  return (
    <div
      className="charcoal-texture rounded-md w-full overflow-hidden"
      data-testid={`metrics-tc-card-${card.tc}`}
    >
      {/* Card header section: distinct recessed background + bottom separator,
          full-bleed to the card edges (outer has no padding; header pads itself). */}
      <div
        className="flex items-center gap-2 px-4 py-3 bg-black/20 border-b border-border/40"
        data-testid={`metrics-tc-card-${card.tc}-header`}
      >
        <TimeControlIcon
          timeControl={card.tc}
          className="h-4 w-4"
        />
        <h3 className="text-base font-semibold">{TC_LABELS[card.tc]}</h3>
        <span className="text-sm text-muted-foreground ml-auto">
          {card.total.toLocaleString()} games
        </span>
      </div>

      {/* Body: Conversion / Parity / Recovery trifecta (D-03) — three columns
          split by vertical dividers on desktop (lg+), stacked with horizontal
          dividers below lg. Single charcoal container shared by all three. */}
      <div className="flex flex-col lg:flex-row p-4">
        <MetricBlock
          bucket="conversion"
          block={card.conversion}
          tc={card.tc}
          gaugeZones={convGaugeZones}
          neutralMin={bands.convScoreGap[0]}
          neutralMax={bands.convScoreGap[1]}
          displayShift={convShift}
          anchorRating={anchorRating}
        />
        {divider}
        <MetricBlock
          bucket="parity"
          block={card.parity}
          tc={card.tc}
          gaugeZones={parityGaugeZones}
          neutralMin={SCORE_GAP_PARITY_NEUTRAL_MIN}
          neutralMax={SCORE_GAP_PARITY_NEUTRAL_MAX}
          displayShift={parityShift}
          anchorRating={anchorRating}
        />
        {divider}
        <MetricBlock
          bucket="recovery"
          block={card.recovery}
          tc={card.tc}
          gaugeZones={recovGaugeZones}
          neutralMin={bands.recovScoreGap[0]}
          neutralMax={bands.recovScoreGap[1]}
          displayShift={recovShift}
          anchorRating={anchorRating}
        />
      </div>
    </div>
  );
}
