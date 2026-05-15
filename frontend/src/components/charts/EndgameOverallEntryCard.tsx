/**
 * Phase 85 — Card 2 of the "Endgame Overall Performance" composite section.
 * Two stacked bullet rows: endgame entry eval (pawns) and achievable score
 * (W + 0.5·D expected from the entry eval). No WDL bar — Card 2 is about the
 * position you reach, not the outcome.
 *
 * CR-01 preserved: the achievable-score MiniBulletChart uses OFFSET-form
 * neutralMin/neutralMax (absolute registry bounds minus center), not the
 * absolute bounds directly. Passing absolute bounds collapses the neutral
 * band visually.
 */

import { Cpu } from 'lucide-react';

import { MiniBulletChart } from '@/components/charts/MiniBulletChart';
import { MetricStatPopover } from '@/components/popovers/MetricStatPopover';
import {
  ENTRY_EXPECTED_SCORE_NEUTRAL_MAX,
  ENTRY_EXPECTED_SCORE_NEUTRAL_MIN,
  entryExpectedScoreZoneColor,
} from '@/generated/endgameZones';
import { formatSignedEvalPawns } from '@/lib/clockFormat';
import {
  ENDGAME_ENTRY_EVAL_CENTER,
  ENDGAME_ENTRY_EVAL_DOMAIN_PAWNS,
  ENDGAME_ENTRY_EVAL_NEUTRAL_MAX_PAWNS,
  ENDGAME_ENTRY_EVAL_NEUTRAL_MIN_PAWNS,
  endgameEntryEvalZoneColor,
} from '@/lib/endgameEntryEvalZones';
import { SCORE_BULLET_CENTER, clampScoreCi } from '@/lib/scoreBulletConfig';
import { isConfident } from '@/lib/significance';
import { MIN_GAMES_FOR_RELIABLE_STATS, ZONE_NEUTRAL } from '@/lib/theme';
import type { EndgamePerformanceResponse } from '@/types/endgames';

import { ENDGAME_TILE_SCORE_DOMAIN, deriveLevel } from './EndgameOverallShared';

// Neutral band for score-vs-50% (Achievable Score). See EndgameOverallCard.tsx
// for rationale; matches arrowColor.ts / WdlConfidenceTooltip bounds.
const SCORE_NEUTRAL_LOWER = 0.45;
const SCORE_NEUTRAL_UPPER = 0.55;

interface EntryCardProps {
  data: EndgamePerformanceResponse;
}

