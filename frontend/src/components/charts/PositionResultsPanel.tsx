import { Link } from 'react-router';
import { Cpu, Swords } from 'lucide-react';
import type { ReactNode } from 'react';
import { WDLChartRow } from '@/components/charts/WDLChartRow';
import { MiniBulletChart } from '@/components/charts/MiniBulletChart';
import { EvalConfidencePopover } from '@/components/insights/EvalConfidencePopover';
import { EvalCpuPlaceholder } from '@/components/stats/EvalCpuPlaceholder';
import { VerdictTrack } from '@/components/openings/stats/VerdictBar';
import {
  EvalVerdictPopover,
  ScoreVerdictPopover,
} from '@/components/openings/stats/VerdictPopover';
import { Card, CardHeader, CardBody } from '@/components/ui/card';
import { useReadiness } from '@/hooks/useReadiness';
import { formatSignedEvalPawns } from '@/lib/clockFormat';
import { isConfident } from '@/lib/significance';
import { formatSignedGap } from '@/lib/gapBar';
import {
  EVAL_VERDICT_BAND,
  SCORE_VERDICT_BAND,
  evalBaselinePawns as colorEvalBaselinePawns,
  openingVerdict,
  openingVerdictReason,
  scoreDelta,
  verdictValueColor,
} from '@/lib/openingVerdict';
import {
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
import type { Color, WDLStats } from '@/types/api';

type PositionResultsPanelProps = {
  stats: WDLStats;
  /** Backend eval_baseline_pawns. If a stale cache omits it at runtime, the component
   *  falls back to the per-color constant. */
  evalBaselinePawns: number;
  filterColor: Color;
  label: ReactNode;
  /** When provided, renders the games count as a link navigating to this href.
   *  When omitted, games count is plain text (data-testid="games-count-position"). */
  gamesHref?: string;
  className?: string;
  /** Which game phase the averaged eval is sampled at. 'opening-end' (default,
   *  move explorer / Openings) = end of the openings containing this position;
   *  'endgame-entry' (Endgames Games subtab) = the position where the endgame
   *  begins. Drives the Eval popover copy and hides the opening-only per-color
   *  baseline tick (the Endgames eval is color-agnostic). */
  evalContext?: 'opening-end' | 'endgame-entry';
};

/**
 * Shared WDL + Score bullet + Eval bullet three-row results panel.
 *
 * Shared by ExplorerTab, Openings GamesTab and the Endgames games subtab so all
 * three render the same presentation.
 *
 * Returns null when stats.total === 0.
 */
export function PositionResultsPanel({
  stats,
  evalBaselinePawns,
  filterColor,
  label,
  gamesHref,
  className = 'order-2 lg:order-1',
  evalContext = 'opening-end',
}: PositionResultsPanelProps) {
  // Hook must run before the early return below (Rules of Hooks).
  const { tier2 } = useReadiness();
  if (stats.total === 0) return null;

  const isUnreliable = stats.total < MIN_GAMES_FOR_RELIABLE_STATS;
  const scorePct = Math.round(stats.score * 100);

  // Score verdict: same 95% / 20-game / +-5-point rule as the repertoire cards. The value text
  // takes the dot colour only for a better or worse verdict.
  const scoreVerdictInput = {
    delta: scoreDelta(stats.score),
    band: SCORE_VERDICT_BAND,
    confidence: stats.confidence,
    games: stats.total,
  };
  const scoreVerdict = openingVerdict(scoreVerdictInput);
  const scoreColor = verdictValueColor(scoreVerdict);

  // MG-entry eval row: 'opening-end' with data renders the baseline-centred VerdictBar (D-17);
  // everything else (Endgames entry eval, or no eval data) keeps the bullet-chart cells.
  const hasAvgEval =
    stats.eval_n > 0 &&
    stats.avg_eval_pawns !== null &&
    stats.avg_eval_pawns !== undefined;
  const showVerdictBar = hasAvgEval && evalContext === 'opening-end';

  return (
    <Card
      className={className}
      style={isUnreliable ? { opacity: UNRELIABLE_OPACITY } : undefined}
      data-testid="wdl-moves-position"
    >
      <CardHeader as="h4" size="compact" data-testid="wdl-moves-position-header">
        {label}
      </CardHeader>
      <CardBody>

      {/* Three same-width chart rows (indicator-left / chart-right). */}
      <div className="grid grid-cols-[auto_minmax(0,1fr)] gap-x-3 gap-y-2 items-center">
        {/* Row 1: games indicator (link or plain) + WDL bar. */}
        {gamesHref ? (
          <Link
            to={gamesHref}
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
        ) : (
          <span
            className="flex items-center gap-1 text-sm tabular-nums w-full"
            data-testid="games-count-position"
          >
            <span>Games:</span>
            <span className="ml-auto font-semibold tabular-nums inline-flex items-center gap-0.3">
              {stats.total}
              <Swords className="h-3.5 w-3.5" aria-hidden="true" />
            </span>
          </span>
        )}
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
          {/* Fixed trigger testId: it is the Umami popover-open target, keep its history. */}
          <ScoreVerdictPopover
            testId="score-bullet-popover-trigger"
            score={stats.score}
            games={stats.total}
            wins={stats.wins}
            draws={stats.draws}
            losses={stats.losses}
            reason={openingVerdictReason(scoreVerdictInput)}
            ciLow={stats.ci_low ?? null}
            ciHigh={stats.ci_high ?? null}
            pValue={stats.p_value}
            lastPlayedAt={stats.last_played_at}
          />
        </span>
        <div className="min-w-0" data-testid="score-bullet-position">
          <VerdictTrack
            delta={scoreDelta(stats.score)}
            band={SCORE_VERDICT_BAND}
            verdict={scoreVerdict}
            testId="score-verdict-position"
            ariaLabel={`Score ${scorePct}%, centred on 50%`}
          />
        </div>

        {/* Row 3: End Eval. Gated on Tier 2 — when !tier2 (Stockfish still analyzing)
            both eval cells are replaced by the pulsating-Cpu placeholder spanning the
            2-col grid. In the endgame-entry context tier2 is always true (the Endgames
            page is itself Tier-2 gated), so this only affects the openings explorer. */}
        {!tier2 ? (
          <EvalCpuPlaceholder />
        ) : showVerdictBar ? (
          <OpeningEvalVerdictRow
            stats={stats}
            evalBaselinePawns={evalBaselinePawns}
            filterColor={filterColor}
          />
        ) : (
          <EvalBulletCells stats={stats} hasAvgEval={hasAvgEval} evalContext={evalContext} filterColor={filterColor} />
        )}
      </div>
      </CardBody>
    </Card>
  );
}

interface OpeningEvalVerdictRowProps {
  stats: WDLStats;
  evalBaselinePawns: number | undefined;
  filterColor: Color;
}

/**
 * Opening-end End Eval: label, value and popover in the left cell and a verdict track centred
 * on the colour's average eval in the right cell, the same layout as the Score row. Dot is
 * green/red only for a confident (95%), out-of-band eval over 20+ evals.
 */
function OpeningEvalVerdictRow({ stats, evalBaselinePawns, filterColor }: OpeningEvalVerdictRowProps) {
  const avgEval = stats.avg_eval_pawns as number;
  // Prefer the backend baseline; a stale cache that omits it falls back to the per-color constant.
  const baseline = evalBaselinePawns ?? colorEvalBaselinePawns(filterColor);
  const delta = avgEval - baseline;
  const verdictInput = {
    delta,
    band: EVAL_VERDICT_BAND,
    confidence: stats.eval_confidence,
    // WR-02: the 20-game verdict floor applies to the eval sample (eval_n), not the game count:
    // the mean excludes mate/NULL evals and trims outliers, so a 40-game opening can rest on 11 evals.
    games: stats.eval_n,
  };
  const verdict = openingVerdict(verdictInput);
  const valueColor = verdictValueColor(verdict);
  const colourName = filterColor === 'black' ? 'Black' : 'White';
  return (
    <>
      <span
        className="flex items-center gap-1 text-sm tabular-nums w-full"
        data-testid="eval-text-position"
      >
        <span className="text-muted-foreground">End Eval:</span>
        <span
          className="ml-auto font-semibold inline-flex items-center gap-0.3"
          style={valueColor ? { color: valueColor } : undefined}
          data-testid="eval-verdict-position-value"
        >
          {formatSignedEvalPawns(avgEval)}
          <Cpu className="h-3.5 w-3.5" aria-hidden="true" />
        </span>
        {/* Fixed trigger testId: it is the Umami popover-open target, keep its history. */}
        <EvalVerdictPopover
          testId="eval-bullet-popover-trigger"
          label="End Eval"
          avgEvalPawns={avgEval}
          evalN={stats.eval_n}
          color={filterColor}
          reason={openingVerdictReason(verdictInput)}
          ciLow={stats.eval_ci_low_pawns ?? null}
          ciHigh={stats.eval_ci_high_pawns ?? null}
          pValue={stats.eval_p_value ?? null}
        />
      </span>
      <div className="min-w-0" data-testid="eval-verdict-position">
        <VerdictTrack
          delta={delta}
          band={EVAL_VERDICT_BAND}
          verdict={verdict}
          zeroTickDelta={-baseline}
          centreSwatch={filterColor}
          testId="eval-verdict-position"
          ariaLabel={`End eval ${formatSignedGap(avgEval)}, centred on an average ${colourName} game at ${formatSignedGap(baseline)}`}
        />
      </div>
    </>
  );
}

interface EvalBulletCellsProps {
  stats: WDLStats;
  hasAvgEval: boolean;
  evalContext: 'opening-end' | 'endgame-entry';
  filterColor: Color;
}

/**
 * The two-cell bullet-chart End Eval row: the Endgames games subtab (eval at endgame entry,
 * color-agnostic so no per-color baseline tick) and the em-dash fallback when an Openings
 * position has no eval data.
 */
function EvalBulletCells({ stats, hasAvgEval, evalContext, filterColor }: EvalBulletCellsProps) {
  const evalZoneHex = hasAvgEval ? evalZoneColor(stats.avg_eval_pawns as number) : null;
  const showEvalZoneFont =
    hasAvgEval &&
    isConfident(stats.eval_confidence) &&
    evalZoneHex !== ZONE_NEUTRAL;
  const isEndgameEntryEval = evalContext === 'endgame-entry';
  const evalAriaLabel = isEndgameEntryEval
    ? `Avg eval at endgame entry: ${hasAvgEval ? (stats.avg_eval_pawns as number).toFixed(2) : '—'} pawns`
    : `Avg eval at MG entry: ${hasAvgEval ? (stats.avg_eval_pawns as number).toFixed(2) : '—'} pawns`;

  return (
    <>
      <span
        className="flex items-center gap-1 text-sm tabular-nums w-full"
        data-testid="eval-text-position"
      >
        <span className="text-muted-foreground">End Eval:</span>
        {hasAvgEval ? (
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
        {hasAvgEval && (
          <EvalConfidencePopover
            level={stats.eval_confidence}
            pValue={stats.eval_p_value}
            gameCount={stats.eval_n}
            evalMeanPawns={stats.avg_eval_pawns}
            color={filterColor}
            testId="eval-bullet-popover-trigger"
            evalContext={evalContext}
            showBaselineTick={isEndgameEntryEval ? false : undefined}
          />
        )}
      </span>
      <div className="min-w-0 tabular-nums" data-testid="eval-bullet-position">
        {hasAvgEval ? (
          <MiniBulletChart
            value={stats.avg_eval_pawns as number}
            ciLow={stats.eval_ci_low_pawns ?? undefined}
            ciHigh={stats.eval_ci_high_pawns ?? undefined}
            neutralMin={EVAL_NEUTRAL_MIN_PAWNS}
            neutralMax={EVAL_NEUTRAL_MAX_PAWNS}
            domain={EVAL_BULLET_DOMAIN_PAWNS}
            barColor="neutral"
            ariaLabel={evalAriaLabel}
          />
        ) : (
          <span className="text-muted-foreground">—</span>
        )}
      </div>
    </>
  );
}
