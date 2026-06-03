import { ArrowRightLeft, Cpu, Swords } from 'lucide-react';
import { LazyMiniBoard } from '@/components/board/LazyMiniBoard';
import { WDLChartRow } from '@/components/charts/WDLChartRow';
import { MiniBulletChart } from '@/components/charts/MiniBulletChart';
import { Tooltip } from '@/components/ui/tooltip';
import { BulletConfidencePopover } from '@/components/insights/BulletConfidencePopover';
import { ScoreConfidencePopover } from '@/components/insights/ScoreConfidencePopover';
import { EvalCpuPlaceholder } from '@/components/stats/EvalCpuPlaceholder';
import { useReadiness } from '@/hooks/useReadiness';
import { formatCandidateMove } from '@/lib/openingInsights';
import { sanToSquares } from '@/lib/sanToSquares';
import {
  EVAL_BULLET_DOMAIN_PAWNS,
  EVAL_NEUTRAL_MAX_PAWNS,
  EVAL_NEUTRAL_MIN_PAWNS,
  evalZoneColor,
} from '@/lib/openingStatsZones';
import { formatSignedEvalPawns } from '@/lib/clockFormat';
import {
  SCORE_BULLET_CENTER,
  SCORE_BULLET_NEUTRAL_MIN,
  SCORE_BULLET_NEUTRAL_MAX,
  SCORE_BULLET_DOMAIN,
  clampScoreCi,
  scoreZoneColor,
} from '@/lib/scoreBulletConfig';
import { isConfident } from '@/lib/significance';
import { UNRELIABLE_OPACITY, ZONE_NEUTRAL } from '@/lib/theme';
import type { OpeningInsightFinding } from '@/types/insights';

const MOBILE_BOARD_SIZE = 115;
const DESKTOP_BOARD_SIZE = 110;
const UNNAMED_SENTINEL = '<unnamed line>';

