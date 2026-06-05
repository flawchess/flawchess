/**
 * Phase 88.3 SC-3 — "Endgame Overall Performance" two-card responsive layout.
 * Replaces the Phase 85 3-column grid + ConnectorArrows arrow-flow layout.
 *
 * Layout: two separate charcoal-texture cards, equal height on desktop
 * (grid stretch), stacked on mobile. Within each card the two sections are
 * delimited by their own card headers (the sub-component <h3>s), not by
 * horizontal dividers.
 *   Card 1: "Games without Endgame" / "Games with Endgame"
 *   Card 2: "Eval at Endgame Entry" / "Endgame Score Differences"
 *
 * Cards live in sibling files (EndgameOverallCard, EndgameOverallEntryCard,
 * EndgameOverallScoreGapRow). This file is the orchestrator: it derives
 * per-card score / sig values and renders the grid.
 *
 * v1.17 single-bullet doctrine: per-card score bullet anchored at 0.50.
 * Per-card sig-gating triple (n >= MIN_GAMES_FOR_RELIABLE_STATS AND
 * isConfident(level) AND outside neutral band) gates only the score font color.
 * Score Gap font color is zone-only (no sig test) per D-04.
 */

import { Cpu } from 'lucide-react';

import { MetricStatPopover } from '@/components/popovers/MetricStatPopover';
import { useEvalCoverage } from '@/hooks/useEvalCoverage';
import {
  ACHIEVABLE_SCORE_GAP_NEUTRAL_MAX,
  ACHIEVABLE_SCORE_GAP_NEUTRAL_MIN,
  SCORE_GAP_NEUTRAL_MAX,
  SCORE_GAP_NEUTRAL_MIN,
} from '@/generated/endgameZones';
import { ZONE_DANGER, ZONE_SUCCESS } from '@/lib/theme';
import type {
  EndgamePerformanceResponse,
  ScoreGapMaterialResponse,
} from '@/types/endgames';

import { EndgameCard } from './EndgameOverallCard';
import { EntryCard } from './EndgameOverallEntryCard';
import { ScoreGapRow } from './EndgameOverallScoreGapRow';
import { deriveLevel } from './EndgameOverallShared';
import { PercentileChip } from './PercentileChip';

// 260514: Achievable (±5pp) and Endgame (±10pp) Score Gaps now use distinct
// bands — see reports/benchmarks-latest.md §3.1.5. Helper is parameterized
// so both call sites share the zone logic but pass their own band.
// Score-gap numbers are tinted red or green only — the neutral band uses the
// default foreground color to reduce visual noise and keep attention on the
// outliers.
function gapZoneColor(value: number, neutralMin: number, neutralMax: number): string | undefined {
  if (value < neutralMin) return ZONE_DANGER;
  if (value >= neutralMax) return ZONE_SUCCESS;
  return undefined;
}

