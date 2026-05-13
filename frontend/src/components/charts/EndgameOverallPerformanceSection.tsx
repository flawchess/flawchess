/**
 * Phase 85 redesign-in-place — "Endgame Overall Performance" 3-card composite
 * section. Replaces the legacy EndgameGamesWithWithoutSection (2-card + footer)
 * and absorbs Card 2 from the legacy EndgameStartVsEndSection ("Where you
 * start" tile). See 85-CONTEXT.md §"Redesign Decision (Post-Execution,
 * 2026-05-13)" for the rationale.
 *
 * Layout: 3-column card grid on lg+, stacked on mobile.
 *   Card 1 | Card 2 | Card 3
 *   "Games without Endgame" | "Eval at Endgame Entry" | "Games with Endgame"
 *
 * Endgame Score Gap sits in column 2 on desktop (via lg:col-start-2 on the
 * 4th grid child), naturally stacked at the bottom on mobile after Card 3.
 *
 * Cards live in sibling files (EndgameOverallCard, EndgameOverallEntryCard,
 * EndgameOverallScoreGapRow, EndgameOverallConnectorArrows). This file is the
 * orchestrator: it derives per-card score / sig values and renders the grid.
 *
 * v1.17 single-bullet doctrine: per-card score bullet anchored at 0.50.
 * Per-card sig-gating triple (n >= MIN_GAMES_FOR_RELIABLE_STATS AND
 * isConfident(level) AND outside neutral band) gates only the score font color.
 * Score Gap font color is zone-only (no sig test) per D-04.
 */

import { useRef } from 'react';

import { InfoPopover } from '@/components/ui/info-popover';
import {
  SCORE_GAP_NEUTRAL_MAX,
  SCORE_GAP_NEUTRAL_MIN,
} from '@/generated/endgameZones';
import { scoreZoneColor } from '@/lib/scoreBulletConfig';
import type { ConfidenceLevel } from '@/lib/scoreConfidence';
import { isConfident } from '@/lib/significance';
import { ZONE_DANGER, ZONE_NEUTRAL, ZONE_SUCCESS } from '@/lib/theme';
import type {
  EndgamePerformanceResponse,
  ScoreGapMaterialResponse,
} from '@/types/endgames';

import { EndgameCard } from './EndgameOverallCard';
import { ConnectorArrows } from './EndgameOverallConnectorArrows';
import { EntryCard } from './EndgameOverallEntryCard';
import { ScoreGapRow } from './EndgameOverallScoreGapRow';
import { deriveLevel } from './EndgameOverallShared';

// Score Gap / Score Loss result is always tinted by zone (red / blue / green),
// never default-white. Significance gating applies to the operand (score)
// values via operandColor, but the difference itself reads as a zone signal
// regardless of confidence so the user always sees where they land.
function gapZoneColor(value: number): string {
  if (value < SCORE_GAP_NEUTRAL_MIN) return ZONE_DANGER;
  if (value >= SCORE_GAP_NEUTRAL_MAX) return ZONE_SUCCESS;
  return ZONE_NEUTRAL;
}

// Operand coloring mirrors the per-card Score row: zone color only when the
// score is significant AND outside the neutral (blue) zone; otherwise inherit
// (white).
function operandColor(
  score: number,
  level: ConfidenceLevel,
): string | undefined {
  const zoneHex = scoreZoneColor(score);
  const inColoredZone = zoneHex !== ZONE_NEUTRAL;
  return isConfident(level) && inColoredZone ? zoneHex : undefined;
}

