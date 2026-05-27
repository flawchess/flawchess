/**
 * Phase 86 — Shared shell for the Conversion / Parity / Recovery cards of the
 * "Endgame Metrics" 4-card layout. Renders gauge -> games-count row -> WDL bar ->
 * per-bucket eval-based Delta-ES Score Gap bullet (ScoreGapRow).
 *
 * Phase 87.2 refactor: replaced the rate-based peer-bullet row (You / Opp / Gap
 * text + MiniBulletChart vs mirror-bucket opponent) with a per-bucket ScoreGapRow
 * anchored on the Stockfish baseline (vs 0). The mirror-bucket `mirror` prop and
 * all D-03 lib symbols are deleted. Per D-08: no "vs opponents" framing anywhere.
 * Zone-only tint on the ScoreGapRow value (Phase 85.1 D-04 inherited).
 */

import { useMemo } from 'react';
import type { ReactNode } from 'react';

import { Cpu, Swords } from 'lucide-react';

import { EndgameGauge } from '@/components/charts/EndgameGauge';
import { MetricStatPopover } from '@/components/popovers/MetricStatPopover';
import { useEvalCoverage } from '@/hooks/useEvalCoverage';
import { MiniWDLBar } from '@/components/stats/MiniWDLBar';
import { InfoPopover } from '@/components/ui/info-popover';
import { pickDominantTcAnchor, type RatingAnchorsByTc } from '@/lib/percentileAnchor';
import { ZONE_DANGER, ZONE_SUCCESS } from '@/lib/theme';
import {
  BUCKET_DISPLAY_LABELS,
  BUCKET_DISPLAY_LABELS_WITH_METRIC,
  FIXED_GAUGE_ZONES,
  SCORE_GAP_BUCKET_DISPLAY_SHIFT,
} from '@/lib/endgameMetrics';
// Per-bucket neutral bands for the Section 2 Delta-ES Score Gap bullet (D-02 / Plan 01).
import {
  SCORE_GAP_CONV_NEUTRAL_MIN,
  SCORE_GAP_CONV_NEUTRAL_MAX,
  SCORE_GAP_PARITY_NEUTRAL_MIN,
  SCORE_GAP_PARITY_NEUTRAL_MAX,
  SCORE_GAP_RECOV_NEUTRAL_MIN,
  SCORE_GAP_RECOV_NEUTRAL_MAX,
} from '@/generated/endgameZones';
import type { MaterialBucket, MaterialRow, PerTcBreakdownOut } from '@/types/endgames';

import { PercentileChip } from './PercentileChip';
import { ScoreGapRow } from './EndgameOverallScoreGapRow';
import { deriveLevel } from './EndgameOverallShared';

// Bucket-specific popover copy. Baseline = what a strong (2300+) player would
// score from the same positions (Lichess expected-score formula). The typical
// range is the blue zone, calibrated per bucket. Conversion / recovery each
// carry a benchmark-grounded counter-intuitive note (benchmarks-latest.md
// §3.2.2/§3.2.3): conversion gap is normally negative and a rating-driven
// technique effect; recovery is normally positive because weaker opponents
// blunder away winning positions. Parity is symmetric, no note needed.
const POPOVER_COPY: Record<MaterialBucket, string> = {
  conversion:
    'How your score from winning endgames compares to what a strong (2300+) player would score from the same positions, according to the Lichess expected-score formula. A negative average gap is normal for most players: converting a won endgame is a technique that keeps improving with rating, so the gap is widest below master level and narrows toward zero near 2300+. The blue zone marks the range that is typical for winning endgames.',
  parity:
    'How your score from balanced endgames compares to what a strong (2300+) player would score from the same positions, according to the Lichess expected-score formula. The blue zone marks the range that is typical for balanced endgames.',
  recovery:
    'How your score from losing endgames compares to what a strong (2300+) player would score from the same positions, according to the Lichess expected-score formula. Counter-intuitively, lower-rated players tend to beat this predicted score by more, not from greater skill but because their weaker opponents are likelier to blunder away a winning position. The blue zone marks the range that is typical for losing endgames.',
};

