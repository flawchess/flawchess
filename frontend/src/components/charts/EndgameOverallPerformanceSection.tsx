/**
 * Phase 88.3 SC-3 — "Endgame Overall Performance" 2-column responsive card.
 * Replaces the Phase 85 3-column grid + ConnectorArrows arrow-flow layout.
 *
 * Layout: single outer charcoal-texture card, two equal-height columns on
 * desktop (separated by a vertical divider), stacked on mobile (separated by
 * horizontal dividers).
 *   Column 1: "Games without Endgame" / "Games with Endgame"
 *   Column 2: "Eval at Endgame Entry" / "Endgame Score Differences"
 *
 * Both columns carry exactly 2 sections, guaranteeing equal height on desktop
 * by construction without CSS trickery.
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
import { pickDominantTcAnchor, type RatingAnchorsByTc } from '@/lib/percentileAnchor';
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
  ratingAnchors,
}: {
  data: EndgamePerformanceResponse;
  scoreGap: ScoreGapMaterialResponse;
  /** Phase 94.4 Plan 07: per-TC rating anchors from
   *  EndgameOverviewResponse.rating_anchors. The page-level ΔES chips on this
   *  section are aggregated across TCs, so they use the dominant-TC anchor
   *  (highest game count) for the popover's 4th-bullet disclosure. When no
   *  anchors are available (Stage A hasn't run / all TCs below the inclusion
   *  floor), all chips suppress. Optional so legacy fixtures still render. */
  ratingAnchors?: RatingAnchorsByTc;
}) {
  const { isPending, pendingCount } = useEvalCoverage();
  const dominantAnchor = pickDominantTcAnchor(ratingAnchors ?? {});

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

  // Achievable Score Gap: how much the actual endgame score fell short of (or
  // exceeded) the achievable score expected from the entry eval.
  // achievable_score_gap is computed server-side per SEC1-10 (paired z-test on
  // per-game actual - expected pairs). Phase 85.1 Plan 03 retired the previous
  // frontend derivation `withScore - entry_expected_score`.
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
  // Achievable Score Gap: paired-diff over endgame games with non-null entry
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

      {/* Single outer card with two equal-height columns on desktop, stacked on mobile. */}
      <div className="charcoal-texture rounded-md p-4 mt-2">
        <div className="flex flex-col lg:flex-row">

          {/* Column 1: Games without Endgame + Games with Endgame */}
          <div className="flex-1 flex flex-col gap-4">
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
            <div className="border-t border-border/40" aria-hidden="true" />
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

          {/* Desktop vertical divider / Mobile horizontal divider */}
          <div className="hidden lg:block w-px bg-border/40 mx-6" aria-hidden="true" />
          <div className="block lg:hidden border-t border-border/40 my-4" aria-hidden="true" />

          {/* Column 2: Eval at Endgame Entry + Endgame Score Differences */}
          <div className="flex-1 flex flex-col gap-4">
            <EntryCard data={data} />
            <div className="border-t border-border/40" aria-hidden="true" />
            <div data-testid="endgame-score-differences">
              <h3 className="text-base font-semibold mb-2">Endgame Score Differences</h3>
              <div className="flex flex-col gap-4">
                <ScoreGapRow
                  label={
                    <span className="inline-flex items-center gap-1">
                      <Cpu className="h-3.5 w-3.5" aria-hidden="true" />
                      Achievable Score Gap:
                    </span>
                  }
                  value={achievableGapValue}
                  formatted={achievableGapFormatted}
                  resultColor={achievableGapColor}
                  valueTestId="achievable-score-gap-value"
                  ariaLabel={`Achievable Score Gap: ${achievableGapFormatted}`}
                  neutralMin={ACHIEVABLE_SCORE_GAP_NEUTRAL_MIN}
                  neutralMax={ACHIEVABLE_SCORE_GAP_NEUTRAL_MAX}
                  ciLow={data.achievable_score_gap_ci_low ?? undefined}
                  ciHigh={data.achievable_score_gap_ci_high ?? undefined}
                  chipSlot={
                    data.achievable_score_gap_percentile != null &&
                    dominantAnchor !== undefined ? (
                      <PercentileChip
                        percentile={data.achievable_score_gap_percentile}
                        flavor="achievable"
                        anchorRating={dominantAnchor.anchor_rating}
                        anchorSource={dominantAnchor.source_platform}
                        chesscomRawRating={
                          dominantAnchor.chesscom_raw_rating ?? undefined
                        }
                        metricLabel="Achievable Score Gap"
                        metricValue={achievableGapFormatted}
                        testId="achievable-score-gap-percentile-chip"
                      />
                    ) : undefined
                  }
                  tooltip={
                    <MetricStatPopover
                      name="Achievable Score Gap"
                      explanation="Your average per-game endgame score minus the achievable score from each entry position. Positive means you outperformed the 2300+ baseline; negative means you underperformed."
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
                      ariaLabel="What is Achievable Score Gap?"
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
                    scoreGap.score_gap_percentile != null &&
                    dominantAnchor !== undefined ? (
                      <PercentileChip
                        percentile={scoreGap.score_gap_percentile}
                        flavor="score-gap"
                        anchorRating={dominantAnchor.anchor_rating}
                        anchorSource={dominantAnchor.source_platform}
                        chesscomRawRating={
                          dominantAnchor.chesscom_raw_rating ?? undefined
                        }
                        metricLabel="Endgame Score Gap"
                        metricValue={gapFormatted}
                        testId="endgame-score-gap-percentile-chip"
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
      </div>
    </section>
  );
}
