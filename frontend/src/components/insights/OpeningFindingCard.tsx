import { ArrowRightLeft, Swords } from 'lucide-react';
import { LazyMiniBoard } from '@/components/board/LazyMiniBoard';
import { WDLChartRow } from '@/components/charts/WDLChartRow';
import { MiniBulletChart } from '@/components/charts/MiniBulletChart';
import { Tooltip } from '@/components/ui/tooltip';
import { BulletConfidencePopover } from '@/components/insights/BulletConfidencePopover';
import { formatCandidateMove } from '@/lib/openingInsights';
import { fenAfterMove, sanToSquares } from '@/lib/sanToSquares';
import {
  EVAL_BULLET_DOMAIN_PAWNS,
  EVAL_NEUTRAL_MAX_PAWNS,
  EVAL_NEUTRAL_MIN_PAWNS,
  evalZoneColor,
} from '@/lib/openingStatsZones';
import { formatSignedEvalPawns } from '@/lib/clockFormat';
import {
  scoreZoneColor,
} from '@/lib/scoreBulletConfig';
import { MIN_GAMES_FOR_RELIABLE_STATS, TROLL_WATERMARK_OPACITY, UNRELIABLE_OPACITY } from '@/lib/theme';
import { isTrollPosition } from '@/lib/trollOpenings';
import trollFaceUrl from '@/assets/troll-face.svg';
import type { OpeningInsightFinding } from '@/types/insights';

interface OpeningFindingCardProps {
  finding: OpeningInsightFinding;
  idx: number;
  /** Per-color engine-asymmetry baseline (in pawns). Rendered as reference tick on eval bullet chart. */
  evalBaselinePawns: number;
  onFindingClick: (finding: OpeningInsightFinding) => void;
  onOpenGames: (finding: OpeningInsightFinding) => void;
}

const MOBILE_BOARD_SIZE = 115;
const DESKTOP_BOARD_SIZE = 110;
const UNNAMED_SENTINEL = '<unnamed line>';