interface EndgameMetricCardProps {
  bucket: MaterialBucket;
  row: MaterialRow;
  /** Share of total material games this bucket occupies, as a percent 0-100
   * (e.g. 45.5 for 45.5%). Computed by the caller from `row.games / totalGames`. */
  sharePct: number;
  /** Phase 87.2: 5 eval-baseline Delta-ES Score Gap fields from
   * ScoreGapMaterialResponse.score_gap_{conv,parity,recov}_*. */
  scoreGapMean: number | null;
  scoreGapN: number | null;
  scoreGapPValue: number | null;
  scoreGapCiLow: number | null;
  scoreGapCiHigh: number | null;
  /** Phase 94 (PCTL-03/04) + Phase 94.4 D-05a: cohort percentile [0,100]
   *  sourced from ScoreGapMaterialResponse.score_gap_{conv,parity}_percentile
   *  for conversion/parity, and `recovery_score_gap_percentile` (CdfMetricId-mirror
   *  rescue field) for recovery. Pre-94.4 the recovery slot was hard-suppressed —
   *  D-05a rescues it under the peer-relative cohort framing (same-rated
   *  comparison normalises the opponent-rating confound). */
  scoreGapPercentile: number | null;
  /** Quick task 260527-q0b: per-TC breakdown for the percentile chip's
   *  tooltip bullet 2. Optional so legacy callers / older fixtures keep
   *  rendering without per-TC data. */
  scoreGapPerTc?: PerTcBreakdownOut[];
  /** Phase 94.4 Plan 07: per-TC rating anchors (whole map). The card picks
   *  the dominant-TC anchor for the chip's 4th-bullet disclosure. Aggregated
   *  page-level chips omit the `tc` prop on PercentileChip — bullet 1 frames
   *  them as multi-TC. Optional so legacy fixtures still render the card body. */
  ratingAnchors?: RatingAnchorsByTc;
  /** Container data-testid (e.g. "tile-conversion"). Sub-element testids derive
   * from this: `${tileTestId}-score-gap-bullet`, `${tileTestId}-score-gap-value`,
   * `${tileTestId}-score-gap-info`. */
  tileTestId: string;
  /** Content rendered inside the InfoPopover next to the card's h3 title. */
  titleTooltip: ReactNode;
}