export function EndgameOverallPerformanceSection({
  data,
  scoreGap,
}: {
  data: EndgamePerformanceResponse;
  scoreGap: ScoreGapMaterialResponse;
}) {
  const { isPending, pendingCount } = useEvalCoverage();

  const gapPositive = scoreGap.score_difference >= 0;
  const gapFormatted =
    (gapPositive ? '+' : '') + `${Math.round(scoreGap.score_difference * 100)}%`;

  // Share of total games per card (Card 1 = without endgame, Card 3 = with endgame).
  const totalGames = data.non_endgame_wdl.total + data.endgame_wdl.total;
  const withoutShare = totalGames > 0 ? data.non_endgame_wdl.total / totalGames : 0;
  const withShare = totalGames > 0 ? data.endgame_wdl.total / totalGames : 0;

  const gapColor = gapZoneColor(
    scoreGap.score_difference,
    SCORE_GAP_NEUTRAL_MIN,
    SCORE_GAP_NEUTRAL_MAX,
  );

  // Eval Score Gap (UI label; server field stays achievable_score_gap): how much
  // the actual Endgame Score fell short of (or exceeded) the Entry Eval Score
  // expected from the entry eval. achievable_score_gap is computed server-side
  // per SEC1-10 (paired z-test on per-game actual - expected pairs). Phase 85.1
  // Plan 03 retired the previous frontend derivation `withScore - entry_expected_score`.
  const achievableGapValue = data.achievable_score_gap;
  const achievableGapPositive = achievableGapValue >= 0;
  const achievableGapFormatted =
    (achievableGapPositive ? '+' : '') + `${Math.round(achievableGapValue * 100)}%`;
  const achievableGapColor = gapZoneColor(
    achievableGapValue,
    ACHIEVABLE_SCORE_GAP_NEUTRAL_MIN,
    ACHIEVABLE_SCORE_GAP_NEUTRAL_MAX,
  );

  // Sample sizes for the two paired/two-sample tests powering the gap popovers.
  // Eval Score Gap: paired-diff over endgame games with non-null entry
  // eval (d_n == entry_expected_score_n by construction, see endgame_service.py).
  // Endgame Score Gap: two-sample over both cohorts combined.
  const achievableGapN = data.entry_expected_score_n;
  const endgameGapN = data.endgame_wdl.total + data.non_endgame_wdl.total;

  const achievableGapLevel = deriveLevel(
    data.achievable_score_gap_p_value,
    achievableGapN,
  );
  const endgameGapLevel = deriveLevel(
    scoreGap.score_difference_p_value,
    endgameGapN,
  );

  return (
    <section data-testid="endgame-overall-performance-section">
      <p className="text-sm text-muted-foreground">
        Do you perform better or worse when games reach an endgame?
      </p>

      {/* Two separate charcoal cards, equal height on desktop (grid stretch),
          stacked on mobile. Each stacked sub-section carries a full-bleed card
          header bar (bg-black/20 border-b, matching the Time Pressure cards);
          `divide-y` draws the rule between the two stacked sub-sections. */}
      <div className="grid grid-cols-1 md:grid-cols-2 items-stretch gap-4 mt-2">

        {/* Card 1: Games without Endgame + Games with Endgame */}
        <div className="charcoal-texture rounded-md overflow-hidden h-full flex flex-col divide-y divide-border/40">
          <EndgameCard
            title="Games without Endgame"
            scoreLabel="Non-Endgame Score:"
            tileTestId="tile-games-without-endgame"
            scoreValueTestId="score-value-no"
            scorePopoverTestId="score-info-no"
            popoverAriaLabel="Games without Endgame Score info"
            gamesCountTestId="games-count-no"
            wdl={data.non_endgame_wdl}
            pValue={data.non_endgame_score_p_value}
            gamesShare={withoutShare}
            popoverName="Non-Endgame Score"
            popoverExplanation="Your win rate (with draws counted as half) across games that ended before reaching an endgame."
          />
          <EndgameCard
            title="Games with Endgame"
            scoreLabel="Endgame Score:"
            tileTestId="tile-games-with-endgame"
            scoreValueTestId="score-value-yes"
            scorePopoverTestId="score-info-yes"
            popoverAriaLabel="Games with Endgame Score info"
            gamesCountTestId="games-count-yes"
            wdl={data.endgame_wdl}
            pValue={data.endgame_score_p_value}
            gamesShare={withShare}
            popoverName="Endgame Score"
            popoverExplanation="Your win rate (with draws counted as half) across games that reached an endgame."
          />
        </div>

        {/* Card 2: Eval at Endgame Entry + Endgame Score Differences */}
        <div className="charcoal-texture rounded-md overflow-hidden h-full flex flex-col divide-y divide-border/40">
          <EntryCard data={data} />
          <div data-testid="endgame-score-differences">
            {/* Full-bleed card header bar (matches the Time Pressure cards). */}
            <h3 className="flex items-center gap-2 px-4 py-3 bg-black/20 border-b border-border/40 text-base font-semibold">
              Endgame Score Differences
            </h3>
            <div className="flex flex-col gap-4 p-4">
              <ScoreGapRow
                label={
                  <span className="inline-flex items-center gap-1">
                    <Cpu className="h-3.5 w-3.5" aria-hidden="true" />
                    Eval Score Gap:
                  </span>
                }
                value={achievableGapValue}
                formatted={achievableGapFormatted}
                resultColor={achievableGapColor}
                valueTestId="achievable-score-gap-value"
                ariaLabel={`Eval Score Gap: ${achievableGapFormatted}`}
                neutralMin={ACHIEVABLE_SCORE_GAP_NEUTRAL_MIN}
                neutralMax={ACHIEVABLE_SCORE_GAP_NEUTRAL_MAX}
                ciLow={data.achievable_score_gap_ci_low ?? undefined}
                ciHigh={data.achievable_score_gap_ci_high ?? undefined}
                chipSlot={
                  data.achievable_score_gap_percentile != null ? (
                    <PercentileChip
                      percentile={data.achievable_score_gap_percentile}
                      flavor="achievable"
                      metricLabel="Eval Score Gap"
                      testId="achievable-score-gap-percentile-chip"
                      perTcBreakdown={data.achievable_score_gap_per_tc}
                    />
                  ) : undefined
                }
                tooltip={
                  <MetricStatPopover
                    name="Eval Score Gap"
                    explanation="Your average per-game Endgame Score minus your Entry Eval Score (what a 2300+ rated rapid player would expect to score from your endgame-entry positions). Positive means you outperformed that expectation; negative means you underperformed."
                    value={achievableGapValue}
                    baseline={0}
                    unit="percent"
                    gameCount={achievableGapN}
                    level={achievableGapLevel}
                    pValue={data.achievable_score_gap_p_value}
                    vocabulary="score"
                    neutralLower={ACHIEVABLE_SCORE_GAP_NEUTRAL_MIN}
                    neutralUpper={ACHIEVABLE_SCORE_GAP_NEUTRAL_MAX}
                    baselineLabel="0%"
                    methodology={
                      <>
                        Score: wins + ½ draws.<br />
                        Test: paired one-sample z-test on per-game (actual − expected) diffs vs 0.<br />
                        Confidence interval: 95% normal-approx on the paired diffs.
                      </>
                    }
                    testId="achievable-score-gap-info"
                    ariaLabel="What is Eval Score Gap?"
                    isPending={isPending}
                    pendingCount={pendingCount}
                  />
                }
              />
              <ScoreGapRow
                label="Endgame Score Gap:"
                value={scoreGap.score_difference}
                formatted={gapFormatted}
                resultColor={gapColor}
                valueTestId="endgame-score-gap-value"
                ariaLabel={`Endgame Score Gap: ${gapFormatted}`}
                neutralMin={SCORE_GAP_NEUTRAL_MIN}
                neutralMax={SCORE_GAP_NEUTRAL_MAX}
                valueClassName="text-lg"
                ciLow={scoreGap.score_difference_ci_low ?? undefined}
                ciHigh={scoreGap.score_difference_ci_high ?? undefined}
                chipSlot={
                  scoreGap.score_gap_percentile != null ? (
                    <PercentileChip
                      percentile={scoreGap.score_gap_percentile}
                      flavor="score-gap"
                      metricLabel="Endgame Score Gap"
                      testId="endgame-score-gap-percentile-chip"
                      perTcBreakdown={scoreGap.score_gap_per_tc}
                    />
                  ) : undefined
                }
                tooltip={
                  <MetricStatPopover
                    name="Endgame Score Gap"
                    explanation="Score difference between games that reach an endgame and games that end before. Positive means endgames are your strength; negative means you perform worse once games reach an endgame."
                    value={scoreGap.score_difference}
                    baseline={0}
                    unit="percent"
                    gameCount={endgameGapN}
                    level={endgameGapLevel}
                    pValue={scoreGap.score_difference_p_value}
                    vocabulary="score"
                    neutralLower={SCORE_GAP_NEUTRAL_MIN}
                    neutralUpper={SCORE_GAP_NEUTRAL_MAX}
                    baselineLabel="0%"
                    relative
                    methodology={
                      <>
                        Score: wins + ½ draws.<br />
                        Test: two-sample z-test on (Endgame Score − Non-Endgame Score) vs 0.<br />
                        Confidence interval: 95% normal-approx on the score difference.
                      </>
                    }
                    testId="endgame-score-gap-info"
                    ariaLabel="What is Endgame Score Gap?"
                    isPending={isPending}
                    pendingCount={pendingCount}
                  />
                }
              />
            </div>
          </div>
        </div>

      </div>
    </section>
  );
}
