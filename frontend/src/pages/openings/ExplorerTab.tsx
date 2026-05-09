import { Link } from 'react-router-dom';
import { Cpu, Swords } from 'lucide-react';
import type { ReactNode } from 'react';
import type { UseQueryResult } from '@tanstack/react-query';
import { WDLChartRow } from '@/components/charts/WDLChartRow';
import { MoveExplorer } from '@/components/move-explorer/MoveExplorer';
import { MiniBulletChart } from '@/components/charts/MiniBulletChart';
import { ScoreConfidencePopover } from '@/components/insights/ScoreConfidencePopover';
import { BulletConfidencePopover } from '@/components/insights/BulletConfidencePopover';
import { formatSignedEvalPawns } from '@/lib/clockFormat';
import {
  SCORE_BULLET_CENTER,
  SCORE_BULLET_NEUTRAL_MAX,
  SCORE_BULLET_NEUTRAL_MIN,
  clampScoreCi,
  scoreBulletDomain,
  scoreZoneColor,
} from '@/lib/scoreBulletConfig';
import { isConfident } from '@/lib/significance';
import {
  EVAL_BASELINE_PAWNS_WHITE,
  EVAL_BASELINE_PAWNS_BLACK,
  EVAL_BULLET_DOMAIN_PAWNS,
  EVAL_NEUTRAL_MIN_PAWNS,
  EVAL_NEUTRAL_MAX_PAWNS,
  evalZoneColor,
} from '@/lib/openingStatsZones';
import {
  MIN_GAMES_FOR_RELIABLE_STATS,
  UNRELIABLE_OPACITY,
  ZONE_NEUTRAL,
} from '@/lib/theme';
import type { Color, NextMovesResponse, OpeningsResponse } from '@/types/api';
import type { HighlightedMove } from './useDeepLinkHighlight';

type ExplorerTabProps = {
  gamesData: OpeningsResponse | undefined;
  filterColor: Color;
  positionResultsLabel: ReactNode;
  nextMoves: UseQueryResult<NextMovesResponse>;
  position: string;
  onMoveClick: (from: string, to: string) => boolean;
  onMoveHover: (san: string | null) => void;
  highlightedMove: HighlightedMove | null;
  pulseActive: boolean;
  onHighlightConsumed: () => void;
};