export function EntryCard({ data }: EntryCardProps) {
  // Row 1: entry eval
  const evalLevel = deriveLevel(data.entry_eval_p_value, data.entry_eval_n);
  const evalZoneHex = endgameEntryEvalZoneColor(data.entry_eval_mean_pawns);
  const evalIsInColoredZone = evalZoneHex !== ZONE_NEUTRAL;
  const evalShowZoneFontColor = isConfident(evalLevel) && evalIsInColoredZone;
  const evalColor: string | undefined = evalShowZoneFontColor ? evalZoneHex : undefined;
  const showEntryEvalChart = data.entry_eval_n >= MIN_GAMES_FOR_RELIABLE_STATS;

  // Row 2: achievable score (CR-01: use OFFSET-form for neutralMin/neutralMax)
  const achievableLevel = deriveLevel(
    data.entry_expected_score_p_value,
    data.entry_expected_score_n,
  );
  const achievableZoneHex = entryExpectedScoreZoneColor(data.entry_expected_score);
  const achievableIsInColoredZone = achievableZoneHex !== ZONE_NEUTRAL;
  const achievableShowZoneFontColor =
    isConfident(achievableLevel) && achievableIsInColoredZone;
  const achievableColor: string | undefined = achievableShowZoneFontColor
    ? achievableZoneHex
    : undefined;
  const showAchievableChart =
    data.entry_expected_score_n >= MIN_GAMES_FOR_RELIABLE_STATS;

  return (
    <div className="charcoal-texture rounded-md p-4" data-testid="tile-at-endgame-entry">
      <h3 className="text-base font-semibold mb-2 inline-flex items-center gap-1">
        <Cpu className="h-4 w-4" aria-hidden="true" />
        Eval at Endgame Entry
      </h3>
      <div className="flex flex-col gap-4">
        {/* Row 1: entry-eval bullet (pawns) */}
        {showEntryEvalChart ? (
          <div className="flex flex-col gap-2">
            <span className="flex items-center gap-1 text-sm tabular-nums w-full">
              <span className="text-muted-foreground">Endgame Entry Eval:</span>
              <span
                className="font-semibold inline-flex items-center gap-0.5"
                style={evalColor ? { color: evalColor } : undefined}
                data-testid="entry-eval-value"
              >
                {formatSignedEvalPawns(data.entry_eval_mean_pawns)}
                <Cpu className="h-3.5 w-3.5" aria-hidden="true" />
              </span>
              <MetricStatPopover
                name="Endgame Entry Eval"
                explanation="The average Stockfish eval (in pawns, from your perspective) at the position where the endgame begins. Positive means you reached the endgame with the better position."
                value={data.entry_eval_mean_pawns}
                baseline={0}
                unit="pawns"
                gameCount={data.entry_eval_n}
                level={evalLevel}
                pValue={data.entry_eval_p_value}
                vocabulary="eval"
                neutralLower={ENDGAME_ENTRY_EVAL_NEUTRAL_MIN_PAWNS}
                neutralUpper={ENDGAME_ENTRY_EVAL_NEUTRAL_MAX_PAWNS}
                baselineLabel="0 pawns"
                methodology={
                  <>
                    Test: two-sided Wald z vs 0 pawns.<br />
                    Confidence interval: Wald 95% (whiskers).
                  </>
                }
                testId="entry-eval-popover-trigger"
                ariaLabel="Show eval confidence details"
              />
            </span>
            <div className="min-w-0 tabular-nums">
              <MiniBulletChart
                value={data.entry_eval_mean_pawns}
                center={ENDGAME_ENTRY_EVAL_CENTER}
                neutralMin={ENDGAME_ENTRY_EVAL_NEUTRAL_MIN_PAWNS}
                neutralMax={ENDGAME_ENTRY_EVAL_NEUTRAL_MAX_PAWNS}
                domain={ENDGAME_ENTRY_EVAL_DOMAIN_PAWNS}
                ciLow={data.entry_eval_ci_low_pawns ?? undefined}
                ciHigh={data.entry_eval_ci_high_pawns ?? undefined}
                barColor="neutral"
                ariaLabel={`Endgame Entry Eval: ${data.entry_eval_mean_pawns.toFixed(2)} pawns`}
              />
            </div>
          </div>
        ) : (
          <p className="text-sm text-muted-foreground py-4">Not enough data yet</p>
        )}

        {/* Row 2: achievable score bullet (CR-01: OFFSET-form neutralMin/neutralMax). */}
        <div data-testid="endgame-achievable-score">
          {showAchievableChart ? (
            <div className="flex flex-col gap-2">
              <span className="flex items-center gap-1 text-sm tabular-nums w-full">
                <span className="text-muted-foreground">Achievable Score:</span>
                <span
                  className="font-semibold"
                  style={achievableColor ? { color: achievableColor } : undefined}
                  data-testid="achievable-score-value"
                >
                  {`${(data.entry_expected_score * 100).toFixed(0)}%`}
                </span>
                <MetricStatPopover
                  name="Achievable Score"
                  explanation="What a 2300+ rated player would score from your endgame-entry positions against a peer of similar rating, via the Lichess expected-score formula. Compare against your Endgame Score."
                  value={data.entry_expected_score}
                  baseline={0.5}
                  unit="percent"
                  gameCount={data.entry_expected_score_n}
                  level={achievableLevel}
                  pValue={data.entry_expected_score_p_value}
                  vocabulary="score"
                  neutralLower={SCORE_NEUTRAL_LOWER}
                  neutralUpper={SCORE_NEUTRAL_UPPER}
                  baselineLabel="50%"
                  methodology={
                    <>
                      Score: wins + ½ draws.<br />
                      Test: two-sided Wilson score test vs 50%.<br />
                      Confidence interval: Wilson 95% (whiskers).
                    </>
                  }
                  testId="popover-trigger-achievable-score"
                  ariaLabel="What is Achievable Score?"
                />
              </span>
              <div className="min-w-0 tabular-nums">
                {/* MiniBulletChart neutralMin/neutralMax are OFFSETS from center; the
                    registry stores absolute bounds, so convert by subtracting center
                    (CR-01 fix: passing absolute bounds collapses the neutral band). */}
                <MiniBulletChart
                  value={data.entry_expected_score}
                  center={SCORE_BULLET_CENTER}
                  neutralMin={ENTRY_EXPECTED_SCORE_NEUTRAL_MIN - SCORE_BULLET_CENTER}
                  neutralMax={ENTRY_EXPECTED_SCORE_NEUTRAL_MAX - SCORE_BULLET_CENTER}
                  domain={ENDGAME_TILE_SCORE_DOMAIN}
                  ciLow={
                    data.entry_expected_score_ci_low != null
                      ? clampScoreCi(data.entry_expected_score_ci_low)
                      : undefined
                  }
                  ciHigh={
                    data.entry_expected_score_ci_high != null
                      ? clampScoreCi(data.entry_expected_score_ci_high)
                      : undefined
                  }
                  barColor="neutral"
                  ariaLabel={`Achievable Score: ${(data.entry_expected_score * 100).toFixed(0)}%`}
                />
              </div>
            </div>
          ) : (
            <p className="text-sm text-muted-foreground py-4">Not enough data yet</p>
          )}
        </div>
      </div>
    </div>
  );
}
