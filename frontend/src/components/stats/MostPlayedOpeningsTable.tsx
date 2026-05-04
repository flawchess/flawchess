import * as React from "react"
import { Swords, ChevronDown, ChevronUp } from "lucide-react"
import type { OpeningWDL } from "@/types/stats"
import { MinimapPopover } from "./MinimapPopover"
import { MiniWDLBar } from "./MiniWDLBar"
import { Tooltip } from "@/components/ui/tooltip"
import { MiniBulletChart } from "@/components/charts/MiniBulletChart"
import { BulletConfidencePopover } from "@/components/insights/BulletConfidencePopover"
import {
  EVAL_BULLET_DOMAIN_PAWNS,
  EVAL_NEUTRAL_MAX_PAWNS,
  EVAL_NEUTRAL_MIN_PAWNS,
} from "@/lib/openingStatsZones"
import { formatSignedEvalPawns } from "@/lib/clockFormat"
import {
  MIN_GAMES_OPENING_ROW,
  UNRELIABLE_OPACITY,
  ZONE_DANGER,
  ZONE_NEUTRAL,
  ZONE_SUCCESS,
} from "@/lib/theme"

function evalZoneColor(value: number): string {
  if (value >= EVAL_NEUTRAL_MAX_PAWNS) return ZONE_SUCCESS;
  if (value >= EVAL_NEUTRAL_MIN_PAWNS) return ZONE_NEUTRAL;
  return ZONE_DANGER;
}

// Number of openings to show before the "More" fold
const INITIAL_VISIBLE_COUNT = 3;

// Phase 80 D-10: column-header tooltip strings.
// MG-entry MUST cite "across analyzed games" because Lichess analyzes only ~66%
// of imported games (bench §3 line 350-355).
export const MG_EVAL_HEADER_TOOLTIP =
  "Average Stockfish evaluation at the transition from opening to middlegame, signed from your perspective. " +
  "The evaluation is computed during game import at depth 15. The statistical test tells you how likely the " +
  "difference from 0 is due to random chance.";

interface MostPlayedOpeningsTableProps {
  openings: OpeningWDL[];
  color: "white" | "black";
  testIdPrefix: string;
  /** Called when user clicks the games link on a row. Receives the full opening object so callers can route on any field. */
  onOpenGames: (opening: OpeningWDL, color: "white" | "black") => void;
  /** When true, render every opening without the collapsible "X more" fold. */
  showAll?: boolean;
}

/** Format opening name: split on ": " — line break only on mobile. */
function formatName(name: string): React.ReactNode {
  const parts = name.split(": ");
  if (parts.length > 1) {
    return (
      <>
        <span className="font-medium">{parts[0]}:</span>
        {/* Line break on mobile only, space on desktop */}
        <br className="sm:hidden" />
        <span className="hidden sm:inline"> </span>
        <span>{parts.slice(1).join(": ")}</span>
      </>
    );
  }
  return <span className="font-medium">{name}</span>;
}

