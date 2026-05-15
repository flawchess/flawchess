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
import { MiniWDLBar } from '@/components/stats/MiniWDLBar';
import { InfoPopover } from '@/components/ui/info-popover';
import { ZONE_DANGER, ZONE_SUCCESS } from '@/lib/theme';
import {
  BUCKET_DISPLAY_LABELS,
  BUCKET_DISPLAY_LABELS_WITH_METRIC,
  FIXED_GAUGE_ZONES,
} from '@/lib/endgameMetrics';
// Per-bucket neutral bands for the Section 2 Delta-ES Score Gap bullet (D-02 / Plan 01).
import {
  SECTION2_SCORE_GAP_CONV_NEUTRAL_MIN,
  SECTION2_SCORE_GAP_CONV_NEUTRAL_MAX,
  SECTION2_SCORE_GAP_PARITY_NEUTRAL_MIN,
  SECTION2_SCORE_GAP_PARITY_NEUTRAL_MAX,
  SECTION2_SCORE_GAP_RECOV_NEUTRAL_MIN,
  SECTION2_SCORE_GAP_RECOV_NEUTRAL_MAX,
} from '@/generated/endgameZones';
import type { MaterialBucket, MaterialRow } from '@/types/endgames';

import { ScoreGapRow } from './EndgameOverallScoreGapRow';
import { deriveLevel } from './EndgameOverallShared';

// Bucket-specific popover copy per D-08 with identical sigmoid-bias caveat.
// No "vs opponents" framing anywhere (D-08 rule: Stockfish-baseline anchor).
// No em-dashes per CLAUDE.md style guide.
const POPOVER_COPY: Record<MaterialBucket, string> = {
  conversion:
    'Average per-span Score Gap on endgame spans you entered ahead by >= 1 pawn. Positive = you converted advantages above the Stockfish baseline; negative = you bled away expected score on winning entries. Positive = above the Stockfish baseline; negative = below. Note: the Lichess expected-score sigmoid under-weights endgame eval; rely on the zone bands, not the raw magnitude.',
  parity:
    'Average per-span Score Gap on endgame spans you entered roughly balanced (eval within +/-1 pawn). Positive = you outperformed the baseline from balanced; negative = you underperformed. Positive = above the Stockfish baseline; negative = below. Note: the Lichess expected-score sigmoid under-weights endgame eval; rely on the zone bands, not the raw magnitude.',
  recovery:
    'Average per-span Score Gap on endgame spans you entered behind by >= 1 pawn. Positive = you salvaged disadvantages above the Stockfish baseline; negative = the position deteriorated further than expected. Positive = above the Stockfish baseline; negative = below. Note: the Lichess expected-score sigmoid under-weights endgame eval; rely on the zone bands, not the raw magnitude.',
};

interface EndgameMetricCardProps {
  bucket: MaterialBucket;
  row: MaterialRow;
  /** Share of total material games this bucket occupies, as a percent 0-100
   * (e.g. 45.5 for 45.5%). Computed by the caller from `row.games / totalGames`. */
  sharePct: number;
  /** Phase 87.2: 5 eval-baseline Delta-ES Score Gap fields from
   * ScoreGapMaterialResponse.section2_score_gap_{conv,parity,recov}_*. */
  scoreGapMean: number | null;
  scoreGapN: number | null;
  scoreGapPValue: number | null;
  scoreGapCiLow: number | null;
  scoreGapCiHigh: number | null;
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
  tileTestId,
  titleTooltip,
}: EndgameMetricCardProps) {
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
  const gapFormatted =
    gapMean != null
      ? (gapMean >= 0 ? '+' : '') + `${Math.round(gapMean * 100)}%`
      : '—';

  const { section2NeutralMin, section2NeutralMax } = useMemo(
    () => ({
      section2NeutralMin:
        bucket === 'conversion'
          ? SECTION2_SCORE_GAP_CONV_NEUTRAL_MIN
          : bucket === 'parity'
            ? SECTION2_SCORE_GAP_PARITY_NEUTRAL_MIN
            : SECTION2_SCORE_GAP_RECOV_NEUTRAL_MIN,
      section2NeutralMax:
        bucket === 'conversion'
          ? SECTION2_SCORE_GAP_CONV_NEUTRAL_MAX
          : bucket === 'parity'
            ? SECTION2_SCORE_GAP_PARITY_NEUTRAL_MAX
            : SECTION2_SCORE_GAP_RECOV_NEUTRAL_MAX,
    }),
    [bucket],
  );

  const gapColor: string | undefined =
    gapMean != null
      ? gapMean < section2NeutralMin
        ? ZONE_DANGER
        : gapMean >= section2NeutralMax
          ? ZONE_SUCCESS
          : undefined
      : undefined;
  const gapLevel = deriveLevel(scoreGapPValue ?? null, gapN);

  const sharePctFormatted = sharePct.toFixed(1);
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
                  value={gapMean ?? 0}
                  formatted={gapFormatted}
                  resultColor={gapColor}
                  valueTestId={`${tileTestId}-score-gap-value`}
                  ariaLabel={`${BUCKET_DISPLAY_LABELS[bucket]} Score Gap: ${gapFormatted}`}
                  neutralMin={section2NeutralMin}
                  neutralMax={section2NeutralMax}
                  ciLow={scoreGapCiLow ?? undefined}
                  ciHigh={scoreGapCiHigh ?? undefined}
                  tooltip={
                    <MetricStatPopover
                      name={`${BUCKET_DISPLAY_LABELS[bucket]} Score Gap`}
                      explanation={POPOVER_COPY[bucket]}
                      value={gapMean ?? 0}
                      baseline={0}
                      unit="percent"
                      gameCount={gapN}
                      level={gapLevel}
                      pValue={scoreGapPValue}
                      vocabulary="score"
                      neutralLower={section2NeutralMin}
                      neutralUpper={section2NeutralMax}
                      baselineLabel="0%"
                      methodology={
                        <>
                          Score: per-span exit score minus Stockfish expected score from span entry eval.<br />
                          Test: paired one-sample z-test on per-span Delta-ES values vs 0.<br />
                          Confidence interval: 95% normal-approx on the paired diffs.
                        </>
                      }
                      testId={`${tileTestId}-score-gap-info`}
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
