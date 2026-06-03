import { ArrowRightLeft, Cpu, Swords } from 'lucide-react';
import type { OpeningWDL } from '@/types/stats';
import { LazyMiniBoard } from '@/components/board/LazyMiniBoard';
import { WDLChartRow } from '@/components/charts/WDLChartRow';
import { MiniBulletChart } from '@/components/charts/MiniBulletChart';
import { Tooltip } from '@/components/ui/tooltip';
import { BulletConfidencePopover } from '@/components/insights/BulletConfidencePopover';
import { ScoreConfidencePopover } from '@/components/insights/ScoreConfidencePopover';
import { EvalCpuPlaceholder } from './EvalCpuPlaceholder';
import { useReadiness } from '@/hooks/useReadiness';
import {
  EVAL_BULLET_DOMAIN_PAWNS,
  EVAL_NEUTRAL_MAX_PAWNS,
  EVAL_NEUTRAL_MIN_PAWNS,
  evalZoneColor,
} from '@/lib/openingStatsZones';
import {
  SCORE_BULLET_CENTER,
  SCORE_BULLET_NEUTRAL_MIN,
  SCORE_BULLET_NEUTRAL_MAX,
  SCORE_BULLET_DOMAIN,
  scoreZoneColor,
} from '@/lib/scoreBulletConfig';
import { computeScoreConfidence } from '@/lib/scoreConfidence';
import { isConfident } from '@/lib/significance';
import { formatSignedEvalPawns } from '@/lib/clockFormat';
import {
  MIN_GAMES_FOR_RELIABLE_STATS,
  UNRELIABLE_OPACITY,
  ZONE_NEUTRAL,
} from '@/lib/theme';

const MOBILE_BOARD_SIZE = 115;
const DESKTOP_BOARD_SIZE = 110;

interface OpeningStatsCardProps {
  opening: OpeningWDL;
  color: 'white' | 'black';
  /** Globally unique index for data-testid scoping (matches OpeningFindingCard convention). */
  idx: number;
  /** Reserved for future per-section namespacing; today every card uses the same prefix. */
  testIdPrefix: string;
  /** Routes to the Move Explorer for this opening (mirrors OpeningFindingCard's onFindingClick). */
  onOpenMoves: (opening: OpeningWDL, color: 'white' | 'black') => void;
  /** Routes to the Games subtab filtered to this opening. */
  onOpenGames: (opening: OpeningWDL, color: 'white' | 'black') => void;
  /** Per-color engine-asymmetry baseline (in pawns). Rendered as the bullet chart's reference tick. */
  evalBaselinePawns: number;
}

