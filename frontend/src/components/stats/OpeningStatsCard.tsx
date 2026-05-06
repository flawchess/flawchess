import { ArrowRightLeft, Swords } from 'lucide-react';
import type { OpeningWDL } from '@/types/stats';
import { LazyMiniBoard } from '@/components/board/LazyMiniBoard';
import { WDLChartRow } from '@/components/charts/WDLChartRow';
import { MiniBulletChart } from '@/components/charts/MiniBulletChart';
import { Tooltip } from '@/components/ui/tooltip';
import { BulletConfidencePopover } from '@/components/insights/BulletConfidencePopover';
import {
  EVAL_BULLET_DOMAIN_PAWNS,
  EVAL_NEUTRAL_MAX_PAWNS,
  EVAL_NEUTRAL_MIN_PAWNS,
  evalZoneColor,
} from '@/lib/openingStatsZones';
import { formatSignedEvalPawns } from '@/lib/clockFormat';
import { MIN_GAMES_OPENING_ROW, UNRELIABLE_OPACITY } from '@/lib/theme';

// Match OpeningFindingCard sizing so the Stats subtab matches Insights visually.
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
  const cardTestId = `${testIdPrefix}-${idx}`;

  // Mute the whole card when total games are below the opening-row threshold,
  // matching the previous MostPlayedOpeningsTable behavior so sparse rows can't
  // sustain a reliable MG-entry eval signal.
  const isCardMuted = opening.total < MIN_GAMES_OPENING_ROW;

  const hasMgEval =
    opening.eval_n > 0 &&
    opening.avg_eval_pawns !== null &&
    opening.avg_eval_pawns !== undefined;

  // Border color uses the MG-entry zone (engine-balanced anchor) to convey the
  // card's primary signal at a glance. When eval data is missing we use a
  // transparent border so the border-l-4 still reserves space without shouting
  // a misleading color (260504-rvh / Phase 80 stays anchored on 0 cp).
  const borderLeftColor = hasMgEval ? evalZoneColor(opening.avg_eval_pawns as number) : 'transparent';

  const cardStyle: React.CSSProperties = {
    borderLeftColor,
    ...(isCardMuted ? { opacity: UNRELIABLE_OPACITY } : {}),
  };

  // Phase 80 MG eval text — signed pawns to one decimal (e.g. "+2.1"), zone color
  // anchored at 0 cp. Mirrors MostPlayedOpeningsTable lines 78-87.
  const mgEvalTextContent = hasMgEval ? (
    <span
      className="font-semibold"
      style={{ color: evalZoneColor(opening.avg_eval_pawns as number) }}
    >
      {formatSignedEvalPawns(opening.avg_eval_pawns as number)}
    </span>
  ) : (
    <span className="text-muted-foreground">—</span>
  );

  // MG bullet chart, anchored on 0 cp; per-color baseline rendered as a small tick.
  const mgBulletContent = hasMgEval ? (
    <MiniBulletChart
      value={opening.avg_eval_pawns as number}
      ciLow={opening.eval_ci_low_pawns ?? undefined}
      ciHigh={opening.eval_ci_high_pawns ?? undefined}
      tickPawns={evalBaselinePawns}
      neutralMin={EVAL_NEUTRAL_MIN_PAWNS}
      neutralMax={EVAL_NEUTRAL_MAX_PAWNS}
      domain={EVAL_BULLET_DOMAIN_PAWNS}
      ariaLabel={`Avg eval at MG entry: ${(opening.avg_eval_pawns as number).toFixed(2)} pawns`}
    />
  ) : (
    <span className="text-muted-foreground">—</span>
  );

  const headerLine = (
    <div className="flex items-center gap-2 text-sm min-w-0">
      <span className="truncate text-foreground font-medium min-w-0">
        {/* display_name carries the "vs. " prefix for off-color rows (PRE-01). */}
        {opening.display_name}
        {opening.opening_eco && (
          <span className="ml-1 text-muted-foreground">({opening.opening_eco})</span>
        )}
      </span>
    </div>
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
            level={opening.eval_confidence}
            pValue={opening.eval_p_value}
            gameCount={opening.eval_n}
            evalMeanPawns={opening.avg_eval_pawns}
            color={color}
            testId={`${cardTestId}-bullet-popover`}
          />
        )}
      </span>
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
      className="block relative border-l-4 charcoal-texture border border-border/20 rounded px-4 py-4"
      style={cardStyle}
    >
      {/* Mobile: header full-width on top, board + content row below */}
      <div className="flex flex-col gap-2 sm:hidden">
        {headerLine}
        <div className="flex gap-3 items-start">
          <LazyMiniBoard
            fen={opening.fen}
            flipped={color === 'black'}
            size={MOBILE_BOARD_SIZE}
          />
          <div className="flex-1 min-w-0 flex flex-col gap-2">
            {wdlLine}
            {evalLine}
            {linksRow}
          </div>
        </div>
      </div>

      {/* Desktop: board left, header + content stacked right */}
      <div className="hidden sm:flex gap-3 items-center">
        <LazyMiniBoard
          fen={opening.fen}
          flipped={color === 'black'}
          size={DESKTOP_BOARD_SIZE}
        />
        <div className="min-w-0 flex-1 flex flex-col gap-2">
          {headerLine}
          {wdlLine}
          {evalLine}
          {linksRow}
        </div>
      </div>
    </div>
  );
}