export function ExplorerTab({
  gamesData,
  filterColor,
  positionResultsLabel,
  nextMoves,
  position,
  onMoveClick,
  onMoveHover,
  highlightedMove,
  pulseActive,
  onHighlightConsumed,
}: ExplorerTabProps) {
  return (
    <div className="flex flex-col gap-4">
      {gamesData && gamesData.stats.total > 0 && (() => {
        const stats = gamesData.stats;
        const isUnreliable = stats.total < MIN_GAMES_FOR_RELIABLE_STATS;
        const scorePct = Math.round(stats.score * 100);
        // Score-color font gate mirrors MoveExplorer.tsx: paint Score % in the
        // zone color only when confidence is 'medium'/'high' (not 'low') AND
        // the score is in a colored zone. Otherwise default foreground.
        const zoneHex = scoreZoneColor(stats.score);
        const isInColoredZone = zoneHex !== ZONE_NEUTRAL;
        const showZoneFontColor = isConfident(stats.confidence) && isInColoredZone;
        const scoreColor: string | undefined = showZoneFontColor ? zoneHex : undefined;
        // MG-entry eval row (quick task 260508-f9o). Mirrors OpeningStatsCard /
        // OpeningFindingCard scoreEvalBlock: a third bullet chart row showing
        // signed pawns + Cpu icon + BulletConfidencePopover when MG eval data
        // is available, em-dash otherwise.
        const hasMgEval =
          stats.eval_n > 0 &&
          stats.avg_eval_pawns !== null &&
          stats.avg_eval_pawns !== undefined;
        const evalZoneHex = hasMgEval ? evalZoneColor(stats.avg_eval_pawns as number) : null;
        const showEvalZoneFont =
          hasMgEval &&
          isConfident(stats.eval_confidence) &&
          evalZoneHex !== ZONE_NEUTRAL;
        // Prefer the backend-provided baseline; fall back to the local
        // per-color constant if a stale cache returns no field.
        const evalBaselinePawnsLocal =
          filterColor === 'black' ? EVAL_BASELINE_PAWNS_BLACK : EVAL_BASELINE_PAWNS_WHITE;
        const evalBaselinePawns = gamesData.eval_baseline_pawns ?? evalBaselinePawnsLocal;
        return (
          <div
            className="charcoal-texture rounded-md p-4 order-2 lg:order-1"
            style={isUnreliable ? { opacity: UNRELIABLE_OPACITY } : undefined}
            data-testid="wdl-moves-position"
          >
            <div className="text-sm font-medium mb-2">{positionResultsLabel}</div>

            {/* Three same-width chart rows (indicator-left / chart-right). */}
            <div className="grid grid-cols-[auto_minmax(0,1fr)] gap-x-3 gap-y-2 items-center">
              {/* Row 1: linked games indicator + WDL bar. */}
              <Link
                to="/openings/games"
                onClick={() => window.scrollTo({ top: 0 })}
                className="flex items-center gap-1 text-sm tabular-nums w-full text-brand-brown-light hover:text-brand-brown-highlight transition-colors"
                aria-label="View games for this position"
                data-testid="btn-moves-to-games"
              >
                <span>Games:</span>
                <span className="ml-auto font-semibold tabular-nums inline-flex items-center gap-0.3">
                  {stats.total}
                  <Swords className="h-3.5 w-3.5" aria-hidden="true" />
                </span>
              </Link>
              <div className="min-w-0" data-testid="wdl-bar-position">
                <WDLChartRow data={stats} barHeight="h-6" showSegmentCounts={false} />
              </div>

              {/* Row 2: Score % + popover + Score bullet. */}
              <span
                className="flex items-center gap-1 text-sm tabular-nums w-full"
                data-testid="score-text-position"
              >
                <span className="text-muted-foreground">Score:</span>
                <span
                  className="ml-auto font-semibold"
                  style={scoreColor ? { color: scoreColor } : undefined}
                >
                  {scorePct}%
                </span>
                <ScoreConfidencePopover
                  level={stats.confidence}
                  pValue={stats.p_value}
                  score={stats.score}
                  gameCount={stats.total}
                  lastPlayedAt={stats.last_played_at}
                  testId="score-bullet-popover-trigger"
                  ariaLabel="Show score confidence details"
                />
              </span>
              <div className="min-w-0 tabular-nums" data-testid="score-bullet-position">
                <MiniBulletChart
                  value={stats.score}
                  center={SCORE_BULLET_CENTER}
                  neutralMin={SCORE_BULLET_NEUTRAL_MIN}
                  neutralMax={SCORE_BULLET_NEUTRAL_MAX}
                  domain={scoreBulletDomain()}
                  ciLow={clampScoreCi(stats.ci_low)}
                  ciHigh={clampScoreCi(stats.ci_high)}
                  barColor="neutral"
                  ariaLabel={`Score ${scorePct}% vs 50% baseline`}
                />
              </div>

              {/* Row 3: Eval value + Cpu + popover + Eval bullet. */}
              <span
                className="flex items-center gap-1 text-sm tabular-nums w-full"
                data-testid="eval-text-position"
              >
                <span className="text-muted-foreground">Eval:</span>
                {hasMgEval ? (
                  <span
                    className="ml-auto font-semibold inline-flex items-center gap-0.3"
                    style={showEvalZoneFont && evalZoneHex ? { color: evalZoneHex } : undefined}
                  >
                    {formatSignedEvalPawns(stats.avg_eval_pawns as number)}
                    <Cpu className="h-3.5 w-3.5" aria-hidden="true" />
                  </span>
                ) : (
                  <span className="ml-auto text-muted-foreground">—</span>
                )}
                {hasMgEval && (
                  <BulletConfidencePopover
                    level={stats.eval_confidence}
                    pValue={stats.eval_p_value}
                    gameCount={stats.eval_n}
                    evalMeanPawns={stats.avg_eval_pawns}
                    color={filterColor}
                    testId="eval-bullet-popover-trigger"
                  />
                )}
              </span>
              <div className="min-w-0 tabular-nums" data-testid="eval-bullet-position">
                {hasMgEval ? (
                  <MiniBulletChart
                    value={stats.avg_eval_pawns as number}
                    ciLow={stats.eval_ci_low_pawns ?? undefined}
                    ciHigh={stats.eval_ci_high_pawns ?? undefined}
                    tickPawns={evalBaselinePawns}
                    neutralMin={EVAL_NEUTRAL_MIN_PAWNS}
                    neutralMax={EVAL_NEUTRAL_MAX_PAWNS}
                    domain={EVAL_BULLET_DOMAIN_PAWNS}
                    barColor="neutral"
                    ariaLabel={`Avg eval at MG entry: ${(stats.avg_eval_pawns as number).toFixed(2)} pawns`}
                  />
                ) : (
                  <span className="text-muted-foreground">—</span>
                )}
              </div>
            </div>
          </div>
        );
      })()}
      <div className="charcoal-texture rounded-md p-4 order-1 lg:order-2">
        <MoveExplorer
          moves={nextMoves.data?.moves ?? []}
          isLoading={nextMoves.isLoading}
          isError={nextMoves.isError}
          position={position}
          onMoveClick={onMoveClick}
          onMoveHover={onMoveHover}
          highlightedMove={
            highlightedMove !== null
              ? { ...highlightedMove, pulse: pulseActive }
              : null
          }
          onHighlightConsumed={onHighlightConsumed}
        />
      </div>
    </div>
  );
}