export function OpeningStatsCard({
  opening,
  color,
  idx,
  testIdPrefix,
  onOpenMoves,
  onOpenGames,
  evalBaselinePawns,
}: OpeningStatsCardProps) {
  const { tier2 } = useReadiness();

  const cardTestId = `${testIdPrefix}-${idx}`;

  const hasMgEval =
    opening.eval_n > 0 &&
    opening.avg_eval_pawns !== null &&
    opening.avg_eval_pawns !== undefined;

  // Wilson score confidence computed client-side from (W, D, total). Mirrors
  // the backend `compute_confidence_bucket` so the Stats info icon surfaces
  // the same stats the Insights tab reports for finding rows.
  const scoreStats = computeScoreConfidence(
    opening.wins,
    opening.draws,
    opening.total,
  );
  const derivedScore = scoreStats.score;

  // Border color uses the score zone (reliability-gated). Eval loses the border
  // but keeps its bullet row, Cpu icon, and eval-text color — plenty of signal.
  // When total < MIN_GAMES_FOR_RELIABLE_STATS, a transparent border avoids
  // painting a misleading score zone on a sparse row (260507-t4r D4).
  const isReliableScore = opening.total >= MIN_GAMES_FOR_RELIABLE_STATS;
  const scoreZoneHex = scoreZoneColor(derivedScore);
  const borderLeftColor = isReliableScore ? scoreZoneHex : 'transparent';

  // Quick task 260508-dcp: separate gate for the Score % FONT color.
  // Font reads in zone color only when the confidence bucket is 'medium' or
  // 'high' (n>=10 + p below the medium threshold; current threshold is
  // p<0.05) AND the zone is colored (red/green, not the in-between band).
  // The card border keeps the existing reliability-only gate above (border
  // treatment is out of scope for the significance tightening).
  const showScoreZoneFont =
    isConfident(scoreStats.confidence) && scoreZoneHex !== ZONE_NEUTRAL;

  // Eval-text gate: same shape but uses the eval-domain confidence + zone.
  const evalZoneHex = hasMgEval ? evalZoneColor(opening.avg_eval_pawns as number) : null;
  const showEvalZoneFont =
    hasMgEval &&
    isConfident(opening.eval_confidence) &&
    evalZoneHex !== ZONE_NEUTRAL;

  // Per-row dimming (260603-pgv): fade only the stat row whose confidence is
  // low, instead of the whole card. Eval dims only when an eval value exists
  // (the placeholder / no-eval "—" cases are never dimmed).
  const dimScoreRow = !isConfident(scoreStats.confidence);
  const dimEvalRow = hasMgEval && !isConfident(opening.eval_confidence);

  // Full-height left spine on the card root (see OpeningFindingCard). Reliable
  // cards get the score-zone accent down the whole left edge; unreliable cards
  // (n < MIN_GAMES) get no spine — the uniform 1px border stays, avoiding a 4px
  // transparent gap and any color signal on sparse data. The whole-card opacity
  // dim was removed in 260603-pgv (per-row dimming replaces it).
  const rootStyle: React.CSSProperties = {
    ...(isReliableScore ? { borderLeftColor } : {}),
  };

  // Phase 80 MG eval text — signed pawns to one decimal (e.g. "+2.1"), zone color
  // anchored at 0 cp. Mirrors MostPlayedOpeningsTable lines 78-87.
  const mgEvalTextContent = hasMgEval ? (
    <span
      className="font-semibold inline-flex items-center gap-0.3"
      style={showEvalZoneFont && evalZoneHex ? { color: evalZoneHex } : undefined}
    >
      {formatSignedEvalPawns(opening.avg_eval_pawns as number)}
      <Cpu className="h-3.5 w-3.5" aria-hidden="true" />
    </span>
  ) : (
    <span className="text-muted-foreground">—</span>
  );

  // MG bullet chart, anchored on 0 cp; per-color baseline rendered as a small tick.
  // barColor="neutral" so the bar encodes position only; zone bands carry verdict.
  const mgBulletContent = hasMgEval ? (
    <MiniBulletChart
      value={opening.avg_eval_pawns as number}
      ciLow={opening.eval_ci_low_pawns ?? undefined}
      ciHigh={opening.eval_ci_high_pawns ?? undefined}
      tickPawns={evalBaselinePawns}
      neutralMin={EVAL_NEUTRAL_MIN_PAWNS}
      neutralMax={EVAL_NEUTRAL_MAX_PAWNS}
      domain={EVAL_BULLET_DOMAIN_PAWNS}
      barColor="neutral"
      ariaLabel={`Avg eval at MG entry: ${(opening.avg_eval_pawns as number).toFixed(2)} pawns`}
    />
  ) : (
    <span className="text-muted-foreground">—</span>
  );

  const wdlData = {
    wins: opening.wins,
    draws: opening.draws,
    losses: opening.losses,
    total: opening.total,
    win_pct: opening.win_pct,
    draw_pct: opening.draw_pct,
    loss_pct: opening.loss_pct,
  };

  const wdlLine = (
    <WDLChartRow
      data={wdlData}
      showSegmentCounts={false}
      testId={`${cardTestId}-wdl`}
    />
  );

  // Score + eval rows. On mobile: label stacks above the bullet chart for each
  // metric (per-metric flex-col wrapper, label first in DOM). On desktop (sm+):
  // the wrappers become `display:contents` so all four cells (two bullets, two
  // labels) join ONE shared 2-col grid. The shared `auto` text column is sized
  // to the WIDER label ("End Eval:"), so both bullets get the same `1fr` width
  // and stay aligned — without the shared grid each row sized its text column
  // independently and the narrower "Score:" label left the score bullet wider.
  const scoreEvalBlock = (
    <div className="flex flex-col gap-2 sm:grid sm:grid-cols-[minmax(0,1fr)_auto] sm:gap-x-2 sm:gap-y-2 sm:items-center">
      {/* Score row */}
      <div className="flex flex-col gap-1 sm:contents">
        <span
          className="flex items-center gap-1 text-sm tabular-nums w-full sm:col-start-2 sm:row-start-1"
          data-testid={`${cardTestId}-score-text`}
          style={dimScoreRow ? { opacity: UNRELIABLE_OPACITY } : undefined}
        >
          <span className="text-muted-foreground">Score:</span>
          <span
            className="ml-auto font-semibold"
            style={showScoreZoneFont ? { color: scoreZoneHex } : undefined}
          >
            {Math.round(derivedScore * 100)}%
          </span>
          <ScoreConfidencePopover
            level={scoreStats.confidence}
            pValue={scoreStats.pValue}
            score={derivedScore}
            gameCount={opening.total}
            lastPlayedAt={opening.last_played_at}
            testId={`${cardTestId}-score-popover`}
          />
        </span>
        <div
          className="min-w-0 tabular-nums sm:col-start-1 sm:row-start-1"
          data-testid={`${cardTestId}-score-bullet`}
          style={dimScoreRow ? { opacity: UNRELIABLE_OPACITY } : undefined}
        >
          <MiniBulletChart
            value={derivedScore}
            center={SCORE_BULLET_CENTER}
            neutralMin={SCORE_BULLET_NEUTRAL_MIN}
            neutralMax={SCORE_BULLET_NEUTRAL_MAX}
            domain={SCORE_BULLET_DOMAIN}
            ciLow={scoreStats.ciLow}
            ciHigh={scoreStats.ciHigh}
            barColor="neutral"
            ariaLabel={`Score ${Math.round(derivedScore * 100)}% vs 50% baseline`}
          />
        </div>
      </div>

      {/* Eval row — gated on Tier 2 (eval analysis complete).
          When !tier2, the pulsating-Cpu placeholder (col-span-2) replaces the
          entire eval row. The WDL score row above is not eval-dependent. */}
      {tier2 ? (
        <div className="flex flex-col gap-1 sm:contents">
          <span
            className="flex items-center gap-1 text-sm tabular-nums w-full sm:col-start-2 sm:row-start-2"
            data-testid={`${cardTestId}-eval-text`}
            style={dimEvalRow ? { opacity: UNRELIABLE_OPACITY } : undefined}
          >
            <span className="text-muted-foreground">End Eval:</span>
            <span className="ml-auto inline-flex items-center gap-1">{mgEvalTextContent}</span>
            {hasMgEval && (
              <BulletConfidencePopover
                level={opening.eval_confidence}
                pValue={opening.eval_p_value}
                gameCount={opening.eval_n}
                evalMeanPawns={opening.avg_eval_pawns}
                color={color}
                testId={`${cardTestId}-bullet-popover`}
              />
            )}
          </span>
          <div
            className="min-w-0 tabular-nums sm:col-start-1 sm:row-start-2"
            data-testid={`${cardTestId}-bullet`}
            style={dimEvalRow ? { opacity: UNRELIABLE_OPACITY } : undefined}
          >
            {mgBulletContent}
          </div>
        </div>
      ) : (
        <EvalCpuPlaceholder />
      )}
    </div>
  );

  const linksRow = (
    <div className="flex items-center gap-4">
      <Tooltip content={`Open ${opening.display_name} in the Move Explorer`}>
        <button
          type="button"
          className="flex items-center gap-1 text-sm text-brand-brown-light hover:text-brand-brown-highlight transition-colors"
          aria-label={`Open ${opening.display_name} in the Move Explorer`}
          data-testid={`${cardTestId}-moves`}
          onClick={() => onOpenMoves(opening, color)}
        >
          <ArrowRightLeft className="h-3.5 w-3.5" />
          <span>Moves</span>
        </button>
      </Tooltip>
      <Tooltip content={`View ${opening.total} games for ${opening.opening_name}`}>
        <button
          type="button"
          className="flex items-center gap-1 text-sm text-brand-brown-light hover:text-brand-brown-highlight transition-colors"
          aria-label={`View ${opening.total} games for ${opening.opening_name}`}
          data-testid={`${cardTestId}-games`}
          onClick={() => onOpenGames(opening, color)}
        >
          <Swords className="h-3.5 w-3.5" />
          <span className="tabular-nums">{opening.total}</span>
          <span>Games</span>
        </button>
      </Tooltip>
    </div>
  );

  return (
    <div
      data-testid={cardTestId}
      className={`relative charcoal-texture border border-border/20 rounded-md overflow-hidden${
        isReliableScore ? ' border-l-4' : ''
      }`}
      style={rootStyle}
    >
      <h4
        className="flex items-center gap-2 px-4 py-2 bg-black/20 border-b border-border/40 text-sm font-semibold"
        data-testid={`${cardTestId}-header`}
      >
        <span className="truncate text-foreground min-w-0">
          {opening.display_name}
          {opening.opening_eco && (
            <span className="ml-1 text-muted-foreground font-normal">({opening.opening_eco})</span>
          )}
        </span>
      </h4>

      <div
        data-testid={`${cardTestId}-content`}
        className="px-4 py-4"
      >
        {/* Mobile: WDL bar full-width on top, then board left + content right */}
        <div className="flex flex-col gap-2 sm:hidden">
          {wdlLine}
          <div className="flex gap-3 items-start">
            <LazyMiniBoard
              fen={opening.fen}
              flipped={color === 'black'}
              size={MOBILE_BOARD_SIZE}
            />
            <div className="flex-1 min-w-0 flex flex-col gap-2">
              {scoreEvalBlock}
              {linksRow}
            </div>
          </div>
        </div>

        {/* Desktop: board left, content right (header lives above on both) */}
        <div className="hidden sm:flex gap-3 items-center">
          <LazyMiniBoard
            fen={opening.fen}
            flipped={color === 'black'}
            size={DESKTOP_BOARD_SIZE}
          />
          <div className="min-w-0 flex-1 flex flex-col gap-2">
            {wdlLine}
            {scoreEvalBlock}
            {linksRow}
          </div>
        </div>
      </div>
    </div>
  );
}
