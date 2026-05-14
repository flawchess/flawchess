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
import { ZONE_DANGER, ZONE_NEUTRAL, ZONE_SUCCESS } from '@/lib/theme';
import type {
  EndgamePerformanceResponse,
  ScoreGapMaterialResponse,
} from '@/types/endgames';

import { EndgameCard } from './EndgameOverallCard';
import { ConnectorArrows } from './EndgameOverallConnectorArrows';
import { EntryCard } from './EndgameOverallEntryCard';
import { ScoreGapRow } from './EndgameOverallScoreGapRow';

// Endgame Score Gap / Achievable Score Gap result is always tinted by zone (red / blue / green),
// never default-white. The difference reads as a zone signal regardless of
// confidence so the user always sees where they land.
function gapZoneColor(value: number): string {
  if (value < SCORE_GAP_NEUTRAL_MIN) return ZONE_DANGER;
  if (value >= SCORE_GAP_NEUTRAL_MAX) return ZONE_SUCCESS;
  return ZONE_NEUTRAL;
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

  const gapColor = gapZoneColor(scoreGap.score_difference);

  // Achievable Score Gap: how much the actual endgame score fell short of (or
  // exceeded) the achievable score expected from the entry eval.
  // achievable_score_gap is computed server-side per SEC1-10 (paired z-test on
  // per-game actual - expected pairs). Phase 85.1 Plan 03 retired the previous
  // frontend derivation `withScore - entry_expected_score`.
  const achievableGapValue = data.achievable_score_gap;
  const achievableGapPositive = achievableGapValue >= 0;
  const achievableGapFormatted =
    (achievableGapPositive ? '+' : '') + `${Math.round(achievableGapValue * 100)}%`;
  const achievableGapColor = gapZoneColor(achievableGapValue);

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
          popoverAriaLabel="Games without Endgame Score info"
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
          popoverAriaLabel="Games with Endgame Score info"
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
              label="Achievable Score Gap:"
              value={achievableGapValue}
              formatted={achievableGapFormatted}
              resultColor={achievableGapColor}
              valueTestId="achievable-score-gap-value"
              ariaLabel={`Achievable Score Gap: ${achievableGapFormatted}`}
              ciLow={data.achievable_score_gap_ci_low ?? undefined}
              ciHigh={data.achievable_score_gap_ci_high ?? undefined}
              tooltip={
                <InfoPopover
                  ariaLabel="What is Achievable Score Gap?"
                  testId="achievable-score-gap-info"
                >
                  <p>
                    Your Endgame Score minus the Achievable Score from your
                    endgame-entry positions. Positive means you converted
                    your endgame entry positions better than a 2300+ rated
                    rapid player would on average; negative means you
                    converted them worse.
                  </p>
                  <p>
                    The Achievable Score baseline comes from a Lichess
                    winning-chances formula calibrated on a broad rating
                    population. For your specific rating tier the baseline
                    may run a few percentage points high or low, so a small
                    negative gap can partly reflect calibration drift
                    rather than pure underperformance.
                  </p>
                </InfoPopover>
              }
            />
            <ScoreGapRow
              label="Endgame Score Gap:"
              value={scoreGap.score_difference}
              formatted={gapFormatted}
              resultColor={gapColor}
              valueTestId="endgame-score-gap-value"
              ariaLabel={`Endgame Score Gap: ${gapFormatted}`}
              valueClassName="text-lg"
              ciLow={scoreGap.score_difference_ci_low ?? undefined}
              ciHigh={scoreGap.score_difference_ci_high ?? undefined}
              tooltip={
                <InfoPopover
                  ariaLabel="What is Endgame Score Gap?"
                  testId="endgame-score-gap-info"
                >
                  <p>
                    The score difference between games that reach an endgame (Endgame Score) vs. games that end before (Non-Endgame Score). Positive means endgames are
                    your strength; negative means you perform worse once
                    games reach an endgame.
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
