import * as React from "react"
import { Swords, ChevronDown, ChevronUp } from "lucide-react"
import type { OpeningWDL } from "@/types/stats"
import { MinimapPopover } from "./MinimapPopover"
import { MiniWDLBar } from "./MiniWDLBar"
import { Tooltip } from "@/components/ui/tooltip"
import { InfoPopover } from "@/components/ui/info-popover"
import { MiniBulletChart } from "@/components/charts/MiniBulletChart"
import { ConfidencePill } from "@/components/insights/ConfidencePill"
import {
  EVAL_BULLET_DOMAIN_PAWNS,
  EVAL_NEUTRAL_MAX_PAWNS,
  EVAL_NEUTRAL_MIN_PAWNS,
  EVAL_ENDGAME_BULLET_DOMAIN_PAWNS,
  EVAL_ENDGAME_NEUTRAL_MAX_PAWNS,
  EVAL_ENDGAME_NEUTRAL_MIN_PAWNS,
} from "@/lib/openingStatsZones"
import { formatSignedPct1, formatSignedSeconds } from "@/lib/clockFormat"
import { MIN_GAMES_FOR_RELIABLE_STATS, UNRELIABLE_OPACITY } from "@/lib/theme"

// Number of openings to show before the "More" fold
const INITIAL_VISIBLE_COUNT = 3;

// Phase 80 D-10: column-header tooltip strings.
// MG-entry MUST cite "across analyzed games" because Lichess analyzes only ~66%
// of imported games (bench §3 line 350-355). EG-entry has 99.99% coverage —
// no caveat needed.
export const MG_EVAL_HEADER_TOOLTIP =
  "Average Stockfish evaluation when your middlegame begins, signed from your perspective. " +
  "Computed across analyzed games (Lichess analyses ~66% of imported games).";

export const EG_EVAL_HEADER_TOOLTIP =
  "Average Stockfish evaluation when your endgame begins, signed from your perspective.";

export const CONFIDENCE_HEADER_TOOLTIP =
  "One-sample t-test against zero: high (p<0.05), medium (p<0.10), low otherwise. " +
  "Requires at least 10 games.";

export const CLOCK_DIFF_HEADER_TOOLTIP =
  "Difference between your remaining clock and your opponent's at middlegame entry. " +
  "Shown as percent of base time and absolute seconds. Positive = you have more time.";

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