export function OpeningFindingCard({
  finding,
  idx,
  evalBaselinePawns,
  onFindingClick,
  onOpenGames,
}: OpeningFindingCardProps) {
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

  // D-02: Abbreviated prose — "Score <X>% after <candidate_move>".
  // Edge case: if rounding to integer would show 50% but classification implies otherwise,
  // fall back to one decimal place to avoid contradicting the section title.
  const rawPercent = finding.score * 100;
  const wouldContradict =
    (finding.classification === 'weakness' && Math.round(rawPercent) >= 50) ||
    (finding.classification === 'strength' && Math.round(rawPercent) <= 50);
  const scoreDisplay = wouldContradict ? rawPercent.toFixed(1) : Math.round(rawPercent).toString();

  // D-11: Apply UNRELIABLE_OPACITY when n_games < 10 OR confidence is low.
  const isUnreliable =
    finding.n_games < MIN_GAMES_FOR_RELIABLE_STATS || finding.confidence === 'low';
  const cardStyle: React.CSSProperties = {
    borderLeftColor,
    ...(isUnreliable ? { opacity: UNRELIABLE_OPACITY } : {}),
  };

  // Phase 77 D-02/D-10: Show troll-face watermark when the entry position OR the
  // post-candidate-move position matches a curated troll line. Pure O(1) Set.has
  // lookups after a tiny string transform — no useMemo needed. fenAfterMove()
  // returns null on illegal SAN / malformed FEN, which isTrollPosition treats as
  // a non-match, so the second branch degrades safely.
  const resultingFen = fenAfterMove(finding.entry_fen, finding.candidate_move_san);
  const showTroll =
    isTrollPosition(finding.entry_fen, finding.color) ||
    (resultingFen !== null && isTrollPosition(resultingFen, finding.color));

  const cardTestId = `opening-finding-card-${idx}`;

  const headerLine = (
    <div className="flex items-center gap-2 text-sm min-w-0">
      <span className="truncate text-foreground font-medium min-w-0">
        {isUnnamed ? (
          <span className="italic text-muted-foreground">{finding.display_name}</span>
        ) : (
          finding.display_name
        )}
        {finding.opening_eco && (
          <span className="ml-1 text-muted-foreground">({finding.opening_eco})</span>
        )}
      </span>
    </div>
  );

  // Abbreviated prose: "Score <X>% after <move>" — no "You score X% as <Color>".
  // Section title carries the polarity; score-zone tint conveys direction visually.
  const proseLine = (
    <p className="text-sm text-muted-foreground">
      Score{' '}
      <span style={{ color: borderLeftColor }} className="font-semibold">
        {scoreDisplay}%
      </span>{' '}
      after{' '}
      <span className="font-mono text-foreground">{candidateMoveDisplay}</span>
    </p>
  );

  // WDL bar — same pattern as OpeningStatsCard.tsx lines 109-125.
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

  // MG-entry eval line — structurally identical to OpeningStatsCard.tsx lines 127-152.
  const evalN = finding.eval_n ?? 0;
  const avgEvalPawns = finding.avg_eval_pawns ?? null;
  const hasMgEval = evalN > 0 && avgEvalPawns !== null && avgEvalPawns !== undefined;

  const mgEvalTextContent = hasMgEval ? (
    <span
      className="font-semibold"
      style={{ color: evalZoneColor(avgEvalPawns as number) }}
    >
      {formatSignedEvalPawns(avgEvalPawns as number)}
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
      ariaLabel={`Avg eval at MG entry: ${(avgEvalPawns as number).toFixed(2)} pawns`}
    />
  ) : (
    <span className="text-muted-foreground">—</span>
  );

  const evalLine = (
    <div className="flex items-center gap-2">
      <div
        className="flex-1 min-w-0 tabular-nums"
        data-testid={`${cardTestId}-bullet`}
      >
        {mgBulletContent}
      </div>
      <span
        className="inline-flex items-center gap-1 text-sm tabular-nums"
        data-testid={`${cardTestId}-eval-text`}
      >
        {mgEvalTextContent}
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
    </div>
  );

  const linksRow = (
    <div className="flex items-center gap-4">
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

  return (
    <div
      data-testid={cardTestId}
      className="block relative border-l-4 charcoal-texture border border-border/20 rounded px-4 py-4"
      style={cardStyle}
    >
      {/* Mobile: header full-width on top, board + prose/links row below */}
      <div className="flex flex-col gap-2 sm:hidden">
        {headerLine}
        <div className="flex gap-3 items-start">
          <LazyMiniBoard
            fen={finding.entry_fen}
            flipped={finding.color === 'black'}
            size={MOBILE_BOARD_SIZE}
            arrows={arrows}
          />
          <div className="flex-1 min-w-0 flex flex-col gap-2">
            {proseLine}
            {wdlLine}
            {evalLine}
            {linksRow}
          </div>
        </div>
      </div>

      {/* Desktop: board left, header + prose + links stacked right */}
      <div className="hidden sm:flex gap-3 items-center">
        <LazyMiniBoard
          fen={finding.entry_fen}
          flipped={finding.color === 'black'}
          size={DESKTOP_BOARD_SIZE}
          arrows={arrows}
        />
        <div className="min-w-0 flex-1 flex flex-col gap-2">
          {headerLine}
          {proseLine}
          {wdlLine}
          {evalLine}
          {linksRow}
        </div>
      </div>

      {/* Phase 77 D-02/D-03/D-04/D-05: Troll-opening watermark. Single sibling positioned
          absolute bottom-right covers both mobile and desktop layouts. pointer-events-none
          so the Moves/Games buttons remain clickable. Decorative — alt="" + aria-hidden. */}
      {showTroll && (
        <img
          src={trollFaceUrl}
          alt=""
          aria-hidden="true"
          data-testid={`${cardTestId}-troll-watermark`}
          className="hidden sm:block absolute right-3 top-1/2 -translate-y-1/2 sm:h-[100px] w-auto pointer-events-none select-none"
          style={{ opacity: TROLL_WATERMARK_OPACITY }}
        />
      )}
    </div>
  );
}