export function OpeningFindingCard({
  finding,
  idx,
  evalBaselinePawns,
  onFindingClick,
  onOpenGames,
}: {
  finding: OpeningInsightFinding;
  idx: number;
  evalBaselinePawns: number;
  onFindingClick: (finding: OpeningInsightFinding) => void;
  onOpenGames: (finding: OpeningInsightFinding) => void;
}) {
  const { tier2 } = useReadiness();
  const candidateMoveDisplay = formatCandidateMove(
    finding.entry_san_sequence,
    finding.candidate_move_san,
  );
  // Border + arrow + score-percent text all draw from the shared score-zone
  // palette used by the Moves-tab Score column: dark red <= 45%, dark green
  // >= 55%, neutral blue in between. One source of truth across both surfaces.
  const borderLeftColor = scoreZoneColor(finding.score);
  // Quick-task 260429-gmj: render a fine score-colored arrow on the mini board
  // pointing from the candidate move's source to its target square. Same color
  // as the border so the visuals stay in lockstep. Illegal/unparseable SAN
  // returns null and the card simply falls back to no arrow.
  const moveSquares = sanToSquares(finding.entry_fen, finding.candidate_move_san);
  const arrows = moveSquares
    ? ([{ from: moveSquares.from, to: moveSquares.to, color: borderLeftColor }] as const)
    : undefined;
  const isUnnamed = finding.opening_name === UNNAMED_SENTINEL;

  // Full-height left spine: the score-zone accent runs the entire left edge of
  // the card (header band included). It lives on the card root, not the content
  // div — the old content-div border started the colored stripe abruptly under
  // the header band, leaving the rounded top-left corner un-accented.
  // Per-row dimming (260603-pgv): the whole-card opacity dim was removed; each
  // stat row now dims independently (see dimScoreRow / dimEvalRow below).
  const rootStyle: React.CSSProperties = {
    borderLeftColor,
  };

  const cardTestId = `opening-finding-card-${idx}`;

  // WDL bar — same pattern as OpeningStatsCard.tsx.
  // Compute pcts inline, guarding div-by-zero.
  const nGames = finding.n_games;
  const wdlData = {
    wins: finding.wins,
    draws: finding.draws,
    losses: finding.losses,
    total: nGames,
    win_pct: nGames > 0 ? Math.round(finding.wins / nGames * 100 * 10) / 10 : 0,
    draw_pct: nGames > 0 ? Math.round(finding.draws / nGames * 100 * 10) / 10 : 0,
    loss_pct: nGames > 0 ? Math.round(finding.losses / nGames * 100 * 10) / 10 : 0,
  };

  const wdlLine = (
    <WDLChartRow
      data={wdlData}
      showSegmentCounts={false}
      testId={`${cardTestId}-wdl`}
    />
  );

  // Score whiskers come from the finding's Wilson CI (backend).
  const ciLow = clampScoreCi(finding.ci_low);
  const ciHigh = clampScoreCi(finding.ci_high);

  // MG-entry eval bullet — structurally identical to OpeningStatsCard.
  const evalN = finding.eval_n ?? 0;
  const avgEvalPawns = finding.avg_eval_pawns ?? null;
  const hasMgEval = evalN > 0 && avgEvalPawns !== null && avgEvalPawns !== undefined;

  // Quick task 260508-dcp: gate Score % and Eval text on confidence bucket
  // ('medium' or 'high', not 'low') AND value lands in a colored zone
  // (red/green). The card border + on-board arrow keep their existing zone
  // tint — only the font colors are gated here.
  const scoreZoneHex = scoreZoneColor(finding.score);
  const showScoreZoneFont =
    isConfident(finding.confidence) && scoreZoneHex !== ZONE_NEUTRAL;

  const evalZoneHex = hasMgEval ? evalZoneColor(avgEvalPawns as number) : null;
  const showEvalZoneFont =
    hasMgEval &&
    isConfident(finding.eval_confidence) &&
    evalZoneHex !== ZONE_NEUTRAL;

  // Per-row dimming (260603-pgv): fade only the stat row whose confidence is
  // low, instead of the whole card. Eval dims only when an eval value exists
  // (the placeholder / no-eval "—" cases are never dimmed).
  const dimScoreRow = !isConfident(finding.confidence);
  const dimEvalRow = hasMgEval && !isConfident(finding.eval_confidence);

  const mgEvalTextContent = hasMgEval ? (
    <span
      className="font-semibold inline-flex items-center gap-0.3"
      style={showEvalZoneFont && evalZoneHex ? { color: evalZoneHex } : undefined}
    >
      {formatSignedEvalPawns(avgEvalPawns as number)}
      <Cpu className="h-3.5 w-3.5" aria-hidden="true" />
    </span>
  ) : (
    <span className="text-muted-foreground">—</span>
  );

  const mgBulletContent = hasMgEval ? (
    <MiniBulletChart
      value={avgEvalPawns as number}
      ciLow={finding.eval_ci_low_pawns ?? undefined}
      ciHigh={finding.eval_ci_high_pawns ?? undefined}
      tickPawns={evalBaselinePawns}
      neutralMin={EVAL_NEUTRAL_MIN_PAWNS}
      neutralMax={EVAL_NEUTRAL_MAX_PAWNS}
      domain={EVAL_BULLET_DOMAIN_PAWNS}
      barColor="neutral"
      ariaLabel={`Avg eval at MG entry: ${(avgEvalPawns as number).toFixed(2)} pawns`}
    />
  ) : (
    <span className="text-muted-foreground">—</span>
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
      <div className="flex flex-col gap-0.5 sm:contents">
        <span
          className="flex items-center gap-1 text-sm tabular-nums w-full sm:col-start-2 sm:row-start-1"
          data-testid={`${cardTestId}-score-text`}
          style={dimScoreRow ? { opacity: UNRELIABLE_OPACITY } : undefined}
        >
          <span className="text-xs sm:text-sm text-muted-foreground">Score:</span>
          <span className="ml-auto font-semibold" style={showScoreZoneFont ? { color: scoreZoneHex } : undefined}>
            {Math.round(finding.score * 100)}%
          </span>
          <ScoreConfidencePopover
            level={finding.confidence}
            pValue={finding.p_value ?? 1}
            score={finding.score}
            gameCount={finding.n_games}
            lastPlayedAt={finding.last_played_at}
            testId={`${cardTestId}-score-popover`}
          />
        </span>
        <div
          className="min-w-0 tabular-nums sm:col-start-1 sm:row-start-1"
          data-testid={`${cardTestId}-score-bullet`}
          style={dimScoreRow ? { opacity: UNRELIABLE_OPACITY } : undefined}
        >
          <MiniBulletChart
            value={finding.score}
            center={SCORE_BULLET_CENTER}
            neutralMin={SCORE_BULLET_NEUTRAL_MIN}
            neutralMax={SCORE_BULLET_NEUTRAL_MAX}
            domain={SCORE_BULLET_DOMAIN}
            ciLow={ciLow}
            ciHigh={ciHigh}
            barColor="neutral"
            ariaLabel={`Score ${Math.round(finding.score * 100)}% vs 50% baseline`}
          />
        </div>
      </div>

      {/* Eval row — gated on Tier 2 (eval analysis complete). When !tier2 the
          pulsating-Cpu placeholder (col-span-2) replaces the entire eval row,
          matching OpeningStatsCard. The WDL score row is not eval-dependent. */}
      {tier2 ? (
        <div className="flex flex-col gap-0.5 sm:contents">
          <span
            className="flex items-center gap-1 text-sm tabular-nums w-full sm:col-start-2 sm:row-start-2"
            data-testid={`${cardTestId}-eval-text`}
            style={dimEvalRow ? { opacity: UNRELIABLE_OPACITY } : undefined}
          >
            <span className="text-xs sm:text-sm text-muted-foreground">End Eval:</span>
            <span className="ml-auto inline-flex items-center gap-1">{mgEvalTextContent}</span>
            {hasMgEval && (
              <BulletConfidencePopover
                level={finding.eval_confidence ?? 'low'}
                pValue={finding.eval_p_value}
                gameCount={evalN}
                evalMeanPawns={avgEvalPawns}
                color={finding.color}
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
      <span className="hidden sm:inline text-sm text-muted-foreground">
        after{' '}
        <span className="font-mono text-foreground">{candidateMoveDisplay}</span>
      </span>
      <Tooltip content={`Open ${finding.display_name} in the Move Explorer`}>
        <button
          type="button"
          className="flex items-center gap-1 text-sm text-brand-brown-light hover:text-brand-brown-highlight transition-colors"
          aria-label={`Open ${finding.display_name} in the Move Explorer`}
          data-testid={`${cardTestId}-moves`}
          onClick={() => onFindingClick(finding)}
        >
          <ArrowRightLeft className="h-3.5 w-3.5" />
          <span>Moves</span>
        </button>
      </Tooltip>
      <Tooltip content={`View ${finding.n_games} games for ${finding.opening_name}`}>
        <button
          type="button"
          className="flex items-center gap-1 text-sm text-brand-brown-light hover:text-brand-brown-highlight transition-colors"
          aria-label={`View ${finding.n_games} games for ${finding.opening_name}`}
          data-testid={`${cardTestId}-games`}
          onClick={() => onOpenGames(finding)}
        >
          <Swords className="h-3.5 w-3.5" />
          <span className="tabular-nums">{finding.n_games}</span>
          <span>Games</span>
        </button>
      </Tooltip>
    </div>
  );

  // Mobile move-anchor caption — sits directly under the miniboard so the
  // visual + textual move anchor read as a single unit. On desktop the move
  // anchor lives at the left of the Moves/Games row (rendered inside linksRow
  // with `hidden sm:inline`), reclaiming the under-board caption row for the
  // bullet stack.
  const moveCaption = (
    <span className="text-sm text-muted-foreground">
      after{' '}
      <span className="font-mono text-foreground">{candidateMoveDisplay}</span>
    </span>
  );

  return (
    <div
      data-testid={cardTestId}
      className="relative charcoal-texture border border-border/20 border-l-4 rounded-md overflow-hidden"
      style={rootStyle}
    >
      <h4
        className="flex items-center gap-2 px-4 py-2 bg-black/20 border-b border-border/40 text-sm font-semibold"
        data-testid={`${cardTestId}-header`}
      >
        <span className="truncate text-foreground min-w-0">
          {isUnnamed ? (
            <span className="italic text-muted-foreground font-normal">{finding.display_name}</span>
          ) : (
            finding.display_name
          )}
          {finding.opening_eco && (
            <span className="ml-1 text-muted-foreground font-normal">({finding.opening_eco})</span>
          )}
        </span>
      </h4>

      <div
        data-testid={`${cardTestId}-content`}
        className="px-4 py-4"
      >
        {/* Mobile: board + caption left, content right */}
        <div className="flex flex-col gap-2 sm:hidden">
          <div className="flex gap-3 items-start">
            <div className="flex flex-col items-end gap-1">
              <LazyMiniBoard
                fen={finding.entry_fen}
                flipped={finding.color === 'black'}
                size={MOBILE_BOARD_SIZE}
                arrows={arrows}
              />
              {moveCaption}
            </div>
            <div className="flex-1 min-w-0 flex flex-col gap-2">
              {wdlLine}
              {scoreEvalBlock}
              {linksRow}
            </div>
          </div>
        </div>

        {/* Desktop: board left, content stacked right (header above on both).
            Move anchor lives in linksRow (left of Moves/Games), not under the
            board, so the bullet rows can sit closer to the miniboard. */}
        <div className="hidden sm:flex gap-3 items-start">
          <div className="flex flex-col items-end gap-1">
            <LazyMiniBoard
              fen={finding.entry_fen}
              flipped={finding.color === 'black'}
              size={DESKTOP_BOARD_SIZE}
              arrows={arrows}
            />
          </div>
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