function OpeningRow({ o, color, index, testIdPrefix, rowKey, onOpenGames, maxTotal }: {
  o: OpeningWDL;
  color: "white" | "black";
  index: number;
  testIdPrefix: string;
  rowKey: string;
  onOpenGames: (opening: OpeningWDL, color: "white" | "black") => void;
  maxTotal: number;
}) {
  const isEvenRow = index % 2 === 0;

  // Phase 80: independent dimming gates for MG and EG (D-01, D-09).
  // A cell is unreliable when eval_n < MIN_GAMES_FOR_RELIABLE_STATS OR
  // confidence === 'low'. The two gates are independent — one phase can be
  // reliable while the other is not.
  const isMgUnreliable =
    (o.eval_n ?? 0) < MIN_GAMES_FOR_RELIABLE_STATS || o.eval_confidence === 'low';
  const isEgUnreliable =
    (o.eval_endgame_n ?? 0) < MIN_GAMES_FOR_RELIABLE_STATS || o.eval_endgame_confidence === 'low';

  // Phase 80: MG bullet chart cell (D-01, D-02).
  // Renders em-dash when eval_n === 0 or avg_eval_pawns is null/undefined.
  const mgBulletContent =
    o.eval_n === 0 || o.avg_eval_pawns === null || o.avg_eval_pawns === undefined ? (
      <span className="text-muted-foreground">—</span>
    ) : (
      <MiniBulletChart
        value={o.avg_eval_pawns}
        ciLow={o.eval_ci_low_pawns ?? undefined}
        ciHigh={o.eval_ci_high_pawns ?? undefined}
        neutralMin={EVAL_NEUTRAL_MIN_PAWNS}
        neutralMax={EVAL_NEUTRAL_MAX_PAWNS}
        domain={EVAL_BULLET_DOMAIN_PAWNS}
        ariaLabel={`Avg eval at MG entry: ${o.avg_eval_pawns.toFixed(2)} pawns`}
      />
    );

  // Phase 80: EG bullet chart cell (D-09).
  // Renders em-dash when eval_endgame_n === 0 or avg_eval_endgame_entry_pawns is null/undefined.
  const egBulletContent =
    o.eval_endgame_n === 0 ||
    o.avg_eval_endgame_entry_pawns === null ||
    o.avg_eval_endgame_entry_pawns === undefined ? (
      <span className="text-muted-foreground">—</span>
    ) : (
      <MiniBulletChart
        value={o.avg_eval_endgame_entry_pawns}
        ciLow={o.eval_endgame_ci_low_pawns ?? undefined}
        ciHigh={o.eval_endgame_ci_high_pawns ?? undefined}
        neutralMin={EVAL_ENDGAME_NEUTRAL_MIN_PAWNS}
        neutralMax={EVAL_ENDGAME_NEUTRAL_MAX_PAWNS}
        domain={EVAL_ENDGAME_BULLET_DOMAIN_PAWNS}
        ariaLabel={`Avg eval at EG entry: ${o.avg_eval_endgame_entry_pawns.toFixed(2)} pawns`}
      />
    );

  // Phase 80: clock-diff cell content (D-05).
  // Renders em-dash when clock_diff_n === 0 or avg_clock_diff_pct is null/undefined.
  const clockDiffContent =
    o.clock_diff_n === 0 ||
    o.avg_clock_diff_pct === null ||
    o.avg_clock_diff_pct === undefined ? (
      <span className="text-muted-foreground">—</span>
    ) : (
      <>
        {formatSignedPct1(o.avg_clock_diff_pct)}
        <span className="text-muted-foreground ml-1">
          ({formatSignedSeconds(o.avg_clock_diff_seconds ?? null)})
        </span>
      </>
    );

  return (
    <div
      data-testid={`${testIdPrefix}-row-${rowKey}`}
    >
      {/* Desktop row: extended grid with 8 columns (name | games | WDL | MG bullet | MG conf | clock-diff | EG bullet | EG conf) */}
      <div
        className={`grid grid-cols-[1fr_auto_minmax(80px,140px)] sm:grid-cols-[minmax(0,1fr)_auto_minmax(120px,200px)_minmax(100px,160px)_auto_minmax(80px,120px)_minmax(100px,160px)_auto] gap-2 items-center rounded px-2 py-1.5 hover:bg-white/5 transition-colors ${isEvenRow ? 'bg-white/[0.02]' : ''}`}
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
            className="flex items-center gap-1 text-sm text-brand-brown-light hover:text-brand-brown-highlight transition-colors"
            aria-label={`View ${o.total} games for ${o.opening_name}`}
            data-testid={`${testIdPrefix}-games-${rowKey}`}
            onClick={() => onOpenGames(o, color)}
          >
            <span className="tabular-nums">{o.total}</span>
            <Swords className="h-3.5 w-3.5" />
          </button>
        </Tooltip>

        {/* Column 3: Mini WDL bar + proportional frequency bar below */}
        <div>
          <MiniWDLBar win_pct={o.win_pct} draw_pct={o.draw_pct} loss_pct={o.loss_pct} />
          <div className="h-2 mt-0.5">
            <div
              className="h-full rounded-sm"
              style={{
                width: maxTotal > 0 ? `${(o.total / maxTotal) * 100}%` : '0%',
                border: '1px solid oklch(0.6 0 0)',
                backgroundColor: 'transparent',
              }}
              data-testid={`${testIdPrefix}-freq-${rowKey}`}
            />
          </div>
        </div>

        {/* Column 4: MG bullet chart (desktop only) */}
        <div
          className="hidden sm:block text-right tabular-nums"
          data-testid={`${testIdPrefix}-bullet-${rowKey}`}
          style={isMgUnreliable ? { opacity: UNRELIABLE_OPACITY } : undefined}
        >
          {mgBulletContent}
        </div>

        {/* Column 5: MG confidence pill (desktop only) */}
        <div
          className="hidden sm:flex items-center"
          data-testid={`${testIdPrefix}-confidence-${rowKey}`}
        >
          <ConfidencePill
            level={o.eval_confidence}
            pValue={o.eval_p_value}
            gameCount={o.eval_n}
            testId={`${testIdPrefix}-confidence-${rowKey}-info`}
          />
        </div>

        {/* Column 6: Clock diff at MG entry (desktop only) */}
        <div
          className="hidden sm:block text-right text-sm tabular-nums"
          data-testid={`${testIdPrefix}-clock-diff-${rowKey}`}
        >
          {clockDiffContent}
        </div>

        {/* Column 7: EG bullet chart (desktop only) */}
        <div
          className="hidden sm:block text-right tabular-nums"
          data-testid={`${testIdPrefix}-eg-bullet-${rowKey}`}
          style={isEgUnreliable ? { opacity: UNRELIABLE_OPACITY } : undefined}
        >
          {egBulletContent}
        </div>

        {/* Column 8: EG confidence pill (desktop only) */}
        <div
          className="hidden sm:flex items-center"
          data-testid={`${testIdPrefix}-eg-confidence-${rowKey}`}
        >
          <ConfidencePill
            level={o.eval_endgame_confidence}
            pValue={o.eval_endgame_p_value}
            gameCount={o.eval_endgame_n}
            testId={`${testIdPrefix}-eg-confidence-${rowKey}-info`}
          />
        </div>
      </div>

      {/* Mobile line 2: MG-entry triple (D-06).
          Grid: [label | bullet | confidence | clock-diff] */}
      <div
        className="sm:hidden mt-2 grid grid-cols-[auto_1fr_auto_auto] gap-2 items-center px-2"
        data-testid={`${testIdPrefix}-mobile-mg-line-${rowKey}`}
      >
        <span className="text-xs text-muted-foreground">MG entry</span>
        <div
          data-testid={`${testIdPrefix}-bullet-mobile-${rowKey}`}
          style={isMgUnreliable ? { opacity: UNRELIABLE_OPACITY } : undefined}
        >
          {mgBulletContent}
        </div>
        <div data-testid={`${testIdPrefix}-confidence-mobile-${rowKey}`}>
          <ConfidencePill
            level={o.eval_confidence}
            pValue={o.eval_p_value}
            gameCount={o.eval_n}
          />
        </div>
        <div
          data-testid={`${testIdPrefix}-clock-diff-mobile-${rowKey}`}
          className="text-right text-sm tabular-nums"
        >
          {clockDiffContent}
        </div>
      </div>

      {/* Mobile line 3: EG-entry pair (D-06).
          Grid: [label | bullet | confidence] */}
      <div
        className="sm:hidden mt-1 grid grid-cols-[auto_1fr_auto] gap-2 items-center px-2 pb-1.5"
        data-testid={`${testIdPrefix}-mobile-eg-line-${rowKey}`}
      >
        <span className="text-xs text-muted-foreground">EG entry</span>
        <div
          data-testid={`${testIdPrefix}-eg-bullet-mobile-${rowKey}`}
          style={isEgUnreliable ? { opacity: UNRELIABLE_OPACITY } : undefined}
        >
          {egBulletContent}
        </div>
        <div data-testid={`${testIdPrefix}-eg-confidence-mobile-${rowKey}`}>
          <ConfidencePill
            level={o.eval_endgame_confidence}
            pValue={o.eval_endgame_p_value}
            gameCount={o.eval_endgame_n}
          />
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

  // maxTotal spans ALL openings so frequency bar widths are comparable across
  // the collapse/expand toggle (matches MobileMostPlayedRows behavior).
  const maxTotal = Math.max(...openings.map((o) => o.total));

  return (
    <div data-testid={`${testIdPrefix}-table`}>
      {/* Table header — desktop shows 8 columns, mobile shows 3 */}
      <div className="grid grid-cols-[1fr_auto_minmax(80px,140px)] sm:grid-cols-[minmax(0,1fr)_auto_minmax(120px,200px)_minmax(100px,160px)_auto_minmax(80px,120px)_minmax(100px,160px)_auto] gap-2 px-2 pb-1 text-xs text-muted-foreground border-b border-white/10 mb-1">
        <span>Name</span>
        <span>Games</span>
        <span>Win / Draw / Loss</span>
        {/* Phase 80 new column headers — desktop only */}
        <span className="hidden sm:flex items-center gap-1">
          MG entry
          <InfoPopover
            ariaLabel="MG entry eval info"
            testId="opening-stats-mg-eval-info"
            side="top"
          >
            <p>{MG_EVAL_HEADER_TOOLTIP}</p>
          </InfoPopover>
        </span>
        <span className="hidden sm:flex items-center gap-1">
          MG conf.
          <InfoPopover
            ariaLabel="MG confidence info"
            testId="opening-stats-mg-confidence-info"
            side="top"
          >
            <p>{CONFIDENCE_HEADER_TOOLTIP}</p>
          </InfoPopover>
        </span>
        <span className="hidden sm:flex items-center gap-1">
          MG clock
          <InfoPopover
            ariaLabel="MG clock diff info"
            testId="opening-stats-clock-diff-info"
            side="top"
          >
            <p>{CLOCK_DIFF_HEADER_TOOLTIP}</p>
          </InfoPopover>
        </span>
        <span className="hidden sm:flex items-center gap-1">
          EG entry
          <InfoPopover
            ariaLabel="EG entry eval info"
            testId="opening-stats-eg-eval-info"
            side="top"
          >
            <p>{EG_EVAL_HEADER_TOOLTIP}</p>
          </InfoPopover>
        </span>
        <span className="hidden sm:flex items-center gap-1">
          EG conf.
          <InfoPopover
            ariaLabel="EG confidence info"
            testId="opening-stats-eg-confidence-info"
            side="top"
          >
            <p>{CONFIDENCE_HEADER_TOOLTIP}</p>
          </InfoPopover>
        </span>
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
              maxTotal={maxTotal}
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