export function EndgameOverallPerformanceSection({
  data,
  scoreGap,
}: {
  data: EndgamePerformanceResponse;
  scoreGap: ScoreGapMaterialResponse;
}) {
  const gapPositive = scoreGap.score_difference >= 0;
  const gapFormatted =
    (gapPositive ? '+' : '') + `${Math.round(scoreGap.score_difference * 100)}%`;

  // Share of total games per card (Card 1 = without endgame, Card 3 = with endgame).
  const totalGames = data.non_endgame_wdl.total + data.endgame_wdl.total;
  const withoutShare = totalGames > 0 ? data.non_endgame_wdl.total / totalGames : 0;
  const withShare = totalGames > 0 ? data.endgame_wdl.total / totalGames : 0;

  // Per-card scores for the Score Gap math expression. Math order is
  // `<with> − <without> = <gap>` to match the API's
  // `score_difference = endgame - non_endgame` sign convention
  // (positive = endgame better) and the bullet chart's zone meanings.
  const withoutScore =
    data.non_endgame_wdl.total > 0
      ? (data.non_endgame_wdl.wins + 0.5 * data.non_endgame_wdl.draws) /
        data.non_endgame_wdl.total
      : 0;
  const withScore =
    data.endgame_wdl.total > 0
      ? (data.endgame_wdl.wins + 0.5 * data.endgame_wdl.draws) /
        data.endgame_wdl.total
      : 0;
  const withoutLevel = deriveLevel(
    data.non_endgame_score_p_value,
    data.non_endgame_wdl.total,
  );
  const withLevel = deriveLevel(
    data.endgame_score_p_value,
    data.endgame_wdl.total,
  );
  const withoutScoreColor = operandColor(withoutScore, withoutLevel);
  const withScoreColor = operandColor(withScore, withLevel);
  const showGapMath =
    data.non_endgame_wdl.total > 0 && data.endgame_wdl.total > 0;
  const withoutScorePct = `${Math.round(withoutScore * 100)}%`;
  const withScorePct = `${Math.round(withScore * 100)}%`;
  const gapColor = gapZoneColor(scoreGap.score_difference);

  // Endgame Score Loss: how much the actual endgame score fell short of
  // (or exceeded) the achievable score expected from the entry eval.
  // Same math format, colors, and bullet settings as the Score Gap.
  const achievableScore = data.entry_expected_score;
  const achievableLevel = deriveLevel(
    data.entry_expected_score_p_value,
    data.entry_expected_score_n,
  );
  const achievableScoreColor = operandColor(achievableScore, achievableLevel);
  const achievableScorePct = `${Math.round(achievableScore * 100)}%`;
  const lossValue = withScore - achievableScore;
  const lossPositive = lossValue >= 0;
  const lossFormatted =
    (lossPositive ? '+' : '') + `${Math.round(lossValue * 100)}%`;
  const showLossMath =
    data.endgame_wdl.total > 0 && data.entry_expected_score_n > 0;
  const lossColor = gapZoneColor(lossValue);

  const gridRef = useRef<HTMLDivElement>(null);

  return (
    <section data-testid="endgame-overall-performance-section">
      <p className="text-sm text-muted-foreground">
        Do you perform better or worse when games reach an endgame?
      </p>

      {/* 3-column card grid on lg+, stacked on mobile. DOM order: Card 1,
          Card 2, Card 3, ScoreGap. On desktop ScoreGap is lifted to column 2
          via lg:col-start-2. Inside-card layout is single-column at every
          breakpoint (label-above-chart) so the WDL/bullet charts get the
          full card width regardless of viewport. `relative` anchors the
          ConnectorArrows SVG overlay (desktop only). */}
      <div
        ref={gridRef}
        className="relative grid grid-cols-1 lg:grid-cols-3 gap-4 mt-2"
      >
        {/* Card 1: Games without Endgame (left on desktop) */}
        <EndgameCard
          title="Games without Endgame"
          scoreLabel="Non-Endgame Score:"
          tileTestId="tile-games-without-endgame"
          scoreValueTestId="score-value-no"
          scorePopoverTestId="score-info-no"
          popoverAriaLabel="Games without Endgame score info"
          gamesCountTestId="games-count-no"
          wdl={data.non_endgame_wdl}
          pValue={data.non_endgame_score_p_value}
          gamesShare={withoutShare}
        />

        {/* Card 2: At Endgame Entry (center on desktop — no WDL bar) */}
        <EntryCard data={data} />

        {/* Card 3: Games with Endgame (right on desktop) */}
        <EndgameCard
          title="Games with Endgame"
          scoreLabel="Endgame Score:"
          tileTestId="tile-games-with-endgame"
          scoreValueTestId="score-value-yes"
          scorePopoverTestId="score-info-yes"
          popoverAriaLabel="Games with Endgame score info"
          gamesCountTestId="games-count-yes"
          wdl={data.endgame_wdl}
          pValue={data.endgame_score_p_value}
          gamesShare={withShare}
        />

        {/* Endgame Score Differences: lg:col-start-2 places it under Card 2 on desktop.
            On mobile (single column) it falls naturally after Card 3. */}
        <div
          className="charcoal-texture rounded-md p-4 lg:col-start-2 lg:mt-8"
          data-testid="endgame-score-differences"
        >
          <h3 className="text-base font-semibold mb-2">Endgame Score Differences</h3>
          <div className="flex flex-col gap-4">
            <ScoreGapRow
              label="Endgame Score Gap:"
              value={scoreGap.score_difference}
              formatted={gapFormatted}
              operand1Pct={withScorePct}
              operand1Color={withScoreColor}
              operand2Pct={withoutScorePct}
              operand2Color={withoutScoreColor}
              resultColor={gapColor}
              showMath={showGapMath}
              mathTestId="endgame-score-gap-math"
              valueTestId="endgame-score-gap-value"
              ariaLabel={`Endgame vs non-endgame score gap: ${gapFormatted}`}
              tooltip={
                <InfoPopover
                  ariaLabel="What is Endgame Score Gap?"
                  testId="endgame-score-gap-info"
                >
                  <p>
                    The score difference between games that reach an endgame (Endgame score) vs. games that end before (Non-Endgame score). Positive means endgames are
                    your strength; negative means you perform worse once
                    games reach an endgame.
                  </p>
                </InfoPopover>
              }
            />
            <ScoreGapRow
              label="Endgame Score Loss:"
              value={lossValue}
              formatted={lossFormatted}
              operand1Pct={withScorePct}
              operand1Color={withScoreColor}
              operand2Pct={achievableScorePct}
              operand2Color={achievableScoreColor}
              resultColor={lossColor}
              showMath={showLossMath}
              mathTestId="endgame-score-loss-math"
              valueTestId="endgame-score-loss-value"
              ariaLabel={`Endgame score loss: ${lossFormatted}`}
              tooltip={
                <InfoPopover
                  ariaLabel="What is Endgame Score Loss?"
                  testId="endgame-score-loss-info"
                >
                  <p>
                    Your Endgame score minus the Achievable score from your
                    endgame-entry positions. Negative means you converted
                    your endgame entry positions worse than a 2300+ rated
                    rapid player would on average.
                  </p>
                </InfoPopover>
              }
            />
          </div>
        </div>

        <ConnectorArrows containerRef={gridRef} />
      </div>
    </section>
  );
}