function OpeningRow({ o, color, index, testIdPrefix, rowKey, onOpenGames }: {
  o: OpeningWDL;
  color: "white" | "black";
  index: number;
  testIdPrefix: string;
  rowKey: string;
  onOpenGames: (opening: OpeningWDL, color: "white" | "black") => void;
}) {
  const isEvenRow = index % 2 === 0;

  // Mute the whole row when total games are below the opening-row threshold —
  // anything sparser can't sustain a reliable MG-entry eval signal.
  const isRowMuted = o.total < MIN_GAMES_OPENING_ROW;

  const hasMgEval =
    o.eval_n > 0 && o.avg_eval_pawns !== null && o.avg_eval_pawns !== undefined;

  // Phase 80: MG eval text cell — signed pawns to one decimal (e.g. "+2.1").
  const mgEvalTextContent = hasMgEval ? (
    <span
      className="font-semibold"
      style={{ color: evalZoneColor(o.avg_eval_pawns as number) }}
    >
      {formatSignedEvalPawns(o.avg_eval_pawns as number)}
    </span>
  ) : (
    <span className="text-muted-foreground">—</span>
  );

  // Phase 80: MG bullet chart cell.
  const mgBulletContent = hasMgEval ? (
    <MiniBulletChart
      value={o.avg_eval_pawns as number}
      ciLow={o.eval_ci_low_pawns ?? undefined}
      ciHigh={o.eval_ci_high_pawns ?? undefined}
      neutralMin={EVAL_NEUTRAL_MIN_PAWNS}
      neutralMax={EVAL_NEUTRAL_MAX_PAWNS}
      domain={EVAL_BULLET_DOMAIN_PAWNS}
      ariaLabel={`Avg eval at MG entry: ${(o.avg_eval_pawns as number).toFixed(2)} pawns`}
    />
  ) : (
    <span className="text-muted-foreground">—</span>
  );

  return (
    <div
      data-testid={`${testIdPrefix}-row-${rowKey}`}
      style={isRowMuted ? { opacity: UNRELIABLE_OPACITY } : undefined}
    >
      {/* Desktop row: 5-column grid (name | games | WDL | eval text | eval bullet) */}
      <div
        className={`grid grid-cols-[1fr_auto_minmax(80px,140px)] sm:grid-cols-[minmax(0,1fr)_auto_minmax(120px,200px)_auto_minmax(100px,160px)] gap-2 items-center rounded px-2 py-1.5 hover:bg-white/5 transition-colors ${isEvenRow ? 'bg-white/[0.02]' : ''}`}
      >
        {/* Column 1: Name + PGN */}
        <MinimapPopover
          fen={o.fen}
          boardOrientation={color}
          testId={`${testIdPrefix}-minimap-${rowKey}`}
        >
          <div className="min-w-0">
            <div className="text-sm leading-tight">
              {/* display_name carries a "vs. " prefix when the opening is defined by the off-color (PRE-01). */}
              {formatName(o.display_name)}
            </div>
            {o.pgn && (
              <div className="text-xs text-muted-foreground mt-0.5 break-words sm:truncate">{o.pgn}</div>
            )}
          </div>
        </MinimapPopover>

        {/* Column 2: Game count with link to games tab */}
        <Tooltip content={`View ${o.total} games for ${o.opening_name}`}>
          <button
            className="flex items-center justify-end gap-1 text-sm text-brand-brown-light hover:text-brand-brown-highlight transition-colors justify-self-end"
            aria-label={`View ${o.total} games for ${o.opening_name}`}
            data-testid={`${testIdPrefix}-games-${rowKey}`}
            onClick={() => onOpenGames(o, color)}
          >
            <span className="tabular-nums">{o.total}</span>
            <Swords className="h-3.5 w-3.5" />
          </button>
        </Tooltip>

        {/* Column 3: Mini WDL bar */}
        <div>
          <MiniWDLBar win_pct={o.win_pct} draw_pct={o.draw_pct} loss_pct={o.loss_pct} />
        </div>

        {/* Column 4: MG eval text (desktop only) */}
        <div
          className="hidden sm:block text-right text-sm tabular-nums sm:pl-4"
          data-testid={`${testIdPrefix}-eval-text-${rowKey}`}
        >
          {mgEvalTextContent}
        </div>

        {/* Column 5: MG bullet chart + info-icon popover trigger (desktop only) */}
        <div
          className="hidden sm:flex items-center gap-2 tabular-nums"
          data-testid={`${testIdPrefix}-bullet-${rowKey}`}
        >
          <div className="flex-1 min-w-0">{mgBulletContent}</div>
          {hasMgEval && (
            <BulletConfidencePopover
              level={o.eval_confidence}
              pValue={o.eval_p_value}
              gameCount={o.eval_n}
              evalMeanPawns={o.avg_eval_pawns}
              evalCiLowPawns={o.eval_ci_low_pawns}
              evalCiHighPawns={o.eval_ci_high_pawns}
              testId={`${testIdPrefix}-bullet-popover-${rowKey}`}
              prefaceText={MG_EVAL_HEADER_TOOLTIP}
            />
          )}
        </div>
      </div>
    </div>
  );
}

export function MostPlayedOpeningsTable({ openings, color, testIdPrefix, onOpenGames, showAll = false }: MostPlayedOpeningsTableProps) {
  const [expanded, setExpanded] = React.useState(false);

  if (openings.length === 0) return null;

  const visibleOpenings = showAll || expanded ? openings : openings.slice(0, INITIAL_VISIBLE_COUNT);
  const hiddenCount = openings.length - INITIAL_VISIBLE_COUNT;
  const hasMore = !showAll && hiddenCount > 0;

  return (
    <div data-testid={`${testIdPrefix}-table`}>
      {/* Table header — desktop shows 5 columns, mobile shows 3 */}
      <div className="grid grid-cols-[1fr_auto_minmax(80px,140px)] sm:grid-cols-[minmax(0,1fr)_auto_minmax(120px,200px)_auto_minmax(100px,160px)] gap-2 px-2 pb-1 text-xs text-muted-foreground border-b border-white/10 mb-1">
        <span>Name</span>
        <span className="text-right">Games</span>
        <span>Win / Draw / Loss</span>
        {/* Eval text header has no label — column 4 just carries the signed-pawn number */}
        <span className="hidden sm:block" />
        <span className="hidden sm:block">Eval</span>
      </div>

      {/* Rows */}
      <div>
        {visibleOpenings.map((o, i) => {
          const rowKey = o.opening_eco || o.full_hash || `${o.opening_name}-${i}`;
          return (
            <OpeningRow
              key={rowKey}
              o={o}
              color={color}
              index={i}
              testIdPrefix={testIdPrefix}
              rowKey={rowKey}
              onOpenGames={onOpenGames}
            />
          );
        })}
      </div>

      {/* More/Less toggle */}
      {hasMore && (
        <button
          className="flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground transition-colors mt-2 px-2"
          onClick={() => setExpanded(!expanded)}
          data-testid={`${testIdPrefix}-btn-more`}
          aria-label={expanded ? "Show fewer openings" : `Show ${hiddenCount} more openings`}
        >
          {expanded ? (
            <>
              <ChevronUp className="h-4 w-4" />
              Less
            </>
          ) : (
            <>
              <ChevronDown className="h-4 w-4" />
              {hiddenCount} more
            </>
          )}
        </button>
      )}
    </div>
  );
}