export function EndgameMetricCard({
  bucket,
  row,
  sharePct,
  scoreGapMean,
  scoreGapN,
  scoreGapPValue,
  scoreGapCiLow,
  scoreGapCiHigh,
  scoreGapPercentile,
  scoreGapPerTc,
  ratingAnchors,
  tileTestId,
  titleTooltip,
}: EndgameMetricCardProps) {
  const { isPending, pendingCount } = useEvalCoverage();
  // Phase 94.4 Plan 07: aggregated chip uses the dominant-TC anchor for the
  // popover's 4th bullet. When no anchors are available, the chip suppresses
  // entirely (`pickDominantTcAnchor` returns undefined → conditional below
  // resolves to undefined chipSlot).
  const dominantAnchor = pickDominantTcAnchor(ratingAnchors ?? {});

  const userR = bucket === 'conversion'
    ? row.win_pct / 100
    : bucket === 'recovery'
      ? (row.win_pct + row.draw_pct) / 100
      : row.score;
  const hasGames = row.games > 0;

  // Phase 87.2: per-bucket Delta-ES Score Gap derivation.
  // Zone-only tint (Phase 85.1 D-04): no sig-gate on the row font color.
  const gapMean = scoreGapMean;
  const gapN = scoreGapN ?? 0;
  const showGapRow = gapN > 0;

  const { neutralMin, neutralMax } = useMemo(
    () => ({
      neutralMin:
        bucket === 'conversion'
          ? SCORE_GAP_CONV_NEUTRAL_MIN
          : bucket === 'parity'
            ? SCORE_GAP_PARITY_NEUTRAL_MIN
            : SCORE_GAP_RECOV_NEUTRAL_MIN,
      neutralMax:
        bucket === 'conversion'
          ? SCORE_GAP_CONV_NEUTRAL_MAX
          : bucket === 'parity'
            ? SCORE_GAP_PARITY_NEUTRAL_MAX
            : SCORE_GAP_RECOV_NEUTRAL_MAX,
    }),
    [bucket],
  );

  // Phase 87.4 D-03/D-04: presentation-layer affine that recenters Conv/Recov
  // bullets on a single visual zero. Conv shifts by -0.055, Parity by 0,
  // Recov by +0.06 (each = midpoint of the metric's calibrated band). The
  // displayed value, neutral-band edges, and formatted text are all shifted;
  // gapColor below stays on RAW values so zone tinting is unaffected.
  const displayShift = SCORE_GAP_BUCKET_DISPLAY_SHIFT[bucket];
  const displayedValue = (gapMean ?? 0) + displayShift;
  const displayedNeutralMin = neutralMin + displayShift;
  const displayedNeutralMax = neutralMax + displayShift;
  const gapFormatted =
    gapMean != null
      ? (displayedValue >= 0 ? '+' : '') + `${Math.round(displayedValue * 100)}%`
      : '—';

  // Phase 87.4 D-04: zone color uses raw values; only the rendered value + band
  // are shifted. Without this carve-out the bullet would tint differently from
  // the LLM zone semantics (which still reason about raw Conv ΔES space).
  const gapColor: string | undefined =
    gapMean != null
      ? gapMean < neutralMin
        ? ZONE_DANGER
        : gapMean >= neutralMax
          ? ZONE_SUCCESS
          : undefined
      : undefined;
  const gapLevel = deriveLevel(scoreGapPValue ?? null, gapN);

  const sharePctFormatted = Math.round(sharePct);
  const gamesCountFormatted = row.games.toLocaleString();

  return (
    <div className="charcoal-texture rounded-md p-4" data-testid={tileTestId}>
      <h3 className="text-base font-semibold mb-2 inline-flex items-center gap-1">
        {BUCKET_DISPLAY_LABELS_WITH_METRIC[bucket]}
        <InfoPopover
          ariaLabel={`${BUCKET_DISPLAY_LABELS_WITH_METRIC[bucket]} info`}
          testId={`${tileTestId}-title-info`}
          side="top"
        >
          {titleTooltip}
        </InfoPopover>
      </h3>
      <div className="flex flex-col gap-4">
        {/* Gauge row -- opacity-50 when no games per D-17. */}
        <div className={`flex justify-center${hasGames ? '' : ' opacity-50'}`}>
          <EndgameGauge
            value={userR * 100}
            label={BUCKET_DISPLAY_LABELS[bucket]}
            zones={FIXED_GAUGE_ZONES[bucket]}
          />
        </div>

        {hasGames ? (
          <>
            {/* Games-count row -- mirrors EndgameOverallCard.tsx:88-100. */}
            <div className="flex flex-col gap-2">
              <span className="flex items-center gap-2 text-sm tabular-nums w-full">
                <span className="text-muted-foreground">Win/Draw/Loss</span>
                <span
                  className="ml-auto inline-flex items-center gap-1 text-sm text-muted-foreground tabular-nums whitespace-nowrap"
                  data-testid={`${tileTestId}-games-count`}
                >
                  <span>
                    Games: {sharePctFormatted}% ({gamesCountFormatted})
                  </span>
                  <Swords className="h-3.5 w-3.5" aria-hidden="true" />
                </span>
              </span>
              <div className="min-w-0">
                <MiniWDLBar
                  win_pct={row.win_pct}
                  draw_pct={row.draw_pct}
                  loss_pct={row.loss_pct}
                />
              </div>
            </div>

            {/* Phase 87.2: per-bucket Delta-ES Score Gap bullet (replaces peer-bullet row).
                Shows when gapN > 0; hidden when no span data yet. */}
            {showGapRow && (
              <div data-testid={`${tileTestId}-score-gap-bullet`}>
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
                  valueTestId={`${tileTestId}-score-gap-value`}
                  ariaLabel={`${BUCKET_DISPLAY_LABELS[bucket]} Score Gap: ${gapFormatted}`}
                  neutralMin={displayedNeutralMin}
                  neutralMax={displayedNeutralMax}
                  ciLow={scoreGapCiLow != null ? scoreGapCiLow + displayShift : undefined}
                  ciHigh={scoreGapCiHigh != null ? scoreGapCiHigh + displayShift : undefined}
                  chipSlot={
                    // Phase 94.4 D-05a: recovery rescued under peer-relative.
                    // All 3 buckets now render a chip when percentile + anchor
                    // are both present. Bucket-to-flavor map uses kebab-case
                    // matching the new flavor enum.
                    scoreGapPercentile != null && dominantAnchor !== undefined ? (
                      <PercentileChip
                        percentile={scoreGapPercentile}
                        flavor={
                          bucket === 'conversion'
                            ? 'conversion'
                            : bucket === 'parity'
                              ? 'parity'
                              : 'recovery'
                        }
                        anchorRating={dominantAnchor.anchor_rating}
                        nChesscomGames={dominantAnchor.n_chesscom_games}
                        nLichessGames={dominantAnchor.n_lichess_games}
                        chesscomMedianNative={dominantAnchor.chesscom_median_native ?? undefined}
                        lichessMedianNative={dominantAnchor.lichess_median_native ?? undefined}
                        metricLabel={`${BUCKET_DISPLAY_LABELS[bucket]} Score Gap`}
                        testId={`${tileTestId}-percentile-chip`}
                        perTcBreakdown={scoreGapPerTc}
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
                      pValue={scoreGapPValue}
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
                      testId={`${tileTestId}-score-gap-info`}
                      ariaLabel={`What is ${BUCKET_DISPLAY_LABELS[bucket]} Score Gap?`}
                      isPending={isPending}
                      pendingCount={pendingCount}
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
